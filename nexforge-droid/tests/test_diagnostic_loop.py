"""Comprehensive unit tests for TracebackParser, DiagnosticReasoner, TestRunner, DiagnosticLoopController, and Diagnostic Tools."""

import os
import shutil
import tempfile
import unittest
from typing import Any, Dict

from app.diagnostics.diagnostic_loop_controller import (
    DiagnosticLoopController,
    TerminationGuardReason,
)
from app.diagnostics.diagnostic_reasoner import (
    DiagnosisHypothesis,
    DiagnosticReasoner,
)
from app.diagnostics.test_runner import TestRunner
from app.diagnostics.traceback_parser import (
    FailureCategory,
    ParsedFailure,
    StackFrame,
    TestExecutionReport,
    TracebackParser,
)
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor
from app.tools import get_default_tool_registry


class TestTracebackParser(unittest.TestCase):
    """Test suite for TracebackParser."""

    def test_parse_python_traceback_multiframe(self) -> None:
        """Verify parsing standard Python tracebacks with multiple stack frames."""
        tb_text = """Traceback (most recent call last):
  File "/workspace/app/math/calc.py", line 42, in compute_rate
    return numerator / denominator
  File "/workspace/app/engine.py", line 88, in process_batch
    rate = compute_rate(100, 0)
ZeroDivisionError: division by zero
"""
        failures = TracebackParser.parse_python_traceback(tb_text)
        self.assertEqual(len(failures), 1)
        f = failures[0]
        self.assertEqual(f.error_type, "ZeroDivisionError")
        self.assertEqual(f.error_message, "division by zero")
        self.assertEqual(f.category, FailureCategory.ZERO_DIVISION)
        self.assertEqual(len(f.frames), 2)

        # Check innermost workspace frame
        self.assertIsNotNone(f.innermost_frame)
        self.assertEqual(f.innermost_frame.line_number, 88)
        self.assertEqual(f.innermost_frame.function_name, "process_batch")

    def test_parse_error_categories(self) -> None:
        """Verify proper categorization across common exceptions."""
        self.assertEqual(
            TracebackParser.categorize_error("AssertionError", "Expected 10 but got 20"),
            FailureCategory.ASSERTION_ERROR,
        )
        self.assertEqual(
            TracebackParser.categorize_error("TypeError", "can only concatenate str (not 'int') to str"),
            FailureCategory.TYPE_ERROR,
        )
        self.assertEqual(
            TracebackParser.categorize_error("IndexError", "list index out of range"),
            FailureCategory.INDEX_ERROR,
        )
        self.assertEqual(
            TracebackParser.categorize_error("KeyError", "'session_token'"),
            FailureCategory.KEY_ERROR,
        )
        self.assertEqual(
            TracebackParser.categorize_error("AttributeError", "'NoneType' object has no attribute 'get'"),
            FailureCategory.ATTRIBUTE_ERROR,
        )

    def test_parse_unittest_stdout_and_stderr(self) -> None:
        """Verify unittest stdout/stderr parsing for both clean runs and failures."""
        # 1. Clean run
        ok_report = TracebackParser.parse_unittest_output(
            stdout="",
            stderr="Ran 12 tests in 0.045s\n\nOK\n",
            exit_code=0,
        )
        self.assertTrue(ok_report.all_passed)
        self.assertEqual(ok_report.total_tests, 12)
        self.assertEqual(ok_report.passed_count, 12)
        self.assertEqual(ok_report.failed_count, 0)

        # 2. Failed run with traceback
        fail_stderr = """======================================================================
FAIL: test_divide (tests.test_math.TestMath)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/tests/test_math.py", line 15, in test_divide
    self.assertEqual(divide(10, 2), 5)
AssertionError: 4 != 5

======================================================================
ERROR: test_crash (tests.test_math.TestMath)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/workspace/tests/test_math.py", line 22, in test_crash
    divide(10, 0)
ZeroDivisionError: division by zero

----------------------------------------------------------------------
Ran 8 tests in 0.021s

FAILED (failures=1, errors=1)
"""
        fail_report = TracebackParser.parse_unittest_output(
            stdout="",
            stderr=fail_stderr,
            exit_code=1,
        )
        self.assertFalse(fail_report.all_passed)
        self.assertEqual(fail_report.total_tests, 8)
        self.assertEqual(fail_report.failed_count, 1)
        self.assertEqual(fail_report.error_count, 1)
        self.assertEqual(len(fail_report.failures), 2)
        self.assertIn("test_divide", fail_report.failures[0].test_name)
        self.assertIn("test_crash", fail_report.failures[1].test_name)

    def test_parse_javascript_stack(self) -> None:
        """Verify JavaScript/TypeScript error stack trace extraction."""
        js_stack = """TypeError: Cannot read property 'id' of undefined
    at verifyAuth (/workspace/src/auth.ts:45:12)
    at handleRequest (/workspace/src/server.ts:102:5)
    at processTicksAndRejections (internal/process/task_queues.js:95:5)"""

        failures = TracebackParser.parse_javascript_stack(js_stack)
        self.assertEqual(len(failures), 1)
        f = failures[0]
        self.assertEqual(f.error_type, "TypeError")
        self.assertEqual(f.category, FailureCategory.TYPE_ERROR)
        self.assertIsNotNone(f.innermost_frame)
        self.assertEqual(f.innermost_frame.function_name, "verifyAuth")
        self.assertEqual(f.innermost_frame.line_number, 45)


class TestDiagnosticReasoner(unittest.TestCase):
    """Test suite for DiagnosticReasoner."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="nexforge_diag_test_")
        self.sample_file = os.path.join(self.test_dir, "calculator.py")
        with open(self.sample_file, "w", encoding="utf-8") as f:
            f.write(
                "def calculate_ratio(val_a: float, val_b: float) -> float:\n"
                "    # Compute ratio\n"
                "    ratio = val_a / val_b\n"
                "    return ratio\n"
            )

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_extract_context_and_diagnose(self) -> None:
        """Verify source correlation, context extraction, and hypothesis formulation."""
        reasoner = DiagnosticReasoner(workspace_root=self.test_dir)

        failure = ParsedFailure(
            test_name="test_calculate_ratio_zero",
            error_type="ZeroDivisionError",
            error_message="division by zero",
            frames=[
                StackFrame(
                    file_path=self.sample_file,
                    line_number=3,
                    function_name="calculate_ratio",
                    code_snippet="ratio = val_a / val_b",
                    is_workspace_file=True,
                )
            ],
            innermost_frame=StackFrame(
                file_path=self.sample_file,
                line_number=3,
                function_name="calculate_ratio",
                code_snippet="ratio = val_a / val_b",
                is_workspace_file=True,
            ),
            category=FailureCategory.ZERO_DIVISION,
            raw_traceback="ZeroDivisionError: division by zero",
        )

        hyp = reasoner.analyze_failure(failure)
        self.assertEqual(hyp.category, FailureCategory.ZERO_DIVISION.value)
        self.assertEqual(hyp.target_line, 3)
        self.assertEqual(hyp.suggested_fix_strategy, "ZERO_DIVISION_GUARD")
        self.assertGreaterEqual(hyp.confidence_score, 0.8)
        self.assertIn("ratio = val_a / val_b", hyp.code_context)
        self.assertIn("val_b", hyp.suspect_symbols)

        # Verify patch proposal generation
        proposal = reasoner.generate_targeted_patch_proposal(hyp)
        self.assertEqual(proposal["strategy"], "ZERO_DIVISION_GUARD")
        self.assertEqual(proposal["target_line"], 3)


class TestDiagnosticLoopController(unittest.TestCase):
    """Test suite for DiagnosticLoopController and loop termination guards."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="nexforge_loop_test_")
        self.source_file = os.path.join(self.test_dir, "service.py")
        with open(self.source_file, "w", encoding="utf-8") as f:
            f.write("def divide_scores(a: int, b: int) -> float:\n    return a / b\n")

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_successful_repair_loop(self) -> None:
        """Verify full test-observe-patch-retest resolution in controller."""
        # Mock test runner that transitions from fail to pass once file is fixed
        class MockRunner(TestRunner):
            def __init__(self, src_file: str) -> None:
                self.src_file = src_file
                self.call_count = 0

            def run_command(self, command: str, cwd: Any = None, timeout_seconds: float = 30.0) -> TestExecutionReport:
                self.call_count += 1
                with open(self.src_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if "b != 0" in content:
                    return TestExecutionReport(
                        total_tests=3, passed_count=3, failed_count=0, all_passed=True, exit_code=0
                    )
                else:
                    return TestExecutionReport(
                        total_tests=3,
                        passed_count=2,
                        failed_count=1,
                        all_passed=False,
                        exit_code=1,
                        failures=[
                            ParsedFailure(
                                test_name="test_divide_scores_zero",
                                error_type="ZeroDivisionError",
                                error_message="division by zero",
                                frames=[
                                    StackFrame(
                                        file_path=self.src_file,
                                        line_number=2,
                                        function_name="divide_scores",
                                        code_snippet="return a / b",
                                        is_workspace_file=True,
                                    )
                                ],
                                innermost_frame=StackFrame(
                                    file_path=self.src_file,
                                    line_number=2,
                                    function_name="divide_scores",
                                    code_snippet="return a / b",
                                    is_workspace_file=True,
                                ),
                                category=FailureCategory.ZERO_DIVISION,
                            )
                        ],
                    )

        runner = MockRunner(self.source_file)
        controller = DiagnosticLoopController(workspace_root=self.test_dir, test_runner=runner)

        # Custom patch provider for explicit surgical replacement
        def custom_fix(hyp: DiagnosisHypothesis) -> Dict[str, str]:
            return {
                "target_content": "    return a / b",
                "replacement_content": "    return a / b if b != 0 else 0.0",
            }

        res = controller.execute_loop(
            test_command="pytest",
            max_iterations=3,
            custom_patch_provider=custom_fix,
        )

        self.assertTrue(res.success)
        self.assertEqual(res.termination_reason, TerminationGuardReason.RESOLVED)
        self.assertGreaterEqual(res.snapshots_taken, 1)
        self.assertEqual(res.rollbacks_triggered, 0)

        # Check patched file on disk
        with open(self.source_file, "r", encoding="utf-8") as f:
            self.assertIn("b != 0", f.read())

    def test_oscillation_guard_termination(self) -> None:
        """Verify oscillation detector terminates loop when error signatures repeat in cycle."""
        class OscillatingRunner(TestRunner):
            def __init__(self) -> None:
                self.calls = 0

            def run_command(self, command: str, cwd: Any = None, timeout_seconds: float = 30.0) -> TestExecutionReport:
                self.calls += 1
                err = "TypeError" if self.calls % 2 == 1 else "ValueError"
                return TestExecutionReport(
                    total_tests=2,
                    passed_count=1,
                    failed_count=1,
                    all_passed=False,
                    exit_code=1,
                    failures=[
                        ParsedFailure(
                            test_name="test_oscillation",
                            error_type=err,
                            error_message="cyclic fault",
                            frames=[StackFrame(file_path="service.py", line_number=2, is_workspace_file=True)],
                            innermost_frame=StackFrame(file_path="service.py", line_number=2, is_workspace_file=True),
                            category=FailureCategory.TYPE_ERROR,
                        )
                    ],
                )

        controller = DiagnosticLoopController(
            workspace_root=self.test_dir,
            test_runner=OscillatingRunner(),
        )

        def toggle_patch(hyp: DiagnosisHypothesis) -> Dict[str, str]:
            return {
                "target_content": "def divide_scores",
                "replacement_content": "def divide_scores",
            }

        res = controller.execute_loop(
            test_command="pytest",
            max_iterations=6,
            custom_patch_provider=toggle_patch,
        )
        self.assertFalse(res.success)
        self.assertEqual(res.termination_reason, TerminationGuardReason.OSCILLATION_DETECTED)
        self.assertIn("Oscillation detected", res.summary)

    def test_regression_guard_and_automatic_rollback(self) -> None:
        """Verify regression guard triggers atomic snapshot rollback when a patch worsens test outcomes."""
        class RegressingRunner(TestRunner):
            def __init__(self) -> None:
                self.calls = 0

            def run_command(self, command: str, cwd: Any = None, timeout_seconds: float = 30.0) -> TestExecutionReport:
                self.calls += 1
                if self.calls == 1:
                    # Initial run: 1 failure
                    return TestExecutionReport(
                        total_tests=5,
                        passed_count=4,
                        failed_count=1,
                        all_passed=False,
                        exit_code=1,
                        failures=[
                            ParsedFailure(
                                test_name="test_original_bug",
                                error_type="IndexError",
                                error_message="list index out of range",
                                frames=[StackFrame(file_path="service.py", line_number=1, is_workspace_file=True)],
                                innermost_frame=StackFrame(file_path="service.py", line_number=1, is_workspace_file=True),
                                category=FailureCategory.INDEX_ERROR,
                            )
                        ],
                    )
                else:
                    # Patch caused regression: 3 failures now!
                    return TestExecutionReport(
                        total_tests=5,
                        passed_count=2,
                        failed_count=3,
                        all_passed=False,
                        exit_code=1,
                        failures=[
                            ParsedFailure(
                                test_name="test_regression_1",
                                error_type="TypeError",
                                error_message="broke everything",
                                frames=[StackFrame(file_path="service.py", line_number=1, is_workspace_file=True)],
                                innermost_frame=StackFrame(file_path="service.py", line_number=1, is_workspace_file=True),
                                category=FailureCategory.TYPE_ERROR,
                            )
                        ],
                    )

        with open(self.source_file, "r", encoding="utf-8") as f:
            initial_content = f.read()

        controller = DiagnosticLoopController(
            workspace_root=self.test_dir,
            test_runner=RegressingRunner(),
        )

        def bad_patch(hyp: DiagnosisHypothesis) -> Dict[str, str]:
            return {
                "target_content": "def divide_scores",
                "replacement_content": "def divide_scores_broken",
            }

        res = controller.execute_loop(
            test_command="pytest",
            max_iterations=3,
            auto_rollback_on_regression=True,
            custom_patch_provider=bad_patch,
        )

        self.assertFalse(res.success)
        self.assertEqual(res.termination_reason, TerminationGuardReason.REGRESSION_ABORT)
        self.assertEqual(res.rollbacks_triggered, 1)

        # Ensure file was restored back to pristine initial content
        with open(self.source_file, "r", encoding="utf-8") as f:
            restored_content = f.read()
        self.assertEqual(restored_content, initial_content)


class TestDiagnosticToolsRegistry(unittest.TestCase):
    """Test suite verifying ToolRegistry integration for diagnostic tools."""

    def setUp(self) -> None:
        self.registry = get_default_tool_registry()

    def test_registered_diagnostic_tools(self) -> None:
        """Verify run_diagnostics, diagnose_test_failure, and auto_fix_loop are registered."""
        tool_names = [t.name for t in self.registry.list_tools()]
        self.assertIn("run_diagnostics", tool_names)
        self.assertIn("diagnose_test_failure", tool_names)
        self.assertIn("auto_fix_loop", tool_names)

    def test_dispatch_diagnose_tool(self) -> None:
        """Verify diagnose_test_failure dispatches and parses traceback text."""
        sample_tb = """Traceback (most recent call last):
  File "app/utils.py", line 12, in parse_int
    return int(val)
ValueError: invalid literal for int() with base 10: 'abc'
"""
        res = self.registry.dispatch(
            "diagnose_test_failure",
            {"traceback_text": sample_tb, "test_name": "test_parse_int"},
        )
        self.assertTrue(res.success)
        self.assertIn("hypotheses", res.data)
        hyp = res.data["hypotheses"][0]
        self.assertEqual(hyp["error_type"], "ValueError")
        self.assertEqual(hyp["target_line"], 12)


if __name__ == "__main__":
    unittest.main()

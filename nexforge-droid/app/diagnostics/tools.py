"""LLM Diagnostic Tools for automated test execution, failure diagnosis, and repair loops."""

import json
from typing import Any, Dict, Optional

from app.diagnostics.diagnostic_loop_controller import DiagnosticLoopController
from app.diagnostics.diagnostic_reasoner import DiagnosticReasoner
from app.diagnostics.test_runner import TestRunner
from app.diagnostics.traceback_parser import ParsedFailure, TracebackParser
from app.tools.base import Tool, ToolResult


class RunDiagnosticsTool(Tool):
    """Tool for running test suites and extracting structured diagnostic failure reports."""

    name = "run_diagnostics"
    description = (
        "Executes a test command (e.g., 'python3 -m unittest discover' or 'pytest') "
        "and returns structured failure reports with parsed stack frames, line numbers, and error classifications."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "test_command": {
                "type": "string",
                "description": "Shell command to execute tests (e.g. 'python3 -m unittest discover -s ./tests').",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for test execution.",
            },
            "timeout_seconds": {
                "type": "number",
                "description": "Maximum execution time before timeout (default 30s).",
            },
        },
        "required": ["test_command"],
    }

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = workspace_root
        self.runner = TestRunner(workspace_root=workspace_root)

    def execute(self, **kwargs: Any) -> ToolResult:
        test_command = kwargs.get("test_command", "")
        cwd = kwargs.get("cwd")
        timeout_seconds = float(kwargs.get("timeout_seconds", 30.0))

        if not test_command:
            return ToolResult(success=False, error="Missing required argument 'test_command'.")

        try:
            report = self.runner.run_command(
                test_command, cwd=cwd, timeout_seconds=timeout_seconds
            )
            return ToolResult(
                success=True,
                data=report.to_dict(),
                metadata={
                    "all_passed": report.all_passed,
                    "total_tests": report.total_tests,
                    "failed_count": report.failed_count,
                    "error_count": report.error_count,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Diagnostic test execution failed: {str(e)}")


class DiagnoseTestFailureTool(Tool):
    """Tool for analyzing a traceback or test failure against workspace source files."""

    name = "diagnose_test_failure"
    description = (
        "Analyzes a test failure or raw traceback, inspects the source code surrounding the failure lines, "
        "and synthesizes a root-cause hypothesis and surgical fix strategy."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "traceback_text": {
                "type": "string",
                "description": "Raw traceback or test failure text to analyze.",
            },
            "test_name": {
                "type": "string",
                "description": "Optional name of failing test.",
            },
            "file_path": {
                "type": "string",
                "description": "Optional explicit file path where error occurred.",
            },
            "line_number": {
                "type": "integer",
                "description": "Optional explicit line number where error occurred.",
            },
        },
        "required": ["traceback_text"],
    }

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = workspace_root
        self.reasoner = DiagnosticReasoner(workspace_root=workspace_root)

    def execute(self, **kwargs: Any) -> ToolResult:
        traceback_text = kwargs.get("traceback_text", "")
        test_name = kwargs.get("test_name", "manual_diagnostic")
        file_path = kwargs.get("file_path")
        line_number = kwargs.get("line_number")

        if not traceback_text:
            return ToolResult(success=False, error="Missing required argument 'traceback_text'.")

        try:
            parsed_list = TracebackParser.parse_python_traceback(
                traceback_text, workspace_root=self.workspace_root
            )

            if not parsed_list and file_path and line_number:
                # Construct synthetic failure
                from app.diagnostics.traceback_parser import FailureCategory, StackFrame
                synthetic = ParsedFailure(
                    test_name=test_name,
                    error_type="CustomDiagnostic",
                    error_message=traceback_text.split("\n")[-1],
                    frames=[
                        StackFrame(
                            file_path=file_path,
                            line_number=line_number,
                            is_workspace_file=True,
                        )
                    ],
                    innermost_frame=StackFrame(
                        file_path=file_path,
                        line_number=line_number,
                        is_workspace_file=True,
                    ),
                    category=FailureCategory.UNKNOWN,
                    raw_traceback=traceback_text,
                )
                parsed_list = [synthetic]

            if not parsed_list:
                return ToolResult(
                    success=False,
                    error="Unable to parse stack frames or error type from provided traceback text.",
                )

            hypotheses = [self.reasoner.analyze_failure(f) for f in parsed_list]
            return ToolResult(
                success=True,
                data={
                    "total_failures_parsed": len(parsed_list),
                    "hypotheses": [h.to_dict() for h in hypotheses],
                },
                metadata={"primary_file": hypotheses[0].primary_file if hypotheses else None},
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failure diagnosis failed: {str(e)}")


class AutoFixLoopTool(Tool):
    """Tool for running the autonomous Test-Observe-Diagnose-Fix-ReTest loop."""

    name = "auto_fix_loop"
    description = (
        "Runs an autonomous closed-loop repair cycle: executes tests, diagnoses failures, "
        "applies surgical patches, verifies syntax, and re-tests with oscillation and regression rollback guards."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "test_command": {
                "type": "string",
                "description": "Shell command to run test suite (e.g. 'python3 -m unittest discover -s ./tests').",
            },
            "max_iterations": {
                "type": "integer",
                "description": "Maximum number of fix-test iterations (default 4).",
            },
            "auto_rollback": {
                "type": "boolean",
                "description": "Whether to automatically rollback to snapshot if regression is detected (default true).",
            },
        },
        "required": ["test_command"],
    }

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = workspace_root
        self.controller = DiagnosticLoopController(workspace_root=workspace_root)

    def execute(self, **kwargs: Any) -> ToolResult:
        test_command = kwargs.get("test_command", "")
        max_iterations = int(kwargs.get("max_iterations", 4))
        auto_rollback = bool(kwargs.get("auto_rollback", True))

        if not test_command:
            return ToolResult(success=False, error="Missing required argument 'test_command'.")

        try:
            result = self.controller.execute_loop(
                test_command=test_command,
                max_iterations=max_iterations,
                auto_rollback_on_regression=auto_rollback,
            )

            return ToolResult(
                success=result.success,
                data=result.to_dict(),
                metadata={
                    "termination_reason": result.termination_reason.value,
                    "total_iterations": result.total_iterations,
                    "snapshots_taken": result.snapshots_taken,
                    "rollbacks_triggered": result.rollbacks_triggered,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Autonomous fix loop failed: {str(e)}")

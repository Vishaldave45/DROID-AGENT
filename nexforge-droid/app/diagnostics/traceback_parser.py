"""Traceback Parsing, Stack Frame Extraction, and Test Execution Output Normalization."""

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FailureCategory(str, Enum):
    """Categorized root failure classification."""

    ASSERTION_ERROR = "ASSERTION_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    VALUE_ERROR = "VALUE_ERROR"
    INDEX_ERROR = "INDEX_ERROR"
    KEY_ERROR = "KEY_ERROR"
    ATTRIBUTE_ERROR = "ATTRIBUTE_ERROR"
    IMPORT_ERROR = "IMPORT_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    ZERO_DIVISION = "ZERO_DIVISION"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    UNHANDLED_EXCEPTION = "UNHANDLED_EXCEPTION"
    UNKNOWN = "UNKNOWN"


@dataclass
class StackFrame:
    """Individual stack execution frame in a diagnostic traceback."""

    file_path: str
    line_number: int
    column_number: Optional[int] = None
    function_name: str = "<unknown>"
    code_snippet: str = ""
    is_workspace_file: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "function_name": self.function_name,
            "code_snippet": self.code_snippet,
            "is_workspace_file": self.is_workspace_file,
        }


@dataclass
class ParsedFailure:
    """Structured extraction of a test or runtime execution failure."""

    test_name: str
    error_type: str
    error_message: str
    frames: List[StackFrame] = field(default_factory=list)
    innermost_frame: Optional[StackFrame] = None
    category: FailureCategory = FailureCategory.UNKNOWN
    raw_traceback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "category": self.category.value if isinstance(self.category, FailureCategory) else str(self.category),
            "frames": [f.to_dict() for f in self.frames],
            "innermost_frame": self.innermost_frame.to_dict() if self.innermost_frame else None,
            "raw_traceback": self.raw_traceback,
        }


@dataclass
class TestExecutionReport:
    """Aggregated report of test suite execution."""

    total_tests: int = 0
    passed_count: int = 0
    failed_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    duration_seconds: float = 0.0
    failures: List[ParsedFailure] = field(default_factory=list)
    raw_stdout: str = ""
    raw_stderr: str = ""
    exit_code: int = 0
    all_passed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "error_count": self.error_count,
            "skipped_count": self.skipped_count,
            "duration_seconds": round(self.duration_seconds, 4),
            "all_passed": self.all_passed,
            "exit_code": self.exit_code,
            "failures": [f.to_dict() for f in self.failures],
            "raw_stdout": self.raw_stdout,
            "raw_stderr": self.raw_stderr,
        }


class TracebackParser:
    """Robust parser for Python unittest/pytest, JS/TS stacks, and raw tracebacks."""

    # Regex patterns for Python stack frames: File "/path/to/file.py", line 42, in my_func
    PY_FRAME_PATTERN = re.compile(
        r'File\s+["\'](?P<file>[^"\']+)["\'],\s+line\s+(?P<line>\d+)(?:,\s+in\s+(?P<func>[^\n]+))?'
    )

    # JS/TS stack frame: at Function (path/to/file.ts:42:15) or at path/to/file.js:42:15
    JS_FRAME_PATTERN = re.compile(
        r'at\s+(?:(?P<func>[^\s(]+)\s+\()?(?P<file>[^\s():]+):(?P<line>\d+)(?::(?P<col>\d+))?\)?'
    )

    # Python Unittest test header: FAIL: test_calc (tests.test_math.TestMath)
    UNITTEST_HEADER_PATTERN = re.compile(
        r'^(?:FAIL|ERROR):\s+(?P<test>[^\s(]+)(?:\s+\((?P<class>[^)]+)\))?',
        re.MULTILINE,
    )

    @classmethod
    def categorize_error(cls, error_type: str, error_msg: str) -> FailureCategory:
        """Classify error into actionable failure category."""
        type_upper = error_type.upper()
        msg_lower = error_msg.lower()

        if "ASSERTION" in type_upper or "ASSERT" in type_upper:
            return FailureCategory.ASSERTION_ERROR
        if "TYPE" in type_upper or "TYPEERROR" in type_upper:
            return FailureCategory.TYPE_ERROR
        if "VALUE" in type_upper or "VALUEERROR" in type_upper:
            return FailureCategory.VALUE_ERROR
        if "INDEX" in type_upper or "INDEXERROR" in type_upper or "out of range" in msg_lower:
            return FailureCategory.INDEX_ERROR
        if "KEY" in type_upper or "KEYERROR" in type_upper:
            return FailureCategory.KEY_ERROR
        if "ATTRIBUTE" in type_upper or "ATTRIBUTEERROR" in type_upper:
            return FailureCategory.ATTRIBUTE_ERROR
        if "IMPORT" in type_upper or "MODULE" in type_upper or "MODULENOTFOUND" in type_upper:
            return FailureCategory.IMPORT_ERROR
        if "SYNTAX" in type_upper or "INDENTATION" in type_upper:
            return FailureCategory.SYNTAX_ERROR
        if "ZERODIVISION" in type_upper or "division by zero" in msg_lower:
            return FailureCategory.ZERO_DIVISION
        if "TIMEOUT" in type_upper or "timed out" in msg_lower:
            return FailureCategory.TIMEOUT_ERROR
        if "RUNTIME" in type_upper or "RUNTIMEERROR" in type_upper:
            return FailureCategory.RUNTIME_ERROR

        return FailureCategory.UNHANDLED_EXCEPTION

    @classmethod
    def parse_python_traceback(
        cls, traceback_text: str, workspace_root: Optional[str] = None
    ) -> List[ParsedFailure]:
        """Extracts structured stack frames and error types from standard Python traceback text."""
        if not traceback_text or not traceback_text.strip():
            return []

        failures: List[ParsedFailure] = []
        # Split multiple tracebacks if formatted in sequence
        chunks = re.split(r"(?:={10,}|-{10,}|Traceback \(most recent call last\):)", traceback_text)

        for chunk in chunks:
            if not chunk.strip():
                continue

            lines = chunk.strip().split("\n")
            frames: List[StackFrame] = []
            error_type = "Exception"
            error_msg = ""

            i = 0
            while i < len(lines):
                line = lines[i]
                match = cls.PY_FRAME_PATTERN.search(line)
                if match:
                    file_path = match.group("file")
                    line_num = int(match.group("line"))
                    func_name = match.group("func") or "<module>"
                    code_snippet = ""
                    # Check next line for code snippet
                    if i + 1 < len(lines) and not cls.PY_FRAME_PATTERN.search(lines[i + 1]) and not lines[i + 1].startswith("Traceback"):
                        code_snippet = lines[i + 1].strip()
                        i += 1

                    is_ws = True
                    if "/site-packages/" in file_path or "/dist-packages/" in file_path or "/usr/lib/" in file_path:
                        is_ws = False
                    elif workspace_root and not file_path.startswith(workspace_root) and not file_path.startswith("./"):
                        is_ws = False

                    frames.append(
                        StackFrame(
                            file_path=file_path,
                            line_number=line_num,
                            function_name=func_name.strip(),
                            code_snippet=code_snippet,
                            is_workspace_file=is_ws,
                        )
                    )
                else:
                    # Check for exception line: "ZeroDivisionError: division by zero"
                    err_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)$", line)
                    if err_match:
                        error_type = err_match.group(1)
                        error_msg = err_match.group(2)
                    elif line.startswith("AssertionError"):
                        error_type = "AssertionError"
                        error_msg = line[len("AssertionError:") :].strip()

                i += 1

            if frames or error_msg or error_type != "Exception":
                innermost = None
                ws_frames = [f for f in frames if f.is_workspace_file]
                if ws_frames:
                    innermost = ws_frames[-1]
                elif frames:
                    innermost = frames[-1]

                category = cls.categorize_error(error_type, error_msg)

                failures.append(
                    ParsedFailure(
                        test_name=innermost.function_name if innermost else "runtime_execution",
                        error_type=error_type,
                        error_message=error_msg,
                        frames=frames,
                        innermost_frame=innermost,
                        category=category,
                        raw_traceback=chunk.strip(),
                    )
                )

        return failures

    @classmethod
    def parse_unittest_output(
        cls,
        stdout: str,
        stderr: str,
        exit_code: int = 0,
        workspace_root: Optional[str] = None,
    ) -> TestExecutionReport:
        """Parses stdout and stderr from python3 -m unittest into a TestExecutionReport."""
        combined = f"{stdout}\n{stderr}"
        report = TestExecutionReport(raw_stdout=stdout, raw_stderr=stderr, exit_code=exit_code)

        # 1. Parse summary line: "Ran 12 tests in 0.045s"
        ran_match = re.search(r"Ran\s+(\d+)\s+tests?\s+in\s+([\d\.]+)s", combined)
        if ran_match:
            report.total_tests = int(ran_match.group(1))
            report.duration_seconds = float(ran_match.group(2))

        # 2. Check OK or FAILED
        if "OK" in combined and exit_code == 0 and "FAILED" not in combined:
            report.all_passed = True
            report.passed_count = report.total_tests
            return report

        # 3. Parse FAILED summary: "FAILED (failures=2, errors=1, skipped=1)"
        failed_match = re.search(r"FAILED\s*\(([^)]+)\)", combined)
        if failed_match:
            details_str = failed_match.group(1)
            for part in details_str.split(","):
                part = part.strip()
                if "failures=" in part:
                    report.failed_count = int(part.split("=")[1])
                elif "errors=" in part:
                    report.error_count = int(part.split("=")[1])
                elif "skipped=" in part:
                    report.skipped_count = int(part.split("=")[1])

        # 4. Parse individual failure blocks:
        # ======================================================================
        # FAIL: test_add (tests.test_math.TestMath)
        # ----------------------------------------------------------------------
        # Traceback (most recent call last):
        # ...
        fail_blocks = re.split(r"={40,}", combined)
        failures: List[ParsedFailure] = []

        for block in fail_blocks:
            hdr_match = re.search(r"(FAIL|ERROR):\s+([^\s(]+)(?:\s+\(([^)]+)\))?", block)
            if hdr_match:
                test_fn = hdr_match.group(2)
                test_class = hdr_match.group(3) or ""
                test_full_name = f"{test_class}.{test_fn}" if test_class else test_fn

                # Parse traceback inside this block
                parsed_list = cls.parse_python_traceback(block, workspace_root=workspace_root)
                if parsed_list:
                    pf = parsed_list[0]
                    pf.test_name = test_full_name
                    failures.append(pf)
                else:
                    # Fallback extraction
                    failures.append(
                        ParsedFailure(
                            test_name=test_full_name,
                            error_type="Failure",
                            error_message="Test failed with assertion or error",
                            category=FailureCategory.ASSERTION_ERROR,
                            raw_traceback=block.strip(),
                        )
                    )

        report.failures = failures
        if report.failed_count == 0 and report.error_count == 0:
            report.failed_count = len(failures)

        report.passed_count = max(0, report.total_tests - report.failed_count - report.error_count - report.skipped_count)
        report.all_passed = (report.failed_count == 0 and report.error_count == 0 and exit_code == 0)
        return report

    @classmethod
    def parse_pytest_output(
        cls,
        stdout: str,
        stderr: str,
        exit_code: int = 0,
        workspace_root: Optional[str] = None,
    ) -> TestExecutionReport:
        """Parses output from pytest runner."""
        combined = f"{stdout}\n{stderr}"
        report = TestExecutionReport(raw_stdout=stdout, raw_stderr=stderr, exit_code=exit_code)

        # Pytest summary: "=== 2 failed, 8 passed in 0.25s ==="
        summary_match = re.search(r"=\s+(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+passed,?\s*)?(?:(\d+)\s+skipped,?\s*)?in\s+([\d\.]+)s\s+=", combined)
        if summary_match:
            report.failed_count = int(summary_match.group(1) or 0)
            report.passed_count = int(summary_match.group(2) or 0)
            report.skipped_count = int(summary_match.group(3) or 0)
            report.total_tests = report.failed_count + report.passed_count + report.skipped_count
            report.duration_seconds = float(summary_match.group(4) or 0.0)

        # Pytest FAILURES section
        if "FAILURES" in combined:
            failures_section = combined.split("FAILURES")[-1]
            failure_chunks = re.split(r"_{20,}\s+([^\s_]+)\s+_{20,}", failures_section)
            i = 1
            while i < len(failure_chunks):
                test_name = failure_chunks[i]
                traceback_text = failure_chunks[i + 1] if i + 1 < len(failure_chunks) else ""
                parsed = cls.parse_python_traceback(traceback_text, workspace_root=workspace_root)
                if parsed:
                    pf = parsed[0]
                    pf.test_name = test_name
                    report.failures.append(pf)
                i += 2

        report.all_passed = (report.failed_count == 0 and report.error_count == 0 and exit_code == 0)
        return report

    @classmethod
    def parse_javascript_stack(
        cls,
        stack_text: str,
        workspace_root: Optional[str] = None,
    ) -> List[ParsedFailure]:
        """Parses JS/TS Error stack traces (Node.js, Vitest, Jest)."""
        if not stack_text:
            return []

        lines = stack_text.strip().split("\n")
        error_type = "Error"
        error_msg = ""
        frames: List[StackFrame] = []

        if lines:
            first_line = lines[0]
            if ":" in first_line:
                parts = first_line.split(":", 1)
                error_type = parts[0].strip()
                error_msg = parts[1].strip()
            else:
                error_msg = first_line.strip()

        for line in lines[1:]:
            match = cls.JS_FRAME_PATTERN.search(line)
            if match:
                file_path = match.group("file")
                line_num = int(match.group("line"))
                col_num = int(match.group("col")) if match.group("col") else None
                func_name = match.group("func") or "<anonymous>"

                is_ws = True
                if "node_modules" in file_path or "internal/" in file_path:
                    is_ws = False
                elif workspace_root and not file_path.startswith(workspace_root) and not file_path.startswith("./"):
                    is_ws = False

                frames.append(
                    StackFrame(
                        file_path=file_path,
                        line_number=line_num,
                        column_number=col_num,
                        function_name=func_name,
                        is_workspace_file=is_ws,
                    )
                )

        innermost = None
        ws_frames = [f for f in frames if f.is_workspace_file]
        if ws_frames:
            innermost = ws_frames[0]  # JS stacks are innermost-first (top of stack)
        elif frames:
            innermost = frames[0]

        return [
            ParsedFailure(
                test_name=innermost.function_name if innermost else "js_runtime",
                error_type=error_type,
                error_message=error_msg,
                frames=frames,
                innermost_frame=innermost,
                category=cls.categorize_error(error_type, error_msg),
                raw_traceback=stack_text,
            )
        ]

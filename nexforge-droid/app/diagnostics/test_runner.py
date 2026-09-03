"""Test Runner: executes test commands and normalizes raw outputs into structured diagnostic reports."""

import os
import shlex
import subprocess
import time
from typing import Optional

from app.diagnostics.traceback_parser import TestExecutionReport, TracebackParser
from app.observability.logger import get_logger

logger = get_logger("nexforge.diagnostics.runner")


class TestRunner:
    """Executes test suites and parses output into standardized TestExecutionReport."""

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = workspace_root or os.getcwd()

    def run_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> TestExecutionReport:
        """Runs an arbitrary shell command (e.g. pytest or python3 -m unittest) and parses results."""
        work_dir = cwd or self.workspace_root
        start_time = time.time()

        try:
            logger.info(f"Executing test command: '{command}' in '{work_dir}'")
            proc = subprocess.run(
                shlex.split(command),
                cwd=work_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout_seconds,
            )
            duration = time.time() - start_time
            stdout = proc.stdout
            stderr = proc.stderr
            exit_code = proc.returncode

            # Determine parser style
            if "pytest" in command:
                report = TracebackParser.parse_pytest_output(
                    stdout, stderr, exit_code=exit_code, workspace_root=work_dir
                )
            elif "unittest" in command or "python" in command:
                report = TracebackParser.parse_unittest_output(
                    stdout, stderr, exit_code=exit_code, workspace_root=work_dir
                )
            else:
                # Generic fallback
                report = TracebackParser.parse_unittest_output(
                    stdout, stderr, exit_code=exit_code, workspace_root=work_dir
                )

            report.duration_seconds = duration
            return report

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.error(f"Test command timed out after {timeout_seconds}s")
            return TestExecutionReport(
                total_tests=1,
                failed_count=1,
                duration_seconds=duration,
                exit_code=124,
                all_passed=False,
                raw_stderr=f"Execution timed out after {timeout_seconds} seconds.",
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Failed to execute test command: {e}")
            return TestExecutionReport(
                total_tests=1,
                error_count=1,
                duration_seconds=duration,
                exit_code=1,
                all_passed=False,
                raw_stderr=f"Exception during test runner invocation: {str(e)}",
            )

    def run_python_tests(
        self,
        test_pattern: str = "tests",
        cwd: Optional[str] = None,
    ) -> TestExecutionReport:
        """Executes python3 -m unittest discover."""
        cmd = f"python3 -m unittest discover -s ./{test_pattern} -t ."
        return self.run_command(cmd, cwd=cwd)

"""Terminal and command execution tool for NexForge Droid."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.tools.base import Tool, ToolResult

DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_CHARS = 100000


class RunCommandTool(Tool):
    """Tool for executing shell commands in a sandboxed subprocess."""

    name = "run_command"
    description = "Execute a shell command in the workspace and capture stdout, stderr, and exit code."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command line string to execute.",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory path for command execution (default current working directory).",
            },
            "timeout": {
                "type": "number",
                "description": "Execution timeout in seconds (default 30.0).",
            },
        },
        "required": ["command"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "").strip()
        cwd = kwargs.get("cwd")
        timeout = float(kwargs.get("timeout", DEFAULT_TIMEOUT_SECONDS))

        if not command:
            return ToolResult(success=False, error="Parameter 'command' is required.")

        working_dir = str(Path(cwd).resolve()) if cwd else os.getcwd()
        if not Path(working_dir).exists():
            return ToolResult(success=False, error=f"Working directory does not exist: '{working_dir}'")

        start_time = time.perf_counter()

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds.",
                    execution_time_ms=elapsed_ms,
                    data={
                        "command": command,
                        "exit_code": -1,
                        "stdout": stdout[:MAX_OUTPUT_CHARS] if stdout else "",
                        "stderr": (stderr[:MAX_OUTPUT_CHARS] if stderr else "") + f"\n[Process killed: timed out after {timeout}s]",
                        "timed_out": True,
                    },
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # Trim oversized outputs
            truncated_stdout = stdout[:MAX_OUTPUT_CHARS] if stdout else ""
            truncated_stderr = stderr[:MAX_OUTPUT_CHARS] if stderr else ""

            is_success = exit_code == 0

            return ToolResult(
                success=is_success,
                error=None if is_success else f"Command exited with non-zero status code: {exit_code}",
                execution_time_ms=elapsed_ms,
                data={
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": truncated_stdout,
                    "stderr": truncated_stderr,
                    "cwd": working_dir,
                },
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return ToolResult(
                success=False,
                error=f"Failed to execute command: {str(e)}",
                execution_time_ms=elapsed_ms,
            )

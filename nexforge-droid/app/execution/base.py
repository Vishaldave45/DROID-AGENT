"""Execution contracts, timeout limits, and sandbox interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ExecutionRequest:
    """Execution parameters dispatched to the execution environment."""

    command: str
    cwd: str
    timeout_seconds: int = 60
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Captured terminal output and exit telemetry."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class SandboxExecutor(ABC):
    """Abstract interface for command execution inside an isolated environment."""

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Executes a command safely inside the sandbox."""
        pass

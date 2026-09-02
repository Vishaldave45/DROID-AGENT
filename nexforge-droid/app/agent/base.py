"""Agent runtime lifecycle contracts and step models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.storage.base import TaskState


@dataclass
class AgentStepResult:
    """Outcome of a single step inside the Droid runtime loop."""

    iteration: int
    tool_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    tool_success: Optional[bool] = None
    thought_summary: Optional[str] = None
    is_terminal: bool = False
    final_output: Optional[str] = None
    errors: List[str] = field(default_factory=list)


class DroidRuntime(ABC):
    """Abstract interface for the autonomous Droid agent execution loop."""

    @abstractmethod
    def run_task(self, state: TaskState) -> TaskState:
        """Runs the complete autonomous loop until task success or termination."""
        pass

    @abstractmethod
    def step(self, state: TaskState) -> AgentStepResult:
        """Executes a single step (plan/reason/tool execution/observation)."""
        pass

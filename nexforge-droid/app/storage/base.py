"""State data models and persistent storage interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    TESTING = "TESTING"
    EVALUATING = "EVALUATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"


@dataclass
class TaskState:
    """Complete, serializable snapshot of an autonomous Droid run."""

    task_id: str
    repository_id: str
    requirement: str
    status: TaskStatus = TaskStatus.PENDING
    plan: List[Dict[str, Any]] = field(default_factory=list)
    current_step_index: int = 0
    iteration: int = 0
    files_read: List[str] = field(default_factory=list)
    files_changed: List[str] = field(default_factory=list)
    test_runs_count: int = 0
    test_failures_count: int = 0
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def mark_updated(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


class TaskStore(ABC):
    """Abstract interface for task state persistence."""

    @abstractmethod
    def save(self, state: TaskState) -> None:
        """Persist or update a task state."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> Optional[TaskState]:
        """Fetch task state by task ID."""
        pass

    @abstractmethod
    def list_tasks(self) -> List[TaskState]:
        """List all known tasks."""
        pass


class InMemoryTaskStore(TaskStore):
    """Volatile in-memory store for unit tests and local isolation."""

    def __init__(self) -> None:
        self._records: Dict[str, TaskState] = {}

    def save(self, state: TaskState) -> None:
        state.mark_updated()
        self._records[state.task_id] = state

    def get(self, task_id: str) -> Optional[TaskState]:
        return self._records.get(task_id)

    def list_tasks(self) -> List[TaskState]:
        return list(self._records.values())

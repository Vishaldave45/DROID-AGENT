"""State data models, timeline events, checkpoints, and persistent storage interfaces."""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from typing import Any, Dict, List, Optional
import uuid


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
    CANCELLED = "CANCELLED"


class TimelineEventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    STEP_START = "STEP_START"
    TOOL_INVOCATION = "TOOL_INVOCATION"
    TOOL_RESULT = "TOOL_RESULT"
    ERROR_LOGGED = "ERROR_LOGGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    CHECKPOINT_SAVED = "CHECKPOINT_SAVED"
    CHECKPOINT_RESTORED = "CHECKPOINT_RESTORED"
    STATE_PAUSED = "STATE_PAUSED"
    STATE_RESUMED = "STATE_RESUMED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


@dataclass
class TaskTimelineEvent:
    """Chronological event emitted during agent task execution."""

    event_id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:10]}")
    task_id: str = ""
    iteration: int = 0
    event_type: TimelineEventType = TimelineEventType.STEP_START
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "task_id": self.task_id,
            "iteration": self.iteration,
            "event_type": self.event_type.value if isinstance(self.event_type, TimelineEventType) else str(self.event_type),
            "payload": self.payload,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskTimelineEvent":
        ev_type = data.get("event_type", TimelineEventType.STEP_START.value)
        if isinstance(ev_type, str) and ev_type in TimelineEventType._value2member_map_:
            ev_type = TimelineEventType(ev_type)
        return cls(
            event_id=data.get("event_id", f"evt_{uuid.uuid4().hex[:10]}"),
            task_id=data.get("task_id", ""),
            iteration=int(data.get("iteration", 0)),
            event_type=ev_type,
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class TaskCheckpoint:
    """Point-in-time snapshot of task state for rollback and recovery."""

    checkpoint_id: str = field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:10]}")
    task_id: str = ""
    iteration: int = 0
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    git_commit_hash: Optional[str] = None
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "task_id": self.task_id,
            "iteration": self.iteration,
            "state_snapshot": self.state_snapshot,
            "git_commit_hash": self.git_commit_hash,
            "description": self.description,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskCheckpoint":
        return cls(
            checkpoint_id=data.get("checkpoint_id", f"chk_{uuid.uuid4().hex[:10]}"),
            task_id=data.get("task_id", ""),
            iteration=int(data.get("iteration", 0)),
            state_snapshot=data.get("state_snapshot", {}),
            git_commit_hash=data.get("git_commit_hash"),
            description=data.get("description", ""),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class TaskMessageRecord:
    """Persisted multi-turn dialogue message record."""

    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:10]}")
    task_id: str = ""
    iteration: int = 0
    role: str = "user"
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "task_id": self.task_id,
            "iteration": self.iteration,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskMessageRecord":
        return cls(
            message_id=data.get("message_id", f"msg_{uuid.uuid4().hex[:10]}"),
            task_id=data.get("task_id", ""),
            iteration=int(data.get("iteration", 0)),
            role=data.get("role", "user"),
            content=data.get("content"),
            tool_calls=data.get("tool_calls"),
            tool_call_id=data.get("tool_call_id"),
            name=data.get("name"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


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

    def pause(self, reason: str = "") -> None:
        """Transitions state into PAUSED status with audit reason."""
        if self.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            self.metadata["previous_status"] = self.status.value
            self.metadata["pause_reason"] = reason
            self.metadata["paused_at"] = datetime.now(timezone.utc).isoformat()
            self.status = TaskStatus.PAUSED
            self.mark_updated()

    def resume(self) -> None:
        """Resumes a paused task back to its previous execution state."""
        if self.status == TaskStatus.PAUSED:
            prev_status = self.metadata.get("previous_status", TaskStatus.EXECUTING.value)
            if prev_status in TaskStatus._value2member_map_:
                self.status = TaskStatus(prev_status)
            else:
                self.status = TaskStatus.EXECUTING
            self.metadata["resumed_at"] = datetime.now(timezone.utc).isoformat()
            self.mark_updated()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the task state into a JSON-compatible dictionary."""
        return {
            "task_id": self.task_id,
            "repository_id": self.repository_id,
            "requirement": self.requirement,
            "status": self.status.value if isinstance(self.status, TaskStatus) else str(self.status),
            "plan": self.plan,
            "current_step_index": self.current_step_index,
            "iteration": self.iteration,
            "files_read": self.files_read,
            "files_changed": self.files_changed,
            "test_runs_count": self.test_runs_count,
            "test_failures_count": self.test_failures_count,
            "errors": self.errors,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """Serializes the state to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """Reconstitutes a TaskState instance from a dictionary."""
        status_val = data.get("status", TaskStatus.PENDING.value)
        if isinstance(status_val, str) and status_val in TaskStatus._value2member_map_:
            status_obj = TaskStatus(status_val)
        elif isinstance(status_val, TaskStatus):
            status_obj = status_val
        else:
            status_obj = TaskStatus.PENDING

        return cls(
            task_id=data["task_id"],
            repository_id=data.get("repository_id", "default_repo"),
            requirement=data.get("requirement", ""),
            status=status_obj,
            plan=data.get("plan", []),
            current_step_index=int(data.get("current_step_index", 0)),
            iteration=int(data.get("iteration", 0)),
            files_read=data.get("files_read", []),
            files_changed=data.get("files_changed", []),
            test_runs_count=int(data.get("test_runs_count", 0)),
            test_failures_count=int(data.get("test_failures_count", 0)),
            errors=data.get("errors", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskState":
        """Reconstitutes a TaskState instance from a JSON string."""
        return cls.from_dict(json.loads(json_str))


class TaskStore(ABC):
    """Abstract interface for task state persistence, timelines, and checkpoints."""

    @abstractmethod
    def save(self, state: TaskState) -> None:
        """Persist or update a task state."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> Optional[TaskState]:
        """Fetch task state by task ID."""
        pass

    @abstractmethod
    def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: int = 100
    ) -> List[TaskState]:
        """List all known tasks, optionally filtered by status."""
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        """Deletes a task and all associated timeline events and checkpoints."""
        pass

    @abstractmethod
    def record_event(self, event: TaskTimelineEvent) -> None:
        """Appends a timeline event for an execution trace."""
        pass

    @abstractmethod
    def get_timeline(self, task_id: str) -> List[TaskTimelineEvent]:
        """Retrieves chronological timeline events for a task."""
        pass

    @abstractmethod
    def create_checkpoint(
        self, task_id: str, description: str, git_commit_hash: Optional[str] = None
    ) -> TaskCheckpoint:
        """Creates a state snapshot checkpoint."""
        pass

    @abstractmethod
    def get_checkpoints(self, task_id: str) -> List[TaskCheckpoint]:
        """Retrieves all checkpoints saved for a task."""
        pass

    @abstractmethod
    def get_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        """Retrieves a single checkpoint by its ID."""
        pass

    @abstractmethod
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[TaskState]:
        """Restores task state from a saved checkpoint."""
        pass

    @abstractmethod
    def save_messages(self, task_id: str, messages: List[Dict[str, Any]]) -> None:
        """Persists dialogue history messages."""
        pass

    @abstractmethod
    def get_messages(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieves dialogue history messages for a task."""
        pass

    @abstractmethod
    def pause_task(self, task_id: str, reason: str = "") -> Optional[TaskState]:
        """Pauses execution of a task."""
        pass

    @abstractmethod
    def resume_task(self, task_id: str) -> Optional[TaskState]:
        """Resumes execution of a paused task."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Retrieves storage metrics and table statistics."""
        pass


class InMemoryTaskStore(TaskStore):
    """Volatile in-memory store for unit tests and local isolation."""

    def __init__(self) -> None:
        self._records: Dict[str, TaskState] = {}
        self._timeline: Dict[str, List[TaskTimelineEvent]] = {}
        self._checkpoints: Dict[str, List[TaskCheckpoint]] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}

    def save(self, state: TaskState) -> None:
        state.mark_updated()
        self._records[state.task_id] = state

    def get(self, task_id: str) -> Optional[TaskState]:
        return self._records.get(task_id)

    def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: int = 100
    ) -> List[TaskState]:
        tasks = list(self._records.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def delete_task(self, task_id: str) -> bool:
        existed = task_id in self._records
        self._records.pop(task_id, None)
        self._timeline.pop(task_id, None)
        self._checkpoints.pop(task_id, None)
        self._messages.pop(task_id, None)
        return existed

    def record_event(self, event: TaskTimelineEvent) -> None:
        if event.task_id not in self._timeline:
            self._timeline[event.task_id] = []
        self._timeline[event.task_id].append(event)

    def get_timeline(self, task_id: str) -> List[TaskTimelineEvent]:
        events = self._timeline.get(task_id, [])
        return sorted(events, key=lambda e: (e.iteration, e.timestamp))

    def create_checkpoint(
        self, task_id: str, description: str, git_commit_hash: Optional[str] = None
    ) -> TaskCheckpoint:
        state = self.get(task_id)
        if not state:
            raise ValueError(f"Task '{task_id}' not found for checkpointing.")
        chk = TaskCheckpoint(
            task_id=task_id,
            iteration=state.iteration,
            state_snapshot=state.to_dict(),
            git_commit_hash=git_commit_hash,
            description=description,
        )
        if task_id not in self._checkpoints:
            self._checkpoints[task_id] = []
        self._checkpoints[task_id].append(chk)
        self.record_event(
            TaskTimelineEvent(
                task_id=task_id,
                iteration=state.iteration,
                event_type=TimelineEventType.CHECKPOINT_SAVED,
                payload={"checkpoint_id": chk.checkpoint_id, "description": description},
            )
        )
        return chk

    def get_checkpoints(self, task_id: str) -> List[TaskCheckpoint]:
        return self._checkpoints.get(task_id, [])

    def get_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        for chk_list in self._checkpoints.values():
            for chk in chk_list:
                if chk.checkpoint_id == checkpoint_id:
                    return chk
        return None

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[TaskState]:
        chk = self.get_checkpoint(checkpoint_id)
        if not chk:
            return None
        restored = TaskState.from_dict(chk.state_snapshot)
        restored.mark_updated()
        self.save(restored)
        self.record_event(
            TaskTimelineEvent(
                task_id=restored.task_id,
                iteration=restored.iteration,
                event_type=TimelineEventType.CHECKPOINT_RESTORED,
                payload={"checkpoint_id": checkpoint_id},
            )
        )
        return restored

    def save_messages(self, task_id: str, messages: List[Dict[str, Any]]) -> None:
        self._messages[task_id] = messages

    def get_messages(self, task_id: str) -> List[Dict[str, Any]]:
        return self._messages.get(task_id, [])

    def pause_task(self, task_id: str, reason: str = "") -> Optional[TaskState]:
        state = self.get(task_id)
        if not state:
            return None
        state.pause(reason)
        self.save(state)
        self.record_event(
            TaskTimelineEvent(
                task_id=task_id,
                iteration=state.iteration,
                event_type=TimelineEventType.STATE_PAUSED,
                payload={"reason": reason},
            )
        )
        return state

    def resume_task(self, task_id: str) -> Optional[TaskState]:
        state = self.get(task_id)
        if not state:
            return None
        state.resume()
        self.save(state)
        self.record_event(
            TaskTimelineEvent(
                task_id=task_id,
                iteration=state.iteration,
                event_type=TimelineEventType.STATE_RESUMED,
                payload={"resumed_status": state.status.value},
            )
        )
        return state

    def get_stats(self) -> Dict[str, Any]:
        tasks = list(self._records.values())
        status_counts = {}
        for t in tasks:
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
        total_events = sum(len(evs) for evs in self._timeline.values())
        total_checkpoints = sum(len(chks) for chks in self._checkpoints.values())
        return {
            "storage_type": "in_memory",
            "total_tasks": len(tasks),
            "status_distribution": status_counts,
            "total_timeline_events": total_events,
            "total_checkpoints": total_checkpoints,
            "db_size_bytes": 0,
        }

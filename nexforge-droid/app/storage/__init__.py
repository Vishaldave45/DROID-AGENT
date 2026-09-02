"""Storage and persistence abstractions for NexForge Droid."""

import os
from typing import Optional

from app.storage.base import (
    InMemoryTaskStore,
    TaskCheckpoint,
    TaskMessageRecord,
    TaskState,
    TaskStatus,
    TaskStore,
    TaskTimelineEvent,
    TimelineEventType,
)
from app.storage.sqlite_store import SqliteTaskStore

_default_store: Optional[TaskStore] = None


def get_default_task_store(db_path: Optional[str] = None) -> TaskStore:
    """Retrieves or instantiates the default persistent SQLite TaskStore."""
    global _default_store
    if _default_store is None:
        path = db_path or os.getenv("SQLITE_DB_PATH", ".nexforge/droid_state.db")
        _default_store = SqliteTaskStore(db_path=path)
    return _default_store


__all__ = [
    "TaskState",
    "TaskStatus",
    "TaskStore",
    "InMemoryTaskStore",
    "SqliteTaskStore",
    "TaskTimelineEvent",
    "TimelineEventType",
    "TaskCheckpoint",
    "TaskMessageRecord",
    "get_default_task_store",
]

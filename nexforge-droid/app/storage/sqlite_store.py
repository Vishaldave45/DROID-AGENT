"""SQLite-backed persistent storage implementation for NexForge Droid."""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

from app.storage.base import (
    TaskCheckpoint,
    TaskMessageRecord,
    TaskState,
    TaskStatus,
    TaskStore,
    TaskTimelineEvent,
    TimelineEventType,
)
from app.storage.schema import SQLITE_SCHEMA_DDL


class SqliteTaskStore(TaskStore):
    """Production persistent storage engine backed by SQLite."""

    def __init__(self, db_path: str = ".nexforge/droid_state.db") -> None:
        self.db_path = os.path.abspath(db_path)
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(SQLITE_SCHEMA_DDL)
            conn.commit()

    def save(self, state: TaskState) -> None:
        """Persist or update a task state in SQLite."""
        state.mark_updated()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, repository_id, requirement, status,
                    current_step_index, iteration, plan_json,
                    files_read_json, files_changed_json, test_runs_count,
                    test_failures_count, errors_json, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    repository_id = excluded.repository_id,
                    requirement = excluded.requirement,
                    status = excluded.status,
                    current_step_index = excluded.current_step_index,
                    iteration = excluded.iteration,
                    plan_json = excluded.plan_json,
                    files_read_json = excluded.files_read_json,
                    files_changed_json = excluded.files_changed_json,
                    test_runs_count = excluded.test_runs_count,
                    test_failures_count = excluded.test_failures_count,
                    errors_json = excluded.errors_json,
                    metadata_json = excluded.metadata_json,
                    updated_at = excluded.updated_at
                """,
                (
                    state.task_id,
                    state.repository_id,
                    state.requirement,
                    state.status.value if isinstance(state.status, TaskStatus) else str(state.status),
                    state.current_step_index,
                    state.iteration,
                    json.dumps(state.plan),
                    json.dumps(state.files_read),
                    json.dumps(state.files_changed),
                    state.test_runs_count,
                    state.test_failures_count,
                    json.dumps(state.errors),
                    json.dumps(state.metadata),
                    state.created_at,
                    state.updated_at,
                ),
            )
            conn.commit()

    def get(self, task_id: str) -> Optional[TaskState]:
        """Fetch task state by task ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM tasks WHERE task_id = ?", (task_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_task_state(row)

    def list_tasks(
        self, status: Optional[TaskStatus] = None, limit: int = 100
    ) -> List[TaskState]:
        """List all tasks, optionally filtered by status."""
        with self._get_connection() as conn:
            if status:
                st_val = status.value if isinstance(status, TaskStatus) else str(status)
                cursor = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (st_val, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM tasks ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [self._row_to_task_state(r) for r in rows]

    def delete_task(self, task_id: str) -> bool:
        """Deletes a task and all associated timeline events, checkpoints, and messages."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0

    def record_event(self, event: TaskTimelineEvent) -> None:
        """Appends a timeline event for an execution trace."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_timeline_events (
                    event_id, task_id, iteration, event_type, payload_json, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.task_id,
                    event.iteration,
                    event.event_type.value if isinstance(event.event_type, TimelineEventType) else str(event.event_type),
                    json.dumps(event.payload),
                    event.timestamp,
                ),
            )
            conn.commit()

    def get_timeline(self, task_id: str) -> List[TaskTimelineEvent]:
        """Retrieves chronological timeline events for a task."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_timeline_events WHERE task_id = ? ORDER BY iteration ASC, timestamp ASC",
                (task_id,),
            )
            rows = cursor.fetchall()
            events = []
            for r in rows:
                ev_type_str = r["event_type"]
                ev_type = (
                    TimelineEventType(ev_type_str)
                    if ev_type_str in TimelineEventType._value2member_map_
                    else TimelineEventType.STEP_START
                )
                events.append(
                    TaskTimelineEvent(
                        event_id=r["event_id"],
                        task_id=r["task_id"],
                        iteration=r["iteration"],
                        event_type=ev_type,
                        payload=json.loads(r["payload_json"] or "{}"),
                        timestamp=r["timestamp"],
                    )
                )
            return events

    def create_checkpoint(
        self, task_id: str, description: str, git_commit_hash: Optional[str] = None
    ) -> TaskCheckpoint:
        """Creates a state snapshot checkpoint and records it."""
        state = self.get(task_id)
        if not state:
            raise ValueError(f"Task '{task_id}' not found for checkpointing.")

        chk = TaskCheckpoint(
            checkpoint_id=f"chk_{uuid.uuid4().hex[:10]}",
            task_id=task_id,
            iteration=state.iteration,
            state_snapshot=state.to_dict(),
            git_commit_hash=git_commit_hash,
            description=description,
        )

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_checkpoints (
                    checkpoint_id, task_id, iteration, state_snapshot_json,
                    git_commit_hash, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chk.checkpoint_id,
                    chk.task_id,
                    chk.iteration,
                    json.dumps(chk.state_snapshot),
                    chk.git_commit_hash,
                    chk.description,
                    chk.created_at,
                ),
            )
            conn.commit()

        self.record_event(
            TaskTimelineEvent(
                task_id=task_id,
                iteration=state.iteration,
                event_type=TimelineEventType.CHECKPOINT_SAVED,
                payload={
                    "checkpoint_id": chk.checkpoint_id,
                    "description": description,
                    "iteration": state.iteration,
                },
            )
        )
        return chk

    def get_checkpoints(self, task_id: str) -> List[TaskCheckpoint]:
        """Retrieves all checkpoints saved for a task."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_checkpoints WHERE task_id = ? ORDER BY created_at DESC",
                (task_id,),
            )
            rows = cursor.fetchall()
            checkpoints = []
            for r in rows:
                checkpoints.append(
                    TaskCheckpoint(
                        checkpoint_id=r["checkpoint_id"],
                        task_id=r["task_id"],
                        iteration=r["iteration"],
                        state_snapshot=json.loads(r["state_snapshot_json"] or "{}"),
                        git_commit_hash=r["git_commit_hash"],
                        description=r["description"] or "",
                        created_at=r["created_at"],
                    )
                )
            return checkpoints

    def get_checkpoint(self, checkpoint_id: str) -> Optional[TaskCheckpoint]:
        """Retrieves a single checkpoint by its ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,),
            )
            r = cursor.fetchone()
            if not r:
                return None
            return TaskCheckpoint(
                checkpoint_id=r["checkpoint_id"],
                task_id=r["task_id"],
                iteration=r["iteration"],
                state_snapshot=json.loads(r["state_snapshot_json"] or "{}"),
                git_commit_hash=r["git_commit_hash"],
                description=r["description"] or "",
                created_at=r["created_at"],
            )

    def restore_checkpoint(self, checkpoint_id: str) -> Optional[TaskState]:
        """Restores task state from a saved checkpoint."""
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
                payload={
                    "checkpoint_id": checkpoint_id,
                    "description": chk.description,
                },
            )
        )
        return restored

    def save_messages(self, task_id: str, messages: List[Dict[str, Any]]) -> None:
        """Persists dialogue history messages in order."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM task_messages WHERE task_id = ?", (task_id,))
            for msg in messages:
                msg_id = msg.get("message_id", f"msg_{uuid.uuid4().hex[:10]}")
                conn.execute(
                    """
                    INSERT INTO task_messages (
                        message_id, task_id, iteration, role, content,
                        tool_calls_json, tool_call_id, name, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    (
                        msg_id,
                        task_id,
                        int(msg.get("iteration", 0)),
                        msg.get("role", "user"),
                        msg.get("content"),
                        json.dumps(msg.get("tool_calls")) if msg.get("tool_calls") else None,
                        msg.get("tool_call_id"),
                        msg.get("name"),
                    ),
                )
            conn.commit()

    def get_messages(self, task_id: str) -> List[Dict[str, Any]]:
        """Retrieves dialogue history messages for a task."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM task_messages WHERE task_id = ? ORDER BY rowid ASC",
                (task_id,),
            )
            rows = cursor.fetchall()
            messages = []
            for r in rows:
                m: Dict[str, Any] = {
                    "message_id": r["message_id"],
                    "task_id": r["task_id"],
                    "iteration": r["iteration"],
                    "role": r["role"],
                    "content": r["content"],
                }
                if r["tool_calls_json"]:
                    m["tool_calls"] = json.loads(r["tool_calls_json"])
                if r["tool_call_id"]:
                    m["tool_call_id"] = r["tool_call_id"]
                if r["name"]:
                    m["name"] = r["name"]
                messages.append(m)
            return messages

    def pause_task(self, task_id: str, reason: str = "") -> Optional[TaskState]:
        """Pauses execution of a task."""
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
        """Resumes execution of a paused task."""
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
        """Retrieves SQLite storage metrics, table row counts, and disk usage."""
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        with self._get_connection() as conn:
            tasks_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            events_count = conn.execute("SELECT COUNT(*) FROM task_timeline_events").fetchone()[0]
            checkpoints_count = conn.execute("SELECT COUNT(*) FROM task_checkpoints").fetchone()[0]
            messages_count = conn.execute("SELECT COUNT(*) FROM task_messages").fetchone()[0]

            cursor = conn.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            status_dist = {r[0]: r[1] for r in cursor.fetchall()}

        return {
            "storage_type": "sqlite",
            "db_path": self.db_path,
            "db_size_bytes": db_size,
            "db_size_kb": round(db_size / 1024, 2),
            "total_tasks": tasks_count,
            "status_distribution": status_dist,
            "total_timeline_events": events_count,
            "total_checkpoints": checkpoints_count,
            "total_messages": messages_count,
        }

    def _row_to_task_state(self, r: sqlite3.Row) -> TaskState:
        st_val = r["status"]
        status_obj = (
            TaskStatus(st_val)
            if st_val in TaskStatus._value2member_map_
            else TaskStatus.PENDING
        )
        return TaskState(
            task_id=r["task_id"],
            repository_id=r["repository_id"],
            requirement=r["requirement"],
            status=status_obj,
            current_step_index=r["current_step_index"],
            iteration=r["iteration"],
            plan=json.loads(r["plan_json"] or "[]"),
            files_read=json.loads(r["files_read_json"] or "[]"),
            files_changed=json.loads(r["files_changed_json"] or "[]"),
            test_runs_count=r["test_runs_count"],
            test_failures_count=r["test_failures_count"],
            errors=json.loads(r["errors_json"] or "[]"),
            metadata=json.loads(r["metadata_json"] or "{}"),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

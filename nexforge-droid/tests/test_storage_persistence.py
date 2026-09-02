"""Unit and integration tests for SQLite persistent storage, timelines, and checkpoints."""

import os
import tempfile
import unittest

from app.storage.base import (
    TaskCheckpoint,
    TaskState,
    TaskStatus,
    TaskTimelineEvent,
    TimelineEventType,
)
from app.storage.sqlite_store import SqliteTaskStore


class TestStoragePersistence(unittest.TestCase):
    """Test suite for SQLite state storage, checkpointing, and timeline auditing."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_state.db")
        self.store = SqliteTaskStore(db_path=self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_sqlite_schema_initialization(self) -> None:
        """Verify database tables and indexes are created properly."""
        self.assertTrue(os.path.exists(self.db_path))
        stats = self.store.get_stats()
        self.assertEqual(stats["storage_type"], "sqlite")
        self.assertEqual(stats["total_tasks"], 0)
        self.assertEqual(stats["total_timeline_events"], 0)
        self.assertEqual(stats["total_checkpoints"], 0)

    def test_task_save_and_retrieve(self) -> None:
        """Verify saving and retrieving rich TaskState with JSON fields."""
        state = TaskState(
            task_id="task_100",
            repository_id="repo_alpha",
            requirement="Implement user permissions middleware",
            status=TaskStatus.PLANNING,
            iteration=1,
            files_read=["/src/auth.py"],
            files_changed=["/src/permissions.py"],
            test_runs_count=2,
            test_failures_count=1,
            errors=["SyntaxError in line 4"],
            metadata={"priority": "high", "agent_version": "v1.2"},
        )
        self.store.save(state)

        retrieved = self.store.get("task_100")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.task_id, "task_100")
        self.assertEqual(retrieved.repository_id, "repo_alpha")
        self.assertEqual(retrieved.status, TaskStatus.PLANNING)
        self.assertEqual(retrieved.iteration, 1)
        self.assertEqual(retrieved.files_read, ["/src/auth.py"])
        self.assertEqual(retrieved.files_changed, ["/src/permissions.py"])
        self.assertEqual(retrieved.test_runs_count, 2)
        self.assertEqual(retrieved.test_failures_count, 1)
        self.assertEqual(retrieved.errors, ["SyntaxError in line 4"])
        self.assertEqual(retrieved.metadata["priority"], "high")

    def test_task_update_on_conflict(self) -> None:
        """Verify updating existing task mutates record in-place."""
        state = TaskState(
            task_id="task_200",
            repository_id="repo_main",
            requirement="Bug fix in router",
            status=TaskStatus.PENDING,
        )
        self.store.save(state)

        state.status = TaskStatus.EXECUTING
        state.iteration = 5
        state.files_changed.append("/src/router.py")
        self.store.save(state)

        updated = self.store.get("task_200")
        self.assertEqual(updated.status, TaskStatus.EXECUTING)
        self.assertEqual(updated.iteration, 5)
        self.assertIn("/src/router.py", updated.files_changed)

    def test_timeline_event_recording_and_chronology(self) -> None:
        """Verify timeline events are stored and retrieved chronologically."""
        t_id = "task_300"
        self.store.save(TaskState(task_id=t_id, repository_id="r1", requirement="Test Timeline"))

        ev1 = TaskTimelineEvent(
            task_id=t_id,
            iteration=1,
            event_type=TimelineEventType.STEP_START,
            payload={"turn": 1},
        )
        ev2 = TaskTimelineEvent(
            task_id=t_id,
            iteration=1,
            event_type=TimelineEventType.TOOL_INVOCATION,
            payload={"tool_name": "read_file", "path": "/src/main.py"},
        )
        ev3 = TaskTimelineEvent(
            task_id=t_id,
            iteration=2,
            event_type=TimelineEventType.TASK_COMPLETED,
            payload={"summary": "Done"},
        )

        self.store.record_event(ev1)
        self.store.record_event(ev2)
        self.store.record_event(ev3)

        timeline = self.store.get_timeline(t_id)
        self.assertEqual(len(timeline), 3)
        self.assertEqual(timeline[0].event_type, TimelineEventType.STEP_START)
        self.assertEqual(timeline[1].event_type, TimelineEventType.TOOL_INVOCATION)
        self.assertEqual(timeline[2].event_type, TimelineEventType.TASK_COMPLETED)
        self.assertEqual(timeline[1].payload["tool_name"], "read_file")

    def test_checkpoint_creation_and_state_rollback(self) -> None:
        """Verify creating checkpoint and restoring state rollback."""
        t_id = "task_400"
        state = TaskState(
            task_id=t_id,
            repository_id="r1",
            requirement="Refactor storage layer",
            status=TaskStatus.EXECUTING,
            iteration=2,
            files_changed=["/src/storage.py"],
        )
        self.store.save(state)

        # Create checkpoint at iteration 2
        chk = self.store.create_checkpoint(
            task_id=t_id,
            description="Pre-destructive schema migration",
            git_commit_hash="a1b2c3d",
        )
        self.assertIsNotNone(chk.checkpoint_id)
        self.assertEqual(chk.iteration, 2)

        # Mutate state to iteration 5 with errors
        state.iteration = 5
        state.status = TaskStatus.FAILED
        state.errors.append("Fatal database corrupt error")
        state.files_changed.append("/src/broken.py")
        self.store.save(state)

        # Verify state is corrupted
        curr = self.store.get(t_id)
        self.assertEqual(curr.status, TaskStatus.FAILED)
        self.assertEqual(curr.iteration, 5)

        # Restore from checkpoint
        restored = self.store.restore_checkpoint(chk.checkpoint_id)
        self.assertIsNotNone(restored)
        self.assertEqual(restored.task_id, t_id)
        self.assertEqual(restored.status, TaskStatus.EXECUTING)
        self.assertEqual(restored.iteration, 2)
        self.assertEqual(restored.files_changed, ["/src/storage.py"])

    def test_pause_and_resume_lifecycle(self) -> None:
        """Verify pausing and resuming tasks."""
        t_id = "task_500"
        state = TaskState(
            task_id=t_id,
            repository_id="r1",
            requirement="Long running refactor",
            status=TaskStatus.EXECUTING,
            iteration=3,
        )
        self.store.save(state)

        paused = self.store.pause_task(t_id, reason="User requested review")
        self.assertEqual(paused.status, TaskStatus.PAUSED)
        self.assertEqual(paused.metadata["pause_reason"], "User requested review")

        resumed = self.store.resume_task(t_id)
        self.assertEqual(resumed.status, TaskStatus.EXECUTING)
        self.assertIn("resumed_at", resumed.metadata)

    def test_message_history_persistence(self) -> None:
        """Verify saving and retrieving dialogue message records."""
        t_id = "task_600"
        self.store.save(TaskState(task_id=t_id, repository_id="r1", requirement="Message Test"))
        messages = [
            {"role": "system", "content": "You are NexForge Droid."},
            {"role": "user", "content": "Fix calculation bug."},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"tool_name": "read_file", "arguments": {"path": "/app.py"}}],
            },
            {"role": "tool", "content": "print('hello')", "name": "read_file"},
        ]
        self.store.save_messages(t_id, messages)

        retrieved = self.store.get_messages(t_id)
        self.assertEqual(len(retrieved), 4)
        self.assertEqual(retrieved[0]["role"], "system")
        self.assertEqual(retrieved[2]["tool_calls"][0]["tool_name"], "read_file")

    def test_delete_task_cascade(self) -> None:
        """Verify deleting a task cascades and removes related checkpoints and events."""
        t_id = "task_700"
        self.store.save(TaskState(task_id=t_id, repository_id="r1", requirement="To Delete"))
        self.store.record_event(TaskTimelineEvent(task_id=t_id, iteration=0, event_type=TimelineEventType.TASK_CREATED))
        self.store.create_checkpoint(t_id, "Temp Checkpoint")

        deleted = self.store.delete_task(t_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.store.get(t_id))
        self.assertEqual(len(self.store.get_timeline(t_id)), 0)
        self.assertEqual(len(self.store.get_checkpoints(t_id)), 0)


if __name__ == "__main__":
    unittest.main()

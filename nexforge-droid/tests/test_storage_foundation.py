"""Unit tests for task state models and in-memory persistence."""

import unittest
from app.storage.base import InMemoryTaskStore, TaskState, TaskStatus


class TestStorageFoundation(unittest.TestCase):

    def setUp(self) -> None:
        self.store = InMemoryTaskStore()

    def test_task_state_creation_and_retrieval(self) -> None:
        state = TaskState(
            task_id="task-001",
            repository_id="repo-main",
            requirement="Implement user authentication",
            status=TaskStatus.PENDING,
        )
        self.store.save(state)

        retrieved = self.store.get("task-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.task_id, "task-001")
        self.assertEqual(retrieved.status, TaskStatus.PENDING)
        self.assertEqual(retrieved.requirement, "Implement user authentication")

    def test_state_status_mutation(self) -> None:
        state = TaskState(
            task_id="task-002",
            repository_id="repo-main",
            requirement="Fix bug in auth middleware",
        )
        self.store.save(state)

        state.status = TaskStatus.EXECUTING
        state.files_changed.append("src/auth.py")
        self.store.save(state)

        updated = self.store.get("task-002")
        self.assertEqual(updated.status, TaskStatus.EXECUTING)
        self.assertIn("src/auth.py", updated.files_changed)

    def test_list_tasks(self) -> None:
        self.store.save(TaskState(task_id="t1", repository_id="r1", requirement="Task 1"))
        self.store.save(TaskState(task_id="t2", repository_id="r1", requirement="Task 2"))
        tasks = self.store.list_tasks()
        self.assertEqual(len(tasks), 2)


if __name__ == "__main__":
    unittest.main()

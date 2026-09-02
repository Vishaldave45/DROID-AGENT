#!/usr/bin/env python3
"""CLI utility for querying and executing SQLite state and persistence operations."""

import argparse
import json
import os
import sys
import uuid

# Ensure root package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.storage import (
    SqliteTaskStore,
    TaskState,
    TaskStatus,
    TaskTimelineEvent,
    TimelineEventType,
    get_default_task_store,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="NexForge Droid Storage CLI")
    parser.add_argument(
        "--op",
        required=True,
        choices=[
            "stats",
            "list-tasks",
            "get-task",
            "create-task",
            "pause-task",
            "resume-task",
            "create-checkpoint",
            "restore-checkpoint",
            "delete-task",
            "seed-demo-data",
        ],
        help="Storage operation to execute",
    )
    parser.add_argument("--db-path", default=".nexforge/droid_state.db", help="SQLite DB path")
    parser.add_argument("--task-id", help="Target task ID")
    parser.add_argument("--checkpoint-id", help="Target checkpoint ID")
    parser.add_argument("--requirement", help="Task requirement text")
    parser.add_argument("--repo-id", default="repo_core", help="Target repository ID")
    parser.add_argument("--status", help="TaskStatus filter")
    parser.add_argument("--reason", default="Manual user pause", help="Pause reason")
    parser.add_argument("--desc", default="Manual state snapshot", help="Checkpoint description")
    parser.add_argument("--limit", type=int, default=50, help="Max items to list")

    args = parser.parse_args()
    store = SqliteTaskStore(db_path=args.db_path)

    if args.op == "stats":
        stats = store.get_stats()
        print(json.dumps(stats, indent=2))
        return

    if args.op == "list-tasks":
        st_filter = None
        if args.status and args.status in TaskStatus._value2member_map_:
            st_filter = TaskStatus(args.status)
        tasks = store.list_tasks(status=st_filter, limit=args.limit)
        print(json.dumps([t.to_dict() for t in tasks], indent=2))
        return

    if args.op == "get-task":
        if not args.task_id:
            print(json.dumps({"error": "--task-id is required"}), file=sys.stderr)
            sys.exit(1)
        state = store.get(args.task_id)
        if not state:
            print(json.dumps({"error": f"Task '{args.task_id}' not found"}), file=sys.stderr)
            sys.exit(1)
        timeline = store.get_timeline(args.task_id)
        checkpoints = store.get_checkpoints(args.task_id)
        messages = store.get_messages(args.task_id)
        result = {
            "task": state.to_dict(),
            "timeline": [e.to_dict() for e in timeline],
            "checkpoints": [c.to_dict() for c in checkpoints],
            "messages": messages,
        }
        print(json.dumps(result, indent=2))
        return

    if args.op == "create-task":
        req = args.requirement or "Default initialized autonomous task"
        tid = args.task_id or f"task_{uuid.uuid4().hex[:8]}"
        state = TaskState(
            task_id=tid,
            repository_id=args.repo_id,
            requirement=req,
            status=TaskStatus.PENDING,
        )
        store.save(state)
        store.record_event(
            TaskTimelineEvent(
                task_id=tid,
                iteration=0,
                event_type=TimelineEventType.TASK_CREATED,
                payload={"requirement": req, "repository_id": args.repo_id},
            )
        )
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.op == "pause-task":
        if not args.task_id:
            print(json.dumps({"error": "--task-id is required"}), file=sys.stderr)
            sys.exit(1)
        state = store.pause_task(args.task_id, reason=args.reason)
        if not state:
            print(json.dumps({"error": f"Task '{args.task_id}' not found"}), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.op == "resume-task":
        if not args.task_id:
            print(json.dumps({"error": "--task-id is required"}), file=sys.stderr)
            sys.exit(1)
        state = store.resume_task(args.task_id)
        if not state:
            print(json.dumps({"error": f"Task '{args.task_id}' not found"}), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.op == "create-checkpoint":
        if not args.task_id:
            print(json.dumps({"error": "--task-id is required"}), file=sys.stderr)
            sys.exit(1)
        chk = store.create_checkpoint(args.task_id, description=args.desc)
        print(json.dumps(chk.to_dict(), indent=2))
        return

    if args.op == "restore-checkpoint":
        if not args.checkpoint_id:
            print(json.dumps({"error": "--checkpoint-id is required"}), file=sys.stderr)
            sys.exit(1)
        state = store.restore_checkpoint(args.checkpoint_id)
        if not state:
            print(json.dumps({"error": f"Checkpoint '{args.checkpoint_id}' not found"}), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(state.to_dict(), indent=2))
        return

    if args.op == "delete-task":
        if not args.task_id:
            print(json.dumps({"error": "--task-id is required"}), file=sys.stderr)
            sys.exit(1)
        success = store.delete_task(args.task_id)
        print(json.dumps({"success": success, "task_id": args.task_id}, indent=2))
        return

    if args.op == "seed-demo-data":
        # Create a few real initial task records in SQLite if empty
        tasks = store.list_tasks()
        if not tasks:
            t1 = TaskState(
                task_id="task_calc_patch",
                repository_id="repo_math",
                requirement="Fix zero division error and empty array safety in calculate_total",
                status=TaskStatus.COMPLETED,
                iteration=4,
                files_read=["/src/math_utils.py"],
                files_changed=["/src/math_utils.py"],
                test_runs_count=3,
                metadata={"final_output": "Successfully patched calculate_total with safe fallback for empty lists."},
            )
            store.save(t1)
            store.record_event(
                TaskTimelineEvent(
                    task_id=t1.task_id,
                    iteration=0,
                    event_type=TimelineEventType.TASK_CREATED,
                    payload={"requirement": t1.requirement},
                )
            )
            store.record_event(
                TaskTimelineEvent(
                    task_id=t1.task_id,
                    iteration=1,
                    event_type=TimelineEventType.TOOL_INVOCATION,
                    payload={"tool_name": "read_file", "arguments": {"path": "/src/math_utils.py"}},
                )
            )
            store.record_event(
                TaskTimelineEvent(
                    task_id=t1.task_id,
                    iteration=2,
                    event_type=TimelineEventType.TOOL_INVOCATION,
                    payload={"tool_name": "edit_file", "arguments": {"path": "/src/math_utils.py"}},
                )
            )
            store.record_event(
                TaskTimelineEvent(
                    task_id=t1.task_id,
                    iteration=4,
                    event_type=TimelineEventType.TASK_COMPLETED,
                    payload={"final_output": t1.metadata["final_output"]},
                )
            )
            store.create_checkpoint(t1.task_id, "Post-surgical patch verified")

            t2 = TaskState(
                task_id="task_sec_audit",
                repository_id="repo_core",
                requirement="Audit SecurityContext policy engine and verify sandbox path containment",
                status=TaskStatus.EXECUTING,
                iteration=2,
                files_read=["/src/security.py", "/tests/test_security_policy.py"],
                files_changed=[],
            )
            store.save(t2)
            store.record_event(
                TaskTimelineEvent(
                    task_id=t2.task_id,
                    iteration=0,
                    event_type=TimelineEventType.TASK_CREATED,
                    payload={"requirement": t2.requirement},
                )
            )
            store.record_event(
                TaskTimelineEvent(
                    task_id=t2.task_id,
                    iteration=1,
                    event_type=TimelineEventType.STEP_START,
                    payload={"status": "EXECUTING"},
                )
            )

        stats = store.get_stats()
        print(json.dumps({"seeded": True, "stats": stats}, indent=2))
        return


if __name__ == "__main__":
    main()

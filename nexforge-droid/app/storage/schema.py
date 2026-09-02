"""SQL schemas, DDL statements, and table migrations for persistent storage."""

SQLITE_SCHEMA_DDL = """
-- NexForge Droid Persistent Storage Schema

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    repository_id TEXT NOT NULL,
    requirement TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    current_step_index INTEGER NOT NULL DEFAULT 0,
    iteration INTEGER NOT NULL DEFAULT 0,
    plan_json TEXT NOT NULL DEFAULT '[]',
    files_read_json TEXT NOT NULL DEFAULT '[]',
    files_changed_json TEXT NOT NULL DEFAULT '[]',
    test_runs_count INTEGER NOT NULL DEFAULT 0,
    test_failures_count INTEGER NOT NULL DEFAULT 0,
    errors_json TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at DESC);

CREATE TABLE IF NOT EXISTS task_timeline_events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    timestamp TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_events_task_id ON task_timeline_events(task_id, iteration, timestamp);

CREATE TABLE IF NOT EXISTS task_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    state_snapshot_json TEXT NOT NULL,
    git_commit_hash TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_task_id ON task_checkpoints(task_id, created_at DESC);

CREATE TABLE IF NOT EXISTS task_messages (
    message_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    iteration INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL,
    content TEXT,
    tool_calls_json TEXT,
    tool_call_id TEXT,
    name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_task_id ON task_messages(task_id, created_at ASC);
"""

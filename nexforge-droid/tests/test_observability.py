"""Unit tests for structured logging and event telemetry."""

import json
import logging
import unittest
from app.observability.logger import JSONFormatter, configure_logging, get_logger
from app.observability.events import AuditEvent, EventType, TraceSpan


class TestObservability(unittest.TestCase):

    def test_json_formatter(self) -> None:
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test_observability.py",
            lineno=10,
            msg="Task step executed",
            args=(),
            exc_info=None,
        )
        record.task_id = "task-123"
        record.droid_id = "droid-main"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        self.assertEqual(parsed["level"], "INFO")
        self.assertEqual(parsed["message"], "Task step executed")
        self.assertEqual(parsed["task_id"], "task-123")
        self.assertEqual(parsed["droid_id"], "droid-main")
        self.assertIn("timestamp", parsed)

    def test_audit_event_creation(self) -> None:
        event = AuditEvent(
            event_type=EventType.SECURITY_AUDIT,
            action="run_command",
            actor="droid:main",
            status="ALLOW",
            task_id="task-456",
            details={"command": "pytest tests/"},
        )
        self.assertEqual(event.event_type, EventType.SECURITY_AUDIT)
        self.assertEqual(event.status, "ALLOW")
        self.assertEqual(event.task_id, "task-456")

    def test_trace_span_lifecycle(self) -> None:
        span = TraceSpan(span_id="span-001", name="tool:read_file")
        self.assertIsNone(span.end_time)
        span.finish()
        self.assertIsNotNone(span.end_time)


if __name__ == "__main__":
    unittest.main()

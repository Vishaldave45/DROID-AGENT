"""Observability event models for telemetry, traces, and audit logs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_REQUESTED = "tool_requested"
    TOOL_EXECUTED = "tool_executed"
    TOOL_BLOCKED = "tool_blocked"
    PLAN_UPDATED = "plan_updated"
    TEST_RUN = "test_run"
    SECURITY_AUDIT = "security_audit"


@dataclass
class AuditEvent:
    """Security audit event recording decisions and tool attempts."""

    event_type: EventType
    action: str
    actor: str  # e.g., 'droid:main', 'user:system'
    status: str  # 'ALLOW', 'DENY', 'APPROVED'
    task_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class TraceSpan:
    """Span representation for tracking latency and execution paths."""

    span_id: str
    name: str
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        self.end_time = datetime.now(timezone.utc).isoformat()

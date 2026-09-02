"""Observability package for structured logging, traces, and metrics."""

from app.observability.logger import get_logger, configure_logging
from app.observability.events import AuditEvent, TraceSpan

__all__ = ["get_logger", "configure_logging", "AuditEvent", "TraceSpan"]

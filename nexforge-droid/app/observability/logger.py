"""Structured JSON logging implementation for NexForge Droid."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats log records into machine-readable structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func_name": record.funcName,
            "line_no": record.lineno,
        }

        # Include custom context fields if present in extra
        if hasattr(record, "task_id"):
            log_data["task_id"] = getattr(record, "task_id")
        if hasattr(record, "droid_id"):
            log_data["droid_id"] = getattr(record, "droid_id")
        if hasattr(record, "tool_name"):
            log_data["tool_name"] = getattr(record, "tool_name")
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_data.update(record.extra_data)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure the root logger with either JSON or console formatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        )

    root_logger.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Obtain a named logger instance."""
    return logging.getLogger(name)

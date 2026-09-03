"""Data models for Real-Time Event Streaming and Interactive Debugging."""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class StreamEventType(str, Enum):
    THINKING = "THINKING"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    AST_VALIDATION = "AST_VALIDATION"
    PATCH_STAGE = "PATCH_STAGE"
    REGRESSION_TEST = "REGRESSION_TEST"
    BREAKPOINT = "BREAKPOINT"
    COMPLETION = "COMPLETION"
    ERROR = "ERROR"
    METRIC_SAMPLE = "METRIC_SAMPLE"


@dataclass
class StreamEvent:
    event_type: StreamEventType
    step: int
    total_steps: int
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    sequence_id: int = 0
    token_count: int = 0
    latency_ms: float = 0.0
    memory_mb: float = 42.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "sequenceId": self.sequence_id,
            "step": self.step,
            "total": self.total_steps,
            "tokenCount": self.token_count,
            "latencyMs": self.latency_ms,
            "memoryMb": self.memory_mb,
            "event": {
                "type": self.event_type.value,
                **self.payload,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        ev_dict = data.get("event", {})
        ev_type_str = ev_dict.get("type", "THINKING")
        payload = {k: v for k, v in ev_dict.items() if k != "type"}

        return cls(
            event_type=StreamEventType(ev_type_str),
            step=data.get("step", 1),
            total_steps=data.get("total", 1),
            payload=payload,
            timestamp=data.get("timestamp", time.time()),
            sequence_id=data.get("sequenceId", 0),
            token_count=data.get("tokenCount", 0),
            latency_ms=data.get("latencyMs", 0.0),
            memory_mb=data.get("memoryMb", 42.5),
        )


@dataclass
class BreakpointConfig:
    event_types: List[StreamEventType] = field(default_factory=list)
    step_numbers: List[int] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)
    enabled: bool = True

    def matches(self, event: StreamEvent) -> bool:
        if not self.enabled:
            return False
        if event.step in self.step_numbers:
            return True
        if event.event_type in self.event_types:
            return True
        target_file = event.payload.get("file") or event.payload.get("target_file")
        if target_file and any(f in target_file for f in self.target_files):
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "eventTypes": [t.value for t in self.event_types],
            "stepNumbers": self.step_numbers,
            "targetFiles": self.target_files,
            "enabled": self.enabled,
        }


@dataclass
class ExecutionTrace:
    trace_id: str
    scenario_id: str
    title: str
    events: List[StreamEvent] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: str = "COMPLETED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "traceId": self.trace_id,
            "scenarioId": self.scenario_id,
            "title": self.title,
            "events": [e.to_dict() for e in self.events],
            "createdAt": self.created_at,
            "status": self.status,
            "totalTokens": sum(e.token_count for e in self.events),
            "totalDurationMs": sum(e.latency_ms for e in self.events),
        }

"""Agent Event Streamer and Scenario Synthesizer."""

import queue
import threading
import time
from typing import Any, Callable, Dict, Generator, List, Optional
from app.streaming.models import (
    StreamEvent,
    StreamEventType,
    BreakpointConfig,
    ExecutionTrace,
)


SCENARIOS: Dict[str, Dict[str, Any]] = {
    "refactor-sqlite": {
        "id": "refactor-sqlite",
        "title": "Refactor SQLite Storage Cascade & Indexing",
        "steps": [
            {
                "type": StreamEventType.THINKING,
                "payload": {"text": "Analyzing foreign key constraints and cascade deletion in app/storage/sqlite_persistence.py..."},
                "tokens": 48,
                "latency_ms": 320,
            },
            {
                "type": StreamEventType.TOOL_CALL,
                "payload": {
                    "tool": "file_search",
                    "args": {"pattern": "FOREIGN KEY", "directory": "app/storage"},
                },
                "tokens": 28,
                "latency_ms": 110,
            },
            {
                "type": StreamEventType.TOOL_RESULT,
                "payload": {
                    "result": "Matched 4 table definitions with active ON DELETE CASCADE pragmas in schema.",
                },
                "tokens": 34,
                "latency_ms": 85,
            },
            {
                "type": StreamEventType.AST_VALIDATION,
                "payload": {
                    "file": "app/storage/sqlite_persistence.py",
                    "status": "VALID",
                    "nodesChecked": 184,
                },
                "tokens": 15,
                "latency_ms": 60,
            },
            {
                "type": StreamEventType.PATCH_STAGE,
                "payload": {
                    "file": "app/storage/sqlite_persistence.py",
                    "diffLines": "+12, -4",
                    "chunk": "@@ -124,4 +124,12 @@ PRAGMA foreign_keys = ON;",
                },
                "tokens": 82,
                "latency_ms": 210,
            },
            {
                "type": StreamEventType.REGRESSION_TEST,
                "payload": {
                    "suite": "tests/test_storage_persistence.py",
                    "testsPassed": 8,
                    "durationMs": 420,
                },
                "tokens": 22,
                "latency_ms": 420,
            },
            {
                "type": StreamEventType.COMPLETION,
                "payload": {
                    "summary": "Successfully updated SQLite cascading deletion logic and validated all 8 test cases.",
                },
                "tokens": 65,
                "latency_ms": 190,
            },
        ],
    },
    "fix-import-cycle": {
        "id": "fix-import-cycle",
        "title": "Resolve Circular Import in Diagnostics Subsystem",
        "steps": [
            {
                "type": StreamEventType.THINKING,
                "payload": {"text": "Detected circular dependency between DiagnosticReasoner and DiagnosticLoopController."},
                "tokens": 52,
                "latency_ms": 340,
            },
            {
                "type": StreamEventType.TOOL_CALL,
                "payload": {
                    "tool": "surgical_edit",
                    "args": {"path": "app/diagnostics/diagnostic_reasoner.py", "action": "extract_types"},
                },
                "tokens": 40,
                "latency_ms": 140,
            },
            {
                "type": StreamEventType.AST_VALIDATION,
                "payload": {
                    "file": "app/diagnostics/models.py",
                    "status": "VALID",
                    "nodesChecked": 92,
                },
                "tokens": 18,
                "latency_ms": 70,
            },
            {
                "type": StreamEventType.PATCH_STAGE,
                "payload": {
                    "file": "app/diagnostics/diagnostic_reasoner.py",
                    "diffLines": "+6, -8",
                    "chunk": "from app.diagnostics.models import FailureDiagnostic",
                },
                "tokens": 64,
                "latency_ms": 180,
            },
            {
                "type": StreamEventType.REGRESSION_TEST,
                "payload": {
                    "suite": "tests/test_diagnostic_loop.py",
                    "testsPassed": 10,
                    "durationMs": 310,
                },
                "tokens": 20,
                "latency_ms": 310,
            },
            {
                "type": StreamEventType.COMPLETION,
                "payload": {
                    "summary": "Circular import resolved. Clean dependency DAG established.",
                },
                "tokens": 45,
                "latency_ms": 160,
            },
        ],
    },
    "security-audit": {
        "id": "security-audit",
        "title": "Autonomous Path Traversal & Shell Injection Sandbox Audit",
        "steps": [
            {
                "type": StreamEventType.THINKING,
                "payload": {"text": "Evaluating command execution boundaries against malicious payloads (e.g. `rm -rf /`, `cat /etc/shadow`)."},
                "tokens": 60,
                "latency_ms": 290,
            },
            {
                "type": StreamEventType.TOOL_CALL,
                "payload": {
                    "tool": "policy_check",
                    "args": {"command": "rm -rf /", "context": "security_sandbox"},
                },
                "tokens": 30,
                "latency_ms": 95,
            },
            {
                "type": StreamEventType.TOOL_RESULT,
                "payload": {
                    "result": "DENIED: PolicyEngine rule BLOCKED_COMMANDS triggered (Severity: CRITICAL).",
                },
                "tokens": 25,
                "latency_ms": 40,
            },
            {
                "type": StreamEventType.REGRESSION_TEST,
                "payload": {
                    "suite": "tests/test_security_policy.py",
                    "testsPassed": 4,
                    "durationMs": 150,
                },
                "tokens": 18,
                "latency_ms": 150,
            },
            {
                "type": StreamEventType.COMPLETION,
                "payload": {
                    "summary": "Security perimeter validated. 0 unauthenticated path escapes permitted.",
                },
                "tokens": 50,
                "latency_ms": 140,
            },
        ],
    },
}


class AgentEventStreamer:
    """Manages real-time event distribution and scenario execution for Phase 12."""

    def __init__(self):
        self._subscribers: List[Callable[[StreamEvent], None]] = []
        self._traces: Dict[str, ExecutionTrace] = {}
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[StreamEvent], None]) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def emit(self, event: StreamEvent) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for s in subs:
            try:
                s(event)
            except Exception:
                pass

    def get_scenarios(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": s["id"],
                "title": s["title"],
                "totalSteps": len(s["steps"]),
            }
            for s in SCENARIOS.values()
        ]

    def build_trace_for_scenario(self, scenario_id: str) -> ExecutionTrace:
        scenario = SCENARIOS.get(scenario_id, SCENARIOS["refactor-sqlite"])
        raw_steps = scenario["steps"]
        total = len(raw_steps)

        trace = ExecutionTrace(
            trace_id=f"trace_{scenario_id}_{int(time.time())}",
            scenario_id=scenario_id,
            title=scenario["title"],
        )

        for idx, s in enumerate(raw_steps, 1):
            ev = StreamEvent(
                event_type=s["type"],
                step=idx,
                total_steps=total,
                payload=s["payload"],
                sequence_id=idx,
                token_count=s.get("tokens", 25),
                latency_ms=s.get("latency_ms", 150),
                memory_mb=42.0 + (idx * 1.8),
            )
            trace.events.append(ev)

        with self._lock:
            self._traces[trace.trace_id] = trace

        return trace

    def stream_generator(
        self, scenario_id: str = "refactor-sqlite", delay_sec: float = 0.5
    ) -> Generator[Dict[str, Any], None, None]:
        trace = self.build_trace_for_scenario(scenario_id)
        for ev in trace.events:
            self.emit(ev)
            yield ev.to_dict()
            if delay_sec > 0:
                time.sleep(delay_sec)

"""Interactive Agent Execution Debugger with Breakpoints and Step-Through Logic."""

import time
from typing import Any, Dict, List, Optional
from app.streaming.models import (
    StreamEvent,
    StreamEventType,
    BreakpointConfig,
    ExecutionTrace,
)
from app.streaming.streamer import SCENARIOS, AgentEventStreamer


class InteractiveDebugger:
    """Provides step-by-step interactive debugging session for agent thought loops."""

    def __init__(self, streamer: Optional[AgentEventStreamer] = None):
        self.streamer = streamer or AgentEventStreamer()
        self.active_scenario_id = "refactor-sqlite"
        self.current_step_index = 0
        self.trace: Optional[ExecutionTrace] = None
        self.breakpoints: BreakpointConfig = BreakpointConfig()
        self.is_paused = False
        self.paused_at_event: Optional[StreamEvent] = None
        self.session_id = f"dbg_{int(time.time())}"
        self.reset_session(self.active_scenario_id)

    def reset_session(self, scenario_id: str = "refactor-sqlite") -> Dict[str, Any]:
        self.active_scenario_id = scenario_id
        self.trace = self.streamer.build_trace_for_scenario(scenario_id)
        self.current_step_index = 0
        self.is_paused = False
        self.paused_at_event = None
        return self.get_session_state()

    def set_breakpoints(
        self,
        event_types: Optional[List[str]] = None,
        step_numbers: Optional[List[int]] = None,
        enabled: bool = True,
    ) -> BreakpointConfig:
        parsed_types = []
        if event_types:
            for t in event_types:
                try:
                    parsed_types.append(StreamEventType(t))
                except ValueError:
                    pass

        self.breakpoints = BreakpointConfig(
            event_types=parsed_types,
            step_numbers=step_numbers or [],
            enabled=enabled,
        )
        return self.breakpoints

    def step_next(self) -> Dict[str, Any]:
        """Advances execution by exactly 1 event/step."""
        if not self.trace or self.current_step_index >= len(self.trace.events):
            return {
                "done": True,
                "step": self.current_step_index,
                "total": len(self.trace.events) if self.trace else 0,
                "event": None,
                "session": self.get_session_state(),
            }

        event = self.trace.events[self.current_step_index]
        self.current_step_index += 1
        self.streamer.emit(event)

        # Check if next step would hit a breakpoint
        hit_breakpoint = False
        if self.current_step_index < len(self.trace.events):
            next_ev = self.trace.events[self.current_step_index]
            if self.breakpoints.matches(next_ev):
                hit_breakpoint = True
                self.is_paused = True
                self.paused_at_event = next_ev

        return {
            "done": self.current_step_index >= len(self.trace.events),
            "step": self.current_step_index,
            "total": len(self.trace.events),
            "event": event.to_dict()["event"],
            "rawEvent": event.to_dict(),
            "hitBreakpoint": hit_breakpoint,
            "session": self.get_session_state(),
        }

    def continue_execution(self) -> List[Dict[str, Any]]:
        """Runs until a breakpoint is hit or completion."""
        results = []
        while self.trace and self.current_step_index < len(self.trace.events):
            next_ev = self.trace.events[self.current_step_index]
            if self.breakpoints.matches(next_ev) and self.current_step_index > 0:
                self.is_paused = True
                self.paused_at_event = next_ev
                break

            step_res = self.step_next()
            results.append(step_res)

        return results

    def get_session_state(self) -> Dict[str, Any]:
        total = len(self.trace.events) if self.trace else 0
        return {
            "sessionId": self.session_id,
            "scenarioId": self.active_scenario_id,
            "currentStep": self.current_step_index,
            "totalSteps": total,
            "isPaused": self.is_paused,
            "breakpoints": self.breakpoints.to_dict(),
            "isComplete": self.current_step_index >= total if total > 0 else False,
            "activeTrace": self.trace.to_dict() if self.trace else None,
        }

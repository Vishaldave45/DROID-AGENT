"""Unit tests for Phase 12: Live Agent Event Streaming & Interactive Debugger."""

import unittest
import time
from app.streaming.models import (
    StreamEvent,
    StreamEventType,
    BreakpointConfig,
    ExecutionTrace,
)
from app.streaming.streamer import AgentEventStreamer, SCENARIOS
from app.streaming.debugger import InteractiveDebugger


class TestEventStreamingAndDebugger(unittest.TestCase):
    def setUp(self):
        self.streamer = AgentEventStreamer()
        self.debugger = InteractiveDebugger(streamer=self.streamer)

    def test_stream_event_serialization_and_deserialization(self):
        """Verify StreamEvent serializes cleanly to dict and roundtrips without data loss."""
        event = StreamEvent(
            event_type=StreamEventType.AST_VALIDATION,
            step=3,
            total_steps=7,
            payload={"file": "app/main.py", "status": "VALID", "nodesChecked": 120},
            token_count=45,
            latency_ms=180.5,
        )
        d = event.to_dict()
        self.assertEqual(d["step"], 3)
        self.assertEqual(d["total"], 7)
        self.assertEqual(d["tokenCount"], 45)
        self.assertEqual(d["event"]["type"], "AST_VALIDATION")
        self.assertEqual(d["event"]["file"], "app/main.py")

        restored = StreamEvent.from_dict(d)
        self.assertEqual(restored.event_type, StreamEventType.AST_VALIDATION)
        self.assertEqual(restored.step, 3)
        self.assertEqual(restored.payload["nodesChecked"], 120)

    def test_streamer_subscriber_dispatch(self):
        """Verify subscribers receive emitted stream events in real time."""
        received_events = []

        def on_event(ev: StreamEvent):
            received_events.append(ev)

        self.streamer.subscribe(on_event)

        ev = StreamEvent(
            event_type=StreamEventType.THINKING,
            step=1,
            total_steps=5,
            payload={"text": "Analyzing codebase"},
        )
        self.streamer.emit(ev)

        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_type, StreamEventType.THINKING)

        self.streamer.unsubscribe(on_event)
        self.streamer.emit(ev)
        # Should still be 1 after unsubscribe
        self.assertEqual(len(received_events), 1)

    def test_debugger_step_progression(self):
        """Verify stepping forward one event at a time advances current step index."""
        state = self.debugger.reset_session("refactor-sqlite")
        self.assertEqual(state["currentStep"], 0)
        self.assertFalse(state["isComplete"])

        # Step 1
        res1 = self.debugger.step_next()
        self.assertEqual(res1["step"], 1)
        self.assertEqual(res1["event"]["type"], "THINKING")
        self.assertFalse(res1["done"])

        # Step 2
        res2 = self.debugger.step_next()
        self.assertEqual(res2["step"], 2)
        self.assertEqual(res2["event"]["type"], "TOOL_CALL")

    def test_debugger_breakpoint_matching_and_pause(self):
        """Verify debugger pauses when next event matches configured breakpoint."""
        self.debugger.reset_session("refactor-sqlite")
        # Set breakpoint on AST_VALIDATION (which is step 4 in refactor-sqlite)
        self.debugger.set_breakpoints(event_types=["AST_VALIDATION"])

        # Step 1 (Thinking)
        r1 = self.debugger.step_next()
        self.assertFalse(r1["hitBreakpoint"])

        # Step 2 (Tool Call)
        r2 = self.debugger.step_next()
        self.assertFalse(r2["hitBreakpoint"])

        # Step 3 (Tool Result) -> Next is AST_VALIDATION, should flag hitBreakpoint
        r3 = self.debugger.step_next()
        self.assertTrue(r3["hitBreakpoint"])
        self.assertTrue(self.debugger.is_paused)

    def test_scenario_catalog_and_trace_generation(self):
        """Verify pre-built scenarios are discoverable and build valid execution traces."""
        scenarios = self.streamer.get_scenarios()
        self.assertTrue(len(scenarios) >= 3)
        scenario_ids = [s["id"] for s in scenarios]
        self.assertIn("refactor-sqlite", scenario_ids)
        self.assertIn("fix-import-cycle", scenario_ids)
        self.assertIn("security-audit", scenario_ids)

        trace = self.streamer.build_trace_for_scenario("fix-import-cycle")
        self.assertEqual(trace.scenario_id, "fix-import-cycle")
        self.assertTrue(len(trace.events) > 0)
        trace_dict = trace.to_dict()
        self.assertIn("totalTokens", trace_dict)
        self.assertIn("totalDurationMs", trace_dict)


if __name__ == "__main__":
    unittest.main()

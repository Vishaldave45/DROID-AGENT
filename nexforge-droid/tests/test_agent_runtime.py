"""Unit tests for Phase 3 Autonomous Agent Runtime and Step Controller."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from app.agent import AutonomousAgentRuntime, AgentStepResult
from app.agent.prompts import build_system_prompt
from app.llm.base import ChatMessage, ChatRole, LLMResponse, ToolCallRequest
from app.llm.mock import MockLLMProvider
from app.storage.base import InMemoryTaskStore, TaskState, TaskStatus
from app.tools import get_default_tool_registry
from app.tools.base import ToolRegistry


class TestAutonomousAgentRuntime(unittest.TestCase):
    """Test suite for autonomous step execution, tool dispatch loop, and state mutation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_agent_test_")
        self.workspace = Path(self.temp_dir)
        self.task_store = InMemoryTaskStore()
        self.registry = get_default_tool_registry(
            workspace_root=str(self.workspace),
            include_agent_tools=True,
        )

        # Seed sample project files
        (self.workspace / "src").mkdir(parents=True, exist_ok=True)
        (self.workspace / "src" / "math_utils.py").write_text(
            "def calculate_total(items):\n    return sum(items)\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_turn_direct_text_resolution(self) -> None:
        """Verify the agent immediately completes when the LLM returns direct text output."""
        mock_provider = MockLLMProvider(
            responses=[
                LLMResponse(
                    content="The mathematical formula has been verified as mathematically sound.",
                    tool_calls=[],
                    prompt_tokens=45,
                    completion_tokens=15,
                )
            ]
        )

        runtime = AutonomousAgentRuntime(
            llm_provider=mock_provider,
            tool_registry=self.registry,
            task_store=self.task_store,
            workspace_root=str(self.workspace),
        )

        state = TaskState(
            task_id="task-001",
            repository_id="repo-alpha",
            requirement="Verify mathematical integrity of the calculator utility.",
        )

        final_state = runtime.run_task(state)

        self.assertEqual(final_state.status, TaskStatus.COMPLETED)
        self.assertEqual(final_state.iteration, 1)
        self.assertIn("mathematically sound", final_state.metadata["final_output"])
        self.assertEqual(len(final_state.metadata["conversation"]), 3)  # System, User, Assistant

    def test_multi_turn_tool_chaining_and_finish_task(self) -> None:
        """Verify multi-step tool invocation: read file -> edit file -> finish_task."""
        mock_provider = MockLLMProvider(
            responses=[
                # Step 1: LLM calls read_file
                LLMResponse(
                    content="I will read src/math_utils.py to inspect the implementation.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-1",
                            tool_name="read_file",
                            arguments={"path": str(self.workspace / "src" / "math_utils.py")},
                        )
                    ],
                ),
                # Step 2: LLM calls edit_file
                LLMResponse(
                    content="I will update calculate_total to handle empty lists safely.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-2",
                            tool_name="edit_file",
                            arguments={
                                "path": str(self.workspace / "src" / "math_utils.py"),
                                "target_content": "    return sum(items)",
                                "replacement_content": "    return sum(items) if items else 0",
                            },
                        )
                    ],
                ),
                # Step 3: LLM calls finish_task
                LLMResponse(
                    content="The implementation has been successfully patched.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-3",
                            tool_name="finish_task",
                            arguments={
                                "summary": "calculate_total now safely handles empty lists.",
                                "status": "SUCCESS",
                                "verification_evidence": "Edited file successfully.",
                            },
                        )
                    ],
                ),
            ]
        )

        runtime = AutonomousAgentRuntime(
            llm_provider=mock_provider,
            tool_registry=self.registry,
            task_store=self.task_store,
            workspace_root=str(self.workspace),
        )

        state = TaskState(
            task_id="task-002",
            repository_id="repo-alpha",
            requirement="Patch calculate_total to return 0 when items is empty.",
        )

        final_state = runtime.run_task(state)

        self.assertEqual(final_state.status, TaskStatus.COMPLETED)
        self.assertEqual(final_state.iteration, 3)
        self.assertEqual(
            final_state.metadata["final_output"],
            "calculate_total now safely handles empty lists.",
        )

        # Verify file tracking
        self.assertIn(str(self.workspace / "src" / "math_utils.py"), final_state.files_read)
        self.assertIn(str(self.workspace / "src" / "math_utils.py"), final_state.files_changed)

        # Verify file content was actually modified on disk
        updated_content = (self.workspace / "src" / "math_utils.py").read_text(encoding="utf-8")
        self.assertIn("return sum(items) if items else 0", updated_content)

    def test_error_feedback_and_recovery(self) -> None:
        """Verify that when a tool encounters an error, the agent receives feedback and self-corrects."""
        mock_provider = MockLLMProvider(
            responses=[
                # Step 1: Agent tries to edit a non-existent target block
                LLMResponse(
                    content="Attempting invalid edit.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-err",
                            tool_name="edit_file",
                            arguments={
                                "path": str(self.workspace / "src" / "math_utils.py"),
                                "target_content": "non_existent_code_block",
                                "replacement_content": "new_code",
                            },
                        )
                    ],
                ),
                # Step 2: Agent receives error feedback and calls finish_task with failure explanation
                LLMResponse(
                    content="I detected the error and will report back.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-rec",
                            tool_name="finish_task",
                            arguments={
                                "summary": "Could not locate target block in source file.",
                                "status": "FAILED",
                            },
                        )
                    ],
                ),
            ]
        )

        runtime = AutonomousAgentRuntime(
            llm_provider=mock_provider,
            tool_registry=self.registry,
            task_store=self.task_store,
            workspace_root=str(self.workspace),
        )

        state = TaskState(
            task_id="task-003",
            repository_id="repo-alpha",
            requirement="Perform targeted modification.",
        )

        final_state = runtime.run_task(state)

        self.assertEqual(final_state.status, TaskStatus.FAILED)
        self.assertEqual(final_state.iteration, 2)
        self.assertTrue(any("target_content not found" in err.lower() for err in final_state.errors))

    def test_max_iteration_guard(self) -> None:
        """Verify the runtime terminates runaway loops when max iterations threshold is reached."""
        # Infinitely looping mock response
        infinite_response = LLMResponse(
            content="Listing files again...",
            tool_calls=[
                ToolCallRequest(
                    call_id="call-loop",
                    tool_name="list_dir",
                    arguments={"path": str(self.workspace)},
                )
            ],
        )

        mock_provider = MockLLMProvider(
            responses=[infinite_response, infinite_response, infinite_response, infinite_response]
        )

        runtime = AutonomousAgentRuntime(
            llm_provider=mock_provider,
            tool_registry=self.registry,
            task_store=self.task_store,
            workspace_root=str(self.workspace),
            max_iterations=3,
        )

        state = TaskState(
            task_id="task-004",
            repository_id="repo-alpha",
            requirement="Endless loop task.",
        )

        final_state = runtime.run_task(state)

        self.assertEqual(final_state.status, TaskStatus.FAILED)
        self.assertEqual(final_state.iteration, 3)
        self.assertTrue(any("maximum iterations threshold" in err for err in final_state.errors))

    def test_step_hooks_invocation(self) -> None:
        """Verify that registered step hooks are called on each step execution."""
        hook_calls = []

        def sample_hook(st: TaskState, step_res: AgentStepResult) -> None:
            hook_calls.append((st.iteration, step_res.tool_name))

        mock_provider = MockLLMProvider(
            responses=[
                LLMResponse(
                    content="Done immediately.",
                    tool_calls=[],
                )
            ]
        )

        runtime = AutonomousAgentRuntime(
            llm_provider=mock_provider,
            tool_registry=self.registry,
            task_store=self.task_store,
            workspace_root=str(self.workspace),
        )
        runtime.register_step_hook(sample_hook)

        state = TaskState(task_id="task-005", repository_id="repo-1", requirement="Quick check.")
        runtime.run_task(state)

        self.assertEqual(len(hook_calls), 1)
        self.assertEqual(hook_calls[0][0], 1)
        self.assertIsNone(hook_calls[0][1])


if __name__ == "__main__":
    unittest.main()

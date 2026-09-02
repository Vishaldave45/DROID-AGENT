#!/usr/bin/env python3
"""CLI and Subprocess execution bridge for running autonomous agent tasks."""

import argparse
import json
import os
import sys
import uuid
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.agent import AutonomousAgentRuntime, AgentStepResult
from app.llm import LLMProviderFactory
from app.llm.base import LLMResponse, ToolCallRequest
from app.llm.mock import MockLLMProvider
from app.storage.base import InMemoryTaskStore, TaskState, TaskStatus
from app.tools import get_default_tool_registry


def get_mock_scenario_provider(scenario: str, workspace: str) -> MockLLMProvider:
    """Generates scripted mock responses for deterministic testing and demonstrations."""
    if scenario == "patch_bug":
        return MockLLMProvider(
            responses=[
                LLMResponse(
                    content="I will search the codebase for math calculation functions.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-1",
                            tool_name="search_code",
                            arguments={"query": "def calculate_total"},
                        )
                    ],
                ),
                LLMResponse(
                    content="Found the function. Let me inspect src/math_utils.py.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-2",
                            tool_name="read_file",
                            arguments={"path": os.path.join(workspace, "src", "math_utils.py")},
                        )
                    ],
                ),
                LLMResponse(
                    content="I will now apply a surgical patch to ensure zero division and empty list safety.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-3",
                            tool_name="edit_file",
                            arguments={
                                "path": os.path.join(workspace, "src", "math_utils.py"),
                                "target_content": "    return sum(items)",
                                "replacement_content": "    return sum(items) if items else 0",
                            },
                        )
                    ],
                ),
                LLMResponse(
                    content="Running git diff to review the staged modifications.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-4",
                            tool_name="git_diff",
                            arguments={},
                        )
                    ],
                ),
                LLMResponse(
                    content="Changes verified. Concluding task.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-5",
                            tool_name="finish_task",
                            arguments={
                                "summary": "Successfully patched calculate_total with safe fallback for empty lists.",
                                "status": "SUCCESS",
                                "verification_evidence": "git diff shows single line surgical replacement.",
                            },
                        )
                    ],
                ),
            ]
        )
    elif scenario == "explore_repo":
        return MockLLMProvider(
            responses=[
                LLMResponse(
                    content="Let me explore the repository structure and configuration.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-exp-1",
                            tool_name="list_dir",
                            arguments={"path": workspace, "recursive": False},
                        )
                    ],
                ),
                LLMResponse(
                    content="Let me find all python source files in the project.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-exp-2",
                            tool_name="find_files",
                            arguments={"pattern": "*.py", "root_dir": workspace},
                        )
                    ],
                ),
                LLMResponse(
                    content="Repository analysis complete.",
                    tool_calls=[
                        ToolCallRequest(
                            call_id="call-exp-3",
                            tool_name="finish_task",
                            arguments={
                                "summary": "Explored directory hierarchy and indexed Python source modules.",
                                "status": "SUCCESS",
                            },
                        )
                    ],
                ),
            ]
        )
    else:
        return MockLLMProvider(
            responses=[
                LLMResponse(
                    content=f"Analysis of objective complete: Evaluated environment and verified system readiness.",
                    tool_calls=[],
                )
            ]
        )


def main():
    parser = argparse.ArgumentParser(description="Run an autonomous NexForge Droid agent task")
    parser.add_argument("--requirement", type=str, required=True, help="Engineering task requirement")
    parser.add_argument("--provider", type=str, default="gemini", choices=["gemini", "mock"], help="LLM backend")
    parser.add_argument("--mock-scenario", type=str, default="patch_bug", help="Mock scenario preset")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max reasoning iterations")
    parser.add_argument("--workspace", type=str, default=BASE_DIR, help="Workspace root directory")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Gemini model name")
    parser.add_argument("--stream", action="store_true", help="Stream step events to stdout as NDJSON")

    args = parser.parse_args()

    # Determine provider
    api_key = os.environ.get("GEMINI_API_KEY")
    if args.provider == "gemini" and not api_key:
        # Fallback to mock if API key is not set
        sys.stderr.write("[WARNING] GEMINI_API_KEY not found in environment; falling back to MockLLMProvider.\n")
        args.provider = "mock"

    if args.provider == "gemini":
        llm_provider = LLMProviderFactory.create(
            "gemini",
            api_key=api_key,
            model_name=args.model,
        )
    else:
        llm_provider = get_mock_scenario_provider(args.mock_scenario, args.workspace)

    registry = get_default_tool_registry(
        workspace_root=args.workspace,
        include_agent_tools=True,
    )
    task_store = InMemoryTaskStore()

    runtime = AutonomousAgentRuntime(
        llm_provider=llm_provider,
        tool_registry=registry,
        task_store=task_store,
        workspace_root=args.workspace,
        max_iterations=args.max_iterations,
    )

    task_id = f"task_{uuid.uuid4().hex[:8]}"
    state = TaskState(
        task_id=task_id,
        repository_id="local_workspace",
        requirement=args.requirement,
    )

    steps_log: List[Dict[str, Any]] = []

    def on_step(st: TaskState, step_res: AgentStepResult):
        event = {
            "event_type": "AGENT_STEP",
            "task_id": st.task_id,
            "iteration": step_res.iteration,
            "tool_name": step_res.tool_name,
            "arguments": step_res.arguments,
            "tool_success": step_res.tool_success,
            "thought_summary": step_res.thought_summary,
            "is_terminal": step_res.is_terminal,
            "final_output": step_res.final_output,
            "errors": step_res.errors,
            "status": st.status.value,
            "files_read": st.files_read,
            "files_changed": st.files_changed,
        }
        steps_log.append(event)
        if args.stream:
            print(json.dumps(event), flush=True)

    runtime.register_step_hook(on_step)
    final_state = runtime.run_task(state)

    final_payload = {
        "event_type": "TASK_COMPLETE",
        "task_id": final_state.task_id,
        "status": final_state.status.value,
        "iteration": final_state.iteration,
        "requirement": final_state.requirement,
        "files_read": final_state.files_read,
        "files_changed": final_state.files_changed,
        "test_runs_count": final_state.test_runs_count,
        "test_failures_count": final_state.test_failures_count,
        "errors": final_state.errors,
        "final_output": final_state.metadata.get("final_output"),
        "steps": steps_log,
    }

    if args.stream:
        print(json.dumps(final_payload), flush=True)
    else:
        print(json.dumps(final_payload, indent=2))


if __name__ == "__main__":
    main()

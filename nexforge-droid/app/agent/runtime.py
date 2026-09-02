"""Autonomous Droid runtime and step controller implementation."""

import json
import time
from typing import Any, Callable, Dict, List, Optional

from app.agent.base import AgentStepResult, DroidRuntime
from app.agent.prompts import build_system_prompt
from app.llm.base import ChatMessage, ChatRole, LLMProvider, ToolCallRequest
from app.observability.events import AuditEvent, EventType
from app.observability.logger import get_logger
from app.storage.base import InMemoryTaskStore, TaskState, TaskStatus, TaskStore
from app.tools import get_default_tool_registry
from app.tools.base import ToolRegistry, ToolResult

logger = get_logger("nexforge.agent")


def message_to_dict(msg: ChatMessage) -> Dict[str, Any]:
    """Serializes a ChatMessage into a JSON-compatible dictionary."""
    d: Dict[str, Any] = {
        "role": msg.role.value if isinstance(msg.role, ChatRole) else str(msg.role),
        "content": msg.content,
    }
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "call_id": tc.call_id,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
            }
            for tc in msg.tool_calls
        ]
    if msg.tool_call_id:
        d["tool_call_id"] = msg.tool_call_id
    if msg.name:
        d["name"] = msg.name
    return d


def dict_to_message(d: Dict[str, Any]) -> ChatMessage:
    """Deserializes a dictionary into a ChatMessage."""
    role_str = d.get("role", "user")
    role = ChatRole(role_str) if role_str in ChatRole._value2member_map_ else ChatRole.USER

    tool_calls = None
    if "tool_calls" in d and d["tool_calls"]:
        tool_calls = [
            ToolCallRequest(
                call_id=tc.get("call_id", ""),
                tool_name=tc.get("tool_name", ""),
                arguments=tc.get("arguments", {}),
            )
            for tc in d["tool_calls"]
        ]

    return ChatMessage(
        role=role,
        content=d.get("content"),
        tool_calls=tool_calls,
        tool_call_id=d.get("tool_call_id"),
        name=d.get("name"),
    )


class AutonomousAgentRuntime(DroidRuntime):
    """Production autonomous agent runtime with multi-turn reasoning and tool dispatch."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_registry: Optional[ToolRegistry] = None,
        task_store: Optional[TaskStore] = None,
        workspace_root: str = ".",
        max_iterations: int = 20,
        temperature: float = 0.2,
    ) -> None:
        self.llm_provider = llm_provider
        self.workspace_root = workspace_root
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.task_store = task_store or InMemoryTaskStore()
        self.tool_registry = tool_registry or get_default_tool_registry(
            workspace_root=workspace_root,
            include_agent_tools=True,
        )
        self._step_hooks: List[Callable[[TaskState, AgentStepResult], None]] = []

    def register_step_hook(
        self, hook: Callable[[TaskState, AgentStepResult], None]
    ) -> None:
        """Adds a callback invoked after every agent step execution."""
        self._step_hooks.append(hook)

    def _get_conversation(self, state: TaskState) -> List[ChatMessage]:
        """Retrieves or initializes the conversation message list from task state."""
        raw_history = state.metadata.get("conversation", [])
        if not raw_history:
            # Initialize with system prompt and task requirement
            system_msg = ChatMessage(
                role=ChatRole.SYSTEM,
                content=build_system_prompt(
                    workspace_root=self.workspace_root,
                    repository_id=state.repository_id,
                ),
            )
            user_msg = ChatMessage(
                role=ChatRole.USER,
                content=f"Engineering Objective / Task Requirement:\n{state.requirement}",
            )
            conversation = [system_msg, user_msg]
            state.metadata["conversation"] = [message_to_dict(m) for m in conversation]
            return conversation

        return [dict_to_message(m) for m in raw_history]

    def _save_conversation(
        self, state: TaskState, conversation: List[ChatMessage]
    ) -> None:
        """Persists the updated conversation back into task state metadata."""
        state.metadata["conversation"] = [message_to_dict(m) for m in conversation]
        state.mark_updated()
        self.task_store.save(state)

    def step(self, state: TaskState) -> AgentStepResult:
        """Executes one step in the autonomous reasoning loop."""
        if state.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return AgentStepResult(
                iteration=state.iteration,
                is_terminal=True,
                final_output=state.metadata.get("final_output", "Task is already resolved."),
            )

        if state.iteration >= self.max_iterations:
            state.status = TaskStatus.FAILED
            err_msg = f"Terminated: Reached maximum iterations threshold ({self.max_iterations})."
            state.errors.append(err_msg)
            state.mark_updated()
            self.task_store.save(state)
            return AgentStepResult(
                iteration=state.iteration,
                is_terminal=True,
                final_output=err_msg,
                errors=[err_msg],
            )

        state.iteration += 1
        state.status = TaskStatus.EXECUTING
        conversation = self._get_conversation(state)

        # Retrieve all tool schemas
        tool_schemas = self.tool_registry.get_all_schemas()

        logger.info(
            f"[Task {state.task_id}] Iteration {state.iteration}: Requesting LLM reasoning turn "
            f"({len(conversation)} messages, {len(tool_schemas)} tools available)..."
        )

        try:
            start_t = time.perf_counter()
            response = self.llm_provider.generate(
                messages=conversation,
                tools=tool_schemas,
                temperature=self.temperature,
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000
        except Exception as e:
            error_str = f"LLM Generation Error: {str(e)}"
            logger.error(f"[Task {state.task_id}] {error_str}")
            state.errors.append(error_str)
            state.status = TaskStatus.FAILED
            self.task_store.save(state)
            return AgentStepResult(
                iteration=state.iteration,
                is_terminal=True,
                errors=[error_str],
                final_output=error_str,
            )

        # 1. Model returned tool calls
        if response.tool_calls:
            assistant_msg = ChatMessage(
                role=ChatRole.ASSISTANT,
                content=response.content,
                tool_calls=response.tool_calls,
            )
            conversation.append(assistant_msg)

            last_tool_name = None
            last_tool_args = None
            last_tool_success = True
            is_terminal = False
            final_output = None

            for tool_call in response.tool_calls:
                last_tool_name = tool_call.tool_name
                last_tool_args = tool_call.arguments

                logger.info(
                    f"[Task {state.task_id}] Dispatching tool '{tool_call.tool_name}' "
                    f"with arguments: {tool_call.arguments}"
                )

                tool_res: ToolResult = self.tool_registry.dispatch(
                    tool_call.tool_name, tool_call.arguments
                )
                last_tool_success = tool_res.success

                # Update state statistics based on tool execution
                self._update_state_from_tool(state, tool_call.tool_name, tool_call.arguments, tool_res)

                # Format tool response message
                tool_msg = ChatMessage(
                    role=ChatRole.TOOL,
                    content=tool_res.to_json(),
                    tool_call_id=tool_call.call_id,
                    name=tool_call.tool_name,
                )
                conversation.append(tool_msg)

                # Check if this tool indicates terminal completion (e.g. finish_task)
                if tool_call.tool_name == "finish_task" and tool_res.success:
                    is_terminal = True
                    final_status = tool_res.data.get("status", "SUCCESS")
                    final_output = tool_res.data.get("summary", "Task completed.")
                    state.status = TaskStatus.COMPLETED if final_status == "SUCCESS" else TaskStatus.FAILED
                    state.metadata["final_output"] = final_output
                    state.metadata["verification_evidence"] = tool_res.data.get("verification_evidence")

            self._save_conversation(state, conversation)

            step_res = AgentStepResult(
                iteration=state.iteration,
                tool_name=last_tool_name,
                arguments=last_tool_args,
                tool_success=last_tool_success,
                thought_summary=response.content,
                is_terminal=is_terminal,
                final_output=final_output,
                errors=state.errors[-3:] if not last_tool_success else [],
            )

            for hook in self._step_hooks:
                hook(state, step_res)

            return step_res

        # 2. Model responded with direct text (no tool calls) -> Final Resolution
        assistant_msg = ChatMessage(
            role=ChatRole.ASSISTANT,
            content=response.content,
        )
        conversation.append(assistant_msg)
        self._save_conversation(state, conversation)

        state.status = TaskStatus.COMPLETED
        state.metadata["final_output"] = response.content

        step_res = AgentStepResult(
            iteration=state.iteration,
            thought_summary=response.content,
            is_terminal=True,
            final_output=response.content,
        )

        for hook in self._step_hooks:
            hook(state, step_res)

        return step_res

    def _update_state_from_tool(
        self,
        state: TaskState,
        tool_name: str,
        arguments: Dict[str, Any],
        tool_res: ToolResult,
    ) -> None:
        """Updates file inspection/modification tracking and error counts."""
        if tool_name in ("read_file", "search_code", "find_files"):
            path_arg = arguments.get("path")
            if path_arg and path_arg not in state.files_read:
                state.files_read.append(path_arg)
        elif tool_name in ("write_file", "edit_file", "delete_file"):
            path_arg = arguments.get("path")
            if path_arg and path_arg not in state.files_changed:
                state.files_changed.append(path_arg)
        elif tool_name == "run_command":
            cmd = arguments.get("command", "").lower()
            if "test" in cmd or "pytest" in cmd:
                state.test_runs_count += 1
                if not tool_res.success:
                    state.test_failures_count += 1

        if not tool_res.success and tool_res.error:
            state.errors.append(f"[{tool_name}] {tool_res.error}")
            if len(state.errors) > 20:
                state.errors = state.errors[-20:]

    def run_task(
        self, state: TaskState, max_iterations: Optional[int] = None
    ) -> TaskState:
        """Executes autonomous steps until completion, failure, or max iteration limit."""
        if max_iterations:
            self.max_iterations = max_iterations

        logger.info(f"Starting autonomous task execution: '{state.requirement}' (Task ID: {state.task_id})")

        while state.status in (TaskStatus.PENDING, TaskStatus.ANALYZING, TaskStatus.PLANNING, TaskStatus.EXECUTING):
            step_result = self.step(state)
            if step_result.is_terminal:
                break

        logger.info(
            f"Autonomous task {state.task_id} completed with status: {state.status.value} "
            f"after {state.iteration} iterations."
        )
        return state

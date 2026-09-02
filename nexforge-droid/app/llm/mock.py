"""Deterministic Mock LLM Provider for unit testing and offline verification."""

from typing import Any, Dict, List, Optional

from app.llm.base import ChatMessage, LLMProvider, LLMResponse, ToolCallRequest


class MockLLMProvider(LLMProvider):
    """Predictable mock provider that returns queued responses or echoes input."""

    def __init__(
        self,
        responses: Optional[List[LLMResponse]] = None,
        model_name: str = "mock-model",
    ):
        self.responses = list(responses) if responses else []
        self.model_name = model_name
        self.call_history: List[Dict[str, Any]] = []

    def queue_response(self, response: LLMResponse) -> None:
        """Enqueue a scripted response to return on subsequent generate call."""
        self.responses.append(response)

    def queue_tool_call(self, tool_name: str, arguments: Dict[str, Any], call_id: str = "call_mock_1") -> None:
        """Enqueue a scripted tool call response."""
        self.responses.append(
            LLMResponse(
                content=None,
                tool_calls=[ToolCallRequest(call_id=call_id, tool_name=tool_name, arguments=arguments)],
                model_name=self.model_name,
                prompt_tokens=15,
                completion_tokens=25,
                finish_reason="TOOL_CALLS",
            )
        )

    def queue_text(self, text: str) -> None:
        """Enqueue a scripted text completion."""
        self.responses.append(
            LLMResponse(
                content=text,
                tool_calls=[],
                model_name=self.model_name,
                prompt_tokens=10,
                completion_tokens=20,
                finish_reason="STOP",
            )
        )

    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Records invocation and returns queued response or sensible default."""
        self.call_history.append({
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })

        if self.responses:
            return self.responses.pop(0)

        # Default echo response if queue empty
        last_msg = messages[-1].content if messages else "No message"
        return LLMResponse(
            content=f"Mock response to: {last_msg}",
            tool_calls=[],
            prompt_tokens=12,
            completion_tokens=18,
            model_name=self.model_name,
            finish_reason="STOP",
        )

    async def generate_async(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Asynchronously returns next response."""
        return self.generate(messages, tools, temperature, max_tokens)

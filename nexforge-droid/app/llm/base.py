"""Provider-agnostic interface for Language Models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChatRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCallRequest:
    """Structured invocation request emitted by the model."""

    call_id: str
    tool_name: str
    arguments: Dict[str, Any]


@dataclass
class ChatMessage:
    """Standard message representation across providers."""

    role: ChatRole
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCallRequest]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: Optional[str] = None
    tool_calls: List[ToolCallRequest] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model_name: str = ""
    finish_reason: Optional[str] = None


class LLMProvider(ABC):
    """Abstract interface for all model backends (Gemini, Claude, OpenAI, etc.)."""

    @abstractmethod
    def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Synchronously generate a completion or tool call."""
        pass

    @abstractmethod
    async def generate_async(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Asynchronously generate a completion or tool call."""
        pass

"""LLM provider abstraction module and registry."""

from typing import Any, Dict, Optional, Type

from app.config import get_settings
from app.llm.base import (
    ChatMessage,
    ChatRole,
    LLMProvider,
    LLMResponse,
    ToolCallRequest,
)
from app.llm.exceptions import (
    AuthenticationError,
    InvalidRequestError,
    LLMError,
    ModelUnavailableError,
    ProviderTimeoutError,
    RateLimitError,
)
from app.llm.gemini import GeminiProvider
from app.llm.mock import MockLLMProvider

_PROVIDER_REGISTRY: Dict[str, Type[LLMProvider]] = {
    "gemini": GeminiProvider,
    "mock": MockLLMProvider,
}


def register_provider(name: str, provider_cls: Type[LLMProvider]) -> None:
    """Registers a new LLM provider class under the specified identifier."""
    _PROVIDER_REGISTRY[name.lower()] = provider_cls


def create_llm_provider(
    provider_name: str = "gemini",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs: Any,
) -> LLMProvider:
    """Factory function to instantiate an LLM provider by name."""
    provider_key = provider_name.lower()
    if provider_key not in _PROVIDER_REGISTRY:
        raise ValueError(
            f"Unsupported LLM provider '{provider_name}'. Available providers: {list(_PROVIDER_REGISTRY.keys())}"
        )

    provider_cls = _PROVIDER_REGISTRY[provider_key]
    if provider_key == "gemini":
        return GeminiProvider(api_key=api_key, model_name=model_name, **kwargs)
    elif provider_key == "mock":
        return MockLLMProvider(model_name=model_name or "mock-model", **kwargs)

    return provider_cls(**kwargs)


class LLMProviderFactory:
    """Factory helper for creating LLMProvider instances."""

    @staticmethod
    def create(
        provider_name: str = "gemini",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        **kwargs: Any,
    ) -> LLMProvider:
        return create_llm_provider(
            provider_name=provider_name,
            api_key=api_key,
            model_name=model_name,
            **kwargs,
        )


def get_default_provider() -> LLMProvider:
    """Retrieves the default configured provider based on runtime settings."""
    settings = get_settings()
    return create_llm_provider(
        provider_name="gemini",
        api_key=settings.gemini_api_key,
        model_name=settings.default_model,
    )


__all__ = [
    "ChatMessage",
    "ChatRole",
    "LLMProvider",
    "LLMResponse",
    "ToolCallRequest",
    "GeminiProvider",
    "MockLLMProvider",
    "create_llm_provider",
    "get_default_provider",
    "register_provider",
    "LLMProviderFactory",
    "LLMError",
    "RateLimitError",
    "AuthenticationError",
    "InvalidRequestError",
    "ProviderTimeoutError",
    "ModelUnavailableError",
]

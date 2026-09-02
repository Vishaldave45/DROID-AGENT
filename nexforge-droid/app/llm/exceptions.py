"""Standardized exception hierarchy for LLM Providers."""


class LLMError(Exception):
    """Base exception for all LLM provider failures."""

    def __init__(self, message: str, provider: str = "unknown", status_code: int = None, raw_response: str = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code
        self.raw_response = raw_response

    def __str__(self) -> str:
        return f"[{self.provider}] {self.message} (status: {self.status_code})"


class RateLimitError(LLMError):
    """Raised when provider rate limits or quotas are exceeded (e.g., HTTP 429)."""
    pass


class AuthenticationError(LLMError):
    """Raised when API key or credentials fail validation (e.g., HTTP 401, 403)."""
    pass


class InvalidRequestError(LLMError):
    """Raised when request payload or parameters are invalid (e.g., HTTP 400)."""
    pass


class ProviderTimeoutError(LLMError):
    """Raised when provider fails to respond within the configured deadline."""
    pass


class ModelUnavailableError(LLMError):
    """Raised when the target model is down, overloaded, or unreachable (e.g., HTTP 500, 502, 503)."""
    pass

"""Configuration management for NexForge Droid."""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Settings:
    """Central configuration for runtime, execution, and security boundaries."""

    environment: str = field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )
    gemini_api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    default_model: str = field(
        default_factory=lambda: os.getenv("DEFAULT_MODEL", "gemini-2.5-flash")
    )
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", "postgresql://nexforge:nexforge_secret@localhost:5432/nexforge_droid"
        )
    )
    workspace_root: str = field(
        default_factory=lambda: os.getenv("WORKSPACE_ROOT", "/workspace")
    )
    sandbox_timeout_seconds: int = field(
        default_factory=lambda: int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
    )
    max_execution_memory_mb: int = field(
        default_factory=lambda: int(os.getenv("MAX_EXECUTION_MEMORY_MB", "1024"))
    )
    max_iterations: int = field(
        default_factory=lambda: int(os.getenv("MAX_ITERATIONS", "25"))
    )
    max_context_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "32000"))
    )
    auto_approve_safe_tools: bool = field(
        default_factory=lambda: os.getenv("AUTO_APPROVE_SAFE_TOOLS", "true").lower() == "true"
    )

    def is_production(self) -> bool:
        """Returns True if the runtime is running in production mode."""
        return self.environment.lower() == "production"


# Global singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Retrieve or initialize the active configuration settings."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset configuration settings (primarily for testing purposes)."""
    global _settings
    _settings = None

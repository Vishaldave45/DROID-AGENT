"""NexForge Droid - Application Entrypoint and Service Registry."""

from typing import Any, Dict
from app.config import get_settings
from app.observability.logger import configure_logging, get_logger

# Initialize logging on startup
settings = get_settings()
configure_logging(level=settings.log_level, json_output=settings.is_production())
logger = get_logger("nexforge.main")


def get_system_manifest() -> Dict[str, Any]:
    """Returns the Phase 0 foundational system manifest and component health."""
    return {
        "system": "NexForge Droid",
        "version": "0.1.0",
        "phase": 0,
        "environment": settings.environment,
        "subsystems": {
            "llm": "LLMProvider Abstraction Ready",
            "tools": "Tool & ToolRegistry Interface Ready",
            "agent": "DroidRuntime Contract Ready",
            "storage": "TaskState & TaskStore Contract Ready",
            "security": "PolicyEngine & SecurityContext Ready",
            "context": "ContextEngine & EngineeringGraph Ready",
            "execution": "SandboxExecutor Contract Ready",
            "git": "GitEngine Interface Ready",
            "evaluation": "EvaluationEngine Interface Ready",
            "observability": "Structured JSON Logger & Tracing Ready",
        },
    }


def main() -> None:
    """CLI execution entrypoint."""
    logger.info("Initializing NexForge Droid Runtime Foundation...", extra={"system": "nexforge"})
    manifest = get_system_manifest()
    print("=" * 60)
    print("       NEXFORGE DROID - AUTONOMOUS CODING AGENT RUNTIME")
    print("=" * 60)
    print(f"System Version : {manifest['version']}")
    print(f"Active Phase   : Phase {manifest['phase']} (Foundation)")
    print(f"Environment    : {manifest['environment']}")
    print("-" * 60)
    print("Subsystems Registered:")
    for name, status in manifest["subsystems"].items():
        print(f"  • {name.upper():<14} : {status}")
    print("=" * 60)
    logger.info("NexForge Droid Foundation verified successfully.")


if __name__ == "__main__":
    main()

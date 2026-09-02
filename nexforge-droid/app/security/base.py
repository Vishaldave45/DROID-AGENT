"""Security policy contracts and governance validation engine."""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    APPROVE = "APPROVE"  # Requires human authorization gate
    DENY = "DENY"


@dataclass(frozen=True)
class SecurityContext:
    """Security boundaries and rules for a specific task or repository."""

    workspace_root: str
    allowed_commands: List[str] = field(default_factory=lambda: ["pytest", "python", "git", "rg", "ls"])
    denied_command_patterns: List[str] = field(
        default_factory=lambda: ["rm -rf /", "sudo", "chmod 777", "mkfs", "dd", "> /dev/"]
    )
    read_only: bool = False
    allow_network: bool = False

    def is_path_safe(self, target_path: str) -> bool:
        """Enforces that all path operations stay strictly inside the workspace boundary."""
        try:
            resolved_root = Path(self.workspace_root).resolve()
            resolved_target = Path(target_path).resolve()
            return resolved_target == resolved_root or resolved_root in resolved_target.parents
        except Exception:
            return False


class PolicyEngine(ABC):
    """Abstract interface for verifying tool actions before execution."""

    @abstractmethod
    def evaluate(self, tool_name: str, arguments: Dict[str, Any], context: SecurityContext) -> PolicyDecision:
        """Evaluates whether an action is ALLOWed, requires APPROVAL, or is DENIed."""
        pass


class DefaultPolicyEngine(PolicyEngine):
    """Reference implementation of deterministic security policy enforcement."""

    def evaluate(self, tool_name: str, arguments: Dict[str, Any], context: SecurityContext) -> PolicyDecision:
        # Check path safety for filesystem operations
        if tool_name in ["read_file", "write_file", "list_files", "delete_file"]:
            path = arguments.get("path") or arguments.get("file_path") or arguments.get("directory")
            if path and not context.is_path_safe(path):
                return PolicyDecision.DENY

        # Terminal and execution safety
        if tool_name in ["run_command", "execute"]:
            command = arguments.get("command", "").strip()
            for denied in context.denied_command_patterns:
                if denied in command:
                    return PolicyDecision.DENY

        # Critical actions requiring explicit approval
        if tool_name in ["git_push", "deploy_production", "publish_release"]:
            return PolicyDecision.APPROVE

        return PolicyDecision.ALLOW

"""Tool contracts, structured results, and Registry interface for NexForge Droid."""

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.observability.events import AuditEvent, EventType
from app.observability.logger import get_logger
from app.security.base import DefaultPolicyEngine, PolicyDecision, PolicyEngine, SecurityContext

logger = get_logger("nexforge.tools")


@dataclass
class ToolResult:
    """Standardized output returned by any tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class Tool(ABC):
    """Abstract base class for all Droid tools."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    requires_permission: bool = False

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Executes the tool with validated keyword arguments."""
        pass

    def validate_arguments(self, kwargs: Dict[str, Any]) -> Optional[str]:
        """Validates required properties specified in input_schema."""
        schema = getattr(self, "input_schema", {})
        required = schema.get("required", [])
        for req_field in required:
            if req_field not in kwargs or kwargs[req_field] is None:
                return f"Missing required parameter '{req_field}' for tool '{self.name}'."
        return None


class ToolRegistry:
    """Central registry holding available tools with discovery, validation, security checks, and dispatch."""

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        security_context: Optional[SecurityContext] = None,
    ) -> None:
        self._tools: Dict[str, Tool] = {}
        self.policy_engine = policy_engine or DefaultPolicyEngine()
        self.security_context = security_context

    def register(self, tool: Tool) -> None:
        """Register a new tool instance."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Retrieve a registered tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Tool]:
        """Returns all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns provider-agnostic schemas for all registered tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            }
            for tool in self._tools.values()
        ]

    def dispatch(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        security_context: Optional[SecurityContext] = None,
    ) -> ToolResult:
        """Safely dispatches and executes a tool with policy gating and execution timing."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found in registry. Available tools: {list(self._tools.keys())}",
            )

        # 1. Parameter validation
        validation_error = tool.validate_arguments(arguments)
        if validation_error:
            return ToolResult(success=False, error=validation_error)

        # 2. Security policy check
        sec_ctx = security_context or self.security_context
        if sec_ctx and self.policy_engine:
            decision = self.policy_engine.evaluate(tool_name, arguments, sec_ctx)
            if decision == PolicyDecision.DENY:
                logger.warning("Security policy DENIED execution for tool '%s': %s", tool_name, arguments)
                return ToolResult(
                    success=False,
                    error=f"Security Policy Violation: Execution of tool '{tool_name}' was DENIED by policy.",
                    metadata={"policy_decision": "DENY"},
                )
            elif decision == PolicyDecision.APPROVE:
                logger.info("Tool '%s' requires human approval: %s", tool_name, arguments)
                return ToolResult(
                    success=False,
                    error=f"Approval Required: Tool '{tool_name}' requires human authorization gate.",
                    metadata={"policy_decision": "APPROVE", "status": "pending_approval"},
                )

        # 3. Execution with timing telemetry
        start_time = time.perf_counter()
        try:
            result = tool.execute(**arguments)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            result.execution_time_ms = elapsed_ms
            return result
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logger.exception("Error executing tool '%s': %s", tool_name, str(e))
            return ToolResult(
                success=False,
                error=f"Tool execution failed: {str(e)}",
                execution_time_ms=elapsed_ms,
            )

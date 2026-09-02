"""Agent orchestration tools such as finish_task and plan_step."""

from typing import Any, Dict, Optional
from app.tools.base import Tool, ToolResult


class FinishTaskTool(Tool):
    """Signals that the task has been completed or terminated with a final resolution."""

    name = "finish_task"
    description = (
        "Call this tool when the requested objective has been accomplished or cannot be completed further. "
        "Provides a concise summary of results and the final status."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "Comprehensive summary of actions taken and final resolution.",
            },
            "status": {
                "type": "string",
                "enum": ["SUCCESS", "FAILED", "PARTIAL"],
                "description": "Final completion status.",
            },
            "verification_evidence": {
                "type": "string",
                "description": "Evidence verifying success (e.g. test results, file contents).",
            },
        },
        "required": ["summary"],
    }

    def execute(
        self,
        summary: str,
        status: str = "SUCCESS",
        verification_evidence: Optional[str] = None,
        **kwargs: Any,
    ) -> ToolResult:
        return ToolResult(
            success=True,
            data={
                "summary": summary,
                "status": status.upper(),
                "verification_evidence": verification_evidence,
            },
            metadata={"is_terminal": True},
        )

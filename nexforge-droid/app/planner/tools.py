"""Planner Tools callable by the Droid LLM runtime (Phase 8)."""

from typing import Any, Dict, Optional

from app.planner.base import ExecutionPlan, PlanStepType, StepStatus
from app.planner.planner import ExplicitTaskPlanner
from app.planner.replanner import DynamicReplanner
from app.tools.base import Tool, ToolResult


class GeneratePlanTool(Tool):
    """Generates a structured execution plan for an engineering task."""

    name = "generate_plan"
    description = "Generates a multi-step DAG execution plan for the current engineering task."
    input_schema = {
        "type": "object",
        "properties": {
            "task_requirement": {
                "type": "string",
                "description": "The engineering objective to plan.",
            },
            "task_id": {
                "type": "string",
                "description": "Optional task identifier.",
                "default": "task-active",
            },
        },
        "required": ["task_requirement"],
    }

    def __init__(self, planner: Optional[ExplicitTaskPlanner] = None) -> None:
        self.planner = planner or ExplicitTaskPlanner()

    def execute(self, **kwargs: Any) -> ToolResult:
        req = kwargs.get("task_requirement", "")
        task_id = kwargs.get("task_id", "task-active")
        if not req:
            return ToolResult(success=False, error="task_requirement parameter is required.")

        try:
            plan = self.planner.generate_plan(task_id=task_id, task_requirement=req)
            return ToolResult(
                success=True,
                data={
                    "plan": plan.to_dict(),
                    "total_steps": len(plan.steps),
                    "next_runnable_steps": [s.step_id for s in plan.get_next_runnable_steps()],
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Plan generation failed: {str(e)}")


class ReplanTaskTool(Tool):
    """Dynamically replans an active execution plan upon failure or unexpected error."""

    name = "replan_task"
    description = "Dynamically mutates and inserts diagnostic/fix steps into the plan when a step fails."
    input_schema = {
        "type": "object",
        "properties": {
            "plan_dict": {
                "type": "object",
                "description": "The current execution plan as a JSON dictionary.",
            },
            "failed_step_id": {
                "type": "string",
                "description": "The ID of the step that encountered an error (e.g. 'step-3').",
            },
            "error_message": {
                "type": "string",
                "description": "Description of the error or failure.",
            },
        },
        "required": ["plan_dict", "failed_step_id", "error_message"],
    }

    def __init__(self, replanner: Optional[DynamicReplanner] = None) -> None:
        self.replanner = replanner or DynamicReplanner()

    def execute(self, **kwargs: Any) -> ToolResult:
        plan_dict = kwargs.get("plan_dict")
        failed_step_id = kwargs.get("failed_step_id")
        error_message = kwargs.get("error_message")

        if not plan_dict or not failed_step_id or not error_message:
            return ToolResult(success=False, error="plan_dict, failed_step_id, and error_message are required.")

        try:
            plan = ExecutionPlan.from_dict(plan_dict)
            new_plan = self.replanner.replan_on_failure(
                plan=plan,
                failed_step_id=failed_step_id,
                error_message=error_message,
            )
            return ToolResult(
                success=True,
                data={
                    "plan": new_plan.to_dict(),
                    "new_steps_count": len(new_plan.steps),
                    "next_runnable_steps": [s.step_id for s in new_plan.get_next_runnable_steps()],
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Replanning failed: {str(e)}")

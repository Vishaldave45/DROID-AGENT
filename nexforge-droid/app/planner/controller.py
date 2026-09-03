"""Plan Execution Controller coordinating DAG execution with Agent State (Phase 8)."""

from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Optional, Tuple

from app.observability.events import AuditEvent, EventType
from app.observability.logger import get_logger
from app.planner.base import ExecutionPlan, PlanStep, StepStatus
from app.planner.replanner import DynamicReplanner
from app.storage.base import TaskState, TaskStore, TaskTimelineEvent, TimelineEventType

logger = get_logger("nexforge.planner")


class PlanExecutionController:
    """Oversees step advancement, acceptance criteria evaluation, and state persistence."""

    def __init__(self, task_store: Optional[TaskStore] = None) -> None:
        self.task_store = task_store
        self.replanner = DynamicReplanner()

    def attach_plan_to_state(self, state: TaskState, plan: ExecutionPlan) -> None:
        """Saves active plan into TaskState metadata and records timeline event."""
        state.metadata["execution_plan"] = plan.to_dict()
        state.mark_updated()
        if self.task_store:
            self.task_store.save(state)
            self.task_store.record_event(
                TaskTimelineEvent(
                    task_id=state.task_id,
                    iteration=state.iteration,
                    event_type=TimelineEventType.STATUS_CHANGED,
                    payload={
                        "action": "plan_initialized",
                        "plan_id": plan.plan_id,
                        "steps_count": len(plan.steps),
                    },
                )
            )

    def get_plan_from_state(self, state: TaskState) -> Optional[ExecutionPlan]:
        """Loads active plan from TaskState metadata."""
        plan_dict = state.metadata.get("execution_plan")
        if not plan_dict:
            return None
        return ExecutionPlan.from_dict(plan_dict)

    def advance_step(
        self,
        state: TaskState,
        step_id: str,
        new_status: StepStatus,
        evidence: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> Tuple[ExecutionPlan, Optional[PlanStep]]:
        """Updates status of a step and resolves the next runnable step."""
        plan = self.get_plan_from_state(state)
        if not plan:
            raise ValueError(f"No active execution plan associated with task {state.task_id}.")

        step = plan.get_step(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' not found in plan '{plan.plan_id}'.")

        if new_status == StepStatus.IN_PROGRESS:
            step.mark_in_progress()
        elif new_status == StepStatus.COMPLETED:
            step.mark_completed(evidence=evidence, duration_ms=duration_ms)
        elif new_status == StepStatus.FAILED:
            step.mark_failed(error=evidence)
        else:
            step.status = new_status

        # Find next runnable step
        runnable = plan.get_next_runnable_steps()
        next_step = runnable[0] if runnable else None
        plan.current_step_id = next_step.step_id if next_step else None

        self.attach_plan_to_state(state, plan)
        return plan, next_step

    def handle_step_failure_and_replan(
        self,
        state: TaskState,
        failed_step_id: str,
        error_message: str,
    ) -> ExecutionPlan:
        """Triggers dynamic replanning, updating the plan DAG stored in state."""
        plan = self.get_plan_from_state(state)
        if not plan:
            raise ValueError("No active plan in state to replan.")

        new_plan = self.replanner.replan_on_failure(
            plan=plan,
            failed_step_id=failed_step_id,
            error_message=error_message,
        )

        self.attach_plan_to_state(state, new_plan)
        return new_plan

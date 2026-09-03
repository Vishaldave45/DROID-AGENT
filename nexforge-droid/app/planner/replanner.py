"""Dynamic Replanner for self-healing error recovery and DAG mutation (Phase 8)."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from app.planner.base import ExecutionPlan, PlanStep, PlanStepType, StepStatus


class DynamicReplanner:
    """Modifies an active ExecutionPlan when steps fail or unexpected tool errors arise."""

    def replan_on_failure(
        self,
        plan: ExecutionPlan,
        failed_step_id: str,
        error_message: str,
        tool_output: Optional[str] = None,
    ) -> ExecutionPlan:
        """Dynamically mutates the plan by inserting remediation and diagnostic steps before downstream steps."""
        updated_plan = deepcopy(plan)
        failed_step = updated_plan.get_step(failed_step_id)

        if not failed_step:
            return updated_plan

        failed_step.mark_failed(error=error_message)

        # Generate unique remediation step IDs
        remediation_diag_id = f"{failed_step_id}-diag-{uuid.uuid4().hex[:4]}"
        remediation_fix_id = f"{failed_step_id}-fix-{uuid.uuid4().hex[:4]}"
        remediation_retest_id = f"{failed_step_id}-retest-{uuid.uuid4().hex[:4]}"

        # Step A: Diagnose root cause of failure
        diag_step = PlanStep(
            step_id=remediation_diag_id,
            title=f"Diagnose Failure: {failed_step.title}",
            description=f"Investigate cause of failure: {error_message[:100]}",
            step_type=PlanStepType.INVESTIGATION,
            dependencies=[failed_step_id],
            target_files=failed_step.target_files,
            target_symbols=failed_step.target_symbols,
            required_tools=["read_file", "search_code", "run_command"],
            acceptance_criteria="Root cause of the tool failure or broken assertion is isolated.",
            status=StepStatus.PENDING,
            metadata={"remediation_for": failed_step_id, "original_error": error_message},
        )

        # Step B: Apply corrective patch
        fix_step = PlanStep(
            step_id=remediation_fix_id,
            title=f"Remediate & Patch: {failed_step.title}",
            description=f"Apply targeted correction to resolve error encountered in step {failed_step_id}.",
            step_type=PlanStepType.IMPLEMENTATION,
            dependencies=[remediation_diag_id],
            target_files=failed_step.target_files,
            target_symbols=failed_step.target_symbols,
            required_tools=["edit_file", "write_file"],
            acceptance_criteria="Corrective patch applied successfully.",
            status=StepStatus.PENDING,
            metadata={"remediation_for": failed_step_id},
        )

        # Step C: Re-verify
        retest_step = PlanStep(
            step_id=remediation_retest_id,
            title=f"Re-verify: {failed_step.title}",
            description=f"Validate that corrective fix resolved failure and restored green baseline.",
            step_type=PlanStepType.VERIFICATION,
            dependencies=[remediation_fix_id],
            target_files=failed_step.target_files,
            target_symbols=failed_step.target_symbols,
            required_tools=["run_command"],
            acceptance_criteria="Verification tests pass cleanly.",
            status=StepStatus.PENDING,
            metadata={"remediation_for": failed_step_id},
        )

        # Locate position of failed step to insert remediation steps immediately following
        insert_idx = len(updated_plan.steps)
        for i, s in enumerate(updated_plan.steps):
            if s.step_id == failed_step_id:
                insert_idx = i + 1
                break

        remediation_steps = [diag_step, fix_step, retest_step]
        for idx, r_step in enumerate(remediation_steps):
            updated_plan.steps.insert(insert_idx + idx, r_step)

        # Rewire any downstream steps that directly depended on failed_step_id to now depend on retest_step
        for s in updated_plan.steps:
            if s.step_id not in (failed_step_id, remediation_diag_id, remediation_fix_id, remediation_retest_id):
                if failed_step_id in s.dependencies:
                    s.dependencies.remove(failed_step_id)
                    if remediation_retest_id not in s.dependencies:
                        s.dependencies.append(remediation_retest_id)

        updated_plan.updated_at = datetime.now(timezone.utc).isoformat()
        updated_plan.current_step_id = remediation_diag_id
        return updated_plan

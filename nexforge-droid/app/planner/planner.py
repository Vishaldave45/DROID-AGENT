"""Explicit Task Planner generating structured multi-step ExecutionPlans (Phase 8)."""

import os
from typing import Any, Dict, List, Optional, Set
import uuid

from app.context.base import ContextPackage, EngineeringGraphNode, RepositorySummary
from app.context.engineering_graph import EngineeringGraph
from app.planner.base import ExecutionPlan, PlanStep, PlanStepType, StepStatus


class ExplicitTaskPlanner:
    """Generates structured DAG execution plans broken into clear engineering phases."""

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = os.path.abspath(workspace_root) if workspace_root else os.getcwd()

    def generate_plan(
        self,
        task_id: str,
        task_requirement: str,
        context_package: Optional[ContextPackage] = None,
        engineering_graph: Optional[EngineeringGraph] = None,
    ) -> ExecutionPlan:
        """Constructs a deterministic, well-formed DAG execution plan for the engineering objective."""
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"
        req_lower = task_requirement.lower()

        steps: List[PlanStep] = []

        # Target files / symbols extracted from context
        target_files: List[str] = []
        target_symbols: List[str] = []

        if context_package:
            target_files = list(context_package.relevant_files.keys())
            target_symbols = [s.name for s in context_package.symbols[:5]]

        # Step 1: DISCOVERY
        s1 = PlanStep(
            step_id="step-1",
            title="Repository & Codebase Discovery",
            description=f"Inspect repository structure, locate modules and files related to: '{task_requirement[:60]}...'",
            step_type=PlanStepType.DISCOVERY,
            dependencies=[],
            target_files=target_files[:3],
            target_symbols=[],
            required_tools=["list_dir", "find_files", "search_code"],
            acceptance_criteria="Relevant source files, manifests, and test suites are mapped and identified.",
            status=StepStatus.PENDING,
        )
        steps.append(s1)

        # Step 2: INVESTIGATION
        s2 = PlanStep(
            step_id="step-2",
            title="Symbol Analysis & Root Cause Investigation",
            description="Examine AST symbol call hierarchy, signatures, and target logic to determine exact changes needed.",
            step_type=PlanStepType.INVESTIGATION,
            dependencies=["step-1"],
            target_files=target_files[:3],
            target_symbols=target_symbols[:4],
            required_tools=["read_file", "search_code"],
            acceptance_criteria="Target function/class lines and failure points are pinpointed with no ambiguity.",
            status=StepStatus.PENDING,
        )
        steps.append(s2)

        # Step 3: IMPLEMENTATION
        is_refactor = "refactor" in req_lower or "cleanup" in req_lower
        s3 = PlanStep(
            step_id="step-3",
            title="Surgical Code Implementation" if not is_refactor else "Code Refactoring & Cleanup",
            description=f"Apply targeted modifications to fulfill requirement: '{task_requirement[:80]}'",
            step_type=PlanStepType.IMPLEMENTATION if not is_refactor else PlanStepType.REFACTOR,
            dependencies=["step-2"],
            target_files=target_files[:2],
            target_symbols=target_symbols[:3],
            required_tools=["edit_file", "write_file"],
            acceptance_criteria="Source files updated cleanly with no syntax regressions.",
            status=StepStatus.PENDING,
        )
        steps.append(s3)

        # Step 4: VERIFICATION
        s4 = PlanStep(
            step_id="step-4",
            title="Automated Test & Validation Gate",
            description="Run unit test suite or targeted validation commands to confirm zero regressions.",
            step_type=PlanStepType.VERIFICATION,
            dependencies=["step-3"],
            target_files=target_files[:2],
            target_symbols=target_symbols[:2],
            required_tools=["run_command"],
            acceptance_criteria="All relevant unit test assertions pass with exit code 0.",
            status=StepStatus.PENDING,
        )
        steps.append(s4)

        # Step 5: ACCEPTANCE & COMPLETION
        s5 = PlanStep(
            step_id="step-5",
            title="Task Review & Acceptance Sign-off",
            description="Perform final verification summary and sign-off task with verification evidence.",
            step_type=PlanStepType.DOCUMENTATION,
            dependencies=["step-4"],
            target_files=[],
            target_symbols=[],
            required_tools=["finish_task"],
            acceptance_criteria="Task status marked SUCCESS with clear summary evidence.",
            status=StepStatus.PENDING,
        )
        steps.append(s5)

        plan = ExecutionPlan(
            plan_id=plan_id,
            task_id=task_id,
            title=f"Plan: {task_requirement[:50]}",
            objective=task_requirement,
            steps=steps,
            current_step_id="step-1",
            metadata={
                "target_files_count": len(target_files),
                "target_symbols_count": len(target_symbols),
                "is_refactor": is_refactor,
            },
        )

        return plan

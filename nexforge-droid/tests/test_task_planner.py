"""Unit tests for Phase 8 Explicit Task Planner and Dynamic Replanning."""

import unittest

from app.planner.base import ExecutionPlan, PlanStep, PlanStepType, StepStatus
from app.planner.controller import PlanExecutionController
from app.planner.planner import ExplicitTaskPlanner
from app.planner.replanner import DynamicReplanner
from app.planner.tools import GeneratePlanTool, ReplanTaskTool
from app.storage.base import InMemoryTaskStore, TaskState, TaskStatus


class TestTaskPlanner(unittest.TestCase):
    """Test suite for execution plan generation, DAG validation, progression, and dynamic replanning."""

    def test_plan_generation_and_dag_validity(self) -> None:
        planner = ExplicitTaskPlanner()
        plan = planner.generate_plan(
            task_id="task-test-01",
            task_requirement="Fix zero division error in calculate_average",
        )

        self.assertIsInstance(plan, ExecutionPlan)
        self.assertEqual(len(plan.steps), 5)
        self.assertEqual(plan.steps[0].step_type, PlanStepType.DISCOVERY)
        self.assertEqual(plan.steps[3].step_type, PlanStepType.VERIFICATION)

        # Validate DAG
        is_valid, err = plan.is_valid_dag()
        self.assertTrue(is_valid, f"DAG must be valid: {err}")
        self.assertIsNone(err)

    def test_dag_cycle_detection(self) -> None:
        s1 = PlanStep(step_id="step-1", title="Step 1", description="", step_type=PlanStepType.DISCOVERY, dependencies=["step-2"])
        s2 = PlanStep(step_id="step-2", title="Step 2", description="", step_type=PlanStepType.IMPLEMENTATION, dependencies=["step-1"])
        plan = ExecutionPlan(plan_id="cyclic-plan", task_id="task-cycle", title="Cyclic", objective="", steps=[s1, s2])

        is_valid, err = plan.is_valid_dag()
        self.assertFalse(is_valid)
        self.assertIn("cycle", err.lower())

    def test_step_progression_and_runnable_steps(self) -> None:
        planner = ExplicitTaskPlanner()
        plan = planner.generate_plan(task_id="task-prog", task_requirement="Add logging to agent runtime")

        # Initially, only step-1 (no dependencies) should be runnable
        runnable = plan.get_next_runnable_steps()
        self.assertEqual(len(runnable), 1)
        self.assertEqual(runnable[0].step_id, "step-1")
        self.assertEqual(plan.progress_percentage(), 0.0)

        # Mark step-1 completed
        plan.steps[0].mark_completed(evidence="Files located.")
        runnable = plan.get_next_runnable_steps()
        self.assertEqual(len(runnable), 1)
        self.assertEqual(runnable[0].step_id, "step-2")
        self.assertEqual(plan.progress_percentage(), 20.0)

    def test_dynamic_replanner_on_failure(self) -> None:
        planner = ExplicitTaskPlanner()
        plan = planner.generate_plan(task_id="task-fail-demo", task_requirement="Refactor database schemas")

        replanner = DynamicReplanner()
        mutated_plan = replanner.replan_on_failure(
            plan=plan,
            failed_step_id="step-3",
            error_message="SyntaxError: invalid syntax at line 42",
        )

        self.assertGreater(len(mutated_plan.steps), len(plan.steps))
        failed_step = mutated_plan.get_step("step-3")
        self.assertIsNotNone(failed_step)
        self.assertEqual(failed_step.status, StepStatus.FAILED)

        # Check that remediation steps exist
        remediation_steps = [s for s in mutated_plan.steps if "remediation_for" in s.metadata]
        self.assertEqual(len(remediation_steps), 3)

        # Verify DAG validity of the mutated plan
        is_valid, err = mutated_plan.is_valid_dag()
        self.assertTrue(is_valid, f"Mutated plan must be a valid DAG: {err}")

    def test_plan_execution_controller_with_task_state(self) -> None:
        store = InMemoryTaskStore()
        controller = PlanExecutionController(task_store=store)

        state = TaskState(
            task_id="task-state-001",
            repository_id="repo-main",
            requirement="Implement user authentication token verification",
            status=TaskStatus.PLANNING,
        )
        planner = ExplicitTaskPlanner()
        plan = planner.generate_plan(task_id=state.task_id, task_requirement=state.requirement)

        controller.attach_plan_to_state(state, plan)
        loaded_plan = controller.get_plan_from_state(state)
        self.assertIsNotNone(loaded_plan)
        self.assertEqual(len(loaded_plan.steps), 5)

        # Advance step 1
        updated_plan, next_step = controller.advance_step(
            state=state,
            step_id="step-1",
            new_status=StepStatus.COMPLETED,
            evidence="Auth middleware identified in src/auth.py",
        )
        self.assertIsNotNone(next_step)
        self.assertEqual(next_step.step_id, "step-2")

    def test_planner_tool_dispatch(self) -> None:
        gen_tool = GeneratePlanTool()
        res = gen_tool.execute(task_requirement="Fix regression in payment gateway")
        self.assertTrue(res.success)
        self.assertIn("plan", res.data)
        self.assertEqual(res.data["total_steps"], 5)

        # Test replan tool
        replan_tool = ReplanTaskTool()
        replan_res = replan_tool.execute(
            plan_dict=res.data["plan"],
            failed_step_id="step-4",
            error_message="Test failed: AssertionError in test_payment",
        )
        self.assertTrue(replan_res.success)
        self.assertGreater(replan_res.data["new_steps_count"], 5)


if __name__ == "__main__":
    unittest.main()

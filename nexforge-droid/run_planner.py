#!/usr/bin/env python3
"""CLI utility for Context Engine token budgeting and Explicit Task Planner (Phase 7 & 8)."""

import argparse
import json
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.context.base import ContextBudget
from app.context.budget import ContextGovernor, TieredTokenBudget, TokenEstimator, TokenModelPreset
from app.context.engine import RepositoryContextEngine
from app.context.engineering_graph import EngineeringGraph
from app.context.scanner import RepositoryScanner
from app.planner.base import ExecutionPlan, PlanStepType, StepStatus
from app.planner.controller import PlanExecutionController
from app.planner.planner import ExplicitTaskPlanner
from app.planner.replanner import DynamicReplanner


def main() -> None:
    parser = argparse.ArgumentParser(description="NexForge Droid Context Budgeting & Task Planner CLI (Phase 7 & 8)")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Command: plan
    plan_parser = subparsers.add_parser("plan", help="Generate an explicit execution plan for a task")
    plan_parser.add_argument("requirement", type=str, help="Engineering task requirement/objective")
    plan_parser.add_argument("--repo", type=str, default=".", help="Repository path")
    plan_parser.add_argument("--task-id", type=str, default="task-cli-001", help="Task ID")
    plan_parser.add_argument("--json", action="store_true", help="Output raw JSON")

    # Command: replan
    replan_parser = subparsers.add_parser("replan", help="Simulate failure and dynamic replanning")
    replan_parser.add_argument("requirement", type=str, help="Initial task requirement")
    replan_parser.add_argument("--failed-step", type=str, default="step-3", help="Step ID that failed")
    replan_parser.add_argument("--error", type=str, default="AssertionError: Expected status 200 but got 500", help="Error message")

    # Command: context
    context_parser = subparsers.add_parser("context", help="Assemble budgeted context for a task")
    context_parser.add_argument("requirement", type=str, help="Task requirement")
    context_parser.add_argument("--repo", type=str, default=".", help="Repository path")
    context_parser.add_argument("--budget", type=int, default=16000, help="Max total token budget")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "plan":
        planner = ExplicitTaskPlanner(workspace_root=args.repo)
        engine = RepositoryContextEngine(repo_root=args.repo)
        context_pkg = engine.build_context(task_requirement=args.requirement, repo_root=args.repo)
        plan = planner.generate_plan(task_id=args.task_id, task_requirement=args.requirement, context_package=context_pkg)

        if args.json:
            print(json.dumps(plan.to_dict(), indent=2))
        else:
            print(f"=== Execution Plan: {plan.title} ===")
            print(f"Plan ID: {plan.plan_id} | Objective: {plan.objective}")
            print(f"Total Steps: {len(plan.steps)} | Progress: {plan.progress_percentage()}%")
            print("\nSteps DAG:")
            for s in plan.steps:
                deps = f" [depends on: {', '.join(s.dependencies)}]" if s.dependencies else " [Root]"
                print(f"  [{s.status.value}] {s.step_id}: {s.title} ({s.step_type.value}){deps}")
                print(f"       Acceptance: {s.acceptance_criteria}")
                if s.target_files:
                    print(f"       Target files: {', '.join(s.target_files)}")

    elif args.command == "replan":
        planner = ExplicitTaskPlanner()
        initial_plan = planner.generate_plan(task_id="task-replan-demo", task_requirement=args.requirement)
        print("=== Initial Plan Steps ===")
        for s in initial_plan.steps:
            print(f"  - {s.step_id}: {s.title} (Status: {s.status.value})")

        print(f"\n>> Simulating failure on '{args.failed_step}': {args.error}")
        replanner = DynamicReplanner()
        new_plan = replanner.replan_on_failure(
            plan=initial_plan,
            failed_step_id=args.failed_step,
            error_message=args.error,
        )

        print("\n=== Mutated & Remediated Plan Steps ===")
        for s in new_plan.steps:
            deps = f" (deps: {', '.join(s.dependencies)})" if s.dependencies else ""
            print(f"  - [{s.status.value}] {s.step_id}: {s.title}{deps}")

    elif args.command == "context":
        engine = RepositoryContextEngine(repo_root=args.repo)
        budget = ContextBudget(max_total_tokens=args.budget)
        ctx = engine.build_context(task_requirement=args.requirement, repo_root=args.repo, budget=budget)
        print(f"=== Budgeted Context Package for: '{args.requirement}' ===")
        print(f"Total Estimated Tokens: {ctx.estimated_tokens} (Budget Cap: {args.budget})")
        print(f"Symbols Included: {len(ctx.symbols)}")
        print(f"Files Sliced: {len(ctx.relevant_files)}")
        for f_path in ctx.relevant_files.keys():
            print(f"  - File slice: {f_path} ({len(ctx.relevant_files[f_path])} chars)")
        print(f"Telemetry: {json.dumps(ctx.metadata, indent=2)}")


if __name__ == "__main__":
    main()

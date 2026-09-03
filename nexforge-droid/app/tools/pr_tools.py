"""Git, Pull Request & CI/CD Lifecycle Tools for NexForge Droid (Phase 17)."""

from typing import Any, Dict, List, Optional

from app.git.branch import GitBranchManager
from app.git.ci_pipeline import CISelfHealingEngine
from app.git.pr_generator import PullRequestSynthesizer
from app.git.worktree import GitWorktreeManager
from app.tools.base import Tool, ToolResult


class GitBranchTool(Tool):
    """Tool for listing, creating, and switching Git branches."""

    name = "git_branch"
    description = "Manage Git branches: list existing branches, create new feature branches, or switch active branch."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create", "switch", "delete"],
                "description": "Branch operation to perform.",
            },
            "branch_name": {
                "type": "string",
                "description": "Name of the branch (required for create, switch, delete).",
            },
            "start_point": {
                "type": "string",
                "description": "Starting commit or branch for new branch (default main).",
            },
        },
        "required": ["action"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "list")
        branch_name = kwargs.get("branch_name")
        start_point = kwargs.get("start_point", "main")

        mgr = GitBranchManager()

        if action == "list":
            branches = [b.to_dict() for b in mgr.list_branches()]
            return ToolResult(success=True, data={"branches": branches, "count": len(branches)})

        if not branch_name:
            return ToolResult(success=False, error="branch_name parameter is required for this action.")

        if action == "create":
            try:
                b = mgr.create_branch(branch_name, start_point=start_point, switch=True)
                return ToolResult(success=True, data={"created_branch": b.to_dict(), "switched": True})
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        if action == "switch":
            ok = mgr.switch_branch(branch_name)
            return ToolResult(success=ok, data={"switched_to": branch_name} if ok else None, error="Branch switch failed" if not ok else None)

        if action == "delete":
            try:
                ok = mgr.delete_branch(branch_name)
                return ToolResult(success=ok, data={"deleted": branch_name} if ok else None)
            except Exception as e:
                return ToolResult(success=False, error=str(e))

        return ToolResult(success=False, error=f"Unknown action: {action}")


class GitWorktreeTool(Tool):
    """Tool for creating and managing isolated worktree sandboxes."""

    name = "git_worktree"
    description = "Create and inspect isolated Git worktree sandboxes to build and test code without dirtying workspace."
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "create", "remove", "prune"],
                "description": "Worktree action to perform.",
            },
            "branch": {
                "type": "string",
                "description": "Branch to check out inside the worktree (required for create).",
            },
            "worktree_id": {
                "type": "string",
                "description": "ID of worktree to remove.",
            },
        },
        "required": ["action"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "list")
        mgr = GitWorktreeManager()

        if action == "list":
            wts = [w.to_dict() for w in mgr.list_worktrees()]
            return ToolResult(success=True, data={"worktrees": wts, "count": len(wts)})

        if action == "create":
            branch = kwargs.get("branch", "feat/isolated-sandbox")
            wt = mgr.create_worktree(branch=branch)
            return ToolResult(success=True, data={"worktree": wt.to_dict()})

        if action == "remove":
            wt_id = kwargs.get("worktree_id")
            if not wt_id:
                return ToolResult(success=False, error="worktree_id required for remove action.")
            ok = mgr.remove_worktree(wt_id)
            return ToolResult(success=ok, data={"removed": wt_id})

        if action == "prune":
            cnt = mgr.prune()
            return ToolResult(success=True, data={"active_count": cnt})

        return ToolResult(success=False, error=f"Unknown action: {action}")


class GitGeneratePRTool(Tool):
    """Tool for synthesizing comprehensive GitHub-ready Pull Request markdown."""

    name = "git_generate_pr"
    description = "Synthesize an automated Pull Request description with diff breakdown, AST symbol impact, and risk checklist."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Custom PR title (optional, auto-synthesized if omitted).",
            },
            "branch_source": {
                "type": "string",
                "description": "Source feature branch (e.g. feat/mcp-gateway).",
            },
            "branch_target": {
                "type": "string",
                "description": "Target base branch (default main).",
            },
            "task_objective": {
                "type": "string",
                "description": "High-level goal achieved by this PR.",
            },
        },
        "required": ["branch_source"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        branch_source = kwargs.get("branch_source", "feat/nexforge-feature")
        branch_target = kwargs.get("branch_target", "main")
        title = kwargs.get("title")
        task_objective = kwargs.get("task_objective")

        synthesizer = PullRequestSynthesizer()
        pr_spec = synthesizer.synthesize_pr(
            title=title,
            branch_source=branch_source,
            branch_target=branch_target,
            task_objective=task_objective,
        )

        return ToolResult(success=True, data={"pr": pr_spec.to_dict(), "markdown": pr_spec.markdown_body})


class GitRunCITool(Tool):
    """Tool for running the 5-stage CI/CD pipeline matrix."""

    name = "git_run_ci"
    description = "Run 5-stage CI/CD pipeline (syntax, security, unit tests, quality gate, packaging) with detailed step logging."
    input_schema = {
        "type": "object",
        "properties": {
            "branch": {
                "type": "string",
                "description": "Branch to run CI against.",
            },
            "simulate_failure_stage": {
                "type": "string",
                "enum": ["syntax_ast", "security_audit", "unit_tests", "quality_gate", "build_packaging"],
                "description": "Optional stage to simulate a failure for testing self-healing.",
            },
        },
        "required": [],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        branch = kwargs.get("branch", "main")
        simulate_failure = kwargs.get("simulate_failure_stage")

        engine = CISelfHealingEngine()
        pipeline_run = engine.run_pipeline(branch=branch, simulate_failure_stage=simulate_failure)
        return ToolResult(success=True, data={"pipeline": pipeline_run.to_dict()})


class GitHealCITool(Tool):
    """Tool for applying autonomous self-healing repairs to failing CI pipelines."""

    name = "git_heal_ci"
    description = "Analyze failing CI stages, synthesize hotfix patches, apply them, and re-verify pipeline to green."
    input_schema = {
        "type": "object",
        "properties": {
            "branch": {
                "type": "string",
                "description": "Branch to heal.",
            },
            "failed_stage": {
                "type": "string",
                "description": "Stage that failed and requires repair.",
            },
        },
        "required": ["failed_stage"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        branch = kwargs.get("branch", "main")
        failed_stage = kwargs.get("failed_stage")

        engine = CISelfHealingEngine()
        # First create the failed run
        failed_run = engine.run_pipeline(branch=branch, simulate_failure_stage=failed_stage)
        # Now heal it
        healed_run = engine.heal_pipeline(failed_run)

        return ToolResult(
            success=True,
            data={
                "healed_pipeline": healed_run.to_dict(),
                "healed_patch": healed_run.healed_patch,
                "healing_attempts": healed_run.healing_attempts,
            },
        )

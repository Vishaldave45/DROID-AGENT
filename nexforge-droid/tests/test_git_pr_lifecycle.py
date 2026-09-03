"""Unit tests for Phase 17: Autonomous Git Worktrees, Branching, PR Lifecycle & CI/CD Self-Healing."""

import os
import shutil
import tempfile
import unittest

from app.git.branch import GitBranch, GitBranchManager
from app.git.ci_pipeline import CIPipelineRun, CISelfHealingEngine
from app.git.pr_generator import PullRequestSpec, PullRequestSynthesizer
from app.git.worktree import GitWorktreeManager, WorktreeSandbox
from app.tools import get_default_tool_registry


class TestGitPRLifecycle(unittest.TestCase):
    """Test suite for Git branching, isolated worktrees, PR generation, and CI self-healing."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.branch_mgr = GitBranchManager(repo_path=self.temp_dir)
        self.worktree_mgr = GitWorktreeManager(
            repo_path=self.temp_dir,
            worktree_root=os.path.join(self.temp_dir, ".worktrees"),
        )
        self.pr_synthesizer = PullRequestSynthesizer(repo_path=self.temp_dir)
        self.ci_engine = CISelfHealingEngine(repo_path=self.temp_dir)
        self.registry = get_default_tool_registry(workspace_root=self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_git_branch_validation_and_creation(self) -> None:
        """Verifies branch name validation and safe creation of feature branches."""
        # Test validation
        self.assertTrue(self.branch_mgr.validate_branch_name("feat/auth-service"))
        self.assertTrue(self.branch_mgr.validate_branch_name("fix/issue-102"))
        self.assertFalse(self.branch_mgr.validate_branch_name("invalid branch with spaces"))
        self.assertFalse(self.branch_mgr.validate_branch_name("bad..dots"))
        self.assertFalse(self.branch_mgr.validate_branch_name(""))

        # Test creation & switch
        b = self.branch_mgr.create_branch("feat/new-mcp-plugin", switch=True)
        self.assertEqual(b.name, "feat/new-mcp-plugin")
        self.assertTrue(b.is_current)

        branches = self.branch_mgr.list_branches()
        names = [br.name for br in branches]
        self.assertIn("feat/new-mcp-plugin", names)

    def test_git_branch_deletion_protection(self) -> None:
        """Verifies root branch deletion protection and normal branch deletion."""
        with self.assertRaises(ValueError):
            self.branch_mgr.delete_branch("main")

        self.branch_mgr.create_branch("chore/temp-cleanup")
        self.assertTrue(self.branch_mgr.delete_branch("chore/temp-cleanup"))
        names = [br.name for br in self.branch_mgr.list_branches()]
        self.assertNotIn("chore/temp-cleanup", names)

    def test_git_worktree_creation_and_listing(self) -> None:
        """Verifies isolated worktree sandbox creation and discovery."""
        wt = self.worktree_mgr.create_worktree(
            branch="feat/isolated-runner",
            task_id="task-test-99",
        )
        self.assertIsNotNone(wt.worktree_id)
        self.assertEqual(wt.branch, "feat/isolated-runner")
        self.assertTrue(os.path.isdir(wt.path))

        all_wts = self.worktree_mgr.list_worktrees()
        wt_ids = [w.worktree_id for w in all_wts]
        self.assertIn(wt.worktree_id, wt_ids)

    def test_git_worktree_cleanup_and_remove(self) -> None:
        """Verifies safe removal and directory cleanup of worktrees."""
        wt = self.worktree_mgr.create_worktree(branch="feat/discard-worktree")
        self.assertTrue(os.path.isdir(wt.path))

        ok = self.worktree_mgr.remove_worktree(wt.worktree_id)
        self.assertTrue(ok)
        self.assertFalse(os.path.exists(wt.path))

    def test_pr_synthesis_and_markdown_rendering(self) -> None:
        """Verifies autonomous PR synthesis, risk evaluation, and markdown format."""
        spec = self.pr_synthesizer.synthesize_pr(
            title="feat(mcp): universal client tool gateway",
            branch_source="feat/mcp-gateway",
            branch_target="main",
            task_objective="Implement dual-role MCP server and external tool federation.",
        )
        self.assertIsInstance(spec, PullRequestSpec)
        self.assertEqual(spec.title, "feat(mcp): universal client tool gateway")
        self.assertEqual(spec.risk_assessment.get("risk_level"), "LOW")
        self.assertGreater(len(spec.files_changed), 0)
        self.assertGreater(len(spec.checklist), 0)

        # Verify markdown content
        md = spec.markdown_body
        self.assertIn("# feat(mcp): universal client tool gateway", md)
        self.assertIn("## 🎯 Executive Summary", md)
        self.assertIn("## 📁 Modified Files & AST Symbols", md)
        self.assertIn("## 🧪 Verification & Test Results", md)
        self.assertIn("## 🛡️ Risk Assessment & Security", md)
        self.assertIn("## ✅ Autonomous Quality Checklist", md)

    def test_ci_pipeline_runner_all_passed(self) -> None:
        """Verifies 5-stage CI/CD pipeline execution with all stages passing."""
        pipeline_run = self.ci_engine.run_pipeline(branch="main")
        self.assertEqual(pipeline_run.status, "passed")
        self.assertEqual(len(pipeline_run.stages), 5)
        for stage in pipeline_run.stages:
            self.assertEqual(stage.status, "passed")
            self.assertGreater(len(stage.logs), 0)

    def test_ci_pipeline_simulation_failure_and_self_healing(self) -> None:
        """Verifies simulated CI stage failure triggers closed-loop self-healing."""
        # Run with simulated unit test failure
        failed_run = self.ci_engine.run_pipeline(
            branch="feat/broken-code",
            simulate_failure_stage="unit_tests",
        )
        self.assertEqual(failed_run.status, "failed")
        failed_stage = next(s for s in failed_run.stages if s.stage_id == "unit_tests")
        self.assertEqual(failed_stage.status, "failed")
        self.assertIn("AssertionError", failed_stage.error_signature or "")

        # Execute autonomous self-healing
        healed_run = self.ci_engine.heal_pipeline(failed_run)
        self.assertEqual(healed_run.status, "healed")
        self.assertEqual(healed_run.healing_attempts, 1)
        self.assertIsNotNone(healed_run.healed_patch)
        self.assertEqual(failed_stage.status, "healed")
        self.assertIn("SELF-HEALING AGENT", failed_stage.logs)

    def test_git_pr_lifecycle_tools_in_registry(self) -> None:
        """Verifies git_branch, git_worktree, git_generate_pr, git_run_ci, and git_heal_ci in ToolRegistry."""
        # 1. git_branch
        res = self.registry.dispatch("git_branch", {"action": "list"})
        self.assertTrue(res.success)
        self.assertIn("branches", res.data)

        # 2. git_worktree
        res = self.registry.dispatch("git_worktree", {"action": "list"})
        self.assertTrue(res.success)
        self.assertIn("worktrees", res.data)

        # 3. git_generate_pr
        res = self.registry.dispatch("git_generate_pr", {"branch_source": "feat/tool-integration"})
        self.assertTrue(res.success)
        self.assertIn("pr", res.data)
        self.assertIn("markdown", res.data)

        # 4. git_run_ci
        res = self.registry.dispatch("git_run_ci", {"branch": "main"})
        self.assertTrue(res.success)
        self.assertEqual(res.data["pipeline"]["status"], "passed")

        # 5. git_heal_ci
        res = self.registry.dispatch("git_heal_ci", {"branch": "feat/broken", "failed_stage": "syntax_ast"})
        self.assertTrue(res.success)
        self.assertEqual(res.data["healed_pipeline"]["status"], "healed")
        self.assertIsNotNone(res.data["healed_patch"])


if __name__ == "__main__":
    unittest.main()

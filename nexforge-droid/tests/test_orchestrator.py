"""Unit tests for Phase 11: Workspace Orchestration, Multi-File Refactoring, and PR Generator."""

import os
import tempfile
import unittest

from app.orchestrator.changeset_manager import ChangesetManager
from app.orchestrator.human_gate import HumanApprovalGate, RiskLevel
from app.orchestrator.refactor_engine import (
    MultiFileRefactorEngine,
    SymbolRenameRequest,
)
from app.orchestrator.tools import (
    ApplyMultiFileRefactorTool,
    CreateChangesetTool,
    GeneratePullRequestTool,
    RequestHumanApprovalTool,
)


class TestChangesetManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.manager = ChangesetManager(workspace_root=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_create_and_stage_changeset(self):
        # Create a file in workspace
        file_path = "module_a.py"
        abs_path = os.path.join(self.tmp_dir.name, file_path)
        with open(abs_path, "w") as f:
            f.write("def calculate_metrics(data):\n    return sum(data)\n")

        cs = self.manager.create_changeset(
            title="Refactor Metrics Calculator",
            description="Adds validation check to metrics calculation.",
        )
        self.assertEqual(cs.status, "DRAFT")

        modified_code = "def calculate_metrics(data):\n    if not data:\n        return 0\n    return sum(data)\n"
        staged_file = self.manager.stage_file_change(
            changeset_id=cs.changeset_id,
            file_path=file_path,
            modified_content=modified_code,
        )

        self.assertTrue(staged_file.syntax_valid)
        self.assertGreater(staged_file.additions, 0)
        self.assertIn("Metrics Calculator", cs.commit_message)
        self.assertIn("Pull Request", cs.pr_body)

        # Apply atomically
        res = self.manager.apply_changeset_atomically(cs.changeset_id)
        self.assertTrue(res["success"])
        self.assertEqual(cs.status, "COMMITTED")

        # Verify disk content
        with open(abs_path, "r") as f:
            updated = f.read()
        self.assertEqual(updated, modified_code)


class TestHumanApprovalGate(unittest.TestCase):
    def setUp(self):
        self.gate = HumanApprovalGate()

    def test_request_and_approve(self):
        req = self.gate.request_approval(
            action_type="COMMAND_EXEC",
            description="Run database migration on production branch",
            risk_level=RiskLevel.HIGH,
            payload={"command": "alembic upgrade head"},
        )
        self.assertEqual(req.status, "PENDING")
        self.assertEqual(req.risk_level, "HIGH")

        # Approve
        approved = self.gate.approve(req.request_id, approver="security_lead")
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(approved.resolved_by, "security_lead")

    def test_request_and_reject(self):
        req = self.gate.request_approval(
            action_type="FILE_DELETE",
            description="Delete root config",
            risk_level=RiskLevel.CRITICAL,
        )
        rejected = self.gate.reject(req.request_id, reason="Dangerous operation denied")
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.reason, "Dangerous operation denied")


class TestMultiFileRefactorEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.engine = MultiFileRefactorEngine(workspace_root=self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_multi_file_symbol_rename(self):
        # Create two files sharing a symbol
        file_1 = os.path.join(self.tmp_dir.name, "service.py")
        with open(file_1, "w") as f:
            f.write("def fetch_user_record(uid):\n    return {'uid': uid}\n")

        file_2 = os.path.join(self.tmp_dir.name, "controller.py")
        with open(file_2, "w") as f:
            f.write("from service import fetch_user_record\n\nres = fetch_user_record(42)\n")

        req = SymbolRenameRequest(
            old_name="fetch_user_record",
            new_name="retrieve_user_profile",
            target_files=["service.py", "controller.py"],
        )
        plan = self.engine.plan_symbol_rename(req)
        self.assertEqual(len(plan.affected_files), 2)
        self.assertTrue(plan.all_syntax_valid)

        cs = self.engine.execute_refactor_to_changeset(plan)
        self.assertEqual(cs.total_files, 2)
        self.assertIn("retrieve_user_profile", cs.pr_body)


if __name__ == "__main__":
    unittest.main()

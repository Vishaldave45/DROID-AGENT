"""Unit tests for security policies and path traversal prevention."""

import tempfile
import unittest
from pathlib import Path
from app.security.base import DefaultPolicyEngine, PolicyDecision, SecurityContext


class TestSecurityPolicy(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = self.temp_dir.name
        self.context = SecurityContext(workspace_root=self.workspace)
        self.engine = DefaultPolicyEngine()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_safe_path_allowed(self) -> None:
        safe_file = str(Path(self.workspace) / "src" / "main.py")
        decision = self.engine.evaluate(
            tool_name="read_file",
            arguments={"path": safe_file},
            context=self.context,
        )
        self.assertEqual(decision, PolicyDecision.ALLOW)

    def test_path_traversal_denied(self) -> None:
        escaped_path = "/etc/passwd"
        decision = self.engine.evaluate(
            tool_name="read_file",
            arguments={"path": escaped_path},
            context=self.context,
        )
        self.assertEqual(decision, PolicyDecision.DENY)

    def test_dangerous_command_denied(self) -> None:
        decision = self.engine.evaluate(
            tool_name="run_command",
            arguments={"command": "rm -rf /"},
            context=self.context,
        )
        self.assertEqual(decision, PolicyDecision.DENY)

    def test_git_push_requires_approval(self) -> None:
        decision = self.engine.evaluate(
            tool_name="git_push",
            arguments={"remote": "origin", "branch": "main"},
            context=self.context,
        )
        self.assertEqual(decision, PolicyDecision.APPROVE)


if __name__ == "__main__":
    unittest.main()

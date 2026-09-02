"""Unit tests verifying all architectural component interfaces and manifest contracts."""

import unittest
from app.main import get_system_manifest
from app.llm.base import ChatMessage, ChatRole, LLMProvider, LLMResponse
from app.context.base import ContextEngine, ContextPackage, ContextBudget, RepositorySummary
from app.execution.base import SandboxExecutor, ExecutionRequest, ExecutionResult
from app.git.base import GitEngine, GitStatus, GitDiff
from app.evaluation.base import EvaluationEngine, EvaluationResult
from app.agent.base import DroidRuntime, AgentStepResult


class TestArchitectureContracts(unittest.TestCase):

    def test_system_manifest_integrity(self) -> None:
        manifest = get_system_manifest()
        self.assertEqual(manifest["system"], "NexForge Droid")
        self.assertEqual(manifest["phase"], 0)
        required_subsystems = [
            "llm",
            "tools",
            "agent",
            "storage",
            "security",
            "context",
            "execution",
            "git",
            "evaluation",
            "observability",
        ]
        for sub in required_subsystems:
            self.assertIn(sub, manifest["subsystems"])

    def test_llm_message_dataclasses(self) -> None:
        msg = ChatMessage(role=ChatRole.USER, content="Hello")
        self.assertEqual(msg.role, ChatRole.USER)
        self.assertEqual(msg.content, "Hello")

    def test_context_package_structure(self) -> None:
        summary = RepositorySummary(
            root_path="/workspace",
            languages=["Python"],
            total_files=10,
            entry_points=["main.py"],
            test_frameworks=["pytest"],
            key_directories=["src", "tests"],
        )
        pkg = ContextPackage(
            task_id="t-1",
            repository_summary=summary,
            relevant_files={"main.py": "print('hello')"},
            symbols=[],
            estimated_tokens=500,
        )
        self.assertEqual(pkg.task_id, "t-1")
        self.assertEqual(pkg.repository_summary.languages, ["Python"])


if __name__ == "__main__":
    unittest.main()

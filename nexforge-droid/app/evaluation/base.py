"""Evaluation contracts and success verification."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EvaluationResult:
    """Structured objective assessment of task completion."""

    passed: bool
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    files_changed_count: int = 0
    security_findings_count: int = 0
    lint_errors_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


class EvaluationEngine(ABC):
    """Abstract interface for rigorous evaluation of agent output."""

    @abstractmethod
    def evaluate(self, task_id: str, repo_path: str) -> EvaluationResult:
        """Evaluates whether the task criteria and repository tests pass."""
        pass

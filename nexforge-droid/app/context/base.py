"""Context Engine contracts, token budgeting, and Graph representation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    IMPORT = "IMPORT"
    TEST = "TEST"


@dataclass
class EngineeringGraphNode:
    """Representation of code elements and relationships in the repository."""

    node_id: str
    node_type: NodeType
    name: str
    file_path: str
    line_start: int
    line_end: int
    dependencies: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class RepositorySummary:
    """High-level structural intelligence of the target codebase."""

    root_path: str
    languages: List[str]
    total_files: int
    entry_points: List[str]
    test_frameworks: List[str]
    key_directories: List[str]


@dataclass
class ContextBudget:
    """Token boundaries allocated to prevent prompt flooding."""

    max_total_tokens: int = 32000
    repo_summary_tokens: int = 2000
    symbol_context_tokens: int = 8000
    relevant_files_tokens: int = 16000
    tool_history_tokens: int = 6000


@dataclass
class ContextPackage:
    """Task-specific, budgeted context payload assembled for the Droid."""

    task_id: str
    repository_summary: RepositorySummary
    relevant_files: Dict[str, str]
    symbols: List[EngineeringGraphNode]
    estimated_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextEngine(ABC):
    """Abstract interface for task-specific repository context assembly."""

    @abstractmethod
    def build_context(self, task_requirement: str, repo_root: str, budget: Optional[ContextBudget] = None) -> ContextPackage:
        """Assembles a compact, high-signal context package for a specific task."""
        pass

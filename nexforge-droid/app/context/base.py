"""Context Engine contracts, token budgeting, and Engineering Graph representation."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class NodeType(str, Enum):
    FILE = "FILE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    METHOD = "METHOD"
    IMPORT = "IMPORT"
    TEST = "TEST"
    MODULE = "MODULE"
    VARIABLE = "VARIABLE"


class EdgeType(str, Enum):
    CONTAINS = "CONTAINS"       # File -> Class/Function, Class -> Method
    IMPORTS = "IMPORTS"         # File/Module -> Imported Module/Symbol
    CALLS = "CALLS"             # Function/Method -> Called Function/Method
    INHERITS = "INHERITS"       # Class -> Base Class
    REFERENCES = "REFERENCES"   # Code element -> Symbol reference
    TESTS = "TESTS"             # Test Function/Class -> Target Code Function/Class


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
    signature: Optional[str] = None
    async_function: bool = False
    decorators: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    complexity_score: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value if isinstance(self.node_type, NodeType) else str(self.node_type),
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "dependencies": self.dependencies,
            "docstring": self.docstring,
            "signature": self.signature,
            "async_function": self.async_function,
            "decorators": self.decorators,
            "parent_id": self.parent_id,
            "complexity_score": self.complexity_score,
            "metadata": self.metadata,
        }


@dataclass
class EngineeringGraphEdge:
    """Directed relationship between code symbols or artifacts."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value if isinstance(self.edge_type, EdgeType) else str(self.edge_type),
            "weight": self.weight,
            "metadata": self.metadata,
        }


@dataclass
class DependencyManifest:
    """Parsed package dependency manifest file."""

    manifest_file: str
    manifest_type: str  # e.g. "requirements.txt", "package.json", "pyproject.toml"
    packages: Dict[str, str] = field(default_factory=dict)  # name -> version spec
    dev_packages: Dict[str, str] = field(default_factory=dict)


@dataclass
class FileMetric:
    """Individual file metadata and categorization."""

    path: str
    relative_path: str
    language: str
    size_bytes: int
    lines_of_code: int
    is_test: bool = False
    is_entry_point: bool = False


@dataclass
class RepositorySummary:
    """High-level structural intelligence of the target codebase."""

    root_path: str
    languages: List[str]
    total_files: int
    entry_points: List[str]
    test_frameworks: List[str]
    key_directories: List[str]
    total_lines_of_code: int = 0
    language_breakdown: Dict[str, int] = field(default_factory=dict)  # language -> file count
    frameworks: List[str] = field(default_factory=list)
    manifests: List[DependencyManifest] = field(default_factory=list)
    files: List[FileMetric] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "languages": self.languages,
            "total_files": self.total_files,
            "total_lines_of_code": self.total_lines_of_code,
            "entry_points": self.entry_points,
            "test_frameworks": self.test_frameworks,
            "key_directories": self.key_directories,
            "language_breakdown": self.language_breakdown,
            "frameworks": self.frameworks,
            "manifests": [
                {
                    "manifest_file": m.manifest_file,
                    "manifest_type": m.manifest_type,
                    "packages": m.packages,
                    "dev_packages": m.dev_packages,
                }
                for m in self.manifests
            ],
            "files_sample": [
                {
                    "path": f.path,
                    "relative_path": f.relative_path,
                    "language": f.language,
                    "size_bytes": f.size_bytes,
                    "lines_of_code": f.lines_of_code,
                    "is_test": f.is_test,
                    "is_entry_point": f.is_entry_point,
                }
                for f in self.files[:50]
            ],
        }


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "repository_summary": self.repository_summary.to_dict(),
            "relevant_files": self.relevant_files,
            "symbols": [s.to_dict() for s in self.symbols],
            "estimated_tokens": self.estimated_tokens,
            "metadata": self.metadata,
        }


class ContextEngine(ABC):
    """Abstract interface for task-specific repository context assembly."""

    @abstractmethod
    def build_context(self, task_requirement: str, repo_root: str, budget: Optional[ContextBudget] = None) -> ContextPackage:
        """Assembles a compact, high-signal context package for a specific task."""
        pass

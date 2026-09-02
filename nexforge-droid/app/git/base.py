"""Git VCS operations and diff models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GitStatus:
    """Working tree status."""

    current_branch: str
    modified_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    staged_files: List[str] = field(default_factory=list)
    is_clean: bool = True


@dataclass
class GitDiff:
    """Captured diff output."""

    patch: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


class GitEngine(ABC):
    """Abstract interface for Git operations."""

    @abstractmethod
    def status(self, repo_path: str) -> GitStatus:
        pass

    @abstractmethod
    def diff(self, repo_path: str, staged_only: bool = False) -> GitDiff:
        pass

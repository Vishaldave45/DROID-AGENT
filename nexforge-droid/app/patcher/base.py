"""Data models and type definitions for safe code modification and patching."""

from dataclasses import dataclass, field
import hashlib
import time
from typing import Any, Dict, List, Optional


@dataclass
class PatchHunk:
    """Represents a single unified diff hunk (@@ -old_start,old_len +new_start,new_len @@)."""
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[str] = field(default_factory=list)
    context_header: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_start": self.old_start,
            "old_length": self.old_length,
            "new_start": self.new_start,
            "new_length": self.new_length,
            "lines": self.lines,
            "context_header": self.context_header,
        }


@dataclass
class UnifiedDiff:
    """Represents a parsed unified diff containing one or more hunks for a file."""
    old_file: str
    new_file: str
    hunks: List[PatchHunk] = field(default_factory=list)
    raw_diff: str = ""

    @property
    def additions(self) -> int:
        count = 0
        for hunk in self.hunks:
            count += sum(1 for line in hunk.lines if line.startswith("+") and not line.startswith("+++"))
        return count

    @property
    def deletions(self) -> int:
        count = 0
        for hunk in self.hunks:
            count += sum(1 for line in hunk.lines if line.startswith("-") and not line.startswith("---"))
        return count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_file": self.old_file,
            "new_file": self.new_file,
            "hunks_count": len(self.hunks),
            "additions": self.additions,
            "deletions": self.deletions,
            "hunks": [h.to_dict() for h in self.hunks],
        }


@dataclass
class SurgicalEditChunk:
    """Represents a surgical target-replacement code edit."""
    target_content: str
    replacement_content: str
    allow_fuzzy: bool = False
    line_hint: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_content": self.target_content,
            "replacement_content": self.replacement_content,
            "allow_fuzzy": self.allow_fuzzy,
            "line_hint": self.line_hint,
        }


@dataclass
class FileSnapshot:
    """Immutable point-in-time snapshot of a file prior to modification."""
    path: str
    version: int
    sha256_hash: str
    content: str
    timestamp: float = field(default_factory=time.time)
    reason: str = "pre-edit"
    line_count: int = 0
    byte_count: int = 0

    def __post_init__(self):
        if not self.sha256_hash and self.content is not None:
            self.sha256_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.content is not None:
            self.line_count = len(self.content.splitlines())
            self.byte_count = len(self.content.encode("utf-8"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "version": self.version,
            "sha256_hash": self.sha256_hash,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "line_count": self.line_count,
            "byte_count": self.byte_count,
        }


@dataclass
class PatchResult:
    """Outcome of applying a patch or surgical edit."""
    success: bool
    file_path: str
    applied_hunks: int = 0
    failed_hunks: int = 0
    additions: int = 0
    deletions: int = 0
    modified_content: Optional[str] = None
    syntax_valid: bool = True
    syntax_error: Optional[str] = None
    syntax_error_line: Optional[int] = None
    error: Optional[str] = None
    pre_hash: Optional[str] = None
    post_hash: Optional[str] = None
    snapshot_version: Optional[int] = None
    stale_detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "applied_hunks": self.applied_hunks,
            "failed_hunks": self.failed_hunks,
            "additions": self.additions,
            "deletions": self.deletions,
            "syntax_valid": self.syntax_valid,
            "syntax_error": self.syntax_error,
            "syntax_error_line": self.syntax_error_line,
            "error": self.error,
            "pre_hash": self.pre_hash,
            "post_hash": self.post_hash,
            "snapshot_version": self.snapshot_version,
            "stale_detected": self.stale_detected,
        }

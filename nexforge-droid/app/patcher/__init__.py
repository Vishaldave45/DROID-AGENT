"""Safe Code Modification and Patching Engine for NexForge Droid."""

from app.patcher.base import (
    FileSnapshot,
    PatchHunk,
    PatchResult,
    SurgicalEditChunk,
    UnifiedDiff,
)
from app.patcher.diff_engine import DiffEngine
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor, StaleFileConflictError
from app.patcher.syntax_validator import SyntaxValidationResult, SyntaxValidator
from app.patcher.tools import (
    ApplyPatchTool,
    FileSnapshotTool,
    MultiEditTool,
    SurgicalEditTool,
)

__all__ = [
    "ApplyPatchTool",
    "DiffEngine",
    "FileSnapshot",
    "FileSnapshotAuditor",
    "FileSnapshotTool",
    "MultiEditTool",
    "PatchHunk",
    "PatchResult",
    "SafeCodeModifier",
    "StaleFileConflictError",
    "SurgicalEditChunk",
    "SurgicalEditTool",
    "SyntaxValidationResult",
    "SyntaxValidator",
    "UnifiedDiff",
]

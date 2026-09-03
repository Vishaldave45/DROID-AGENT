"""Safe Code Modifier combining snapshots, diff patching, surgical editing, and AST syntax validation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.patcher.base import FileSnapshot, PatchHunk, PatchResult, SurgicalEditChunk, UnifiedDiff
from app.patcher.diff_engine import DiffEngine
from app.patcher.snapshot_auditor import FileSnapshotAuditor, StaleFileConflictError
from app.patcher.syntax_validator import SyntaxValidator


class SafeCodeModifier:
    """Orchestrates resilient, safe code modifications with syntax gates, snapshots, and atomic disk writes."""

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        snapshot_auditor: Optional[FileSnapshotAuditor] = None,
        syntax_validator: Optional[SyntaxValidator] = None,
    ):
        self.workspace_root = workspace_root or os.getcwd()
        self.auditor = snapshot_auditor or FileSnapshotAuditor(self.workspace_root)
        self.syntax_validator = syntax_validator or SyntaxValidator()

    def apply_patch(
        self,
        file_path: str,
        diff_str: str,
        expected_hash: Optional[str] = None,
        dry_run: bool = False,
        validate_syntax: bool = True,
        fuzz_factor: int = 2,
    ) -> PatchResult:
        """Applies a unified diff patch to a file with snapshotting, stale-file detection, and syntax validation."""
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.workspace_root) / p

        if not p.exists() or not p.is_file():
            return PatchResult(
                success=False,
                file_path=file_path,
                error=f"Target file not found: '{file_path}'",
            )

        # 1. Verify freshness / stale file detection
        is_fresh, current_hash, stale_err = self.auditor.verify_file_freshness(str(p), expected_hash)
        if not is_fresh:
            return PatchResult(
                success=False,
                file_path=file_path,
                error=stale_err,
                pre_hash=current_hash,
                stale_detected=True,
            )

        # 2. Capture pre-edit snapshot
        snapshot = self.auditor.take_snapshot(str(p), reason="pre-patch")
        snap_ver = snapshot.version if snapshot else None

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        # 3. Parse unified diff
        diffs = DiffEngine.parse_unified_diff(diff_str)
        if not diffs:
            return PatchResult(
                success=False,
                file_path=file_path,
                error="Failed to parse valid unified diff. Ensure diff has '@@ -l,s +l,s @@' hunk headers.",
                pre_hash=current_hash,
            )

        target_diff = diffs[0]
        # 4. Apply diff hunks
        patch_res = DiffEngine.apply_unified_diff(original_content, target_diff, fuzz_factor=fuzz_factor)
        patch_res.pre_hash = current_hash
        patch_res.snapshot_version = snap_ver

        if not patch_res.success or patch_res.modified_content is None:
            return patch_res

        modified_text = patch_res.modified_content
        post_hash = FileSnapshotAuditor.compute_sha256(modified_text)
        patch_res.post_hash = post_hash

        # 5. Pre-write syntax validation
        if validate_syntax:
            val_res = self.syntax_validator.validate(modified_text, str(p))
            patch_res.syntax_valid = val_res.is_valid
            patch_res.syntax_error = val_res.error_message
            patch_res.syntax_error_line = val_res.error_line

            if not val_res.is_valid:
                patch_res.success = False
                patch_res.error = f"Syntax validation failed after applying diff: {val_res.error_message}. Edit aborted."
                return patch_res

        # 6. Atomic write (if not dry run)
        if not dry_run:
            success, write_err = self.auditor.atomic_write(str(p), modified_text)
            if not success:
                patch_res.success = False
                patch_res.error = write_err
                return patch_res

        return patch_res

    def apply_surgical_edit(
        self,
        file_path: str,
        target_content: str,
        replacement_content: str,
        expected_hash: Optional[str] = None,
        allow_fuzzy: bool = False,
        dry_run: bool = False,
        validate_syntax: bool = True,
    ) -> PatchResult:
        """Applies a single-block surgical edit with snapshot, uniqueness check, and syntax validation."""
        chunk = SurgicalEditChunk(
            target_content=target_content,
            replacement_content=replacement_content,
            allow_fuzzy=allow_fuzzy,
        )
        return self.apply_multi_surgical_edits(
            file_path=file_path,
            chunks=[chunk],
            expected_hash=expected_hash,
            dry_run=dry_run,
            validate_syntax=validate_syntax,
        )

    def apply_multi_surgical_edits(
        self,
        file_path: str,
        chunks: List[SurgicalEditChunk],
        expected_hash: Optional[str] = None,
        dry_run: bool = False,
        validate_syntax: bool = True,
    ) -> PatchResult:
        """Applies multiple surgical edit chunks with atomic rollback on syntax or match failure."""
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.workspace_root) / p

        if not p.exists() or not p.is_file():
            return PatchResult(
                success=False,
                file_path=file_path,
                error=f"Target file not found: '{file_path}'",
            )

        # 1. Verify freshness
        is_fresh, current_hash, stale_err = self.auditor.verify_file_freshness(str(p), expected_hash)
        if not is_fresh:
            return PatchResult(
                success=False,
                file_path=file_path,
                error=stale_err,
                pre_hash=current_hash,
                stale_detected=True,
            )

        # 2. Capture snapshot
        snapshot = self.auditor.take_snapshot(str(p), reason="pre-surgical-edit")
        snap_ver = snapshot.version if snapshot else None

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            original_content = f.read()

        # 3. Apply surgical chunks
        success, modified_text, chunk_err = DiffEngine.apply_surgical_chunks(original_content, chunks)
        if not success:
            return PatchResult(
                success=False,
                file_path=file_path,
                error=chunk_err,
                pre_hash=current_hash,
                snapshot_version=snap_ver,
            )

        post_hash = FileSnapshotAuditor.compute_sha256(modified_text)

        # 4. Syntax validation
        if validate_syntax:
            val_res = self.syntax_validator.validate(modified_text, str(p))
            if not val_res.is_valid:
                return PatchResult(
                    success=False,
                    file_path=file_path,
                    error=f"Syntax validation failed after surgical edit: {val_res.error_message}. Modification rejected.",
                    syntax_valid=False,
                    syntax_error=val_res.error_message,
                    syntax_error_line=val_res.error_line,
                    pre_hash=current_hash,
                    post_hash=post_hash,
                    snapshot_version=snap_ver,
                )

        # 5. Atomic write
        if not dry_run:
            write_success, write_err = self.auditor.atomic_write(str(p), modified_text)
            if not write_success:
                return PatchResult(
                    success=False,
                    file_path=file_path,
                    error=write_err,
                    pre_hash=current_hash,
                    snapshot_version=snap_ver,
                )

        old_lines = len(original_content.splitlines())
        new_lines = len(modified_text.splitlines())

        return PatchResult(
            success=True,
            file_path=file_path,
            applied_hunks=len(chunks),
            additions=max(0, new_lines - old_lines),
            deletions=max(0, old_lines - new_lines),
            modified_content=modified_text,
            pre_hash=current_hash,
            post_hash=post_hash,
            snapshot_version=snap_ver,
        )

    def revert_file(self, file_path: str, version: Optional[int] = None) -> Tuple[bool, Optional[str]]:
        """Restores a file to its previous snapshot state."""
        p = Path(file_path)
        if not p.is_absolute():
            p = Path(self.workspace_root) / p

        success, snapshot, err = self.auditor.revert_to_snapshot(str(p), version)
        if not success:
            return False, err
        return True, f"Reverted '{file_path}' to snapshot version {snapshot.version if snapshot else 'latest'}."

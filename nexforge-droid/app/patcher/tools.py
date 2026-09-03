"""Tool implementations for safe code modification, patching, and snapshot management."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.patcher.base import SurgicalEditChunk
from app.patcher.safe_modifier import SafeCodeModifier
from app.tools.base import Tool, ToolResult


class ApplyPatchTool(Tool):
    """Applies a unified diff patch to a target file with syntax validation and atomic rollback."""

    name = "apply_patch"
    description = (
        "Apply a standard unified diff patch (with --- a/..., +++ b/..., @@ -l,s +l,s @@ headers) "
        "to a file with automatic pre-snapshotting, syntax checking, and atomic writes."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the target file to patch.",
            },
            "diff": {
                "type": "string",
                "description": "Unified diff text with @@ hunk headers.",
            },
            "expected_hash": {
                "type": "string",
                "description": "Optional SHA-256 hash of the file when last read (stale-file guard).",
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, simulates patch application and syntax check without modifying the disk file.",
            },
            "validate_syntax": {
                "type": "boolean",
                "description": "Whether to validate syntax (Python AST, JSON, JS/TS balance) before writing (default true).",
            },
        },
        "required": ["path", "diff"],
    }

    def __init__(self, modifier: Optional[SafeCodeModifier] = None):
        super().__init__()
        self.modifier = modifier or SafeCodeModifier()

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        diff_str = kwargs.get("diff", "")
        expected_hash = kwargs.get("expected_hash")
        dry_run = kwargs.get("dry_run", False)
        validate_syntax = kwargs.get("validate_syntax", True)

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")
        if not diff_str:
            return ToolResult(success=False, error="Parameter 'diff' is required.")

        res = self.modifier.apply_patch(
            file_path=file_path,
            diff_str=diff_str,
            expected_hash=expected_hash,
            dry_run=dry_run,
            validate_syntax=validate_syntax,
        )

        if not res.success:
            return ToolResult(
                success=False,
                error=res.error or "Patch application failed.",
                data=res.to_dict(),
            )

        return ToolResult(
            success=True,
            data=res.to_dict(),
        )


class SurgicalEditTool(Tool):
    """Executes a surgical code modification with uniqueness check and syntax verification."""

    name = "surgical_edit"
    description = (
        "Surgically replace a unique target code block in a file with new content. "
        "Includes automatic SHA-256 conflict detection and AST syntax validation."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "target_content": {
                "type": "string",
                "description": "Exact text block to replace. Must match uniquely within the file.",
            },
            "replacement_content": {
                "type": "string",
                "description": "Replacement text to insert.",
            },
            "expected_hash": {
                "type": "string",
                "description": "Optional SHA-256 hash when last read (stale-file concurrency guard).",
            },
            "allow_fuzzy": {
                "type": "boolean",
                "description": "Allow whitespace/newline tolerant matching if exact match fails (default false).",
            },
            "validate_syntax": {
                "type": "boolean",
                "description": "Validate syntax prior to writing to disk (default true).",
            },
        },
        "required": ["path", "target_content", "replacement_content"],
    }

    def __init__(self, modifier: Optional[SafeCodeModifier] = None):
        super().__init__()
        self.modifier = modifier or SafeCodeModifier()

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        target_content = kwargs.get("target_content", "")
        replacement_content = kwargs.get("replacement_content", "")
        expected_hash = kwargs.get("expected_hash")
        allow_fuzzy = kwargs.get("allow_fuzzy", False)
        validate_syntax = kwargs.get("validate_syntax", True)

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")
        if target_content is None:
            return ToolResult(success=False, error="Parameter 'target_content' is required.")
        if replacement_content is None:
            return ToolResult(success=False, error="Parameter 'replacement_content' is required.")

        res = self.modifier.apply_surgical_edit(
            file_path=file_path,
            target_content=target_content,
            replacement_content=replacement_content,
            expected_hash=expected_hash,
            allow_fuzzy=allow_fuzzy,
            validate_syntax=validate_syntax,
        )

        if not res.success:
            return ToolResult(
                success=False,
                error=res.error or "Surgical edit failed.",
                data=res.to_dict(),
            )

        return ToolResult(
            success=True,
            data=res.to_dict(),
        )


class MultiEditTool(Tool):
    """Executes multiple non-contiguous surgical edits in a file in a single atomic transaction."""

    name = "multi_surgical_edit"
    description = (
        "Perform multiple non-contiguous surgical edits in a file in a single atomic transaction. "
        "If any chunk or syntax check fails, all edits are rolled back."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "chunks": {
                "type": "array",
                "description": "List of edit chunks with target_content and replacement_content.",
                "items": {
                    "type": "object",
                    "properties": {
                        "target_content": {"type": "string"},
                        "replacement_content": {"type": "string"},
                        "allow_fuzzy": {"type": "boolean"},
                    },
                    "required": ["target_content", "replacement_content"],
                },
            },
            "expected_hash": {
                "type": "string",
                "description": "Optional SHA-256 hash when last read.",
            },
            "validate_syntax": {
                "type": "boolean",
                "description": "Validate syntax prior to committing writes (default true).",
            },
        },
        "required": ["path", "chunks"],
    }

    def __init__(self, modifier: Optional[SafeCodeModifier] = None):
        super().__init__()
        self.modifier = modifier or SafeCodeModifier()

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        raw_chunks = kwargs.get("chunks", [])
        expected_hash = kwargs.get("expected_hash")
        validate_syntax = kwargs.get("validate_syntax", True)

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")
        if not raw_chunks:
            return ToolResult(success=False, error="Parameter 'chunks' must not be empty.")

        chunks = [
            SurgicalEditChunk(
                target_content=c.get("target_content", ""),
                replacement_content=c.get("replacement_content", ""),
                allow_fuzzy=c.get("allow_fuzzy", False),
            )
            for c in raw_chunks
        ]

        res = self.modifier.apply_multi_surgical_edits(
            file_path=file_path,
            chunks=chunks,
            expected_hash=expected_hash,
            validate_syntax=validate_syntax,
        )

        if not res.success:
            return ToolResult(
                success=False,
                error=res.error or "Multi-surgical edit failed.",
                data=res.to_dict(),
            )

        return ToolResult(
            success=True,
            data=res.to_dict(),
        )


class FileSnapshotTool(Tool):
    """Captures snapshots, inspects hash signatures, and rolls back files."""

    name = "manage_snapshots"
    description = (
        "Manage file snapshot versions, inspect SHA-256 hash fingerprints, and rollback to prior versions."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["snapshot", "hash", "history", "revert"],
                "description": "Action to perform: 'snapshot' (take snapshot), 'hash' (get SHA-256), 'history' (list versions), or 'revert' (restore prior version).",
            },
            "path": {
                "type": "string",
                "description": "Path to the target file.",
            },
            "version": {
                "type": "integer",
                "description": "Snapshot version number for 'revert' action (default latest).",
            },
            "reason": {
                "type": "string",
                "description": "Reason for taking the snapshot.",
            },
        },
        "required": ["action", "path"],
    }

    def __init__(self, modifier: Optional[SafeCodeModifier] = None):
        super().__init__()
        self.modifier = modifier or SafeCodeModifier()

    def execute(self, **kwargs: Any) -> ToolResult:
        action = kwargs.get("action", "")
        file_path = kwargs.get("path", "")
        version = kwargs.get("version")
        reason = kwargs.get("reason", "manual-snapshot")

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")

        auditor = self.modifier.auditor

        if action == "hash":
            sha = auditor.compute_file_sha256(file_path)
            if sha is None:
                return ToolResult(success=False, error=f"File '{file_path}' not found.")
            return ToolResult(success=True, data={"path": file_path, "sha256_hash": sha})

        elif action == "snapshot":
            snap = auditor.take_snapshot(file_path, reason=reason)
            if not snap:
                return ToolResult(success=False, error=f"Failed to capture snapshot of '{file_path}'.")
            return ToolResult(success=True, data=snap.to_dict())

        elif action == "history":
            snaps = auditor.get_snapshots(file_path)
            return ToolResult(
                success=True,
                data={
                    "path": file_path,
                    "total_versions": len(snaps),
                    "versions": [s.to_dict() for s in snaps],
                },
            )

        elif action == "revert":
            success, msg = self.modifier.revert_file(file_path, version)
            if not success:
                return ToolResult(success=False, error=msg or "Revert failed.")
            return ToolResult(success=True, data={"path": file_path, "message": msg})

        else:
            return ToolResult(success=False, error=f"Unknown action: '{action}'")

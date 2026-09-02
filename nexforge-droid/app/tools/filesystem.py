"""Filesystem operations tool implementations for NexForge Droid."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import Tool, ToolResult

MAX_READ_BYTES = 5 * 1024 * 1024  # 5 MB safety ceiling
DEFAULT_MAX_LINES = 1600


class ReadFileTool(Tool):
    """Tool for reading file content with line slicing and safety boundaries."""

    name = "read_file"
    description = "Read the contents of a file in the workspace with optional start_line and end_line slice notation."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read (relative or absolute).",
            },
            "start_line": {
                "type": "integer",
                "description": "Optional 1-indexed starting line number (inclusive).",
            },
            "end_line": {
                "type": "integer",
                "description": "Optional 1-indexed ending line number (inclusive).",
            },
        },
        "required": ["path"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")

        p = Path(file_path)
        if not p.exists():
            return ToolResult(success=False, error=f"File not found: '{file_path}'")

        if not p.is_file():
            return ToolResult(success=False, error=f"Target path is not a file: '{file_path}'")

        try:
            file_size = p.stat().st_size
            if file_size > MAX_READ_BYTES:
                return ToolResult(
                    success=False,
                    error=f"File exceeds maximum read limit ({file_size} bytes > {MAX_READ_BYTES} bytes).",
                )

            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            s_line = max(1, start_line) if start_line is not None else 1
            e_line = min(total_lines, end_line) if end_line is not None else min(total_lines, s_line + DEFAULT_MAX_LINES - 1)

            if total_lines == 0:
                selected_content = ""
            elif s_line > total_lines:
                return ToolResult(
                    success=False,
                    error=f"start_line ({s_line}) exceeds total lines in file ({total_lines}).",
                )
            else:
                slice_lines = lines[s_line - 1 : e_line]
                selected_content = "".join(slice_lines)

            return ToolResult(
                success=True,
                data={
                    "path": str(p),
                    "content": selected_content,
                    "total_lines": total_lines,
                    "start_line": s_line,
                    "end_line": e_line,
                    "total_bytes": file_size,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to read file: {str(e)}")


class WriteFileTool(Tool):
    """Tool for creating or overwriting files with automatic directory provisioning."""

    name = "write_file"
    description = "Create a new file or completely overwrite an existing file with the provided content."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the destination file.",
            },
            "content": {
                "type": "string",
                "description": "Text content to write to the file.",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Whether to overwrite the file if it already exists (default true).",
            },
        },
        "required": ["path", "content"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        overwrite = kwargs.get("overwrite", True)

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")

        p = Path(file_path)
        if p.exists() and not overwrite:
            return ToolResult(
                success=False,
                error=f"File '{file_path}' already exists and overwrite is set to False.",
            )

        try:
            # Ensure parent directories exist
            p.parent.mkdir(parents=True, exist_ok=True)

            with open(p, "w", encoding="utf-8") as f:
                f.write(content)

            line_count = len(content.splitlines())
            byte_count = len(content.encode("utf-8"))

            return ToolResult(
                success=True,
                data={
                    "path": str(p),
                    "lines_written": line_count,
                    "bytes_written": byte_count,
                    "created": not p.exists() if not overwrite else True,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to write file: {str(e)}")


class EditFileTool(Tool):
    """Tool for surgical single-block code modifications with uniqueness validation."""

    name = "edit_file"
    description = "Perform a surgical replacement of an exact, unique target text block with replacement content."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit.",
            },
            "target_content": {
                "type": "string",
                "description": "Exact text block to find and replace. Must match uniquely within the file.",
            },
            "replacement_content": {
                "type": "string",
                "description": "New replacement text to insert.",
            },
        },
        "required": ["path", "target_content", "replacement_content"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        target = kwargs.get("target_content", "")
        replacement = kwargs.get("replacement_content", "")

        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")
        if target is None:
            return ToolResult(success=False, error="Parameter 'target_content' is required.")
        if replacement is None:
            return ToolResult(success=False, error="Parameter 'replacement_content' is required.")

        p = Path(file_path)
        if not p.exists() or not p.is_file():
            return ToolResult(success=False, error=f"File not found: '{file_path}'")

        try:
            with open(p, "r", encoding="utf-8") as f:
                original = f.read()

            occurrences = original.count(target)
            if occurrences == 0:
                return ToolResult(
                    success=False,
                    error=f"target_content not found in file '{file_path}'. Ensure leading whitespace and characters match exactly.",
                )
            if occurrences > 1:
                return ToolResult(
                    success=False,
                    error=f"target_content matches {occurrences} occurrences in '{file_path}'. Target content must be unique. Provide more surrounding context.",
                )

            updated = original.replace(target, replacement, 1)

            with open(p, "w", encoding="utf-8") as f:
                f.write(updated)

            return ToolResult(
                success=True,
                data={
                    "path": str(p),
                    "modified": True,
                    "old_lines": len(original.splitlines()),
                    "new_lines": len(updated.splitlines()),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to edit file: {str(e)}")


class ListDirTool(Tool):
    """Tool for listing directory contents with file size and type annotations."""

    name = "list_dir"
    description = "List all files and subdirectories inside a directory with size and type metadata."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to inspect (defaults to current directory).",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list subdirectories recursively (default false).",
            },
            "max_items": {
                "type": "integer",
                "description": "Maximum number of entries to return (default 200).",
            },
        },
        "required": [],
    }

    IGNORED_DIRS = {".git", "__pycache__", "node_modules", ".pytest_cache", ".venv", "dist", ".next"}

    def execute(self, **kwargs: Any) -> ToolResult:
        dir_path = kwargs.get("path", ".") or "."
        recursive = kwargs.get("recursive", False)
        max_items = kwargs.get("max_items", 200)

        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            return ToolResult(success=False, error=f"Directory not found: '{dir_path}'")

        try:
            entries: List[Dict[str, Any]] = []

            if recursive:
                for root, dirs, files in os.walk(p):
                    # Filter ignored directories in-place
                    dirs[:] = [d for d in dirs if d not in self.IGNORED_DIRS]
                    for name in dirs:
                        if len(entries) >= max_items:
                            break
                        full = Path(root) / name
                        entries.append({
                            "name": name,
                            "path": str(full.relative_to(p)),
                            "type": "directory",
                        })
                    for name in files:
                        if len(entries) >= max_items:
                            break
                        full = Path(root) / name
                        entries.append({
                            "name": name,
                            "path": str(full.relative_to(p)),
                            "type": "file",
                            "size_bytes": full.stat().st_size if full.exists() else 0,
                        })
                    if len(entries) >= max_items:
                        break
            else:
                for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                    if item.name in self.IGNORED_DIRS:
                        continue
                    if len(entries) >= max_items:
                        break
                    entries.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size_bytes": item.stat().st_size if item.is_file() else None,
                    })

            return ToolResult(
                success=True,
                data={
                    "path": str(p.resolve()),
                    "total_entries": len(entries),
                    "entries": entries,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to list directory: {str(e)}")


class DeleteFileTool(Tool):
    """Tool for deleting a file."""

    name = "delete_file"
    description = "Delete an existing file in the workspace."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to delete.",
            },
        },
        "required": ["path"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("path", "")
        if not file_path:
            return ToolResult(success=False, error="Parameter 'path' is required.")

        p = Path(file_path)
        if not p.exists():
            return ToolResult(success=False, error=f"File not found: '{file_path}'")
        if not p.is_file():
            return ToolResult(success=False, error=f"Path is not a file: '{file_path}'")

        try:
            p.unlink()
            return ToolResult(success=True, data={"path": str(p), "deleted": True})
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to delete file: {str(e)}")

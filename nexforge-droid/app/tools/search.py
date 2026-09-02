"""Code search and file discovery tools for NexForge Droid."""

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import Tool, ToolResult

DEFAULT_MAX_RESULTS = 50
MAX_SEARCH_FILE_BYTES = 2 * 1024 * 1024  # 2MB per file ceiling for regex scanning
IGNORED_PATTERNS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
    ".venv",
    "dist",
    "build",
    ".next",
    "*.pyc",
    "*.lock",
}


class SearchCodeTool(Tool):
    """Tool for regex and literal substring searching across repository codebase."""

    name = "search_code"
    description = "Search for a text pattern or regular expression across files in the workspace directory."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text substring or regex pattern to search for.",
            },
            "path": {
                "type": "string",
                "description": "Directory or file path to search within (default current directory).",
            },
            "file_pattern": {
                "type": "string",
                "description": "Optional file glob filter (e.g., '*.py', '*.ts', 'test_*.py').",
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether search is case-sensitive (default true).",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matched lines to return (default 50).",
            },
        },
        "required": ["query"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        search_path = kwargs.get("path", ".") or "."
        file_pattern = kwargs.get("file_pattern")
        case_sensitive = kwargs.get("case_sensitive", True)
        max_results = kwargs.get("max_results", DEFAULT_MAX_RESULTS)

        if not query:
            return ToolResult(success=False, error="Parameter 'query' is required.")

        p = Path(search_path)
        if not p.exists():
            return ToolResult(success=False, error=f"Path not found: '{search_path}'")

        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(query, flags)
        except re.error:
            # Fallback to literal search if query has regex syntax errors
            regex = re.compile(re.escape(query), flags)

        matches: List[Dict[str, Any]] = []
        files_scanned = 0

        target_files: List[Path] = []
        if p.is_file():
            target_files = [p]
        else:
            for root, dirs, files in os.walk(p):
                # Filter directories
                dirs[:] = [d for d in dirs if d not in IGNORED_PATTERNS and not d.startswith(".")]
                for file in files:
                    if any(fnmatch.fnmatch(file, ign) for ign in IGNORED_PATTERNS):
                        continue
                    if file_pattern and not fnmatch.fnmatch(file, file_pattern):
                        continue
                    target_files.append(Path(root) / file)

        for fpath in target_files:
            if len(matches) >= max_results:
                break
            try:
                if fpath.stat().st_size > MAX_SEARCH_FILE_BYTES:
                    continue
                files_scanned += 1
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, start=1):
                        if regex.search(line):
                            matches.append({
                                "file": str(fpath),
                                "line_number": line_no,
                                "line_content": line.rstrip("\r\n"),
                            })
                            if len(matches) >= max_results:
                                break
            except Exception:
                continue

        return ToolResult(
            success=True,
            data={
                "query": query,
                "total_matches": len(matches),
                "files_scanned": files_scanned,
                "matches": matches,
            },
        )


class FindFilesTool(Tool):
    """Tool for finding files matching glob patterns or names in the workspace."""

    name = "find_files"
    description = "Find files by filename or glob pattern (e.g. '*.py', 'base.py', 'test_*.ts') in the workspace."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern or filename to search for (e.g. '*.py', 'App.tsx').",
            },
            "path": {
                "type": "string",
                "description": "Root directory to search within (default current directory).",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of file paths to return (default 100).",
            },
        },
        "required": ["pattern"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        root_path = kwargs.get("path", ".") or "."
        max_results = kwargs.get("max_results", 100)

        if not pattern:
            return ToolResult(success=False, error="Parameter 'pattern' is required.")

        p = Path(root_path)
        if not p.exists() or not p.is_dir():
            return ToolResult(success=False, error=f"Directory not found: '{root_path}'")

        found_files: List[Dict[str, Any]] = []

        try:
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in IGNORED_PATTERNS and not d.startswith(".")]
                for file in files:
                    if any(fnmatch.fnmatch(file, ign) for ign in IGNORED_PATTERNS):
                        continue
                    if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(file.lower(), pattern.lower()):
                        full_path = Path(root) / file
                        found_files.append({
                            "name": file,
                            "path": str(full_path),
                            "size_bytes": full_path.stat().st_size if full_path.exists() else 0,
                        })
                        if len(found_files) >= max_results:
                            break
                if len(found_files) >= max_results:
                    break

            return ToolResult(
                success=True,
                data={
                    "pattern": pattern,
                    "total_found": len(found_files),
                    "files": found_files,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to find files: {str(e)}")

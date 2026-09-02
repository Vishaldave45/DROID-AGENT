"""Git version control inspection tools for NexForge Droid."""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import Tool, ToolResult


class GitStatusTool(Tool):
    """Tool for checking working tree status, staged and untracked files."""

    name = "git_status"
    description = "Inspect git status to see modified, untracked, and staged files in the repository."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Git repository path (default current directory).",
            },
        },
        "required": [],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        repo_path = kwargs.get("path", ".") or "."
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Git command failed: {res.stderr.strip()}",
                )

            lines = res.stdout.splitlines()
            modified: List[str] = []
            untracked: List[str] = []
            staged: List[str] = []

            for line in lines:
                if len(line) < 3:
                    continue
                code = line[:2]
                filename = line[3:].strip()
                if code.startswith("?"):
                    untracked.append(filename)
                elif code.startswith("M") or code[1] == "M":
                    modified.append(filename)
                elif code.startswith("A") or code.startswith("D") or code.startswith("R"):
                    staged.append(filename)
                else:
                    modified.append(filename)

            is_clean = len(lines) == 0

            return ToolResult(
                success=True,
                data={
                    "is_clean": is_clean,
                    "total_changes": len(lines),
                    "modified": modified,
                    "untracked": untracked,
                    "staged": staged,
                    "raw_output": res.stdout,
                },
            )
        except FileNotFoundError:
            return ToolResult(success=False, error="Git executable not found in environment.")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to check git status: {str(e)}")


class GitDiffTool(Tool):
    """Tool for retrieving unified diffs of uncommitted changes."""

    name = "git_diff"
    description = "Retrieve the uncommitted diffs for the whole repository or a specific file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Specific file path or repository root to diff.",
            },
            "staged": {
                "type": "boolean",
                "description": "Whether to view staged diffs (--cached) instead of unstaged (default false).",
            },
        },
        "required": [],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        target_path = kwargs.get("path")
        staged = kwargs.get("staged", False)

        cmd = ["git", "diff"]
        if staged:
            cmd.append("--cached")
        if target_path and target_path != ".":
            cmd.extend(["--", target_path])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode != 0:
                return ToolResult(success=False, error=f"Git diff failed: {res.stderr.strip()}")

            diff_text = res.stdout
            lines = diff_text.splitlines()

            return ToolResult(
                success=True,
                data={
                    "has_diff": bool(diff_text.strip()),
                    "diff": diff_text,
                    "lines_count": len(lines),
                    "staged": staged,
                },
            )
        except FileNotFoundError:
            return ToolResult(success=False, error="Git executable not found.")
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to retrieve git diff: {str(e)}")


class GitLogTool(Tool):
    """Tool for viewing recent git commit history."""

    name = "git_log"
    description = "View recent commit history with hashes, authors, timestamps, and commit messages."
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of commits to retrieve (default 10).",
            },
            "path": {
                "type": "string",
                "description": "Repository path or specific file path to inspect history for.",
            },
        },
        "required": [],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        limit = kwargs.get("limit", 10)
        repo_path = kwargs.get("path")

        cmd = ["git", "log", f"-n{limit}", "--pretty=format:%H|%an|%ad|%s", "--date=short"]
        if repo_path and repo_path != ".":
            cmd.extend(["--", repo_path])

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode != 0:
                return ToolResult(success=False, error=f"Git log failed: {res.stderr.strip()}")

            commits: List[Dict[str, str]] = []
            for line in res.stdout.splitlines():
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3],
                    })

            return ToolResult(
                success=True,
                data={
                    "total_commits": len(commits),
                    "commits": commits,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Failed to retrieve git log: {str(e)}")

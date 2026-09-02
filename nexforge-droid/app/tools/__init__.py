"""Tool system and default tool registry for NexForge Droid."""

import os
from typing import Optional

from app.security.base import DefaultPolicyEngine, PolicyEngine, SecurityContext
from app.tools.base import Tool, ToolRegistry, ToolResult
from app.tools.filesystem import (
    DeleteFileTool,
    EditFileTool,
    ListDirTool,
    ReadFileTool,
    WriteFileTool,
)
from app.tools.git_tools import GitDiffTool, GitLogTool, GitStatusTool
from app.tools.search import FindFilesTool, SearchCodeTool
from app.tools.terminal import RunCommandTool


def get_default_tool_registry(
    workspace_root: Optional[str] = None,
    policy_engine: Optional[PolicyEngine] = None,
) -> ToolRegistry:
    """Instantiates and registers all standard production tools with security governance."""
    root = workspace_root or os.getcwd()
    sec_context = SecurityContext(workspace_root=root)
    engine = policy_engine or DefaultPolicyEngine()

    registry = ToolRegistry(policy_engine=engine, security_context=sec_context)

    # 1. Filesystem Tools
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(EditFileTool())
    registry.register(ListDirTool())
    registry.register(DeleteFileTool())

    # 2. Search & Discovery Tools
    registry.register(SearchCodeTool())
    registry.register(FindFilesTool())

    # 3. Terminal & Execution Tools
    registry.register(RunCommandTool())

    # 4. Version Control (Git) Tools
    registry.register(GitStatusTool())
    registry.register(GitDiffTool())
    registry.register(GitLogTool())

    return registry


__all__ = [
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirTool",
    "DeleteFileTool",
    "SearchCodeTool",
    "FindFilesTool",
    "RunCommandTool",
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "get_default_tool_registry",
]

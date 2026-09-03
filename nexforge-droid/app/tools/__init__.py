"""Tool system and default tool registry for NexForge Droid."""

import os
from typing import Optional

from app.security.base import DefaultPolicyEngine, PolicyEngine, SecurityContext
from app.tools.base import Tool, ToolRegistry, ToolResult
from app.tools.agent_tools import FinishTaskTool
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
    include_agent_tools: bool = False,
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

    # 5. Safe Patching & Modification Tools
    from app.patcher.tools import (
        ApplyPatchTool,
        FileSnapshotTool,
        MultiEditTool,
        SurgicalEditTool,
    )
    registry.register(ApplyPatchTool())
    registry.register(SurgicalEditTool())
    registry.register(MultiEditTool())
    registry.register(FileSnapshotTool())

    # 6. Diagnostic & Test Repair Tools
    from app.diagnostics.tools import (
        AutoFixLoopTool,
        DiagnoseTestFailureTool,
        RunDiagnosticsTool,
    )
    registry.register(RunDiagnosticsTool())
    registry.register(DiagnoseTestFailureTool())
    registry.register(AutoFixLoopTool())

    # 7. Workspace Orchestrator & Refactor Tools (Phase 11)
    from app.orchestrator.tools import (
        ApplyMultiFileRefactorTool,
        CreateChangesetTool,
        GeneratePullRequestTool,
        RequestHumanApprovalTool,
    )
    registry.register(CreateChangesetTool())
    registry.register(ApplyMultiFileRefactorTool())
    registry.register(GeneratePullRequestTool())
    registry.register(RequestHumanApprovalTool())

    # 8. Git Worktrees, Branching & CI/CD Lifecycle Tools (Phase 17)
    from app.tools.pr_tools import (
        GitBranchTool,
        GitGeneratePRTool,
        GitHealCITool,
        GitRunCITool,
        GitWorktreeTool,
    )
    registry.register(GitBranchTool())
    registry.register(GitWorktreeTool())
    registry.register(GitGeneratePRTool())
    registry.register(GitRunCITool())
    registry.register(GitHealCITool())

    # 9. Code Review, Security Audit & SARIF Tools (Phase 18)
    from app.tools.review_tools import (
        CodeReviewScanTool,
        SarifExportTool,
        SecurityAuditTool,
    )
    registry.register(CodeReviewScanTool())
    registry.register(SecurityAuditTool())
    registry.register(SarifExportTool())

    # 10. Autonomous Test Synthesis & Mutation Testing Tools (Phase 19)
    from app.tools.test_gen_tools import (
        CoverageAuditTool,
        RunMutationTestTool,
        SynthesizeTestsTool,
    )
    registry.register(SynthesizeTestsTool())
    registry.register(RunMutationTestTool())
    registry.register(CoverageAuditTool())

    # 11. Agent Orchestration Tools
    if include_agent_tools:
        from app.planner.tools import GeneratePlanTool, ReplanTaskTool
        registry.register(FinishTaskTool())
        registry.register(GeneratePlanTool())
        registry.register(ReplanTaskTool())

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
    "ApplyPatchTool",
    "SurgicalEditTool",
    "MultiEditTool",
    "FileSnapshotTool",
    "RunDiagnosticsTool",
    "DiagnoseTestFailureTool",
    "AutoFixLoopTool",
    "CreateChangesetTool",
    "ApplyMultiFileRefactorTool",
    "GeneratePullRequestTool",
    "RequestHumanApprovalTool",
    "FinishTaskTool",
    "GeneratePlanTool",
    "ReplanTaskTool",
    "GitBranchTool",
    "GitWorktreeTool",
    "GitGeneratePRTool",
    "GitRunCITool",
    "GitHealCITool",
    "CodeReviewScanTool",
    "SecurityAuditTool",
    "SarifExportTool",
    "SynthesizeTestsTool",
    "RunMutationTestTool",
    "CoverageAuditTool",
    "get_default_tool_registry",
]


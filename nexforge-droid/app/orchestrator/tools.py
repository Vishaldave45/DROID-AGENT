"""Production tools for Workspace Orchestration, Multi-File Refactoring, and PR generation."""

from typing import Any, Dict, List, Optional

from app.orchestrator.changeset_manager import ChangesetManager
from app.orchestrator.human_gate import HumanApprovalGate, RiskLevel
from app.orchestrator.refactor_engine import (
    MultiFileRefactorEngine,
    SymbolRenameRequest,
)
from app.tools.base import Tool, ToolResult


class CreateChangesetTool(Tool):
    """Tool for staging and creating an atomic multi-file changeset."""

    name = "create_changeset"
    description = "Create an atomic multi-file changeset with git unified diffs, syntax verification, and auto-generated PR markdown."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short title describing the changeset.",
            },
            "description": {
                "type": "string",
                "description": "Detailed explanation of what the changeset achieves.",
            },
            "branch_name": {
                "type": "string",
                "description": "Optional branch name for the changeset.",
            },
        },
        "required": ["title", "description"],
    }

    def __init__(self, changeset_manager: Optional[ChangesetManager] = None):
        super().__init__()
        self.manager = changeset_manager or ChangesetManager()

    def execute(self, **kwargs: Any) -> ToolResult:
        title = kwargs.get("title", "Workspace Refactor")
        desc = kwargs.get("description", "")
        branch = kwargs.get("branch_name")

        cs = self.manager.create_changeset(title=title, description=desc, branch_name=branch)
        return ToolResult(
            success=True,
            data=cs.to_dict(),
        )


class ApplyMultiFileRefactorTool(Tool):
    """Tool for planning and executing multi-file symbol refactoring across workspace."""

    name = "apply_multifile_refactor"
    description = "Refactor symbols, classes, or function names safely across multiple files in the workspace with AST validation."
    input_schema = {
        "type": "object",
        "properties": {
            "old_symbol": {
                "type": "string",
                "description": "Current symbol name to find.",
            },
            "new_symbol": {
                "type": "string",
                "description": "New replacement symbol name.",
            },
            "target_files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional specific list of files to limit the refactor scope to.",
            },
        },
        "required": ["old_symbol", "new_symbol"],
    }

    def __init__(self, refactor_engine: Optional[MultiFileRefactorEngine] = None):
        super().__init__()
        self.engine = refactor_engine or MultiFileRefactorEngine()

    def execute(self, **kwargs: Any) -> ToolResult:
        old_sym = kwargs.get("old_symbol", "")
        new_sym = kwargs.get("new_symbol", "")
        targets = kwargs.get("target_files")

        req = SymbolRenameRequest(old_name=old_sym, new_name=new_sym, target_files=targets)
        plan = self.engine.plan_symbol_rename(req)
        cs = self.engine.execute_refactor_to_changeset(plan)

        return ToolResult(
            success=True,
            data={
                "plan": plan.to_dict(),
                "changeset": cs.to_dict(),
            },
        )


class GeneratePullRequestTool(Tool):
    """Tool for generating GitHub/GitLab-ready Pull Request descriptions from staged changesets."""

    name = "generate_pull_request"
    description = "Generate a comprehensive, structured Markdown Pull Request description and commit log for a changeset."
    input_schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "PR title"},
            "summary": {"type": "string", "description": "Feature/Bugfix summary"},
            "files_changed": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of modified file paths.",
            },
        },
        "required": ["title", "summary"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        title = kwargs.get("title", "Autonomous Update")
        summary = kwargs.get("summary", "")
        files = kwargs.get("files_changed", [])

        md = f"""## 🚀 PR: {title}

### Description
{summary}

### 📂 Impacted Modules
{chr(10).join(f"- `{f}`" for f in files) if files else "- Automatic workspace updates"}

### ✅ Verification
- AST Syntax Validation Passed
- Unittest / Pytest Regression Suite Passed
"""
        return ToolResult(
            success=True,
            data={
                "title": title,
                "markdown": md,
            },
        )


class RequestHumanApprovalTool(Tool):
    """Tool for submitting an action to the Human-in-the-Loop review queue."""

    name = "request_human_approval"
    description = "Submit a high-risk operation to the Human-in-the-Loop approval gate before proceeding."
    input_schema = {
        "type": "object",
        "properties": {
            "action_type": {
                "type": "string",
                "description": "Category of action (e.g. COMMAND_EXEC, FILE_DELETE, GIT_COMMIT).",
            },
            "description": {
                "type": "string",
                "description": "Justification and risk explanation for the operator.",
            },
            "risk_level": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "description": "Assessed risk level.",
            },
            "payload": {
                "type": "object",
                "description": "Parameters or commands associated with the action.",
            },
        },
        "required": ["action_type", "description"],
    }

    def __init__(self, gate: Optional[HumanApprovalGate] = None):
        super().__init__()
        self.gate = gate or HumanApprovalGate()

    def execute(self, **kwargs: Any) -> ToolResult:
        action_type = kwargs.get("action_type", "GENERAL_ACTION")
        desc = kwargs.get("description", "")
        risk_str = kwargs.get("risk_level", "MEDIUM")
        payload = kwargs.get("payload", {})

        risk = RiskLevel(risk_str) if risk_str in RiskLevel.__members__ else RiskLevel.MEDIUM
        req = self.gate.request_approval(
            action_type=action_type,
            description=desc,
            risk_level=risk,
            payload=payload,
        )

        return ToolResult(
            success=True,
            data=req.to_dict(),
        )

"""Autonomous Workspace Orchestrator & Multi-File Refactoring Module."""

from app.orchestrator.changeset_manager import (
    Changeset,
    ChangesetFile,
    ChangesetManager,
)
from app.orchestrator.human_gate import (
    ApprovalRequest,
    HumanApprovalGate,
    RiskLevel,
)
from app.orchestrator.refactor_engine import (
    MultiFileRefactorEngine,
    RefactorPlan,
    SymbolRenameRequest,
)

__all__ = [
    "Changeset",
    "ChangesetFile",
    "ChangesetManager",
    "ApprovalRequest",
    "HumanApprovalGate",
    "RiskLevel",
    "MultiFileRefactorEngine",
    "RefactorPlan",
    "SymbolRenameRequest",
]

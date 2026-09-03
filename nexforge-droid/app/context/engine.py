"""Repository Context Engine assembling task-specific high-signal context (Phase 5, 6 & 7)."""

import os
from typing import Dict, List, Optional, Set

from app.context.base import ContextBudget, ContextEngine, ContextPackage, EngineeringGraphNode, NodeType, RepositorySummary
from app.context.budget import ContextGovernor, TieredTokenBudget, TokenEstimator, TokenModelPreset
from app.context.engineering_graph import EngineeringGraph
from app.context.scanner import RepositoryScanner


class RepositoryContextEngine(ContextEngine):
    """Context Engine implementation combining repository scanning, graph-based retrieval, and token budgeting."""

    def __init__(self, repo_root: Optional[str] = None) -> None:
        self.default_repo_root = os.path.abspath(repo_root) if repo_root else os.getcwd()

    def build_context(
        self,
        task_requirement: str,
        repo_root: Optional[str] = None,
        budget: Optional[ContextBudget] = None,
        model_preset: str = TokenModelPreset.GEMINI_2_FLASH.value,
    ) -> ContextPackage:
        """Assembles a compact, high-signal, strictly budgeted context package tailored to a task requirement."""
        target_root = os.path.abspath(repo_root) if repo_root else self.default_repo_root

        # Map basic ContextBudget to TieredTokenBudget if provided
        if budget:
            tiered_budget = TieredTokenBudget(
                max_total_tokens=budget.max_total_tokens,
                repo_summary_tokens=budget.repo_summary_tokens,
                graph_symbols_tokens=budget.symbol_context_tokens,
                file_slices_tokens=budget.relevant_files_tokens,
                conversation_history_tokens=budget.tool_history_tokens,
            )
        else:
            tiered_budget = TieredTokenBudget()

        # Step 1: Scan repository intelligence
        scanner = RepositoryScanner(target_root)
        repo_summary = scanner.scan()

        # Step 2: Build Engineering Graph
        graph = EngineeringGraph()
        graph.build_from_repository(target_root)

        # Step 3: Read candidate files in workspace
        file_contents: Dict[str, str] = {}
        for f in repo_summary.files[:50]:
            abs_path = os.path.join(target_root, f.relative_path)
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="replace") as fh:
                        file_contents[f.relative_path] = fh.read()
                except Exception:
                    continue

        # Step 4: Assemble budgeted context with ContextGovernor
        governor = ContextGovernor(budget=tiered_budget, model_preset=model_preset)
        context_package = governor.assemble_budgeted_context(
            task_id="auto_context",
            task_requirement=task_requirement,
            repo_summary=repo_summary,
            engineering_graph=graph,
            file_contents=file_contents,
        )

        return context_package


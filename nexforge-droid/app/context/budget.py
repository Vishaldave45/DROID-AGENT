"""Context Governor, Token Budgeting, and Relevance Scoring (Phase 7)."""

from dataclasses import dataclass, field
from enum import Enum
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.context.base import (
    ContextBudget,
    ContextPackage,
    EngineeringGraphNode,
    NodeType,
    RepositorySummary,
)
from app.context.engineering_graph import EngineeringGraph


class TokenModelPreset(str, Enum):
    """Supported tokenizer approximation presets."""

    GEMINI_2_FLASH = "gemini-2.0-flash"
    GEMINI_1_5_PRO = "gemini-1.5-pro"
    GPT_4O = "gpt-4o"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet"
    GENERIC_CODE = "generic-code"


@dataclass
class TieredTokenBudget:
    """Detailed multi-tier token allocations preventing prompt flooding."""

    max_total_tokens: int = 32000
    system_prompt_tokens: int = 2000
    task_objective_tokens: int = 1000
    repo_summary_tokens: int = 2500
    graph_symbols_tokens: int = 7000
    file_slices_tokens: int = 12000
    conversation_history_tokens: int = 4500
    output_reserve_tokens: int = 3000

    def validate(self) -> bool:
        """Validates that allocated sub-budgets sum within max_total_tokens."""
        allocated = (
            self.system_prompt_tokens
            + self.task_objective_tokens
            + self.repo_summary_tokens
            + self.graph_symbols_tokens
            + self.file_slices_tokens
            + self.conversation_history_tokens
            + self.output_reserve_tokens
        )
        return allocated <= self.max_total_tokens

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_total_tokens": self.max_total_tokens,
            "system_prompt_tokens": self.system_prompt_tokens,
            "task_objective_tokens": self.task_objective_tokens,
            "repo_summary_tokens": self.repo_summary_tokens,
            "graph_symbols_tokens": self.graph_symbols_tokens,
            "file_slices_tokens": self.file_slices_tokens,
            "conversation_history_tokens": self.conversation_history_tokens,
            "output_reserve_tokens": self.output_reserve_tokens,
            "total_allocated": (
                self.system_prompt_tokens
                + self.task_objective_tokens
                + self.repo_summary_tokens
                + self.graph_symbols_tokens
                + self.file_slices_tokens
                + self.conversation_history_tokens
                + self.output_reserve_tokens
            ),
        }


class TokenEstimator:
    """High-performance heuristic token estimator with model calibration."""

    CALIBRATION_FACTORS: Dict[str, float] = {
        TokenModelPreset.GEMINI_2_FLASH.value: 3.8,  # ~3.8 chars per token in code
        TokenModelPreset.GEMINI_1_5_PRO.value: 3.8,
        TokenModelPreset.GPT_4O.value: 3.7,
        TokenModelPreset.CLAUDE_3_5_SONNET.value: 3.6,
        TokenModelPreset.GENERIC_CODE.value: 3.75,
    }

    @classmethod
    def estimate_tokens(
        cls, text: str, model_preset: str = TokenModelPreset.GEMINI_2_FLASH.value
    ) -> int:
        """Estimates token count using character/whitespace/code symbol heuristics."""
        if not text:
            return 0

        char_ratio = cls.CALIBRATION_FACTORS.get(
            model_preset, cls.CALIBRATION_FACTORS[TokenModelPreset.GENERIC_CODE.value]
        )

        # Baseline character estimate
        char_tokens = len(text) / char_ratio

        # Word count factor (words + punctuation boundaries)
        words = len(text.split())
        word_tokens = words * 1.3

        # Weighted blend (code is denser in symbols than plain prose)
        estimated = int(0.6 * char_tokens + 0.4 * word_tokens)
        return max(1, estimated)

    @classmethod
    def truncate_to_tokens(
        cls, text: str, max_tokens: int, model_preset: str = TokenModelPreset.GEMINI_2_FLASH.value
    ) -> str:
        """Truncates string to fit within max token boundary without splitting lines midway if possible."""
        if cls.estimate_tokens(text, model_preset) <= max_tokens:
            return text

        char_ratio = cls.CALIBRATION_FACTORS.get(
            model_preset, cls.CALIBRATION_FACTORS[TokenModelPreset.GENERIC_CODE.value]
        )
        approx_char_budget = int(max_tokens * char_ratio * 0.95)

        if approx_char_budget >= len(text):
            return text

        truncated = text[:approx_char_budget]
        last_newline = truncated.rfind("\n")
        if last_newline > approx_char_budget * 0.7:
            truncated = truncated[:last_newline]

        return truncated + "\n... [truncated to fit token budget]"


@dataclass
class ScoredSymbol:
    """Graph symbol with relevance score and breakdown."""

    node: EngineeringGraphNode
    relevance_score: float
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    hop_distance: int = 0


@dataclass
class FileSlice:
    """Targeted window slice of a source file."""

    file_path: str
    content: str
    start_line: int
    end_line: int
    total_file_lines: int
    is_truncated: bool
    focal_symbols: List[str] = field(default_factory=list)
    estimated_tokens: int = 0


class RelevanceScorer:
    """Multi-signal scoring engine matching task objectives to symbols and files."""

    def __init__(self, engineering_graph: Optional[EngineeringGraph] = None) -> None:
        self.graph = engineering_graph

    def score_symbols(
        self,
        task_tokens: List[str],
        symbols: List[EngineeringGraphNode],
        focal_symbol_ids: Optional[Set[str]] = None,
        recently_modified_files: Optional[Set[str]] = None,
    ) -> List[ScoredSymbol]:
        """Calculates multi-factor relevance scores for all candidate symbols."""
        focal_ids = focal_symbol_ids or set()
        recent_files = recently_modified_files or set()
        scored_list: List[ScoredSymbol] = []

        # Token set for rapid matching
        normalized_task_tokens = [t.lower() for t in task_tokens if len(t) > 2]

        for node in symbols:
            name_lower = node.name.lower()
            file_lower = node.file_path.lower()
            doc_lower = (node.docstring or "").lower()
            sig_lower = (node.signature or "").lower()

            breakdown: Dict[str, float] = {}

            # 1. Exact Name Match
            name_score = 0.0
            for t in normalized_task_tokens:
                if t == name_lower:
                    name_score = max(name_score, 1.0)
                elif t in name_lower:
                    name_score = max(name_score, 0.7)
            breakdown["name_match"] = name_score

            # 2. File Path / Module Match
            path_score = 0.0
            for t in normalized_task_tokens:
                if t in file_lower:
                    path_score = max(path_score, 0.5)
            breakdown["path_match"] = path_score

            # 3. Docstring & Signature Match
            doc_score = 0.0
            for t in normalized_task_tokens:
                if t in doc_lower or t in sig_lower:
                    doc_score = max(doc_score, 0.4)
            breakdown["doc_sig_match"] = doc_score

            # 4. Graph Proximity / Distance to Focal Points
            graph_score = 0.0
            hop_distance = 999
            if node.node_id in focal_ids:
                graph_score = 1.0
                hop_distance = 0
            elif self.graph and focal_ids:
                for focal_id in focal_ids:
                    # Check 1-hop calls or callers
                    callers = self.graph.get_callers(focal_id)
                    callees = self.graph.get_callees(focal_id)
                    if any(c.node_id == node.node_id for c in callers + callees):
                        graph_score = max(graph_score, 0.8)
                        hop_distance = min(hop_distance, 1)
                        break
            breakdown["graph_proximity"] = graph_score

            # 5. File Recency / Modified Status
            recency_score = 0.8 if node.file_path in recent_files else 0.0
            breakdown["recency"] = recency_score

            # 6. Test Symbol Affinity
            test_score = 0.0
            if node.node_type == NodeType.TEST:
                test_score = 0.6 if any(t in name_lower for t in normalized_task_tokens) else 0.2
            breakdown["test_affinity"] = test_score

            # Weighted Composite Score (0.0 to 1.0)
            composite_score = (
                breakdown["name_match"] * 0.35
                + breakdown["graph_proximity"] * 0.25
                + breakdown["path_match"] * 0.15
                + breakdown["doc_sig_match"] * 0.10
                + breakdown["recency"] * 0.10
                + breakdown["test_affinity"] * 0.05
            )

            scored_list.append(
                ScoredSymbol(
                    node=node,
                    relevance_score=round(composite_score, 4),
                    score_breakdown=breakdown,
                    hop_distance=hop_distance,
                )
            )

        # Sort descending by relevance score
        scored_list.sort(key=lambda s: s.relevance_score, reverse=True)
        return scored_list


class CodeChunkTruncator:
    """Performs intelligent semantic line slicing with context window anchors."""

    @classmethod
    def slice_file(
        cls,
        file_path: str,
        full_content: str,
        focal_symbols: List[EngineeringGraphNode],
        max_tokens: int = 1500,
        model_preset: str = TokenModelPreset.GEMINI_2_FLASH.value,
    ) -> FileSlice:
        """Slices file to preserve module imports + target symbol definitions with breadcrumbs."""
        lines = full_content.splitlines()
        total_lines = len(lines)

        full_tokens = TokenEstimator.estimate_tokens(full_content, model_preset)
        if full_tokens <= max_tokens:
            return FileSlice(
                file_path=file_path,
                content=full_content,
                start_line=1,
                end_line=total_lines,
                total_file_lines=total_lines,
                is_truncated=False,
                focal_symbols=[s.name for s in focal_symbols],
                estimated_tokens=full_tokens,
            )

        # Identify target lines to preserve
        target_line_ranges: List[Tuple[int, int]] = []

        # Always preserve top imports (lines 1 to min(25, total_lines))
        import_end = min(25, total_lines)
        target_line_ranges.append((1, import_end))

        for sym in focal_symbols:
            if sym.line_start > 0 and sym.line_end > 0:
                pad_before = max(1, sym.line_start - 5)
                pad_after = min(total_lines, sym.line_end + 8)
                target_line_ranges.append((pad_before, pad_after))

        # Merge overlapping ranges
        target_line_ranges.sort(key=lambda r: r[0])
        merged_ranges: List[Tuple[int, int]] = []
        for r in target_line_ranges:
            if not merged_ranges:
                merged_ranges.append(r)
            else:
                last_start, last_end = merged_ranges[-1]
                if r[0] <= last_end + 3:  # Merge if gap is small
                    merged_ranges[-1] = (last_start, max(last_end, r[1]))
                else:
                    merged_ranges.append(r)

        # Assemble sliced text with folding breadcrumbs
        assembled_lines: List[str] = []
        last_emitted_line = 0

        for start_idx, end_idx in merged_ranges:
            if start_idx > last_emitted_line + 1:
                skipped_count = start_idx - last_emitted_line - 1
                assembled_lines.append(
                    f"\n# ... [folded {skipped_count} lines (lines {last_emitted_line + 1}-{start_idx - 1})] ...\n"
                )

            for line_no in range(start_idx, end_idx + 1):
                if 1 <= line_no <= total_lines:
                    assembled_lines.append(lines[line_no - 1])

            last_emitted_line = end_idx

        if last_emitted_line < total_lines:
            skipped_tail = total_lines - last_emitted_line
            assembled_lines.append(
                f"\n# ... [folded {skipped_tail} trailing lines (lines {last_emitted_line + 1}-{total_lines})] ...\n"
            )

        sliced_content = "\n".join(assembled_lines)
        sliced_tokens = TokenEstimator.estimate_tokens(sliced_content, model_preset)

        # If still over budget, hard truncate
        if sliced_tokens > max_tokens:
            sliced_content = TokenEstimator.truncate_to_tokens(sliced_content, max_tokens, model_preset)
            sliced_tokens = TokenEstimator.estimate_tokens(sliced_content, model_preset)

        return FileSlice(
            file_path=file_path,
            content=sliced_content,
            start_line=1,
            end_line=total_lines,
            total_file_lines=total_lines,
            is_truncated=True,
            focal_symbols=[s.name for s in focal_symbols],
            estimated_tokens=sliced_tokens,
        )


class ContextGovernor:
    """Strict token budget governor and context package assembler."""

    def __init__(
        self,
        budget: Optional[TieredTokenBudget] = None,
        model_preset: str = TokenModelPreset.GEMINI_2_FLASH.value,
    ) -> None:
        self.budget = budget or TieredTokenBudget()
        self.model_preset = model_preset
        self.token_estimator = TokenEstimator()
        self.chunk_truncator = CodeChunkTruncator()

    def assemble_budgeted_context(
        self,
        task_id: str,
        task_requirement: str,
        repo_summary: RepositorySummary,
        engineering_graph: EngineeringGraph,
        recent_files: Optional[Set[str]] = None,
        file_contents: Optional[Dict[str, str]] = None,
    ) -> ContextPackage:
        """Assembles a high-signal, zero-overflow context package governed by token limits."""
        scorer = RelevanceScorer(engineering_graph)
        task_tokens = [w.strip(".,;:()[]{}\"'`") for w in task_requirement.split() if len(w) > 2]

        all_nodes = list(engineering_graph.nodes.values())
        scored_symbols = scorer.score_symbols(
            task_tokens=task_tokens,
            symbols=all_nodes,
            recently_modified_files=recent_files,
        )

        # 1. Repo Summary Budget Allocation
        summary_dict = repo_summary.to_dict()
        summary_str = str(summary_dict)
        summary_tokens = self.token_estimator.estimate_tokens(summary_str, self.model_preset)
        if summary_tokens > self.budget.repo_summary_tokens:
            # Compress summary by trimming sample files
            summary_dict["files_sample"] = summary_dict.get("files_sample", [])[:10]
            summary_str = str(summary_dict)
            summary_tokens = self.token_estimator.estimate_tokens(summary_str, self.model_preset)

        # 2. Pack Symbols within graph_symbols_tokens
        packed_symbols: List[EngineeringGraphNode] = []
        accumulated_symbol_tokens = 0
        focal_symbol_ids: Set[str] = set()

        for scored in scored_symbols:
            sym_tokens = self.token_estimator.estimate_tokens(str(scored.node.to_dict()), self.model_preset)
            if accumulated_symbol_tokens + sym_tokens <= self.budget.graph_symbols_tokens:
                packed_symbols.append(scored.node)
                accumulated_symbol_tokens += sym_tokens
                if scored.relevance_score >= 0.3:
                    focal_symbol_ids.add(scored.node.node_id)
            else:
                break

        # 3. Pack File Slices within file_slices_tokens
        packed_file_slices: Dict[str, str] = {}
        accumulated_file_tokens = 0
        raw_files = file_contents or {}

        # Prioritize files belonging to focal symbols
        files_by_importance: Dict[str, List[EngineeringGraphNode]] = {}
        for sym in packed_symbols:
            if sym.file_path:
                files_by_importance.setdefault(sym.file_path, []).append(sym)

        # Compute per-file token budget
        num_target_files = max(1, len(files_by_importance))
        per_file_budget = max(400, self.budget.file_slices_tokens // num_target_files)

        for file_path, syms in files_by_importance.items():
            content = raw_files.get(file_path, "")
            if not content:
                continue

            f_slice = self.chunk_truncator.slice_file(
                file_path=file_path,
                full_content=content,
                focal_symbols=syms,
                max_tokens=per_file_budget,
                model_preset=self.model_preset,
            )

            if accumulated_file_tokens + f_slice.estimated_tokens <= self.budget.file_slices_tokens:
                packed_file_slices[file_path] = f_slice.content
                accumulated_file_tokens += f_slice.estimated_tokens

        total_estimated = summary_tokens + accumulated_symbol_tokens + accumulated_file_tokens

        return ContextPackage(
            task_id=task_id,
            repository_summary=repo_summary,
            relevant_files=packed_file_slices,
            symbols=packed_symbols,
            estimated_tokens=total_estimated,
            metadata={
                "governor_budget": self.budget.to_dict(),
                "tokens_by_tier": {
                    "repo_summary": summary_tokens,
                    "graph_symbols": accumulated_symbol_tokens,
                    "file_slices": accumulated_file_tokens,
                },
                "symbols_packed": len(packed_symbols),
                "symbols_total_evaluated": len(all_nodes),
                "files_sliced": len(packed_file_slices),
                "model_preset": self.model_preset,
            },
        )

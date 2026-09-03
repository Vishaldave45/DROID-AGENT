"""Diagnostic Reasoner: source code correlation, root-cause hypothesis generation, and patch proposal."""

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.diagnostics.traceback_parser import FailureCategory, ParsedFailure, StackFrame
from app.observability.logger import get_logger

logger = get_logger("nexforge.diagnostics.reasoner")


@dataclass
class DiagnosisHypothesis:
    """Hypothesis of root-cause for a diagnostic failure with proposed fix strategy."""

    failure_id: str
    test_name: str
    error_type: str
    error_message: str
    category: str
    primary_file: str
    target_line: int
    function_name: str
    code_context: str
    suspect_symbols: List[str] = field(default_factory=list)
    suggested_fix_strategy: str = "GENERAL_CORRECTION"
    confidence_score: float = 0.5
    root_cause_summary: str = ""
    proposed_target_content: Optional[str] = None
    proposed_replacement_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "failure_id": self.failure_id,
            "test_name": self.test_name,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "category": self.category,
            "primary_file": self.primary_file,
            "target_line": self.target_line,
            "function_name": self.function_name,
            "code_context": self.code_context,
            "suspect_symbols": self.suspect_symbols,
            "suggested_fix_strategy": self.suggested_fix_strategy,
            "confidence_score": round(self.confidence_score, 2),
            "root_cause_summary": self.root_cause_summary,
            "proposed_target_content": self.proposed_target_content,
            "proposed_replacement_content": self.proposed_replacement_content,
        }


class DiagnosticReasoner:
    """Extracts source context around stack frames and synthesizes targeted fix strategies."""

    def __init__(self, workspace_root: Optional[str] = None) -> None:
        self.workspace_root = workspace_root or os.getcwd()

    def _resolve_file_path(self, path_str: str) -> Optional[str]:
        """Resolves file path against workspace root if relative or absolute."""
        if os.path.isabs(path_str) and os.path.exists(path_str):
            return path_str
        
        # Try direct relative
        cand = os.path.join(self.workspace_root, path_str.lstrip("./"))
        if os.path.exists(cand):
            return cand
        
        # Search workspace for basename if not found directly
        base = os.path.basename(path_str)
        for root, _, files in os.walk(self.workspace_root):
            if base in files:
                return os.path.join(root, base)
        return None

    def extract_source_context(
        self, file_path: str, line_number: int, context_lines: int = 5
    ) -> Dict[str, Any]:
        """Reads lines surrounding a target line in a source file."""
        resolved = self._resolve_file_path(file_path)
        if not resolved or not os.path.isfile(resolved):
            return {
                "exists": False,
                "resolved_path": file_path,
                "lines": [],
                "target_line_content": "",
                "context_text": "",
            }

        try:
            with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            total_lines = len(all_lines)
            start_idx = max(0, line_number - 1 - context_lines)
            end_idx = min(total_lines, line_number + context_lines)

            target_content = all_lines[line_number - 1].rstrip() if 0 < line_number <= total_lines else ""
            context_snippet = "".join(
                f"{i + 1:4d} | {all_lines[i]}" for i in range(start_idx, end_idx)
            )

            return {
                "exists": True,
                "resolved_path": resolved,
                "lines": all_lines[start_idx:end_idx],
                "target_line_content": target_content,
                "context_text": context_snippet,
            }
        except Exception as e:
            logger.warning(f"Failed to read source context for {file_path}:{line_number}: {e}")
            return {
                "exists": False,
                "resolved_path": file_path,
                "lines": [],
                "target_line_content": "",
                "context_text": "",
            }

    def analyze_failure(self, failure: ParsedFailure) -> DiagnosisHypothesis:
        """Synthesizes stack frame traceback and source context into a concrete diagnostic hypothesis."""
        target_frame: Optional[StackFrame] = failure.innermost_frame
        if not target_frame and failure.frames:
            target_frame = failure.frames[-1]

        primary_file = target_frame.file_path if target_frame else "<unknown_file>"
        target_line = target_frame.line_number if target_frame else 1
        func_name = target_frame.function_name if target_frame else "<unknown_func>"

        ctx = self.extract_source_context(primary_file, target_line)
        target_line_content = ctx.get("target_line_content", "")
        code_context = ctx.get("context_text", target_frame.code_snippet if target_frame else "")

        # Extract potential variable symbols from error message and target line
        suspects: List[str] = []
        if failure.error_message:
            # Look for quoted identifiers e.g. 'foo' or "foo"
            quoted = re.findall(r"['\"]([A-Za-z0-9_]+)['\"]", failure.error_message)
            suspects.extend(quoted)

        # Look for identifiers in target line
        if target_line_content:
            line_idents = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", target_line_content)
            for ident in line_idents:
                if ident not in ["def", "class", "return", "if", "for", "while", "import", "from", "self", "in"]:
                    if ident not in suspects:
                        suspects.append(ident)

        category = failure.category if isinstance(failure.category, FailureCategory) else FailureCategory(str(failure.category))
        
        # Formulate fix strategy and proposed patch based on category heuristics
        strategy = "GENERAL_LOGIC_FIX"
        summary = f"Failure during {func_name} due to {failure.error_type}: {failure.error_message}"
        confidence = 0.65
        proposed_target = None
        proposed_replacement = None

        if category == FailureCategory.ZERO_DIVISION:
            strategy = "ZERO_DIVISION_GUARD"
            summary = f"Division by zero in '{primary_file}' at line {target_line}. Denominator variable must be guarded against 0 or None."
            confidence = 0.90
            if target_line_content:
                proposed_target = target_line_content
                # e.g. "return a / b" -> "return a / b if b != 0 else 0.0"
                if "/" in target_line_content:
                    parts = target_line_content.split("/")
                    denom = parts[1].strip().split()[0].rstrip("),")
                    proposed_replacement = f"{target_line_content} if {denom} != 0 else 0.0"

        elif category == FailureCategory.INDEX_ERROR:
            strategy = "BOUNDS_CHECK_GUARD"
            summary = f"Index out of range access in '{primary_file}' at line {target_line}. Sequence must be checked for non-empty length before indexing."
            confidence = 0.85
            if target_line_content:
                proposed_target = target_line_content
                proposed_replacement = f"if not sequence: return None\n{target_line_content}"

        elif category == FailureCategory.KEY_ERROR:
            strategy = "SAFE_KEY_GET"
            summary = f"Dictionary key lookup failed in '{primary_file}' at line {target_line}. Use `.get(key, default)` or `key in dict` guard."
            confidence = 0.85

        elif category == FailureCategory.ATTRIBUTE_ERROR or "NoneType" in failure.error_message:
            strategy = "NULL_POINTER_GUARD"
            summary = f"Attempted to access attribute or method on None in '{primary_file}' at line {target_line}. Add null check before dereferencing."
            confidence = 0.80

        elif category == FailureCategory.TYPE_ERROR:
            strategy = "TYPE_CONVERSION_OR_FALLBACK"
            summary = f"Type mismatch or invalid argument type in '{primary_file}' at line {target_line}. Cast or validate types before operation."
            confidence = 0.75

        elif category == FailureCategory.ASSERTION_ERROR:
            strategy = "EXPECTED_VALUE_ALIGNMENT"
            summary = f"Assertion failed in test '{failure.test_name}'. Verification condition evaluated to false: {failure.error_message}"
            confidence = 0.70

        hypothesis_id = f"hyp-{abs(hash(failure.test_name + primary_file + str(target_line))) % 100000:05d}"

        return DiagnosisHypothesis(
            failure_id=hypothesis_id,
            test_name=failure.test_name,
            error_type=failure.error_type,
            error_message=failure.error_message,
            category=category.value,
            primary_file=primary_file,
            target_line=target_line,
            function_name=func_name,
            code_context=code_context,
            suspect_symbols=suspects[:6],
            suggested_fix_strategy=strategy,
            confidence_score=confidence,
            root_cause_summary=summary,
            proposed_target_content=proposed_target,
            proposed_replacement_content=proposed_replacement,
        )

    def generate_targeted_patch_proposal(
        self, hypothesis: DiagnosisHypothesis
    ) -> Dict[str, Any]:
        """Creates a patch proposal ready for consumption by ApplyPatchTool or SurgicalEditTool."""
        return {
            "hypothesis_id": hypothesis.failure_id,
            "file_path": hypothesis.primary_file,
            "strategy": hypothesis.suggested_fix_strategy,
            "target_line": hypothesis.target_line,
            "proposed_target": hypothesis.proposed_target_content,
            "proposed_replacement": hypothesis.proposed_replacement_content,
            "confidence": hypothesis.confidence_score,
            "summary": hypothesis.root_cause_summary,
        }

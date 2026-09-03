"""Unit tests for Phase 7 Context Engine & Token Budgeting."""

import os
import tempfile
import unittest

from app.context.base import ContextBudget, ContextPackage, EngineeringGraphNode, NodeType, RepositorySummary
from app.context.budget import (
    CodeChunkTruncator,
    ContextGovernor,
    RelevanceScorer,
    TieredTokenBudget,
    TokenEstimator,
    TokenModelPreset,
)
from app.context.engine import RepositoryContextEngine
from app.context.engineering_graph import EngineeringGraph


class TestContextBudgeting(unittest.TestCase):
    """Test suite for token estimation, relevance scoring, chunk truncator, and context governor."""

    def test_token_estimator_and_truncation(self) -> None:
        text = "def calculate_sum(a: int, b: int) -> int:\n    return a + b\n"
        est_tokens = TokenEstimator.estimate_tokens(text)
        self.assertGreater(est_tokens, 0)
        self.assertLess(est_tokens, 50)

        # Truncation test
        long_text = "line 1\n" * 500
        truncated = TokenEstimator.truncate_to_tokens(long_text, max_tokens=50)
        self.assertIn("truncated", truncated)
        self.assertLess(TokenEstimator.estimate_tokens(truncated), 80)

    def test_tiered_token_budget_validation(self) -> None:
        budget = TieredTokenBudget(
            max_total_tokens=32000,
            system_prompt_tokens=2000,
            task_objective_tokens=1000,
            repo_summary_tokens=2500,
            graph_symbols_tokens=7000,
            file_slices_tokens=12000,
            conversation_history_tokens=4500,
            output_reserve_tokens=3000,
        )
        self.assertTrue(budget.validate())

        # Test overflow budget
        bad_budget = TieredTokenBudget(max_total_tokens=10000, file_slices_tokens=15000)
        self.assertFalse(bad_budget.validate())

    def test_relevance_scorer(self) -> None:
        node1 = EngineeringGraphNode(
            node_id="app.payment:process_order",
            node_type=NodeType.FUNCTION,
            name="process_order",
            file_path="app/payment.py",
            line_start=10,
            line_end=25,
            docstring="Processes user credit card orders and validates transactions.",
            signature="def process_order(order_id: str, amount: float) -> bool",
        )
        node2 = EngineeringGraphNode(
            node_id="app.utils:format_currency",
            node_type=NodeType.FUNCTION,
            name="format_currency",
            file_path="app/utils.py",
            line_start=5,
            line_end=12,
            docstring="Formats raw float into localized currency string.",
            signature="def format_currency(val: float) -> str",
        )

        scorer = RelevanceScorer()
        scored = scorer.score_symbols(
            task_tokens=["process_order", "transaction", "payment"],
            symbols=[node1, node2],
        )

        self.assertEqual(len(scored), 2)
        # node1 must score significantly higher than node2
        self.assertEqual(scored[0].node.name, "process_order")
        self.assertGreater(scored[0].relevance_score, scored[1].relevance_score)

    def test_code_chunk_truncator_folding(self) -> None:
        file_lines = []
        for i in range(1, 101):
            file_lines.append(f"# Line {i}: statement_{i} = {i}")
        full_content = "\n".join(file_lines)

        focal_node = EngineeringGraphNode(
            node_id="test:target_sym",
            node_type=NodeType.FUNCTION,
            name="target_sym",
            file_path="sample.py",
            line_start=40,
            line_end=45,
        )

        f_slice = CodeChunkTruncator.slice_file(
            file_path="sample.py",
            full_content=full_content,
            focal_symbols=[focal_node],
            max_tokens=300,
        )

        self.assertTrue(f_slice.is_truncated)
        self.assertIn("folded", f_slice.content)
        self.assertIn("statement_40", f_slice.content)

    def test_context_governor_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a mock repository
            src_dir = os.path.join(temp_dir, "src")
            os.makedirs(src_dir, exist_ok=True)
            with open(os.path.join(src_dir, "math.py"), "w") as f:
                f.write("def add(x: int, y: int) -> int:\n    return x + y\n")

            engine = RepositoryContextEngine(repo_root=temp_dir)
            ctx = engine.build_context(
                task_requirement="Fix integer addition in math.py",
                repo_root=temp_dir,
                budget=ContextBudget(max_total_tokens=16000),
            )

            self.assertIsInstance(ctx, ContextPackage)
            self.assertGreater(ctx.estimated_tokens, 0)
            self.assertIn("tokens_by_tier", ctx.metadata)
            self.assertIn("governor_budget", ctx.metadata)


if __name__ == "__main__":
    unittest.main()

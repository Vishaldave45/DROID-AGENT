"""Unit tests for Phase 13 Multi-Criteria Quality Gate and SWE Benchmark Runner."""

import os
import shutil
import tempfile
import unittest

from app.evaluation.benchmark_runner import SWEBenchmarkSuite, BenchmarkChallenge, BenchmarkRunResult
from app.evaluation.quality_gate import (
    MultiCriteriaQualityGate,
    QualityDimension,
    QualityGateReport,
    DimensionResult,
)


class TestEvaluationEngine(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_eval_test_")
        self.gate = MultiCriteriaQualityGate(workspace_root=self.temp_dir)

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_quality_gate_dimensions_clean_workspace(self) -> None:
        """Tests that a clean valid Python workspace passes all dimensions."""
        src_file = os.path.join(self.temp_dir, "app", "calculator.py")
        os.makedirs(os.path.dirname(src_file), exist_ok=True)
        with open(src_file, "w", encoding="utf-8") as f:
            f.write(
                '"""Clean module."""\n\n'
                'def add_numbers(a: int, b: int) -> int:\n'
                '    """Add two numbers."""\n'
                '    return a + b\n'
            )

        report = self.gate.evaluate_all(files=[src_file])
        self.assertIsInstance(report, QualityGateReport)
        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.overall_score, 85.0)
        self.assertEqual(report.gate_status, "PASSED")
        self.assertEqual(len(report.dimensions), 6)

    def test_quality_gate_detects_syntax_error(self) -> None:
        """Tests that invalid AST syntax is caught with line number and fails the dimension."""
        broken_file = os.path.join(self.temp_dir, "app", "broken.py")
        os.makedirs(os.path.dirname(broken_file), exist_ok=True)
        with open(broken_file, "w", encoding="utf-8") as f:
            f.write("def broken_func(\n    return 42\n")

        dim_res = self.gate.audit_ast_integrity(files=[broken_file])
        self.assertFalse(dim_res.passed)
        self.assertGreater(len(dim_res.findings), 0)
        self.assertIn("SyntaxError", dim_res.findings[0])

    def test_quality_gate_detects_security_violation(self) -> None:
        """Tests that dangerous patterns in production code are flagged as critical vulnerabilities."""
        vuln_file = os.path.join(self.temp_dir, "app", "danger.py")
        os.makedirs(os.path.dirname(vuln_file), exist_ok=True)
        with open(vuln_file, "w", encoding="utf-8") as f:
            f.write(
                'import os\n'
                'def wipe():\n'
                '    os.system("rm -rf / --no-preserve-root")\n'
            )

        dim_res = self.gate.audit_security(files=[vuln_file])
        self.assertFalse(dim_res.passed)
        self.assertIn("Destructive recursive shell command pattern detected", dim_res.findings[0])

    def test_benchmark_catalog_integrity(self) -> None:
        """Verifies SWE-bench catalog has all 5 challenges with non-empty specifications."""
        suite = SWEBenchmarkSuite()
        challenges = suite.list_challenges()
        self.assertEqual(len(challenges), 5)

        categories = {c.category for c in challenges}
        self.assertIn("BugFix", categories)
        self.assertIn("Feature", categories)
        self.assertIn("Refactor", categories)
        self.assertIn("Security", categories)
        self.assertIn("Performance", categories)

        for c in challenges:
            self.assertTrue(c.id.startswith("BM-"))
            self.assertGreater(len(c.title), 5)
            self.assertGreater(len(c.problem_statement), 20)
            self.assertGreater(len(c.target_files), 0)
            self.assertGreater(len(c.invariants), 0)
            self.assertGreater(c.baseline_duration_ms, 0)
            self.assertGreater(c.expected_tokens, 100)

    def test_benchmark_execution(self) -> None:
        """Executes a benchmark challenge and checks result structure and scoring."""
        suite = SWEBenchmarkSuite()
        result = suite.run_challenge("BM-001")

        self.assertIsInstance(result, BenchmarkRunResult)
        self.assertEqual(result.challenge_id, "BM-001")
        self.assertEqual(result.category, "BugFix")
        self.assertTrue(result.success)
        self.assertTrue(result.pass_at_1)
        self.assertGreaterEqual(result.quality_score, 80.0)
        self.assertGreater(result.duration_ms, 0)
        self.assertEqual(result.test_metrics.get("failed", 0), 0)

    def test_benchmark_leaderboard_aggregation(self) -> None:
        """Tests that get_leaderboard aggregates results into overall metrics."""
        suite = SWEBenchmarkSuite()
        # Seed a run
        suite.run_challenge("BM-001")
        board = suite.get_leaderboard()

        self.assertIn("total_benchmarks", board)
        self.assertIn("total_runs", board)
        self.assertIn("pass_at_1_rate", board)
        self.assertIn("average_quality_score", board)
        self.assertIn("categories", board)
        self.assertGreater(len(board["runs"]), 0)
        self.assertGreaterEqual(board["pass_at_1_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

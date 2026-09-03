"""
Tests for Phase 14: UV Package Engine, Unified CLI Distribution & Production Packaging.
"""

import os
import sys
import unittest
import io
import json
from unittest.mock import patch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.cli.main import (
    main,
    build_parser,
    get_uv_environment_info,
)


class TestCliDistribution(unittest.TestCase):
    """Verifies CLI entrypoints, UV detection, and subcommand executions."""

    def test_uv_environment_info_structure(self):
        """Verifies UV environment detection returns compliant dictionary."""
        info = get_uv_environment_info()
        self.assertIsInstance(info, dict)
        self.assertIn("uv_available", info)
        self.assertIn("python_version", info)
        self.assertIn("workspace_root", info)
        self.assertIn("timestamp", info)
        self.assertTrue(os.path.isdir(info["workspace_root"]))

    def test_cli_parser_build(self):
        """Verifies argparse configuration defines all required subcommands."""
        parser = build_parser()
        subparsers_action = None
        for action in parser._actions:
            if hasattr(action, "choices") and action.choices:
                subparsers_action = action
                break

        self.assertIsNotNone(subparsers_action)
        self.assertIn("info", subparsers_action.choices)
        self.assertIn("bench", subparsers_action.choices)
        self.assertIn("gate", subparsers_action.choices)
        self.assertIn("scan", subparsers_action.choices)
        self.assertIn("run", subparsers_action.choices)

    def test_cli_info_command_execution(self):
        """Verifies nexforge info --json outputs valid JSON payload."""
        captured_out = io.StringIO()
        with patch("sys.stdout", captured_out):
            exit_code = main(["info", "--json"])

        self.assertEqual(exit_code, 0)
        output = captured_out.getvalue().strip()
        data = json.loads(output)
        self.assertEqual(data.get("system"), "NexForge Droid")
        self.assertEqual(data.get("phase"), 14)
        self.assertIn("uv_environment", data)

    def test_cli_bench_list_and_single(self):
        """Verifies nexforge bench lists challenges and runs benchmark."""
        # Test listing
        captured_list = io.StringIO()
        with patch("sys.stdout", captured_list):
            code_list = main(["bench", "--json"])
        self.assertEqual(code_list, 0)
        challenges = json.loads(captured_list.getvalue().strip())
        self.assertIsInstance(challenges, list)
        self.assertGreaterEqual(len(challenges), 5)

        # Test single benchmark run
        captured_single = io.StringIO()
        with patch("sys.stdout", captured_single):
            code_single = main(["bench", "BM-001", "--json"])
        self.assertEqual(code_single, 0)
        result = json.loads(captured_single.getvalue().strip())
        self.assertEqual(result.get("challenge_id"), "BM-001")
        self.assertTrue(result.get("success"))

    def test_cli_gate_command_execution(self):
        """Verifies nexforge gate --json executes 6D quality gate."""
        from app.evaluation.quality_gate import DimensionResult, QualityDimension
        mock_dim = DimensionResult(
            dimension=QualityDimension.TEST_SUITE.value,
            name="Test Suite & Regression Verification",
            score=100.0,
            weight=0.3,
            passed=True,
            metrics={"total_tests": 1, "passed": 1, "failed": 0, "errors": 0},
            findings=[],
        )
        captured_gate = io.StringIO()
        with patch("app.evaluation.quality_gate.MultiCriteriaQualityGate.audit_tests", return_value=mock_dim):
            with patch("sys.stdout", captured_gate):
                code_gate = main([
                    "gate",
                    "--json",
                    os.path.join(BASE_DIR, "app", "storage", "base.py"),
                ])
        self.assertEqual(code_gate, 0)
        report = json.loads(captured_gate.getvalue().strip())
        self.assertIn("overall_score", report)
        self.assertIn("dimensions", report)
        self.assertEqual(len(report["dimensions"]), 6)

    def test_cli_scan_command_execution(self):
        """Verifies nexforge scan --json scans symbols."""
        captured_scan = io.StringIO()
        with patch("sys.stdout", captured_scan):
            code_scan = main([
                "scan",
                "--json",
                "--path",
                os.path.join(BASE_DIR, "app", "cli"),
            ])
        self.assertEqual(code_scan, 0)
        scan_data = json.loads(captured_scan.getvalue().strip())
        self.assertIn("files", scan_data)
        self.assertIn("total_lines_of_code", scan_data)


if __name__ == "__main__":
    unittest.main()

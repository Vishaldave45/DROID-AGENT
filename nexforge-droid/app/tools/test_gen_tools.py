"""Phase 19: Autonomous Test Suite Synthesis & Mutation Testing Tools for LLM ToolRegistry."""

import os
import time
from typing import Any, Dict, Optional

from app.testing.coverage import ASTCoverageEstimator
from app.testing.mutator import MutationEngine
from app.testing.synthesizer import TestSynthesizer
from app.tools.base import Tool, ToolResult


class SynthesizeTestsTool(Tool):
    """Autonomously synthesizes Python unittest.TestCase suites with edge cases and mock fixtures."""

    name = "synthesize_unit_tests"
    description = "Autonomously synthesizes comprehensive unittest.TestCase test suites from Python source code or files."
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Relative path to target Python file to generate tests for.",
            },
            "source_code": {
                "type": "string",
                "description": "Optional inline Python source code to synthesize tests for directly.",
            },
            "module_name": {
                "type": "string",
                "description": "Module import name for generated tests.",
                "default": "target_module",
            },
            "include_edge_cases": {
                "type": "boolean",
                "description": "Whether to include boundary, empty collection, and defensive error test cases.",
                "default": True,
            },
        },
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        file_path = kwargs.get("file_path")
        source_code = kwargs.get("source_code")
        module_name = kwargs.get("module_name", "target_module")
        include_edge_cases = kwargs.get("include_edge_cases", True)
        workspace_root = kwargs.get("workspace_root", os.getcwd())

        synthesizer = TestSynthesizer(workspace_root=workspace_root)

        if not source_code:
            if not file_path:
                return ToolResult(success=False, error="Either 'file_path' or 'source_code' must be provided.")
            abs_path = os.path.join(workspace_root, file_path)
            if not os.path.isfile(abs_path):
                return ToolResult(success=False, error=f"File not found: {file_path}")
            with open(abs_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            if not module_name or module_name == "target_module":
                module_name = os.path.splitext(os.path.basename(file_path))[0]

        suite = synthesizer.synthesize_tests(
            source_code=source_code,
            module_name=module_name,
            file_path=file_path or "inline_code.py",
            include_edge_cases=include_edge_cases,
        )

        return ToolResult(
            success=True,
            data=suite.to_dict(),
            metadata={"output": f"Synthesized {suite.total_tests} unit tests for module '{suite.target_module}'."},
        )


class RunMutationTestTool(Tool):
    """Executes AST mutation testing to calculate test suite robustness and mutation score."""

    name = "run_mutation_tests"
    description = "Executes AST mutation testing (AOR, ROR, COR, LCR, SVR) to evaluate test suite effectiveness and compute mutation score."
    input_schema = {
        "type": "object",
        "properties": {
            "source_code": {
                "type": "string",
                "description": "Target Python source code under test.",
            },
            "test_code": {
                "type": "string",
                "description": "The unittest test suite code to execute against mutated variants.",
            },
            "max_mutants": {
                "type": "integer",
                "description": "Maximum number of AST mutants to evaluate.",
                "default": 15,
            },
        },
        "required": ["source_code", "test_code"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        source_code = kwargs.get("source_code")
        test_code = kwargs.get("test_code")
        max_mutants = int(kwargs.get("max_mutants", 15))
        workspace_root = kwargs.get("workspace_root", os.getcwd())

        if not source_code or not test_code:
            return ToolResult(success=False, error="Both 'source_code' and 'test_code' are required.")

        engine = MutationEngine(workspace_root=workspace_root)
        report = engine.evaluate_mutants(
            source_code=source_code,
            test_code=test_code,
            max_mutants=max_mutants,
        )

        return ToolResult(
            success=True,
            data=report.to_dict(),
            metadata={"output": f"Mutation testing complete: Score {report.mutation_score:.1f}% ({report.killed_count} killed, {report.survived_count} survived)."},
        )


class CoverageAuditTool(Tool):
    """Estimates statement and branch test coverage from source and test code AST."""

    name = "analyze_test_coverage"
    description = "Estimates statement and branch test coverage from source code and test suite AST."
    input_schema = {
        "type": "object",
        "properties": {
            "source_code": {
                "type": "string",
                "description": "Target Python source code to evaluate.",
            },
            "test_code": {
                "type": "string",
                "description": "Optional test code to measure coverage against.",
            },
            "file_path": {
                "type": "string",
                "description": "Optional file path identifier.",
                "default": "target.py",
            },
        },
        "required": ["source_code"],
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        source_code = kwargs.get("source_code")
        test_code = kwargs.get("test_code")
        file_path = kwargs.get("file_path", "target.py")
        workspace_root = kwargs.get("workspace_root", os.getcwd())

        if not source_code:
            return ToolResult(success=False, error="'source_code' is required.")

        estimator = ASTCoverageEstimator(workspace_root=workspace_root)
        summary = estimator.estimate_coverage(
            source_code=source_code,
            test_code=test_code,
            file_path=file_path,
        )

        return ToolResult(
            success=True,
            data=summary.to_dict(),
            metadata={"output": f"Coverage analysis: {summary.overall_coverage_pct:.1f}% estimated coverage ({summary.covered_statements}/{summary.total_statements} statements)."},
        )

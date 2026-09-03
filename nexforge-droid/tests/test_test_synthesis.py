"""Unit test suite for Phase 19: Autonomous Test Suite Synthesizer & Mutation Testing Engine."""

import os
import unittest

from app.testing.coverage import ASTCoverageEstimator
from app.testing.mutator import MutationEngine, MutationOperator
from app.testing.synthesizer import TestSynthesizer
from app.tools import get_default_tool_registry


SAMPLE_MODULE_CODE = '''"""Sample arithmetic and business logic module for test synthesis."""

def calculate_discount(price: float, is_vip: bool) -> float:
    """Calculates discounted item price."""
    if price < 0:
        raise ValueError("Price cannot be negative")
    if is_vip:
        return price * 0.8
    return price * 0.95

def is_eligible(age: int, has_consent: bool) -> bool:
    """Determines eligibility based on age and consent."""
    return age >= 18 and has_consent

class AccountService:
    """Manages bank account balances."""

    def __init__(self):
        self.balance = 100.0

    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balance += amount
        return self.balance
'''

SAMPLE_TEST_CODE = '''import unittest

class TestDiscount(unittest.TestCase):
    def test_calculate_discount_vip(self):
        self.assertEqual(calculate_discount(100.0, True), 80.0)

    def test_calculate_discount_standard(self):
        self.assertEqual(calculate_discount(100.0, False), 95.0)

    def test_calculate_discount_negative(self):
        with self.assertRaises(ValueError):
            calculate_discount(-10.0, False)

    def test_is_eligible_pass(self):
        self.assertTrue(is_eligible(20, True))

    def test_is_eligible_minor(self):
        self.assertFalse(is_eligible(15, True))
'''

WEAK_TEST_CODE = '''import unittest

class TestWeak(unittest.TestCase):
    def test_run_something(self):
        # Weak test without strict assertions
        res = calculate_discount(100.0, True)
        self.assertIsNotNone(res)
'''


class TestTestSynthesisAndMutation(unittest.TestCase):
    """Test coverage for Phase 19 components."""

    def setUp(self):
        self.workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.synthesizer = TestSynthesizer(workspace_root=self.workspace_root)
        self.mutator = MutationEngine(workspace_root=self.workspace_root)
        self.coverage_est = ASTCoverageEstimator(workspace_root=self.workspace_root)

    def test_ast_introspection_functions_and_classes(self):
        """Verifies AST introspection extracts signatures, parameters, types, and methods."""
        signatures = self.synthesizer.introspect_code(SAMPLE_MODULE_CODE)
        self.assertGreaterEqual(len(signatures), 3)

        func_names = [s.name for s in signatures]
        self.assertIn("calculate_discount", func_names)
        self.assertIn("is_eligible", func_names)
        self.assertIn("deposit", func_names)

        disc_sig = next(s for s in signatures if s.name == "calculate_discount")
        self.assertEqual(len(disc_sig.parameters), 2)
        self.assertEqual(disc_sig.parameters[0].name, "price")
        self.assertEqual(disc_sig.return_type, "float")

        dep_sig = next(s for s in signatures if s.name == "deposit")
        self.assertTrue(dep_sig.is_method)
        self.assertEqual(dep_sig.class_name, "AccountService")

    def test_synthesize_tests_nominal_and_boundaries(self):
        """Verifies synthesizing unittest test suite generates happy_path and boundary cases."""
        suite = self.synthesizer.synthesize_tests(
            source_code=SAMPLE_MODULE_CODE,
            module_name="billing_service",
            include_edge_cases=True,
        )
        self.assertEqual(suite.target_module, "billing_service")
        self.assertGreaterEqual(suite.total_tests, 6)

        test_names = [s.name for s in suite.test_specs]
        self.assertTrue(any("nominal" in n for n in test_names))
        self.assertTrue(any("boundary" in n for n in test_names))
        self.assertTrue(any("invalid" in n for n in test_names))

        self.assertIn("import unittest", suite.python_code)
        self.assertIn("class TestBillingServiceSuite(unittest.TestCase):", suite.python_code)

    def test_synthesized_test_suite_syntax_validity(self):
        """Verifies generated Python test suite parses cleanly into valid AST without syntax errors."""
        import ast
        suite = self.synthesizer.synthesize_tests(
            source_code=SAMPLE_MODULE_CODE,
            module_name="billing_service",
        )
        parsed = ast.parse(suite.python_code)
        self.assertIsInstance(parsed, ast.Module)

    def test_mutation_operator_generation(self):
        """Verifies AST mutation engine generates diverse mutants (AOR, ROR, COR, SVR)."""
        mutant_pairs = self.mutator.generate_mutants(SAMPLE_MODULE_CODE, max_mutants=10)
        self.assertGreaterEqual(len(mutant_pairs), 4)

        operators = {m.operator for m, _ in mutant_pairs}
        self.assertTrue(any(op in operators for op in [MutationOperator.ROR, MutationOperator.AOR, MutationOperator.COR, MutationOperator.SVR]))

        for mutant, code in mutant_pairs:
            self.assertIsNotNone(mutant.mutant_id)
            self.assertGreater(mutant.line_number, 0)
            self.assertNotEqual(code, SAMPLE_MODULE_CODE)

    def test_mutation_evaluation_detects_killed_mutants(self):
        """Verifies thorough test suite kills mutants and yields high mutation score."""
        report = self.mutator.evaluate_mutants(
            source_code=SAMPLE_MODULE_CODE,
            test_code=SAMPLE_TEST_CODE,
            max_mutants=10,
        )
        self.assertGreater(report.total_mutants, 0)
        self.assertGreater(report.killed_count, 0)
        self.assertGreaterEqual(report.mutation_score, 60.0)

        killed_mutants = [m for m in report.mutants if m.status == "KILLED"]
        self.assertTrue(len(killed_mutants) > 0)
        self.assertIsNotNone(killed_mutants[0].kill_reason)

    def test_mutation_evaluation_detects_surviving_mutants(self):
        """Verifies weak test suite allows injected mutants to survive, resulting in lower score."""
        report = self.mutator.evaluate_mutants(
            source_code=SAMPLE_MODULE_CODE,
            test_code=WEAK_TEST_CODE,
            max_mutants=10,
        )
        self.assertGreater(report.total_mutants, 0)
        self.assertGreater(report.survived_count, 0)
        self.assertTrue(any("survived" in rec.lower() for rec in report.recommendations))

    def test_ast_coverage_estimation(self):
        """Verifies AST coverage estimator analyzes statements, branches, and function metrics."""
        summary = self.coverage_est.estimate_coverage(
            source_code=SAMPLE_MODULE_CODE,
            test_code=SAMPLE_TEST_CODE,
            file_path="sample_module.py",
        )
        self.assertEqual(summary.target_file, "sample_module.py")
        self.assertGreater(summary.total_statements, 5)
        self.assertGreater(summary.total_branches, 0)
        self.assertGreaterEqual(summary.statement_coverage_pct, 50.0)
        self.assertGreaterEqual(summary.branch_coverage_pct, 50.0)
        self.assertEqual(len(summary.functions), 3)

    def test_test_synthesis_tools_in_registry(self):
        """Verifies synthesize_unit_tests, run_mutation_tests, and analyze_test_coverage tools in ToolRegistry."""
        registry = get_default_tool_registry()

        syn_tool = registry.get("synthesize_unit_tests")
        self.assertIsNotNone(syn_tool)

        mut_tool = registry.get("run_mutation_tests")
        self.assertIsNotNone(mut_tool)

        cov_tool = registry.get("analyze_test_coverage")
        self.assertIsNotNone(cov_tool)

        res = syn_tool.execute(source_code=SAMPLE_MODULE_CODE, module_name="sample", workspace_root=self.workspace_root)
        self.assertTrue(res.success)
        self.assertIn("test_specs", res.data)


if __name__ == "__main__":
    unittest.main()

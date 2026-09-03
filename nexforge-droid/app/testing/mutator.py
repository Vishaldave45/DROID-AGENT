"""Phase 19: Mutation Testing Engine.

Generates syntactic code mutants (AOR, ROR, COR, LCR, SVR, CR) to test the robustness of test suites
and calculate mutation score (Killed vs Survived mutants).
"""

import ast
import copy
import os
import sys
import time
import tempfile
import unittest
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple, Any


class MutationOperator(str, Enum):
    AOR = "AOR"  # Arithmetic Operator Replacement: + <-> -, * <-> /
    ROR = "ROR"  # Relational Operator Replacement: > <-> <=, == <-> !=
    COR = "COR"  # Conditional Operator Replacement: and <-> or
    LCR = "LCR"  # Logical Constant / Inversion: True <-> False
    SVR = "SVR"  # Statement Void / Return Value: return x -> return None
    CR = "CR"    # Constant Replacement: 0 -> 1, non-empty str -> ""


@dataclass
class Mutant:
    mutant_id: str
    operator: MutationOperator
    file_path: str
    line_number: int
    original_code: str
    mutated_code: str
    description: str
    status: str = "PENDING"  # "KILLED", "SURVIVED", "ERROR", "PENDING"
    kill_reason: Optional[str] = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "mutant_id": self.mutant_id,
            "operator": self.operator.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "original_code": self.original_code,
            "mutated_code": self.mutated_code,
            "description": self.description,
            "status": self.status,
            "kill_reason": self.kill_reason,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class MutationReport:
    total_mutants: int
    killed_count: int
    survived_count: int
    error_count: int
    mutation_score: float  # (killed / (killed + survived)) * 100%
    mutants: List[Mutant]
    execution_duration_sec: float
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_mutants": self.total_mutants,
            "killed_count": self.killed_count,
            "survived_count": self.survived_count,
            "error_count": self.error_count,
            "mutation_score": round(self.mutation_score, 1),
            "execution_duration_sec": round(self.execution_duration_sec, 2),
            "mutants": [m.to_dict() for m in self.mutants],
            "recommendations": self.recommendations,
        }


class MutationEngine:
    """Generates and executes AST mutants against target test suites."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())

    def generate_mutants(self, source_code: str, file_path: str = "target.py", max_mutants: int = 30) -> List[Tuple[Mutant, str]]:
        """Generates mutant AST variants and corresponding Python code."""
        tree = ast.parse(source_code)
        mutants_with_code: List[Tuple[Mutant, str]] = []

        # Find potential mutation sites
        sites: List[Dict[str, Any]] = []

        for node in ast.walk(tree):
            lineno = getattr(node, "lineno", None)
            if lineno is None:
                continue

            # 1. ROR: Relational Operators (Compare)
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                op = node.ops[0]
                if isinstance(op, ast.Gt):
                    sites.append({"node": node, "type": MutationOperator.ROR, "new_op": ast.LtE(), "desc": "Replaced '>' with '<='"})
                elif isinstance(op, ast.Lt):
                    sites.append({"node": node, "type": MutationOperator.ROR, "new_op": ast.GtE(), "desc": "Replaced '<' with '>='"})
                elif isinstance(op, ast.Eq):
                    sites.append({"node": node, "type": MutationOperator.ROR, "new_op": ast.NotEq(), "desc": "Replaced '==' with '!='"})
                elif isinstance(op, ast.NotEq):
                    sites.append({"node": node, "type": MutationOperator.ROR, "new_op": ast.Eq(), "desc": "Replaced '!=' with '=='"})

            # 2. AOR: Arithmetic Operators (BinOp)
            elif isinstance(node, ast.BinOp):
                if isinstance(node.op, ast.Add):
                    sites.append({"node": node, "type": MutationOperator.AOR, "new_op": ast.Sub(), "desc": "Replaced '+' with '-'"})
                elif isinstance(node.op, ast.Sub):
                    sites.append({"node": node, "type": MutationOperator.AOR, "new_op": ast.Add(), "desc": "Replaced '-' with '+'"})
                elif isinstance(node.op, ast.Mult):
                    sites.append({"node": node, "type": MutationOperator.AOR, "new_op": ast.Div(), "desc": "Replaced '*' with '/'"})

            # 3. COR: Boolean Operators (BoolOp: and / or)
            elif isinstance(node, ast.BoolOp):
                if isinstance(node.op, ast.And):
                    sites.append({"node": node, "type": MutationOperator.COR, "new_op": ast.Or(), "desc": "Replaced 'and' with 'or'"})
                elif isinstance(node.op, ast.Or):
                    sites.append({"node": node, "type": MutationOperator.COR, "new_op": ast.And(), "desc": "Replaced 'or' with 'and'"})

            # 4. LCR: Constant Booleans
            elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
                sites.append({"node": node, "type": MutationOperator.LCR, "new_val": not node.value, "desc": f"Inverted boolean {node.value} -> {not node.value}"})

            # 5. SVR: Return value voiding
            elif isinstance(node, ast.Return) and node.value is not None:
                sites.append({"node": node, "type": MutationOperator.SVR, "new_val": ast.Constant(value=None), "desc": "Voided return value to None"})

        # Generate each mutant by transforming a fresh AST copy
        idx = 1
        for site in sites[:max_mutants]:
            mutant_tree = copy.deepcopy(tree)
            target_node = site["node"]
            target_line = target_node.lineno

            # Mutator visitor that replaces the single target node
            class SingleNodeMutator(ast.NodeTransformer):
                def __init__(self, target_line, site_info):
                    self.target_line = target_line
                    self.site_info = site_info
                    self.applied = False

                def visit_Compare(self, n):
                    if not self.applied and n.lineno == self.target_line and self.site_info["type"] == MutationOperator.ROR:
                        n.ops = [self.site_info["new_op"]]
                        self.applied = True
                    return self.generic_visit(n)

                def visit_BinOp(self, n):
                    if not self.applied and n.lineno == self.target_line and self.site_info["type"] == MutationOperator.AOR:
                        n.op = self.site_info["new_op"]
                        self.applied = True
                    return self.generic_visit(n)

                def visit_BoolOp(self, n):
                    if not self.applied and n.lineno == self.target_line and self.site_info["type"] == MutationOperator.COR:
                        n.op = self.site_info["new_op"]
                        self.applied = True
                    return self.generic_visit(n)

                def visit_Constant(self, n):
                    if not self.applied and n.lineno == self.target_line and self.site_info["type"] == MutationOperator.LCR:
                        n.value = self.site_info["new_val"]
                        self.applied = True
                    return self.generic_visit(n)

                def visit_Return(self, n):
                    if not self.applied and n.lineno == self.target_line and self.site_info["type"] == MutationOperator.SVR:
                        n.value = self.site_info["new_val"]
                        self.applied = True
                    return self.generic_visit(n)

            mutator = SingleNodeMutator(target_line, site)
            transformed = mutator.visit(mutant_tree)
            ast.fix_missing_locations(transformed)

            try:
                mutated_code = ast.unparse(transformed)
                orig_snippet = ast.unparse(target_node)
                mut_snippet = site["desc"]
                mutant_obj = Mutant(
                    mutant_id=f"MUT-{idx:03d}",
                    operator=site["type"],
                    file_path=file_path,
                    line_number=target_line,
                    original_code=orig_snippet,
                    mutated_code=mut_snippet,
                    description=site["desc"],
                )
                mutants_with_code.append((mutant_obj, mutated_code))
                idx += 1
            except Exception:
                continue

        return mutants_with_code

    def evaluate_mutants(
        self,
        source_code: str,
        test_code: str,
        file_path: str = "solution.py",
        max_mutants: int = 20,
    ) -> MutationReport:
        """Executes test suite against all mutants to determine mutation score."""
        start_time = time.time()
        mutant_pairs = self.generate_mutants(source_code, file_path=file_path, max_mutants=max_mutants)

        mutants: List[Mutant] = []
        killed_count = 0
        survived_count = 0
        error_count = 0

        for mutant, mutated_code in mutant_pairs:
            m_start = time.time()
            outcome, reason = self._run_test_against_mutant(mutated_code, test_code)
            mutant.execution_time_ms = (time.time() - m_start) * 1000.0
            mutant.status = outcome
            mutant.kill_reason = reason

            if outcome == "KILLED":
                killed_count += 1
            elif outcome == "SURVIVED":
                survived_count += 1
            else:
                error_count += 1

            mutants.append(mutant)

        total_eval = killed_count + survived_count
        score = (killed_count / total_eval * 100.0) if total_eval > 0 else 100.0

        recommendations: List[str] = []
        if survived_count > 0:
            survived_lines = [str(m.line_number) for m in mutants if m.status == "SURVIVED"]
            recommendations.append(
                f"{survived_count} mutants survived! Add assertions covering boundary conditions at line(s): {', '.join(set(survived_lines))}."
            )
        if score >= 80.0:
            recommendations.append("Mutation score exceeds 80% threshold — test suite provides robust assertion density.")
        else:
            recommendations.append("Mutation score is below 80% — increase assertion strictness to prevent silent regression.")

        return MutationReport(
            total_mutants=len(mutants),
            killed_count=killed_count,
            survived_count=survived_count,
            error_count=error_count,
            mutation_score=score,
            mutants=mutants,
            execution_duration_sec=time.time() - start_time,
            recommendations=recommendations,
        )

    def _run_test_against_mutant(self, mutated_code: str, test_code: str) -> Tuple[str, Optional[str]]:
        """Runs test_code with mutated_code in an isolated namespace."""
        try:
            # 1. Compile mutated code
            mut_globals: Dict[str, Any] = {}
            exec(mutated_code, mut_globals)

            # 2. Inject exported objects into test globals
            test_globals: Dict[str, Any] = {
                "unittest": unittest,
                "MagicMock": unittest.mock.MagicMock,
                "patch": unittest.mock.patch,
                **mut_globals,
            }

            # 3. Compile and execute test code
            exec(test_code, test_globals)

            # 4. Find TestCase classes
            suite = unittest.TestSuite()
            loader = unittest.TestLoader()
            for obj in test_globals.values():
                if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
                    suite.addTests(loader.loadTestsFromTestCase(obj))

            if suite.countTestCases() == 0:
                return "SURVIVED", "No TestCase found"

            # 5. Run tests with silent runner
            import io
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)

            if len(result.failures) > 0 or len(result.errors) > 0:
                # Mutant was killed by assertion failure!
                err_msg = ""
                if result.failures:
                    err_msg = result.failures[0][1].strip().split("\n")[-1]
                elif result.errors:
                    err_msg = result.errors[0][1].strip().split("\n")[-1]
                return "KILLED", err_msg[:120]
            else:
                # Mutant survived undetected!
                return "SURVIVED", "All tests passed despite injected defect"

        except Exception as e:
            # Syntax or runtime error in compilation
            return "KILLED", f"Crash/Exception: {str(e)[:100]}"

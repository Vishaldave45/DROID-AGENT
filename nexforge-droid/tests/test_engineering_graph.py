"""Unit tests for Phase 6 Python AST Parsing & Multi-Relational Engineering Graph."""

import os
import shutil
import tempfile
import unittest

from app.context.ast_parser import PythonASTParser
from app.context.base import EdgeType, NodeType
from app.context.engineering_graph import EngineeringGraph
from app.context.engine import RepositoryContextEngine


SAMPLE_PYTHON_CODE = '''"""Sample module for AST testing."""

import os
from typing import List, Optional

class BaseEngine:
    """Base abstract engine class."""
    def start(self) -> bool:
        return True

class AutonomousProcessor(BaseEngine):
    """Processes items autonomously with retry logic."""

    def __init__(self, name: str, timeout: int = 30) -> None:
        self.name = name
        self.timeout = timeout

    async def execute_task(self, items: List[str], retry: bool = True) -> int:
        """Executes task and returns processed count."""
        count = 0
        for item in items:
            if item:
                self._log(item)
                count += 1
        return count

    def _log(self, msg: str) -> None:
        print(f"Log: {msg}")

def top_level_helper(x: int, y: int = 10) -> int:
    """Calculates helper sum."""
    return x + y
'''

SAMPLE_TEST_CODE = '''"""Sample test suite for AutonomousProcessor."""

import unittest
from sample import AutonomousProcessor, top_level_helper

class TestAutonomousProcessor(unittest.TestCase):
    def test_execute_task(self):
        proc = AutonomousProcessor("test")
        self.assertEqual(proc.name, "test")

    def test_top_level_helper(self):
        res = top_level_helper(5)
        self.assertEqual(res, 15)
'''


class TestEngineeringGraphAndAST(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_graph_test_")
        self.sample_file = os.path.join(self.temp_dir, "sample.py")
        self.test_file = os.path.join(self.temp_dir, "test_sample.py")

        with open(self.sample_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_PYTHON_CODE)

        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write(SAMPLE_TEST_CODE)

    def tearDown(self) -> None:
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ast_parser_extracts_classes_and_methods(self) -> None:
        parser = PythonASTParser(repo_root=self.temp_dir)
        nodes, edges = parser.parse_file(self.sample_file)

        node_names = [n.name for n in nodes]
        self.assertIn("BaseEngine", node_names)
        self.assertIn("AutonomousProcessor", node_names)
        self.assertIn("execute_task", node_names)
        self.assertIn("_log", node_names)
        self.assertIn("top_level_helper", node_names)

        # Check AutonomousProcessor class details
        proc_node = next(n for n in nodes if n.name == "AutonomousProcessor")
        self.assertEqual(proc_node.node_type, NodeType.CLASS)
        self.assertIn("BaseEngine", proc_node.dependencies)
        self.assertEqual(proc_node.docstring, "Processes items autonomously with retry logic.")

        # Check async method
        exec_node = next(n for n in nodes if n.name == "execute_task")
        self.assertEqual(exec_node.node_type, NodeType.METHOD)
        self.assertTrue(exec_node.async_function)
        self.assertIn("items: List[str]", exec_node.signature)
        self.assertIn("-> int", exec_node.signature)

    def test_ast_parser_extracts_imports_and_calls(self) -> None:
        parser = PythonASTParser(repo_root=self.temp_dir)
        nodes, edges = parser.parse_file(self.sample_file)

        import_nodes = [n for n in nodes if n.node_type == NodeType.IMPORT]
        import_names = [n.name for n in import_nodes]
        self.assertIn("os", import_names)
        self.assertIn("typing.List", import_names)

        call_edges = [e for e in edges if e.edge_type == EdgeType.CALLS]
        self.assertGreater(len(call_edges), 0)

    def test_engineering_graph_build_and_cross_file_resolution(self) -> None:
        graph = EngineeringGraph()
        graph.build_from_repository(self.temp_dir)

        stats = graph.get_stats()
        self.assertGreaterEqual(stats["total_nodes"], 10)
        self.assertGreaterEqual(stats["total_edges"], 10)

        # Find symbol
        symbols = graph.find_symbols_by_name("AutonomousProcessor")
        self.assertEqual(len(symbols), 1)

        # Search symbols
        results = graph.search_symbols("execute_task")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].name, "execute_task")

    def test_call_hierarchy_and_dependencies(self) -> None:
        graph = EngineeringGraph()
        graph.build_from_repository(self.temp_dir)

        # Look up callers of _log
        exec_nodes = graph.find_symbols_by_name("execute_task")
        self.assertTrue(len(exec_nodes) > 0)
        callees = graph.get_callees(exec_nodes[0].node_id)
        callee_names = [c["target_name"] for c in callees]
        self.assertIn("_log", callee_names)

    def test_context_engine_assembly(self) -> None:
        engine = RepositoryContextEngine(self.temp_dir)
        pkg = engine.build_context("Fix AutonomousProcessor execute_task logic", self.temp_dir)

        self.assertGreater(len(pkg.symbols), 0)
        symbol_names = [s.name for s in pkg.symbols]
        self.assertTrue(any("AutonomousProcessor" in name or "execute_task" in name for name in symbol_names))
        self.assertIn("sample.py", pkg.relevant_files)
        self.assertGreater(pkg.estimated_tokens, 0)


if __name__ == "__main__":
    unittest.main()

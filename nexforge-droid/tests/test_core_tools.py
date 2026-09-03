"""Comprehensive unit tests for Core Tools, Security Policy Gating, and Tool Registry."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.security.base import DefaultPolicyEngine, PolicyDecision, SecurityContext
from app.tools import (
    DeleteFileTool,
    EditFileTool,
    FindFilesTool,
    GitDiffTool,
    GitLogTool,
    GitStatusTool,
    ListDirTool,
    ReadFileTool,
    RunCommandTool,
    SearchCodeTool,
    ToolRegistry,
    ToolResult,
    WriteFileTool,
    get_default_tool_registry,
)


class TestFilesystemTools(unittest.TestCase):
    """Unit tests for Filesystem tools (Read, Write, Edit, List, Delete)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_fs_test_")
        self.workspace = Path(self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_and_read_file(self) -> None:
        """Verify writing a new file and reading full content."""
        writer = WriteFileTool()
        reader = ReadFileTool()

        test_file = self.workspace / "test.txt"
        write_res = writer.execute(path=str(test_file), content="Line 1\nLine 2\nLine 3\n")

        self.assertTrue(write_res.success)
        self.assertEqual(write_res.data["lines_written"], 3)

        read_res = reader.execute(path=str(test_file))
        self.assertTrue(read_res.success)
        self.assertEqual(read_res.data["content"], "Line 1\nLine 2\nLine 3\n")
        self.assertEqual(read_res.data["total_lines"], 3)

    def test_read_file_line_slices(self) -> None:
        """Verify reading specific line slices."""
        writer = WriteFileTool()
        reader = ReadFileTool()

        test_file = self.workspace / "numbers.txt"
        lines = [f"Item {i}\n" for i in range(1, 21)]
        writer.execute(path=str(test_file), content="".join(lines))

        # Read slice lines 5 to 8
        slice_res = reader.execute(path=str(test_file), start_line=5, end_line=8)
        self.assertTrue(slice_res.success)
        self.assertEqual(slice_res.data["content"], "Item 5\nItem 6\nItem 7\nItem 8\n")
        self.assertEqual(slice_res.data["start_line"], 5)
        self.assertEqual(slice_res.data["end_line"], 8)

    def test_read_nonexistent_file(self) -> None:
        """Verify reading a missing file returns descriptive error."""
        reader = ReadFileTool()
        res = reader.execute(path=str(self.workspace / "nonexistent.txt"))
        self.assertFalse(res.success)
        self.assertIn("File not found", res.error)

    def test_write_nested_directory_creation(self) -> None:
        """Verify write tool automatically creates missing parent directories."""
        writer = WriteFileTool()
        nested_file = self.workspace / "sub" / "deep" / "module.py"
        res = writer.execute(path=str(nested_file), content="def deep(): pass\n")
        self.assertTrue(res.success)
        self.assertTrue(nested_file.exists())

    def test_write_file_overwrite_protection(self) -> None:
        """Verify overwrite=False protects against accidental overwrites."""
        writer = WriteFileTool()
        test_file = self.workspace / "protected.txt"
        writer.execute(path=str(test_file), content="Initial")

        res = writer.execute(path=str(test_file), content="New", overwrite=False)
        self.assertFalse(res.success)
        self.assertIn("already exists", res.error)

    def test_edit_file_surgical_replacement(self) -> None:
        """Verify surgical unique string replacement."""
        writer = WriteFileTool()
        editor = EditFileTool()

        test_file = self.workspace / "script.py"
        initial_code = "def calculate(a, b):\n    return a - b\n"
        writer.execute(path=str(test_file), content=initial_code)

        target = "    return a - b"
        replacement = "    # Add numbers\n    return a + b"
        res = editor.execute(path=str(test_file), target_content=target, replacement_content=replacement)

        self.assertTrue(res.success)
        with open(test_file, "r") as f:
            updated = f.read()
        self.assertIn("return a + b", updated)
        self.assertNotIn("return a - b", updated)

    def test_edit_file_target_not_found(self) -> None:
        """Verify error when target content does not match."""
        writer = WriteFileTool()
        editor = EditFileTool()

        test_file = self.workspace / "code.py"
        writer.execute(path=str(test_file), content="x = 10\n")

        res = editor.execute(path=str(test_file), target_content="y = 20", replacement_content="y = 30")
        self.assertFalse(res.success)
        self.assertIn("not found in file", res.error)

    def test_edit_file_ambiguous_multiple_matches(self) -> None:
        """Verify error when target content matches more than once."""
        writer = WriteFileTool()
        editor = EditFileTool()

        test_file = self.workspace / "repeat.py"
        writer.execute(path=str(test_file), content="val = 1\nval = 1\n")

        res = editor.execute(path=str(test_file), target_content="val = 1", replacement_content="val = 2")
        self.assertFalse(res.success)
        self.assertIn("matches 2 occurrences", res.error)

    def test_list_dir_shallow_and_recursive(self) -> None:
        """Verify directory listing with metadata and recursion."""
        writer = WriteFileTool()
        lister = ListDirTool()

        writer.execute(path=str(self.workspace / "root_file.txt"), content="Root")
        writer.execute(path=str(self.workspace / "pkg" / "sub_file.txt"), content="Sub")

        # Shallow listing
        shallow = lister.execute(path=str(self.workspace), recursive=False)
        self.assertTrue(shallow.success)
        names = [e["name"] for e in shallow.data["entries"]]
        self.assertIn("root_file.txt", names)
        self.assertIn("pkg", names)

        # Recursive listing
        rec = lister.execute(path=str(self.workspace), recursive=True)
        self.assertTrue(rec.success)
        self.assertGreaterEqual(rec.data["total_entries"], 2)

    def test_delete_file(self) -> None:
        """Verify safe file deletion."""
        writer = WriteFileTool()
        deleter = DeleteFileTool()

        test_file = self.workspace / "to_delete.txt"
        writer.execute(path=str(test_file), content="temporary")
        self.assertTrue(test_file.exists())

        res = deleter.execute(path=str(test_file))
        self.assertTrue(res.success)
        self.assertFalse(test_file.exists())


class TestSearchTools(unittest.TestCase):
    """Unit tests for Search & Discovery tools (search_code, find_files)."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_search_test_")
        self.workspace = Path(self.temp_dir)
        # Seed test workspace
        writer = WriteFileTool()
        writer.execute(
            path=str(self.workspace / "src" / "auth.py"),
            content="class AuthService:\n    def verify_token(self, token: str):\n        return True\n",
        )
        writer.execute(
            path=str(self.workspace / "src" / "db.py"),
            content="def connect_database():\n    # auth with db credentials\n    pass\n",
        )
        writer.execute(
            path=str(self.workspace / "tests" / "test_auth.py"),
            content="def run_unit_checks():\n    assert AuthService().verify_token('abc')\n",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_search_code_substring(self) -> None:
        """Verify code search matches across multiple repository files."""
        searcher = SearchCodeTool()
        res = searcher.execute(query="verify_token", path=str(self.workspace))

        self.assertTrue(res.success)
        self.assertEqual(res.data["total_matches"], 2)
        matched_files = [m["file"] for m in res.data["matches"]]
        self.assertTrue(any("auth.py" in f for f in matched_files))
        self.assertTrue(any("test_auth.py" in f for f in matched_files))

    def test_search_code_with_file_pattern_filter(self) -> None:
        """Verify filtering search results by glob pattern."""
        searcher = SearchCodeTool()
        res = searcher.execute(query="verify_token", path=str(self.workspace), file_pattern="test_*.py")

        self.assertTrue(res.success)
        self.assertEqual(res.data["total_matches"], 1)
        self.assertIn("test_auth.py", res.data["matches"][0]["file"])

    def test_find_files_by_pattern(self) -> None:
        """Verify finding files by glob pattern."""
        finder = FindFilesTool()
        res = finder.execute(pattern="*.py", path=str(self.workspace))

        self.assertTrue(res.success)
        self.assertEqual(res.data["total_found"], 3)
        names = [f["name"] for f in res.data["files"]]
        self.assertIn("auth.py", names)
        self.assertIn("db.py", names)
        self.assertIn("test_auth.py", names)


class TestTerminalAndExecutionTools(unittest.TestCase):
    """Unit tests for Terminal execution tool."""

    def test_run_command_success(self) -> None:
        """Verify running a valid shell command and capturing output."""
        runner = RunCommandTool()
        res = runner.execute(command="python3 -c \"print('NexForge Droid Execution Test')\"")

        self.assertTrue(res.success)
        self.assertEqual(res.data["exit_code"], 0)
        self.assertIn("NexForge Droid Execution Test", res.data["stdout"])
        self.assertGreater(res.execution_time_ms, 0.0)

    def test_run_command_failure_exit_code(self) -> None:
        """Verify non-zero exit code reporting."""
        runner = RunCommandTool()
        res = runner.execute(command="python3 -c \"import sys; sys.exit(42)\"")

        self.assertFalse(res.success)
        self.assertEqual(res.data["exit_code"], 42)
        self.assertIn("non-zero status code: 42", res.error)


class TestToolRegistryAndSecurityPolicy(unittest.TestCase):
    """Unit tests for ToolRegistry dispatch, schema generation, and policy enforcement."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_reg_test_")
        self.workspace = Path(self.temp_dir)
        self.registry = get_default_tool_registry(workspace_root=str(self.workspace))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_registry_has_all_core_tools(self) -> None:
        """Verify default tool registry registers all 11 core tools."""
        tools = self.registry.list_tools()
        tool_names = [t.name for t in tools]

        expected = [
            "read_file",
            "write_file",
            "edit_file",
            "list_dir",
            "delete_file",
            "search_code",
            "find_files",
            "run_command",
            "git_status",
            "git_diff",
            "git_log",
        ]
        for exp in expected:
            self.assertIn(exp, tool_names)

        schemas = self.registry.get_schemas()
        self.assertGreaterEqual(len(schemas), 11)

    def test_dispatch_allowed_tool(self) -> None:
        """Verify registry dispatch executes allowed tools and logs execution time."""
        res = self.registry.dispatch(
            "write_file",
            {"path": str(self.workspace / "app.py"), "content": "print('hello')"},
        )
        self.assertTrue(res.success)
        self.assertTrue((self.workspace / "app.py").exists())
        self.assertGreater(res.execution_time_ms, 0.0)

    def test_dispatch_missing_parameter_fails_validation(self) -> None:
        """Verify dispatch rejects requests with missing required schema parameters."""
        res = self.registry.dispatch("read_file", {})
        self.assertFalse(res.success)
        self.assertIn("Missing required parameter 'path'", res.error)

    def test_dispatch_path_traversal_denied_by_policy(self) -> None:
        """Verify security policy intercepts and denies path traversal out of workspace."""
        res = self.registry.dispatch(
            "read_file",
            {"path": "/etc/passwd"},
        )
        self.assertFalse(res.success)
        self.assertIn("Security Policy Violation", res.error)
        self.assertEqual(res.metadata.get("policy_decision"), "DENY")

    def test_dispatch_dangerous_command_denied(self) -> None:
        """Verify security policy blocks forbidden command execution."""
        res = self.registry.dispatch(
            "run_command",
            {"command": "rm -rf / --no-preserve-root"},
        )
        self.assertFalse(res.success)
        self.assertIn("Security Policy Violation", res.error)
        self.assertEqual(res.metadata.get("policy_decision"), "DENY")


if __name__ == "__main__":
    unittest.main()

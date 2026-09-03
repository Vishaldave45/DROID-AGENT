"""Unit tests for Phase 9: Safe Code Modification & Patching Engine."""

import os
import shutil
import tempfile
import unittest

from app.patcher.base import FileSnapshot, PatchResult, SurgicalEditChunk, UnifiedDiff
from app.patcher.diff_engine import DiffEngine
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor, StaleFileConflictError
from app.patcher.syntax_validator import SyntaxValidationResult, SyntaxValidator
from app.patcher.tools import (
    ApplyPatchTool,
    FileSnapshotTool,
    MultiEditTool,
    SurgicalEditTool,
)
from app.tools import get_default_tool_registry


class TestSafePatcher(unittest.TestCase):
    """Test suite covering diff engine, syntax validation, snapshots, and safe modifier."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="nexforge_patch_test_")
        self.auditor = FileSnapshotAuditor(workspace_root=self.test_dir)
        self.validator = SyntaxValidator()
        self.modifier = SafeCodeModifier(
            workspace_root=self.test_dir,
            snapshot_auditor=self.auditor,
            syntax_validator=self.validator,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_syntax_validator_python_valid_and_invalid(self):
        """Verify Python AST syntax validation for valid and syntactically broken code."""
        valid_py = "def compute(x: int) -> int:\n    return x * 42\n"
        res = self.validator.validate(valid_py, "test.py")
        self.assertTrue(res.is_valid)
        self.assertIsNone(res.error_message)

        invalid_py = "def broken(\n    return 42\n"
        res_inv = self.validator.validate(invalid_py, "test.py")
        self.assertFalse(res_inv.is_valid)
        self.assertIsNotNone(res_inv.error_line)
        self.assertIn("SyntaxError", res_inv.error_message)

    def test_syntax_validator_json_and_js_ts(self):
        """Verify JSON and JS/TS structural bracket/brace validation."""
        valid_json = '{"name": "nexforge", "count": 100}'
        res_json = self.validator.validate(valid_json, "config.json")
        self.assertTrue(res_json.is_valid)

        invalid_json = '{"name": "nexforge", "count": 100,'
        res_json_inv = self.validator.validate(invalid_json, "config.json")
        self.assertFalse(res_json_inv.is_valid)
        self.assertIn("JSONDecodeError", res_json_inv.error_message)

        # JS/TS with balanced delimiters
        valid_ts = "function test() { const a = [1, 2, (3 + 4)]; return a; }"
        res_ts = self.validator.validate(valid_ts, "app.ts")
        self.assertTrue(res_ts.is_valid)

        # JS/TS with mismatched closing brace
        invalid_ts = "function test() { const a = [1, 2); return a; }"
        res_ts_inv = self.validator.validate(invalid_ts, "app.ts")
        self.assertFalse(res_ts_inv.is_valid)
        self.assertIn("Mismatched delimiter", res_ts_inv.error_message)

        # Unclosed brace
        unclosed_ts = "function test() { return 1;"
        res_unclosed = self.validator.validate(unclosed_ts, "app.ts")
        self.assertFalse(res_unclosed.is_valid)
        self.assertIn("Unclosed delimiter", res_unclosed.error_message)

    def test_diff_engine_create_and_parse_unified_diff(self):
        """Verify unified diff creation and parsing into structured models."""
        old_text = "line1\nline2\nline3\n"
        new_text = "line1\nline2_modified\nline3\nline4\n"
        diff_str = DiffEngine.create_unified_diff(old_text, new_text, from_file="a/sample.py", to_file="b/sample.py")
        self.assertIn("@@", diff_str)
        self.assertIn("-line2", diff_str)
        self.assertIn("+line2_modified", diff_str)

        parsed = DiffEngine.parse_unified_diff(diff_str)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].old_file, "sample.py")
        self.assertEqual(parsed[0].new_file, "sample.py")
        self.assertEqual(len(parsed[0].hunks), 1)
        self.assertEqual(parsed[0].deletions, 1)
        self.assertEqual(parsed[0].additions, 2)

    def test_diff_engine_apply_patch_with_offset_and_fuzzy(self):
        """Verify applying unified diff with line shifts and context matching."""
        original = "header\nline1\nline2\nline3\nfooter\n"
        diff_text = (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -2,3 +2,3 @@\n"
            " line1\n"
            "-line2\n"
            "+line2_updated\n"
            " line3\n"
        )
        diffs = DiffEngine.parse_unified_diff(diff_text)
        result = DiffEngine.apply_unified_diff(original, diffs[0])
        self.assertTrue(result.success)
        self.assertIn("line2_updated", result.modified_content)
        self.assertNotIn("line2\n", result.modified_content)

    def test_surgical_edit_exact_and_fuzzy(self):
        """Verify surgical chunk replacement, uniqueness enforcement, and fuzzy whitespace matching."""
        content = "def hello():\n    print('hello world')\n    return True\n"

        # 1. Exact match
        chunk = SurgicalEditChunk(
            target_content="print('hello world')",
            replacement_content="print('hello universe')",
        )
        ok, res, err = DiffEngine.apply_surgical_chunks(content, [chunk])
        self.assertTrue(ok)
        self.assertIn("hello universe", res)

        # 2. Non-unique rejection
        duplicate_content = "item = 1\nitem = 1\n"
        dup_chunk = SurgicalEditChunk(target_content="item = 1", replacement_content="item = 2")
        ok, res, err = DiffEngine.apply_surgical_chunks(duplicate_content, [dup_chunk])
        self.assertFalse(ok)
        self.assertIn("matches 2 occurrences", err)

        # 3. Fuzzy whitespace tolerance
        fuzzy_chunk = SurgicalEditChunk(
            target_content="def hello():   \n    print('hello world') ",
            replacement_content="def hello_fuzzy():\n    print('hello world')",
            allow_fuzzy=True,
        )
        ok, res, err = DiffEngine.apply_surgical_chunks(content, [fuzzy_chunk])
        self.assertTrue(ok)
        self.assertIn("hello_fuzzy", res)

    def test_file_snapshot_auditor_and_stale_detection(self):
        """Verify file snapshots, SHA-256 fingerprinting, and stale-file conflict blocking."""
        file_path = os.path.join(self.test_dir, "data.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("initial content")

        initial_hash = self.auditor.compute_file_sha256(file_path)
        self.assertIsNotNone(initial_hash)

        # Freshness check passes with matching hash
        is_fresh, cur_hash, err = self.auditor.verify_file_freshness(file_path, initial_hash)
        self.assertTrue(is_fresh)

        # Stale check fails when expected hash is stale
        is_fresh, cur_hash, err = self.auditor.verify_file_freshness(file_path, "stale_hash_12345678")
        self.assertFalse(is_fresh)
        self.assertIn("Stale file detected", err)

        # Take snapshot
        snap = self.auditor.take_snapshot(file_path, reason="test-snapshot")
        self.assertEqual(snap.version, 1)
        self.assertEqual(snap.content, "initial content")

        # Mutate file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("mutated content")

        # Revert to snapshot
        ok, restored_snap, err = self.auditor.revert_to_snapshot(file_path)
        self.assertTrue(ok)
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "initial content")

    def test_safe_modifier_atomic_write_and_syntax_rollback(self):
        """Verify SafeCodeModifier aborts writes when patch causes syntax errors."""
        file_path = os.path.join(self.test_dir, "script.py")
        original_py = "def add(a: int, b: int) -> int:\n    return a + b\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(original_py)

        # Attempt edit that creates broken Python syntax
        res = self.modifier.apply_surgical_edit(
            file_path=file_path,
            target_content="return a + b",
            replacement_content="return (a +",  # Unclosed paren / invalid syntax
            validate_syntax=True,
        )
        self.assertFalse(res.success)
        self.assertFalse(res.syntax_valid)
        self.assertIn("Syntax validation failed", res.error)

        # Verify disk file was NOT corrupted
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), original_py)

        # Valid edit succeeds
        valid_res = self.modifier.apply_surgical_edit(
            file_path=file_path,
            target_content="return a + b",
            replacement_content="return a + b + 0",
            validate_syntax=True,
        )
        self.assertTrue(valid_res.success)
        with open(file_path, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "def add(a: int, b: int) -> int:\n    return a + b + 0\n")

    def test_safe_modifier_multi_surgical_edit_and_patch(self):
        """Verify multi-chunk surgical editing and unified diff patching."""
        file_path = os.path.join(self.test_dir, "module.py")
        initial_code = (
            "class Calculator:\n"
            "    def add(self, a, b):\n"
            "        return a + b\n"
            "    def sub(self, a, b):\n"
            "        return a - b\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(initial_code)

        chunks = [
            SurgicalEditChunk(target_content="return a + b", replacement_content="return int(a) + int(b)"),
            SurgicalEditChunk(target_content="return a - b", replacement_content="return int(a) - int(b)"),
        ]
        res = self.modifier.apply_multi_surgical_edits(file_path, chunks)
        self.assertTrue(res.success)
        self.assertEqual(res.applied_hunks, 2)

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("int(a) + int(b)", content)
            self.assertIn("int(a) - int(b)", content)

    def test_patcher_llm_tools_dispatch(self):
        """Verify ApplyPatchTool, SurgicalEditTool, MultiEditTool, and FileSnapshotTool in registry."""
        registry = get_default_tool_registry(workspace_root=self.test_dir)
        self.assertIsNotNone(registry.get("apply_patch"))
        self.assertIsNotNone(registry.get("surgical_edit"))
        self.assertIsNotNone(registry.get("multi_surgical_edit"))
        self.assertIsNotNone(registry.get("manage_snapshots"))

        # Test tool execution
        test_file = os.path.join(self.test_dir, "tool_test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("VAL = 10\n")

        # 1. Take snapshot via tool
        snap_res = registry.dispatch("manage_snapshots", {"action": "snapshot", "path": test_file, "reason": "pre-test"})
        self.assertTrue(snap_res.success)

        # 2. Surgical edit via tool
        edit_res = registry.dispatch(
            "surgical_edit",
            {
                "path": test_file,
                "target_content": "VAL = 10",
                "replacement_content": "VAL = 20",
            },
        )
        self.assertTrue(edit_res.success)
        with open(test_file, "r", encoding="utf-8") as f:
            self.assertIn("VAL = 20", f.read())

        # 3. Hash check tool
        hash_res = registry.dispatch("manage_snapshots", {"action": "hash", "path": test_file})
        self.assertTrue(hash_res.success)
        self.assertIn("sha256_hash", hash_res.data)

        # 4. Revert tool
        rev_res = registry.dispatch("manage_snapshots", {"action": "revert", "path": test_file})
        self.assertTrue(rev_res.success)
        with open(test_file, "r", encoding="utf-8") as f:
            self.assertEqual(f.read(), "VAL = 10\n")


if __name__ == "__main__":
    unittest.main()

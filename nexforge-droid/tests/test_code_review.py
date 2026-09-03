"""Unit Tests for Phase 18: Code Review, Security Vulnerability Scanner & SARIF Export."""

import json
import os
import shutil
import tempfile
import unittest

from app.review.analyzer import CodeQualityAnalyzer, CodeReviewReport
from app.review.sarif import SARIFExporter
from app.review.security_scanner import ASTSecurityScanner, SecurityVulnerability
from app.tools import get_default_tool_registry
from app.tools.review_tools import (
    CodeReviewScanTool,
    SarifExportTool,
    SecurityAuditTool,
)


class TestCodeReviewAndSecurityScanner(unittest.TestCase):
    """Tests security taint scanning, code smell analysis, and SARIF export."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="nexforge_review_test_")
        self.scanner = ASTSecurityScanner(workspace_root=self.temp_dir)
        self.analyzer = CodeQualityAnalyzer(workspace_root=self.temp_dir)
        self.exporter = SARIFExporter(workspace_root=self.temp_dir)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_detect_hardcoded_secrets(self) -> None:
        """Verify regex and heuristic detection of hardcoded secrets and tokens."""
        sample_code = """
import os
API_KEY = "sk-1234567890abcdef1234567890abcdef"
GITHUB_TOKEN = "ghp_123456789012345678901234567890123456"
password = "supersecretpassword123"
def safe():
    return True
"""
        vulns = self.scanner.scan_code(sample_code, file_path="config_sample.py")
        rule_ids = [v.rule_id for v in vulns]
        self.assertIn("SEC-001-HARDCODED-SECRET", rule_ids)
        self.assertGreaterEqual(len(vulns), 2)

    def test_detect_command_and_code_injection(self) -> None:
        """Verify AST detection of unsafe eval/exec and subprocess shell=True."""
        sample_code = """
import subprocess
import os

def run_user_code(user_input):
    eval(user_input)
    subprocess.run("rm -rf " + user_input, shell=True)
    os.system("ls " + user_input)
"""
        vulns = self.scanner.scan_code(sample_code, file_path="vulnerable.py")
        rules = {v.rule_id for v in vulns}
        self.assertIn("SEC-002-DYNAMIC-CODE-EXEC", rules)
        self.assertIn("SEC-004-SHELL-COMMAND-INJECTION", rules)
        self.assertIn("SEC-005-SUBPROCESS-SHELL-TRUE", rules)

    def test_detect_insecure_deserialization_and_sql_injection(self) -> None:
        """Verify detection of pickle loads and SQL string interpolation."""
        sample_code = """
import pickle
import sqlite3

def load_payload(raw_bytes, user_id):
    obj = pickle.loads(raw_bytes)
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = '{user_id}'")
"""
        vulns = self.scanner.scan_code(sample_code, file_path="db.py")
        rules = {v.rule_id for v in vulns}
        self.assertIn("SEC-003-INSECURE-DESERIALIZATION", rules)
        self.assertIn("SEC-007-SQL-INJECTION-FORMAT", rules)

    def test_cyclomatic_complexity_and_code_smells(self) -> None:
        """Verify detection of high cyclomatic complexity and silent exception pass."""
        complex_code = """
def heavily_branched_function(a, b, c, d, e, f, g, h, i, j):
    if a:
        if b:
            pass
        elif c:
            pass
    for x in range(10):
        if d:
            while e:
                pass
    if h:
        pass
    if i:
        pass
    if j:
        pass
    try:
        if f and g:
            pass
    except Exception:
        pass
"""
        findings = self.analyzer.analyze_code(complex_code, file_path="complex.py")
        categories = {f.category for f in findings}
        self.assertIn("COMPLEXITY", categories)
        self.assertIn("BUG_RISK", categories)
        self.assertIn("SMELL", categories)  # argument count > 6

        # Verify silent exception finding
        bug_findings = [f for f in findings if f.category == "BUG_RISK"]
        self.assertTrue(any("Silent exception suppression" in b.message for b in bug_findings))

    def test_workspace_code_review_report_generation(self) -> None:
        """Verify repository-wide code review aggregation and quality scoring."""
        file_a = os.path.join(self.temp_dir, "module_clean.py")
        with open(file_a, "w") as f:
            f.write("def add(x: int, y: int) -> int:\n    return x + y\n")

        file_b = os.path.join(self.temp_dir, "module_smelly.py")
        with open(file_b, "w") as f:
            f.write("def bad():\n    try:\n        x = 1\n    except:\n        pass\n")

        report = self.analyzer.run_review(directory=self.temp_dir)
        self.assertIsInstance(report, CodeReviewReport)
        self.assertGreaterEqual(report.total_files_analyzed, 2)
        self.assertGreater(report.total_findings, 0)
        self.assertGreaterEqual(report.quality_score, 0.0)
        self.assertLessEqual(report.quality_score, 100.0)

    def test_sarif_v2_1_0_schema_generation(self) -> None:
        """Verify OASIS standard SARIF v2.1.0 document structure."""
        vuln = SecurityVulnerability(
            id="VULN-TEST01",
            rule_id="SEC-004-SHELL-COMMAND-INJECTION",
            name="Command Injection",
            severity="HIGH",
            category="CWE-78: Command Injection",
            file_path="app/exec.py",
            line_number=42,
            code_snippet="os.system(cmd)",
            description="Call to os.system executes unsanitized command.",
            recommendation="Use subprocess.run without shell=True.",
            cwe_id="CWE-78",
        )
        sarif = self.exporter.generate_sarif(vulnerabilities=[vuln])
        self.assertEqual(sarif["version"], "2.1.0")
        self.assertIn("sarif-schema-2.1.0.json", sarif["$schema"])
        runs = sarif["runs"]
        self.assertEqual(len(runs), 1)
        results = runs[0]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ruleId"], "SEC-004-SHELL-COMMAND-INJECTION")
        self.assertEqual(results[0]["level"], "error")

        # Test file export
        out_path = os.path.join(self.temp_dir, "security_report.sarif")
        self.exporter.export_to_file(out_path, vulnerabilities=[vuln])
        self.assertTrue(os.path.isfile(out_path))
        with open(out_path, "r") as f:
            data = json.load(f)
            self.assertEqual(data["version"], "2.1.0")

    def test_review_and_security_tools_in_registry(self) -> None:
        """Verify CodeReviewScanTool, SecurityAuditTool, and SarifExportTool in registry."""
        registry = get_default_tool_registry()
        tool_names = [t.name for t in registry.list_tools()]

        self.assertIn("code_review_scan", tool_names)
        self.assertIn("security_audit_scan", tool_names)
        self.assertIn("sarif_export", tool_names)

        # Test tool execution
        scan_tool = registry.get("security_audit_scan")
        self.assertIsNotNone(scan_tool)
        res = scan_tool.execute(code_snippet="eval('1 + 1')")
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.data["total_vulnerabilities"], 1)

        review_tool = registry.get("code_review_scan")
        self.assertIsNotNone(review_tool)
        res_rev = review_tool.execute(code_snippet="def add(a, b): return a + b")
        self.assertTrue(res_rev.success)

        sarif_tool = registry.get("sarif_export")
        self.assertIsNotNone(sarif_tool)
        res_sarif = sarif_tool.execute(directory=self.temp_dir)
        self.assertTrue(res_sarif.success)
        self.assertIn("sarif", res_sarif.data)

    def test_weak_crypto_and_sql_concat(self) -> None:
        """Verify AST detection of weak hashing algorithms and SQL concatenation."""
        sample_code = """
import hashlib
import sqlite3

def hash_password(pw):
    return hashlib.md5(pw.encode()).hexdigest()

def query_user(name):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = " + name)
"""
        vulns = self.scanner.scan_code(sample_code, file_path="crypto_db.py")
        rules = {v.rule_id for v in vulns}
        self.assertIn("SEC-006-WEAK-HASH-ALGORITHM", rules)
        self.assertIn("SEC-007-SQL-INJECTION-CONCAT", rules)


if __name__ == "__main__":
    unittest.main()

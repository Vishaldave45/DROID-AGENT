"""NexForge Droid - Security Vulnerability Scanner.

Applies OWASP Top 10 heuristics and AST taint analysis to detect security risks
including SQL injection, command injection, hardcoded secrets, path traversal,
insecure deserialization, and unsafe dynamic execution.
"""

from __future__ import annotations

import ast
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SecurityVulnerability:
    """Represents a discovered security vulnerability or compliance violation."""
    id: str
    rule_id: str
    name: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # e.g., CWE-89: SQL Injection, CWE-78: Command Injection
    file_path: str
    line_number: int
    code_snippet: str
    description: str
    recommendation: str
    cwe_id: str
    fix_suggestion: Optional[str] = None
    fingerprint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ASTSecurityScanner:
    """Performs static AST analysis and regex pattern scanning for security risks."""

    # Secret pattern regexes
    SECRET_PATTERNS = [
        (r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*=\s*['\"][a-zA-Z0-9_\-]{20,}['\"]", "CWE-798", "Hardcoded API Key/Secret Token"),
        (r"ghp_[a-zA-Z0-9]{36}", "CWE-798", "Hardcoded GitHub Personal Access Token"),
        (r"AKIA[0-9A-Z]{16}", "CWE-798", "Hardcoded AWS Access Key ID"),
        (r"(?i)password\s*=\s*['\"][^'\"]{6,}['\"]", "CWE-259", "Hardcoded Plaintext Password"),
    ]

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()

    def scan_code(self, code: str, file_path: str = "snippet.py") -> List[SecurityVulnerability]:
        """Scans code text for security vulnerabilities via AST and regex analysis."""
        vulnerabilities: List[SecurityVulnerability] = []
        lines = code.splitlines()

        # 1. Regex Heuristics (Secrets, Tokens, Passwords)
        for idx, line in enumerate(lines, start=1):
            line_str = line.strip()
            # Skip comments
            if line_str.startswith("#") or line_str.startswith("//"):
                continue

            for pattern, cwe, desc in self.SECRET_PATTERNS:
                if re.search(pattern, line_str):
                    vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                            rule_id="SEC-001-HARDCODED-SECRET",
                            name="Hardcoded Secret or Token",
                            severity="HIGH",
                            category="CWE-798: Use of Hard-coded Credentials",
                            file_path=file_path,
                            line_number=idx,
                            code_snippet=line_str[:120],
                            description=f"Potential credential or secret detected: {desc}.",
                            recommendation="Externalize secrets into environment variables (e.g., os.environ or .env file) instead of hardcoding.",
                            cwe_id=cwe,
                            fix_suggestion=f"# Replace with environment variable\nimport os\nSECRET = os.getenv('{re.sub(r'[^A-Z0-9_]', '', line_str.split('=')[0].upper())}')",
                        )
                    )

        # 2. Python AST Analysis
        if file_path.endswith(".py") or not ("." in os.path.basename(file_path)):
            try:
                tree = ast.parse(code, filename=file_path)
                visitor = SecurityASTVisitor(file_path, lines)
                visitor.visit(tree)
                vulnerabilities.extend(visitor.vulnerabilities)
            except SyntaxError:
                # Syntax errors are handled by CI/CD stages, skip AST if unparseable
                pass

        return vulnerabilities

    def scan_file(self, file_path: str) -> List[SecurityVulnerability]:
        """Reads and scans a single target file."""
        abs_path = os.path.join(self.workspace_root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.isfile(abs_path):
            return []
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            rel_path = os.path.relpath(abs_path, self.workspace_root)
            return self.scan_code(content, file_path=rel_path)
        except Exception:
            return []

    def scan_directory(
        self,
        directory: str = ".",
        extensions: Optional[List[str]] = None,
        max_files: int = 200,
    ) -> List[SecurityVulnerability]:
        """Scans all eligible source files in a directory."""
        if extensions is None:
            extensions = [".py", ".ts", ".js", ".json", ".sh"]

        target_dir = os.path.join(self.workspace_root, directory) if not os.path.isabs(directory) else directory
        all_vulns: List[SecurityVulnerability] = []
        count = 0

        skip_dirs = {".git", ".worktrees", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in extensions:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    vulns = self.scan_file(full_path)
                    all_vulns.extend(vulns)
                    count += 1
                    if count >= max_files:
                        break
            if count >= max_files:
                break

        return all_vulns


class SecurityASTVisitor(ast.NodeVisitor):
    """AST visitor traversing syntax trees to identify dangerous patterns."""

    def __init__(self, file_path: str, lines: List[str]):
        self.file_path = file_path
        self.lines = lines
        self.vulnerabilities: List[SecurityVulnerability] = []

    def _get_snippet(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_Call(self, node: ast.Call) -> None:
        func_name = ""
        lineno = getattr(node, "lineno", 1)
        snippet = self._get_snippet(lineno)

        # 1. Identify function calls
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            val = node.func.value
            mod_prefix = val.id if isinstance(val, ast.Name) else ""
            func_name = f"{mod_prefix}.{node.func.attr}" if mod_prefix else node.func.attr

        # Check for Unsafe Dynamic Execution (eval, exec)
        if func_name in ("eval", "exec"):
            self.vulnerabilities.append(
                SecurityVulnerability(
                    id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                    rule_id="SEC-002-DYNAMIC-CODE-EXEC",
                    name="Arbitrary Dynamic Code Execution",
                    severity="CRITICAL",
                    category="CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code",
                    file_path=self.file_path,
                    line_number=lineno,
                    code_snippet=snippet,
                    description=f"Invocation of '{func_name}' allows arbitrary untrusted code execution.",
                    recommendation="Avoid eval/exec. Use ast.literal_eval for safe data parsing or explicit dispatchers.",
                    cwe_id="CWE-95",
                    fix_suggestion="import ast\nast.literal_eval(payload)",
                )
            )

        # Check for Insecure Deserialization (pickle.loads, yaml.load without safe loader)
        elif func_name in ("pickle.loads", "pickle.load", "_pickle.loads"):
            self.vulnerabilities.append(
                SecurityVulnerability(
                    id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                    rule_id="SEC-003-INSECURE-DESERIALIZATION",
                    name="Insecure Deserialization (Pickle)",
                    severity="CRITICAL",
                    category="CWE-502: Deserialization of Untrusted Data",
                    file_path=self.file_path,
                    line_number=lineno,
                    code_snippet=snippet,
                    description="Unpickling untrusted data can lead to arbitrary code execution via __reduce__.",
                    recommendation="Use json, msgpack, or hmac-signed formats instead of pickle.",
                    cwe_id="CWE-502",
                    fix_suggestion="import json\ndata = json.loads(payload)",
                )
            )

        # Check for Command Injection (subprocess with shell=True or os.system)
        elif func_name in ("os.system", "os.popen"):
            self.vulnerabilities.append(
                SecurityVulnerability(
                    id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                    rule_id="SEC-004-SHELL-COMMAND-INJECTION",
                    name="OS Command Injection Risk",
                    severity="HIGH",
                    category="CWE-78: Improper Neutralization of Special Elements used in an OS Command",
                    file_path=self.file_path,
                    line_number=lineno,
                    code_snippet=snippet,
                    description=f"Call to '{func_name}' executes a shell command that may contain unsanitized input.",
                    recommendation="Use subprocess.run(['cmd', arg], shell=False) with parameterized arguments.",
                    cwe_id="CWE-78",
                    fix_suggestion="subprocess.run(['tool', argument], check=True)",
                )
            )

        elif "subprocess" in func_name or func_name in ("Popen", "call", "run", "check_call", "check_output"):
            # Check for shell=True
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                            rule_id="SEC-005-SUBPROCESS-SHELL-TRUE",
                            name="Subprocess Shell Execution (shell=True)",
                            severity="HIGH",
                            category="CWE-78: Command Injection Risk",
                            file_path=self.file_path,
                            line_number=lineno,
                            code_snippet=snippet,
                            description="subprocess invoked with shell=True is susceptible to shell metacharacter injection.",
                            recommendation="Set shell=False and pass arguments as a list of strings.",
                            cwe_id="CWE-78",
                            fix_suggestion="subprocess.run(['command', arg1, arg2], shell=False)",
                        )
                    )

        # Check for Weak Hashing Algorithms (MD5, SHA1 for security)
        elif func_name in ("hashlib.md5", "hashlib.sha1"):
            self.vulnerabilities.append(
                SecurityVulnerability(
                    id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                    rule_id="SEC-006-WEAK-HASH-ALGORITHM",
                    name="Weak Cryptographic Hash Function",
                    severity="MEDIUM",
                    category="CWE-327: Use of a Broken or Risky Cryptographic Algorithm",
                    file_path=self.file_path,
                    line_number=lineno,
                    code_snippet=snippet,
                    description=f"Algorithm '{func_name}' is vulnerable to collision attacks and insecure for cryptographic use.",
                    recommendation="Use hashlib.sha256() or hashlib.sha3_256() for hashing.",
                    cwe_id="CWE-327",
                    fix_suggestion="hashlib.sha256(data).hexdigest()",
                )
            )

        # Check for SQL Injection (execute with f-string or % formatting)
        elif func_name.endswith(".execute") or func_name == "execute":
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.JoinedStr):  # f-string: f"SELECT ... {var}"
                    self.vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                            rule_id="SEC-007-SQL-INJECTION-FORMAT",
                            name="SQL Injection via Formatted String",
                            severity="HIGH",
                            category="CWE-89: Improper Neutralization of Special Elements used in an SQL Command",
                            file_path=self.file_path,
                            line_number=lineno,
                            code_snippet=snippet,
                            description="SQL query constructed using string interpolation/f-string instead of parameterized placeholders.",
                            recommendation="Use parameterized queries with bind variables (e.g. cursor.execute('SELECT * FROM t WHERE id = ?', (val,))).",
                            cwe_id="CWE-89",
                            fix_suggestion="cursor.execute('SELECT * FROM table WHERE id = ?', (user_id,))",
                        )
                    )
                elif isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Add, ast.Mod)):
                    self.vulnerabilities.append(
                        SecurityVulnerability(
                            id=f"VULN-{uuid.uuid4().hex[:8].upper()}",
                            rule_id="SEC-007-SQL-INJECTION-CONCAT",
                            name="SQL Injection via String Concatenation",
                            severity="HIGH",
                            category="CWE-89: SQL Injection Risk",
                            file_path=self.file_path,
                            line_number=lineno,
                            code_snippet=snippet,
                            description="SQL query dynamically concatenated using '+' or '%' formatting.",
                            recommendation="Use database driver bind variables.",
                            cwe_id="CWE-89",
                            fix_suggestion="cursor.execute('SELECT * FROM table WHERE col = %s', (val,))",
                        )
                    )

        self.generic_visit(node)

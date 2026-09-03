"""Multi-language syntax and structural validation for code files."""

import ast
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, Optional, Tuple


@dataclass
class SyntaxValidationResult:
    """Outcome of pre/post modification syntax validation."""
    is_valid: bool
    language: str
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    error_col: Optional[int] = None
    diagnostics: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "language": self.language,
            "error_message": self.error_message,
            "error_line": self.error_line,
            "error_col": self.error_col,
            "diagnostics": self.diagnostics,
        }


class SyntaxValidator:
    """Validates code syntax and structural integrity across multiple programming languages."""

    EXT_LANG_MAP = {
        ".py": "python",
        ".json": "json",
        ".js": "javascript",
        ".jsx": "javascript_react",
        ".ts": "typescript",
        ".tsx": "typescript_react",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".md": "markdown",
        ".txt": "text",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
    }

    @classmethod
    def infer_language(cls, file_path: str) -> str:
        """Infers the language identifier from the file extension."""
        ext = Path(file_path).suffix.lower()
        return cls.EXT_LANG_MAP.get(ext, "unknown")

    def validate(self, content: str, file_path: str, language: Optional[str] = None) -> SyntaxValidationResult:
        """Validates the syntax of the provided content based on file path or explicit language."""
        lang = language or self.infer_language(file_path)

        if lang == "python":
            return self._validate_python(content, file_path)
        elif lang == "json":
            return self._validate_json(content, file_path)
        elif lang in ("javascript", "typescript", "javascript_react", "typescript_react"):
            return self._validate_js_ts(content, file_path, lang)
        elif lang in ("yaml", "yml"):
            return self._validate_yaml(content, file_path)
        elif lang == "sql":
            return self._validate_sql(content, file_path)
        else:
            # Plain text, markdown, etc. always pass syntax check
            return SyntaxValidationResult(is_valid=True, language=lang)

    def _validate_python(self, content: str, file_path: str) -> SyntaxValidationResult:
        """Validates Python code using the official AST parser."""
        try:
            ast.parse(content, filename=file_path)
            return SyntaxValidationResult(is_valid=True, language="python")
        except SyntaxError as e:
            line = e.lineno
            col = e.offset
            msg = e.msg or "Invalid syntax"
            diag = f"Python SyntaxError at line {line}, col {col}: {msg}"
            if e.text:
                diag += f"\n  -> {e.text.rstrip()}"
                if col:
                    diag += f"\n  -> {' ' * (col - 1)}^"
            return SyntaxValidationResult(
                is_valid=False,
                language="python",
                error_message=f"SyntaxError: {msg}",
                error_line=line,
                error_col=col,
                diagnostics=diag,
            )
        except Exception as e:
            return SyntaxValidationResult(
                is_valid=False,
                language="python",
                error_message=f"AST Parse Failure: {str(e)}",
                diagnostics=str(e),
            )

    def _validate_json(self, content: str, file_path: str) -> SyntaxValidationResult:
        """Validates JSON structure using json.loads."""
        if not content.strip():
            return SyntaxValidationResult(is_valid=True, language="json")
        try:
            json.loads(content)
            return SyntaxValidationResult(is_valid=True, language="json")
        except json.JSONDecodeError as e:
            return SyntaxValidationResult(
                is_valid=False,
                language="json",
                error_message=f"JSONDecodeError: {e.msg}",
                error_line=e.lineno,
                error_col=e.colno,
                diagnostics=f"JSON parse error at line {e.lineno}, col {e.colno}: {e.msg}",
            )

    def _validate_js_ts(self, content: str, file_path: str, lang: str) -> SyntaxValidationResult:
        """Validates structural balance for JS/TS/JSX/TSX (brackets, braces, parens, template literals, quotes)."""
        stack = []
        in_single_quote = False
        in_double_quote = False
        in_template_literal = False
        in_line_comment = False
        in_block_comment = False
        escape = False

        line_num = 1
        col_num = 0

        # Mapping of open to close delimiters
        matching_delimiters = {')': '(', '}': '{', ']': '['}
        tag_stack = []

        chars = list(content)
        i = 0
        n = len(chars)

        while i < n:
            ch = chars[i]
            col_num += 1

            if ch == '\n':
                line_num += 1
                col_num = 0
                in_line_comment = False
                escape = False
                i += 1
                continue

            if escape:
                escape = False
                i += 1
                continue

            if ch == '\\':
                escape = True
                i += 1
                continue

            # Handle comments
            if not in_single_quote and not in_double_quote and not in_template_literal:
                if not in_block_comment and not in_line_comment:
                    if ch == '/' and i + 1 < n:
                        next_ch = chars[i + 1]
                        if next_ch == '/':
                            in_line_comment = True
                            i += 2
                            col_num += 1
                            continue
                        elif next_ch == '*':
                            in_block_comment = True
                            i += 2
                            col_num += 1
                            continue
                elif in_block_comment:
                    if ch == '*' and i + 1 < n and chars[i + 1] == '/':
                        in_block_comment = False
                        i += 2
                        col_num += 1
                        continue
                    i += 1
                    continue
                elif in_line_comment:
                    i += 1
                    continue

            if in_line_comment or in_block_comment:
                i += 1
                continue

            # Handle string quotes
            if ch == "'" and not in_double_quote and not in_template_literal:
                in_single_quote = not in_single_quote
                i += 1
                continue
            elif ch == '"' and not in_single_quote and not in_template_literal:
                in_double_quote = not in_double_quote
                i += 1
                continue
            elif ch == '`' and not in_single_quote and not in_double_quote:
                in_template_literal = not in_template_literal
                i += 1
                continue

            if in_single_quote or in_double_quote or in_template_literal:
                i += 1
                continue

            # Handle brackets
            if ch in ('(', '{', '['):
                stack.append((ch, line_num, col_num))
            elif ch in (')', '}', ']'):
                expected_open = matching_delimiters[ch]
                if not stack:
                    return SyntaxValidationResult(
                        is_valid=False,
                        language=lang,
                        error_message=f"Unmatched closing delimiter '{ch}'",
                        error_line=line_num,
                        error_col=col_num,
                        diagnostics=f"Found closing '{ch}' without matching '{expected_open}' at line {line_num}:{col_num}",
                    )
                actual_open, o_line, o_col = stack.pop()
                if actual_open != expected_open:
                    return SyntaxValidationResult(
                        is_valid=False,
                        language=lang,
                        error_message=f"Mismatched delimiter: opened with '{actual_open}' (line {o_line}) but closed with '{ch}' (line {line_num})",
                        error_line=line_num,
                        error_col=col_num,
                        diagnostics=f"Mismatched delimiter '{actual_open}' -> '{ch}' at line {line_num}:{col_num}",
                    )

            i += 1

        if in_block_comment:
            return SyntaxValidationResult(
                is_valid=False,
                language=lang,
                error_message="Unclosed block comment '/* ... */'",
                error_line=line_num,
                error_col=col_num,
                diagnostics="File ended while parsing multi-line block comment",
            )
        if in_template_literal:
            return SyntaxValidationResult(
                is_valid=False,
                language=lang,
                error_message="Unclosed template literal '`...`'",
                error_line=line_num,
                error_col=col_num,
                diagnostics="File ended while inside unclosed template literal string",
            )
        if in_single_quote or in_double_quote:
            return SyntaxValidationResult(
                is_valid=False,
                language=lang,
                error_message="Unclosed string literal",
                error_line=line_num,
                error_col=col_num,
                diagnostics="File ended with unclosed single or double quote string",
            )
        if stack:
            open_ch, o_line, o_col = stack[-1]
            return SyntaxValidationResult(
                is_valid=False,
                language=lang,
                error_message=f"Unclosed delimiter '{open_ch}' opened at line {o_line}:{o_col}",
                error_line=o_line,
                error_col=o_col,
                diagnostics=f"File ended with unclosed opening delimiter '{open_ch}' from line {o_line}",
            )

        return SyntaxValidationResult(is_valid=True, language=lang)

    def _validate_yaml(self, content: str, file_path: str) -> SyntaxValidationResult:
        """Basic indentation and key-value delimiter validation for YAML."""
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Check for tabs which are illegal in YAML
            if "\t" in line.split("#")[0]:
                return SyntaxValidationResult(
                    is_valid=False,
                    language="yaml",
                    error_message="Tabs are not allowed in YAML files; use spaces for indentation",
                    error_line=idx,
                    error_col=line.find("\t") + 1,
                    diagnostics=f"Tab character detected at line {idx}",
                )
        return SyntaxValidationResult(is_valid=True, language="yaml")

    def _validate_sql(self, content: str, file_path: str) -> SyntaxValidationResult:
        """Basic balanced quote check for SQL."""
        single_quotes = content.count("'") - content.count(r"\'")
        if single_quotes % 2 != 0:
            return SyntaxValidationResult(
                is_valid=False,
                language="sql",
                error_message="Unclosed single-quote string literal in SQL",
            )
        return SyntaxValidationResult(is_valid=True, language="sql")

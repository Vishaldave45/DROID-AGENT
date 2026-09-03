"""Code Review, Security Audit & SARIF Export Tools for NexForge Droid (Phase 18)."""

from typing import Any, Dict, List, Optional

from app.review.analyzer import CodeQualityAnalyzer
from app.review.sarif import SARIFExporter
from app.review.security_scanner import ASTSecurityScanner
from app.tools.base import Tool, ToolResult


class CodeReviewScanTool(Tool):
    """Tool for analyzing code quality, cyclomatic complexity, and code smells."""

    name = "code_review_scan"
    description = "Analyze code quality, cyclomatic complexity, function lengths, parameter counts, and anti-patterns across a file or workspace."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Specific file path or directory to analyze (defaults to workspace root).",
            },
            "code_snippet": {
                "type": "string",
                "description": "Optional in-memory code string to analyze directly.",
            },
            "max_files": {
                "type": "integer",
                "description": "Maximum number of files to scan when scanning a directory (default 100).",
            },
        },
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        code_snippet = kwargs.get("code_snippet")
        max_files = kwargs.get("max_files", 100)

        analyzer = CodeQualityAnalyzer()

        try:
            if code_snippet:
                findings = analyzer.analyze_code(code_snippet, file_path=path or "snippet.py")
                return ToolResult(
                    success=True,
                    data={
                        "findings": [f.to_dict() for f in findings],
                        "total_findings": len(findings),
                    },
                )

            if path and (path.endswith(".py") or "." in path):
                findings = analyzer.analyze_file(path)
                return ToolResult(
                    success=True,
                    data={
                        "file_path": path,
                        "findings": [f.to_dict() for f in findings],
                        "total_findings": len(findings),
                    },
                )

            # Directory review
            report = analyzer.run_review(directory=path or ".", max_files=max_files)
            return ToolResult(
                success=True,
                data={
                    "report": report.to_dict(),
                    "quality_score": report.quality_score,
                    "status": report.status,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Code review analysis failed: {e}")


class SecurityAuditTool(Tool):
    """Tool for running OWASP Top 10 security scanning and taint analysis."""

    name = "security_audit_scan"
    description = "Scan source code for OWASP Top 10 vulnerabilities, command/SQL injection, hardcoded secrets, and unsafe eval/exec."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Specific file or directory to scan (defaults to workspace root).",
            },
            "code_snippet": {
                "type": "string",
                "description": "Optional in-memory code string to audit directly.",
            },
            "min_severity": {
                "type": "string",
                "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "ALL"],
                "description": "Minimum vulnerability severity threshold (default ALL).",
            },
        },
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path")
        code_snippet = kwargs.get("code_snippet")
        min_severity = kwargs.get("min_severity", "ALL").upper()

        scanner = ASTSecurityScanner()

        try:
            if code_snippet:
                vulns = scanner.scan_code(code_snippet, file_path=path or "snippet.py")
            elif path and (path.endswith(".py") or "." in path):
                vulns = scanner.scan_file(path)
            else:
                vulns = scanner.scan_directory(directory=path or ".")

            # Filter by severity if specified
            severity_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
            min_rank = severity_order.get(min_severity, 0) if min_severity != "ALL" else 0

            filtered = [
                v for v in vulns
                if severity_order.get(v.severity.upper(), 0) >= min_rank
            ]

            return ToolResult(
                success=True,
                data={
                    "vulnerabilities": [v.to_dict() for v in filtered],
                    "total_vulnerabilities": len(filtered),
                    "critical_count": sum(1 for v in filtered if v.severity == "CRITICAL"),
                    "high_count": sum(1 for v in filtered if v.severity == "HIGH"),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"Security audit failed: {e}")


class SarifExportTool(Tool):
    """Tool for exporting static analysis results to OASIS SARIF v2.1.0 standard JSON."""

    name = "sarif_export"
    description = "Export vulnerability and code review findings into SARIF v2.1.0 JSON format for GitHub Security and GitLab CI integration."
    input_schema = {
        "type": "object",
        "properties": {
            "output_path": {
                "type": "string",
                "description": "Optional file path to write SARIF JSON (e.g. 'reports/security.sarif').",
            },
            "directory": {
                "type": "string",
                "description": "Target directory to audit (default workspace root).",
            },
        },
    }

    def execute(self, **kwargs: Any) -> ToolResult:
        output_path = kwargs.get("output_path")
        directory = kwargs.get("directory", ".")

        scanner = ASTSecurityScanner()
        analyzer = CodeQualityAnalyzer()
        exporter = SARIFExporter()

        try:
            vulns = scanner.scan_directory(directory=directory)
            report = analyzer.run_review(directory=directory)
            sarif_doc = exporter.generate_sarif(vulnerabilities=vulns, findings=report.findings)

            written_file = None
            if output_path:
                written_file = exporter.export_to_file(output_path, vulns, report.findings)

            return ToolResult(
                success=True,
                data={
                    "sarif": sarif_doc,
                    "written_file": written_file,
                    "results_count": len(sarif_doc["runs"][0]["results"]),
                    "rules_count": len(sarif_doc["runs"][0]["tool"]["driver"]["rules"]),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=f"SARIF export failed: {e}")

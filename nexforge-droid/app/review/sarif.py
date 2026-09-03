"""NexForge Droid - SARIF (Static Analysis Results Interchange Format) Exporter.

Compliant with OASIS Standard SARIF v2.1.0 JSON specification.
Supports native ingestion by GitHub Advanced Security Code Scanning,
GitLab SAST, Azure DevOps, and IDE SARIF viewers.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from app.review.analyzer import CodeSmellFinding
from app.review.security_scanner import SecurityVulnerability


class SARIFExporter:
    """Transforms security vulnerabilities and code review findings into SARIF v2.1.0 JSON."""

    SCHEMA_URI = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json"
    TOOL_NAME = "NexForge Droid Security & Quality Engine"
    TOOL_VERSION = "1.0.0"
    TOOL_INFO_URI = "https://github.com/nexforge/nexforge-droid"

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or os.getcwd()

    def generate_sarif(
        self,
        vulnerabilities: Optional[List[SecurityVulnerability]] = None,
        findings: Optional[List[CodeSmellFinding]] = None,
    ) -> Dict[str, Any]:
        """Generates standard SARIF v2.1.0 document dictionary."""
        vulns = vulnerabilities or []
        smells = findings or []

        # Rules catalog
        rules: Dict[str, Dict[str, Any]] = {}
        results: List[Dict[str, Any]] = []

        # 1. Process Security Vulnerabilities
        for v in vulns:
            if v.rule_id not in rules:
                rules[v.rule_id] = {
                    "id": v.rule_id,
                    "name": v.name.replace(" ", ""),
                    "shortDescription": {"text": v.name},
                    "fullDescription": {"text": v.description},
                    "help": {
                        "text": f"{v.description}\n\nRecommendation: {v.recommendation}",
                        "markdown": f"### {v.name}\n\n{v.description}\n\n**Recommendation**: {v.recommendation}",
                    },
                    "properties": {
                        "tags": ["security", v.category, v.cwe_id.lower()],
                        "security-severity": self._map_severity_to_score(v.severity),
                    },
                }

            level = "error" if v.severity in ("CRITICAL", "HIGH") else ("warning" if v.severity == "MEDIUM" else "note")

            rel_path = v.file_path.replace("\\", "/")
            if os.path.isabs(rel_path):
                rel_path = os.path.relpath(rel_path, self.workspace_root).replace("\\", "/")

            result_entry: Dict[str, Any] = {
                "ruleId": v.rule_id,
                "level": level,
                "message": {
                    "text": f"[{v.severity}] {v.name}: {v.description}",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": rel_path,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": max(1, v.line_number),
                                "startColumn": 1,
                                "snippet": {
                                    "text": v.code_snippet,
                                },
                            },
                        }
                    }
                ],
            }

            if v.fix_suggestion:
                result_entry["fixes"] = [
                    {
                        "description": {"text": "Apply recommended security fix"},
                        "fileChanges": [
                            {
                                "artifactLocation": {"uri": rel_path},
                                "replacements": [
                                    {
                                        "deletedRegion": {"startLine": max(1, v.line_number)},
                                        "insertedContent": {"text": v.fix_suggestion},
                                    }
                                ],
                            }
                        ],
                    }
                ]

            results.append(result_entry)

        # 2. Process Code Smell / Quality Findings
        for s in smells:
            rule_id = f"SMELL-{s.category}"
            if rule_id not in rules:
                rules[rule_id] = {
                    "id": rule_id,
                    "name": f"CodeSmell{s.category.title()}",
                    "shortDescription": {"text": f"Code Smell / Quality Violation: {s.category}"},
                    "fullDescription": {"text": s.message},
                    "help": {
                        "text": f"{s.message}\nSuggestion: {s.suggestion}",
                        "markdown": f"**Quality Issue**: {s.message}\n\n*Suggestion*: {s.suggestion}",
                    },
                    "properties": {
                        "tags": ["quality", "code-smell", s.category.lower()],
                    },
                }

            level = "error" if s.severity == "ERROR" else ("warning" if s.severity == "WARNING" else "note")
            rel_path = s.file_path.replace("\\", "/")
            if os.path.isabs(rel_path):
                rel_path = os.path.relpath(rel_path, self.workspace_root).replace("\\", "/")

            results.append({
                "ruleId": rule_id,
                "level": level,
                "message": {
                    "text": f"{s.message} ({s.metric_name}: {s.metric_value} > threshold: {s.threshold})",
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": rel_path,
                                "uriBaseId": "%SRCROOT%",
                            },
                            "region": {
                                "startLine": max(1, s.line_number),
                                "startColumn": 1,
                            },
                        }
                    }
                ],
            })

        sarif_doc = {
            "$schema": self.SCHEMA_URI,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.TOOL_NAME,
                            "semanticVersion": self.TOOL_VERSION,
                            "informationUri": self.TOOL_INFO_URI,
                            "rules": list(rules.values()),
                        }
                    },
                    "results": results,
                    "invocations": [
                        {
                            "executionSuccessful": True,
                        }
                    ],
                }
            ],
        }

        return sarif_doc

    def export_to_file(
        self,
        output_path: str,
        vulnerabilities: Optional[List[SecurityVulnerability]] = None,
        findings: Optional[List[CodeSmellFinding]] = None,
    ) -> str:
        """Serializes SARIF JSON to a file and returns the target path."""
        sarif_data = self.generate_sarif(vulnerabilities, findings)
        abs_output = os.path.join(self.workspace_root, output_path) if not os.path.isabs(output_path) else output_path
        os.makedirs(os.path.dirname(abs_output), exist_ok=True)
        with open(abs_output, "w", encoding="utf-8") as f:
            json.dump(sarif_data, f, indent=2)
        return abs_output

    def _map_severity_to_score(self, severity: str) -> str:
        mapping = {
            "CRITICAL": "9.5",
            "HIGH": "8.0",
            "MEDIUM": "5.5",
            "LOW": "2.5",
            "INFO": "1.0",
        }
        return mapping.get(severity.upper(), "5.0")

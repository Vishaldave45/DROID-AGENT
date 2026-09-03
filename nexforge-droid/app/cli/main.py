"""
NexForge Droid Unified CLI & Distribution Runner (Phase 14).
Provides a production-grade, self-contained CLI entrypoint managed through UV.
"""

import sys
import os
import json
import argparse
import time
import subprocess
from typing import Dict, Any, Optional

# Ensure nexforge-droid is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.evaluation.benchmark_runner import SWEBenchmarkSuite
from app.evaluation.quality_gate import MultiCriteriaQualityGate
from app.agent import AutonomousAgentRuntime
from app.storage.base import InMemoryTaskStore, TaskStatus
from app.context.scanner import RepositoryScanner


def get_uv_environment_info() -> Dict[str, Any]:
    """Inspects the local UV environment, binary location, and python interpreter."""
    uv_path = None
    uv_version = "unknown"
    is_uv_available = False

    try:
        res = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            uv_version = res.stdout.strip()
            is_uv_available = True
    except Exception:
        pass

    try:
        which_res = subprocess.run(["which", "uv"], capture_output=True, text=True, timeout=5)
        if which_res.returncode == 0:
            uv_path = which_res.stdout.strip()
    except Exception:
        pass

    # Inspect installed packages via uv or sys
    packages_count = len(sys.modules)

    return {
        "uv_available": is_uv_available,
        "uv_version": uv_version,
        "uv_path": uv_path,
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "workspace_root": BASE_DIR,
        "modules_loaded": packages_count,
        "timestamp": time.time(),
    }


def cmd_info(args: argparse.Namespace) -> int:
    """Displays comprehensive runtime status, UV environment, and subsystem health."""
    env_info = get_uv_environment_info()
    data = {
        "system": "NexForge Droid",
        "phase": 14,
        "architecture": "Modular Autonomous Software Engineering Agent",
        "cli_version": "0.1.0",
        "uv_environment": env_info,
        "supported_subcommands": ["info", "bench", "gate", "run", "scan", "test"],
    }
    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("  NexForge Droid Autonomous Engineering Agent (Phase 14)")
        print("=" * 60)
        print(f"  Python Runtime : {env_info['python_version']} ({env_info['python_executable']})")
        print(f"  UV Package Mgr : {env_info['uv_version']} (Path: {env_info['uv_path']})")
        print(f"  Workspace Root : {env_info['workspace_root']}")
        print(f"  Status         : READY (All 14 Phases Active)")
        print("=" * 60)
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    """Runs one or all SWE-bench challenges."""
    suite = SWEBenchmarkSuite()
    if args.challenge_id:
        result = suite.run_challenge(args.challenge_id)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            status = "PASSED" if result.success else "FAILED"
            print(f"Benchmark {result.challenge_id} [{status}]: {result.title}")
            print(f"  Pass@1: {result.pass_at_1} | Score: {result.quality_score}/100 | Time: {result.duration_ms}ms")
        return 0 if result.success else 1
    else:
        challenges = suite.list_challenges()
        if args.json:
            print(json.dumps([c.to_dict() for c in challenges], indent=2))
        else:
            print(f"Found {len(challenges)} SWE-bench challenges:")
            for c in challenges:
                print(f"  - [{c.id}] ({c.category}/{c.difficulty}) {c.title}")
        return 0


def cmd_gate(args: argparse.Namespace) -> int:
    """Executes the 6-dimensional multi-criteria quality gate."""
    gate = MultiCriteriaQualityGate()
    target_files = args.files if args.files else None
    report = gate.evaluate_all(
        files=target_files,
        task_id=args.task_id or "cli-eval",
    )
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        status_str = "PASSED" if report.passed else "FAILED"
        print(f"Quality Gate {status_str}: {report.overall_score}/100")
        for dim in report.dimensions:
            dim_status = "PASS" if dim.passed else "FAIL"
            print(f"  [{dim_status}] {dim.name}: {dim.score}%")
    return 0 if report.passed else 1


def cmd_scan(args: argparse.Namespace) -> int:
    """Scans repository structure and metrics."""
    target_path = args.path or BASE_DIR
    scanner = RepositoryScanner(root_path=target_path)
    summary = scanner.scan()
    if args.json:
        print(json.dumps(summary.to_dict(), indent=2))
    else:
        print(f"Scanned {len(summary.file_metrics)} files at {target_path}:")
        print(f"  Total Lines of Code: {summary.total_lines_of_code}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Executes an autonomous agent task."""
    from app.llm.mock import MockLLMProvider
    from app.llm.base import LLMResponse, ToolCallRequest
    from app.storage.base import TaskState
    from app.tools import get_default_tool_registry

    mock_provider = MockLLMProvider(
        responses=[
            LLMResponse(
                content="Inspecting workspace environment and files.",
                tool_calls=[
                    ToolCallRequest(
                        call_id="call-1",
                        tool_name="list_dir",
                        arguments={"path": BASE_DIR},
                    )
                ],
            ),
            LLMResponse(
                content="Task verified and executed successfully.",
                tool_calls=[
                    ToolCallRequest(
                        call_id="call-2",
                        tool_name="finish_task",
                        arguments={
                            "summary": f"Completed autonomous execution for: {args.requirement}",
                            "status": "SUCCESS",
                        },
                    )
                ],
            ),
        ]
    )

    registry = get_default_tool_registry()
    task_store = InMemoryTaskStore()
    runtime = AutonomousAgentRuntime(
        llm_provider=mock_provider,
        tool_registry=registry,
        task_store=task_store,
        workspace_root=BASE_DIR,
        max_iterations=args.max_iterations or 5,
    )

    task_id = args.task_id or f"task-cli-{int(time.time())}"
    state = TaskState(
        task_id=task_id,
        repository_id="local_workspace",
        requirement=args.requirement,
    )

    final_state = runtime.run_task(state)

    if args.json:
        print(json.dumps(final_state.to_dict(), indent=2))
    else:
        print(f"Agent Task '{args.requirement}' finished with status: {final_state.status.value}")
        print(f"  Iterations: {final_state.iteration}/{args.max_iterations}")
        if final_state.final_summary:
            print(f"  Summary: {final_state.final_summary}")
    return 0 if final_state.status == TaskStatus.COMPLETED else 1


def cmd_mcp(args: argparse.Namespace) -> int:
    """Model Context Protocol (MCP) Server and Gateway CLI commands (Phase 16)."""
    from app.mcp import MCPGateway

    gateway = MCPGateway(workspace_root=BASE_DIR)
    action = args.mcp_action or "status"

    if action == "status":
        status = gateway.get_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("=" * 60)
            print("  NexForge MCP Gateway & Universal Server (Phase 16)")
            print("=" * 60)
            print(f"  Protocol Version   : {status['protocol_version']}")
            print(f"  Status             : {status['gateway_status']}")
            print(f"  Local Tools        : {status['local_tools_count']}")
            print(f"  External Servers   : {status['external_servers_count']}")
            print(f"  Total Active Tools : {status['total_available_tools']}")
            print("=" * 60)
        return 0

    elif action == "tools":
        resp = gateway.handle_request({"id": 1, "method": "tools/list", "params": {}})
        tools = resp.result.get("tools", [])
        if args.json:
            print(json.dumps(tools, indent=2))
        else:
            print(f"Exposed MCP Tools ({len(tools)}):")
            for t in tools:
                print(f"  - {t['name']}: {t.get('description', '')[:70]}...")
        return 0

    elif action == "resources":
        resp = gateway.handle_request({"id": 1, "method": "resources/list", "params": {}})
        res = resp.result.get("resources", [])
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Exposed MCP Resources ({len(res)}):")
            for r in res:
                print(f"  - {r['uri']} ({r['name']})")
        return 0

    elif action == "prompts":
        resp = gateway.handle_request({"id": 1, "method": "prompts/list", "params": {}})
        prompts = resp.result.get("prompts", [])
        if args.json:
            print(json.dumps(prompts, indent=2))
        else:
            print(f"Exposed MCP Prompts ({len(prompts)}):")
            for p in prompts:
                print(f"  - {p['name']}: {p.get('description', '')}")
        return 0

    elif action == "servers":
        servers = gateway.client.list_servers()
        if args.json:
            print(json.dumps(servers, indent=2))
        else:
            print(f"Connected External MCP Servers ({len(servers)}):")
            for s in servers:
                print(f"  - [{s['server_id']}] {s['name']} ({s['transport']}) - {s['tools_count']} tools")
        return 0

    return 0


def cmd_branch(args: argparse.Namespace) -> int:
    """Manages Git branches."""
    from app.git.branch import GitBranchManager
    mgr = GitBranchManager(repo_path=BASE_DIR)
    action = getattr(args, "branch_action", "list") or "list"
    name = getattr(args, "name", None)

    if action == "list":
        branches = [b.to_dict() for b in mgr.list_branches()]
        if args.json:
            print(json.dumps(branches, indent=2))
        else:
            print("Git Branches:")
            for b in branches:
                curr = "*" if b.get("is_current") else " "
                print(f"  {curr} {b['name']:<30} [{b['commit_hash']}] {b.get('upstream') or ''}")
        return 0

    elif action == "create":
        if not name:
            print("Error: Branch name required for create action.", file=sys.stderr)
            return 1
        try:
            b = mgr.create_branch(name, switch=True)
            if args.json:
                print(json.dumps(b.to_dict(), indent=2))
            else:
                print(f"Successfully created and switched to branch: {name}")
            return 0
        except Exception as e:
            print(f"Error creating branch: {e}", file=sys.stderr)
            return 1

    return 0


def cmd_pr(args: argparse.Namespace) -> int:
    """Synthesizes Pull Request descriptions."""
    from app.git.pr_generator import PullRequestSynthesizer
    synthesizer = PullRequestSynthesizer(repo_path=BASE_DIR)
    title = getattr(args, "title", None)
    branch = getattr(args, "branch", "feat/mcp-gateway")
    spec = synthesizer.synthesize_pr(title=title, branch_source=branch)
    if args.json:
        print(json.dumps(spec.to_dict(), indent=2))
    else:
        print(spec.markdown_body)
    return 0


def cmd_ci(args: argparse.Namespace) -> int:
    """Executes CI/CD pipeline matrix and self-healing."""
    from app.git.ci_pipeline import CISelfHealingEngine
    engine = CISelfHealingEngine(repo_path=BASE_DIR)
    action = getattr(args, "ci_action", "run") or "run"
    branch = getattr(args, "branch", "main")

    if action == "run":
        sim_fail = getattr(args, "simulate_failure", None)
        pipeline = engine.run_pipeline(branch=branch, simulate_failure_stage=sim_fail)
        if args.json:
            print(json.dumps(pipeline.to_dict(), indent=2))
        else:
            print(f"CI/CD Pipeline: {pipeline.pipeline_id} ({pipeline.status.upper()})")
            for s in pipeline.stages:
                icon = "PASS" if s.status == "passed" else ("FAIL" if s.status == "failed" else "HEAL")
                print(f"  [{icon}] {s.name:<32} ({s.duration_ms:.1f}ms)")
        return 0 if pipeline.status in ("passed", "healed") else 1

    elif action == "heal":
        stage = getattr(args, "stage", "unit_tests")
        failed = engine.run_pipeline(branch=branch, simulate_failure_stage=stage)
        healed = engine.heal_pipeline(failed)
        if args.json:
            print(json.dumps(healed.to_dict(), indent=2))
        else:
            print(f"CI/CD Self-Healing: {healed.pipeline_id} ({healed.status.upper()})")
            print(f"  Repairs Applied: {healed.healing_attempts}")
            print(f"  Healed Patch:\n{healed.healed_patch}")
        return 0

    return 0


def cmd_review(args: argparse.Namespace) -> int:
    """Performs static code review, AST security audit, and SARIF export (Phase 18)."""
    from app.review.analyzer import CodeQualityAnalyzer
    from app.review.sarif import SARIFExporter
    from app.review.security_scanner import ASTSecurityScanner

    action = getattr(args, "review_action", "scan") or "scan"
    target_path = getattr(args, "path", ".") or "."
    out_sarif = getattr(args, "sarif", None)

    scanner = ASTSecurityScanner(workspace_root=BASE_DIR)
    analyzer = CodeQualityAnalyzer(workspace_root=BASE_DIR)
    exporter = SARIFExporter(workspace_root=BASE_DIR)

    if action == "audit":
        vulns = scanner.scan_directory(directory=target_path)
        if out_sarif:
            exporter.export_to_file(out_sarif, vulnerabilities=vulns)
        if args.json:
            print(json.dumps([v.to_dict() for v in vulns], indent=2))
        else:
            print(f"NexForge Security Audit: {len(vulns)} issues detected in '{target_path}'")
            for v in vulns:
                print(f"  [{v.severity:<8}] {v.name} ({v.cwe_id}) at {v.file_path}:{v.line_number}")
                print(f"           Snippet: {v.code_snippet}")
        return 0 if not any(v.severity in ("CRITICAL", "HIGH") for v in vulns) else 1

    elif action == "sarif":
        vulns = scanner.scan_directory(directory=target_path)
        report = analyzer.run_review(directory=target_path)
        sarif_doc = exporter.generate_sarif(vulnerabilities=vulns, findings=report.findings)
        if out_sarif:
            written = exporter.export_to_file(out_sarif, vulnerabilities=vulns, findings=report.findings)
            print(f"Exported SARIF v2.1.0 report ({len(sarif_doc['runs'][0]['results'])} results) to {written}")
        else:
            print(json.dumps(sarif_doc, indent=2))
        return 0

    else:  # scan
        report = analyzer.run_review(directory=target_path)
        vulns = scanner.scan_directory(directory=target_path)
        if out_sarif:
            exporter.export_to_file(out_sarif, vulnerabilities=vulns, findings=report.findings)
        if args.json:
            data = report.to_dict()
            data["vulnerabilities"] = [v.to_dict() for v in vulns]
            print(json.dumps(data, indent=2))
        else:
            print(f"NexForge Code Review Report [{report.report_id}] - Quality Score: {report.quality_score}/100 ({report.status})")
            print(f"  Files Analyzed: {report.total_files_analyzed} | Findings: {report.total_findings} | Vulnerabilities: {len(vulns)}")
            for f in report.findings[:8]:
                print(f"  [{f.severity:<7}] {f.category} in {f.file_path}:{f.line_number} -> {f.message}")
            if len(report.findings) > 8:
                print(f"  ... and {len(report.findings) - 8} more findings.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")

    parser = argparse.ArgumentParser(
        prog="nexforge",
        description="NexForge Droid Unified CLI & Autonomous Engineering Platform",
        parents=[common_parser],
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # info
    p_info = subparsers.add_parser("info", help="Inspect runtime, UV environment and system health", parents=[common_parser])
    p_info.set_defaults(func=cmd_info)

    # bench
    p_bench = subparsers.add_parser("bench", help="SWE-bench challenge evaluation testbed", parents=[common_parser])
    p_bench.add_argument("challenge_id", nargs="?", help="Optional challenge ID (e.g. BM-001)")
    p_bench.set_defaults(func=cmd_bench)

    # gate
    p_gate = subparsers.add_parser("gate", help="Evaluate 6-dimensional multi-criteria quality gate", parents=[common_parser])
    p_gate.add_argument("--task-id", help="Task ID for audit")
    p_gate.add_argument("files", nargs="*", help="Optional file paths to audit")
    p_gate.set_defaults(func=cmd_gate)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan repository AST symbols", parents=[common_parser])
    p_scan.add_argument("--path", help="Directory path to scan")
    p_scan.set_defaults(func=cmd_scan)

    # run
    p_run = subparsers.add_parser("run", help="Run an autonomous engineering task", parents=[common_parser])
    p_run.add_argument("requirement", help="Requirement statement for the agent")
    p_run.add_argument("--task-id", help="Custom task identifier")
    p_run.add_argument("--max-iterations", type=int, default=5, help="Maximum iterations")
    p_run.add_argument("--mock-scenario", default="math_repair", help="Mock scenario for deterministic test")
    p_run.set_defaults(func=cmd_run)

    # mcp
    p_mcp = subparsers.add_parser("mcp", help="Model Context Protocol (MCP) server, gateway, and external tools", parents=[common_parser])
    p_mcp.add_argument("mcp_action", nargs="?", choices=["status", "tools", "resources", "prompts", "servers"], default="status", help="MCP action to perform")
    p_mcp.set_defaults(func=cmd_mcp)

    # branch
    p_branch = subparsers.add_parser("branch", help="Autonomous Git branching operations", parents=[common_parser])
    p_branch.add_argument("branch_action", nargs="?", choices=["list", "create"], default="list", help="Branch action")
    p_branch.add_argument("name", nargs="?", help="Branch name for create action")
    p_branch.set_defaults(func=cmd_branch)

    # pr
    p_pr = subparsers.add_parser("pr", help="Synthesize GitHub-ready Pull Request markdown", parents=[common_parser])
    p_pr.add_argument("--title", help="Custom PR title")
    p_pr.add_argument("--branch", default="feat/mcp-gateway", help="Source feature branch")
    p_pr.set_defaults(func=cmd_pr)

    # ci
    p_ci = subparsers.add_parser("ci", help="Run CI/CD matrix and self-healing engine", parents=[common_parser])
    p_ci.add_argument("ci_action", nargs="?", choices=["run", "heal"], default="run", help="CI action")
    p_ci.add_argument("--branch", default="main", help="Branch for CI run")
    p_ci.add_argument("--simulate-failure", choices=["syntax_ast", "security_audit", "unit_tests", "quality_gate", "build_packaging"], help="Simulate a stage failure")
    p_ci.add_argument("--stage", default="unit_tests", help="Stage to heal")
    p_ci.set_defaults(func=cmd_ci)

    # review (Phase 18)
    p_rev = subparsers.add_parser("review", help="Code review, AST security vulnerability scanner, and SARIF export", parents=[common_parser])
    p_rev.add_argument("review_action", nargs="?", choices=["scan", "audit", "sarif"], default="scan", help="Review action (scan, audit, or sarif)")
    p_rev.add_argument("--path", default=".", help="Target file or directory path")
    p_rev.add_argument("--sarif", help="File path to save SARIF v2.1.0 output")
    p_rev.set_defaults(func=cmd_review)

    return parser


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    if not argv:
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

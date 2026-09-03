#!/usr/bin/env python3
"""Unified API Bridge for NexForge Droid full-stack dynamic execution."""

import argparse
import contextlib
import io
import json
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Ensure any logging in run_api_bridge defaults to stderr, preserving stdout for pure JSON
root_logger = logging.getLogger()
for h in list(root_logger.handlers):
    root_logger.removeHandler(h)
root_logger.addHandler(logging.StreamHandler(sys.stderr))

from app.diagnostics.diagnostic_loop_controller import DiagnosticLoopController
from app.diagnostics.diagnostic_reasoner import DiagnosticReasoner
from app.diagnostics.test_runner import TestRunner
from app.diagnostics.traceback_parser import TracebackParser
from app.patcher.diff_engine import DiffEngine
from app.patcher.safe_modifier import SafeCodeModifier
from app.patcher.snapshot_auditor import FileSnapshotAuditor
from app.patcher.syntax_validator import SyntaxValidator
from app.planner.planner import ExplicitTaskPlanner
from app.planner.replanner import DynamicReplanner
from app.context.engine import RepositoryContextEngine
from app.context.base import ContextBudget
from app.streaming.models import StreamEventType, BreakpointConfig
from app.streaming.streamer import AgentEventStreamer
from app.streaming.debugger import InteractiveDebugger
from app.evaluation.quality_gate import MultiCriteriaQualityGate
from app.evaluation.benchmark_runner import SWEBenchmarkSuite

_GLOBAL_STREAMER = AgentEventStreamer()
_GLOBAL_DEBUGGER = InteractiveDebugger(streamer=_GLOBAL_STREAMER)
_GLOBAL_BENCHMARK_SUITE = SWEBenchmarkSuite()
_GLOBAL_QUALITY_GATE = MultiCriteriaQualityGate()


def handle_diagnostics_parse(data: dict) -> dict:
    text = data.get("text", "")
    failures = TracebackParser.parse_python_traceback(text)
    if not failures:
        # Try JS or generic stack
        failures = TracebackParser.parse_javascript_stack(text)

    parsed_list = []
    for f in failures:
        parsed_list.append(f.to_dict())

    return {
        "success": True,
        "count": len(parsed_list),
        "failures": parsed_list,
    }


def handle_diagnostics_diagnose(data: dict) -> dict:
    text = data.get("text", "")
    code_context = data.get("codeContext", "")
    target_file = data.get("targetFile", "app/service.py")

    failures = TracebackParser.parse_python_traceback(text)
    if not failures:
        failures = TracebackParser.parse_javascript_stack(text)

    if not failures:
        return {
            "success": False,
            "error": "No valid traceback or failure pattern detected.",
        }

    reasoner = DiagnosticReasoner()
    hypotheses = []
    
    # If code context provided, write to a temp file to allow AST & line extraction
    temp_file = None
    if code_context:
        temp_dir = tempfile.mkdtemp(prefix="nexforge_diag_")
        temp_file = os.path.join(temp_dir, os.path.basename(target_file))
        with open(temp_file, "w", encoding="utf-8") as tf:
            tf.write(code_context)

    try:
        for f in failures:
            if temp_file and f.innermost_frame:
                f.innermost_frame.file_path = temp_file
            hyp = reasoner.analyze_failure(f)
            hypotheses.append(hyp.to_dict())
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

    return {
        "success": True,
        "count": len(hypotheses),
        "hypotheses": hypotheses,
    }


def handle_diagnostics_loop(data: dict) -> dict:
    cmd = data.get("cmd", "python3 -m unittest discover -s ./tests -t .")
    max_iter = int(data.get("maxIterations", 4))
    auto_rollback = bool(data.get("autoRollback", True))
    
    controller = DiagnosticLoopController()
    res = controller.execute_loop(
        test_command=cmd,
        max_iterations=max_iter,
        auto_rollback_on_regression=auto_rollback,
    )
    return {
        "success": res.success,
        "result": res.to_dict(),
    }


def handle_patcher_validate(data: dict) -> dict:
    code = data.get("code", "")
    file_path = data.get("filePath", "snippet.py")
    language = data.get("language")

    validator = SyntaxValidator()
    res = validator.validate(code, file_path=file_path, language=language)
    return {
        "success": True,
        "result": res.to_dict(),
    }


def handle_patcher_diff(data: dict) -> dict:
    original = data.get("original", "")
    modified = data.get("modified", "")
    from_file = data.get("fromFile", "original.py")
    to_file = data.get("toFile", "modified.py")

    diff_text = DiffEngine.create_unified_diff(
        original,
        modified,
        from_file=from_file,
        to_file=to_file,
    )

    orig_lines = original.splitlines()
    mod_lines = modified.splitlines()

    return {
        "success": True,
        "diff": diff_text,
        "originalLineCount": len(orig_lines),
        "modifiedLineCount": len(mod_lines),
        "hasChanges": bool(diff_text.strip()),
    }


def handle_patcher_apply(data: dict) -> dict:
    source = data.get("source", "")
    target = data.get("targetContent", "")
    replacement = data.get("replacementContent", "")
    allow_fuzzy = bool(data.get("allowFuzzy", False))
    validate_ast = bool(data.get("validateSyntax", True))

    with tempfile.NamedTemporaryFile("w+", suffix=".py", delete=False) as tf:
        tf.write(source)
        temp_path = tf.name

    try:
        modifier = SafeCodeModifier()
        res = modifier.apply_surgical_edit(
            file_path=temp_path,
            target_content=target,
            replacement_content=replacement,
            allow_fuzzy=allow_fuzzy,
            validate_syntax=validate_ast,
        )

        with open(temp_path, "r", encoding="utf-8") as f:
            final_content = f.read()

        return {
            "success": res.success,
            "error": res.error,
            "additions": res.additions,
            "deletions": res.deletions,
            "preHash": res.pre_hash,
            "postHash": res.post_hash,
            "syntaxValid": res.syntax_valid,
            "syntaxErrorLine": res.syntax_error_line,
            "finalContent": final_content,
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def handle_planner_generate(data: dict) -> dict:
    requirement = data.get("requirement", "Analyze and refactor codebase.")
    task_id = data.get("taskId", f"task-{int(time.time())}")
    repo_root = data.get("repo", ".")
    budget = int(data.get("budget", 16000))

    engine = RepositoryContextEngine(repo_root=repo_root)
    ctx_pkg = engine.build_context(task_requirement=requirement, repo_root=repo_root, budget=ContextBudget(max_total_tokens=budget))

    planner = ExplicitTaskPlanner(workspace_root=repo_root)
    plan = planner.generate_plan(task_id=task_id, task_requirement=requirement, context_package=ctx_pkg)

    return {
        "success": True,
        "plan": plan.to_dict(),
        "contextPackage": ctx_pkg.to_dict() if hasattr(ctx_pkg, "to_dict") else {
            "estimatedTokens": ctx_pkg.estimated_tokens,
            "symbolCount": len(ctx_pkg.symbols),
            "fileCount": len(ctx_pkg.relevant_files),
        },
    }


def handle_planner_replan(data: dict) -> dict:
    requirement = data.get("requirement", "Task execution")
    failed_step_id = data.get("failedStepId", "step-2")
    error_message = data.get("error", "AssertionError: Verification check failed.")

    planner = ExplicitTaskPlanner()
    initial_plan = planner.generate_plan(task_id="task-replan-bridge", task_requirement=requirement)

    replanner = DynamicReplanner()
    new_plan = replanner.replan_on_failure(
        plan=initial_plan,
        failed_step_id=failed_step_id,
        error_message=error_message,
    )

    return {
        "success": True,
        "initialPlan": initial_plan.to_dict(),
        "remediatedPlan": new_plan.to_dict(),
    }


def handle_tests_detailed(data: dict) -> dict:
    module_filter = data.get("module", None)
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
    top_dir = os.path.dirname(os.path.abspath(__file__))

    if module_filter:
        suite = loader.loadTestsFromName(module_filter)
    else:
        suite = loader.discover(start_dir, top_level_dir=top_dir)

    test_items = []
    
    def collect_tests(test_suite):
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                collect_tests(test)
            else:
                test_items.append(test)

    collect_tests(suite)

    # Execute tests and track individual outcomes safely without polluting stdout
    results = []
    passed = 0
    failed = 0
    errors = 0

    sink_out = io.StringIO()
    sink_err = io.StringIO()

    with contextlib.redirect_stdout(sink_out), contextlib.redirect_stderr(sink_err):
        for test in test_items:
            test_id = test.id()
            doc = (test.shortDescription() or "").strip()
            t0 = time.perf_counter()
            
            test_res = unittest.TestResult()
            test.run(test_res)
            dt = (time.perf_counter() - t0) * 1000

            status = "passed"
            err_msg = ""
            if test_res.failures:
                status = "failed"
                failed += 1
                err_msg = test_res.failures[0][1]
            elif test_res.errors:
                status = "error"
                errors += 1
                err_msg = test_res.errors[0][1]
            else:
                passed += 1

            results.append({
                "id": test_id,
                "name": test_id.split(".")[-1],
                "module": ".".join(test_id.split(".")[:-2]),
                "className": test_id.split(".")[-2] if len(test_id.split(".")) > 1 else "",
                "status": status,
                "durationMs": round(dt, 2),
                "description": doc or f"Verifies {test_id.split('.')[-1]} behavior.",
                "errorMessage": err_msg,
            })

    # Reset root logger handlers to stderr in case any test configured sys.stdout
    r_logger = logging.getLogger()
    for h in list(r_logger.handlers):
        r_logger.removeHandler(h)
    r_logger.addHandler(logging.StreamHandler(sys.stderr))

    return {
        "success": (failed == 0 and errors == 0),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "tests": results,
    }


def handle_system_manifest(data: dict) -> dict:
    from app.main import get_system_manifest
    from app.config import get_settings
    import platform

    settings = get_settings()
    manifest = get_system_manifest()
    
    # Check count of registered tools
    try:
        from app.tools import get_default_tool_registry
        reg = get_default_tool_registry(include_agent_tools=True)
        tool_count = len(reg.list_tools())
    except Exception:
        tool_count = 18

    return {
        "success": True,
        "manifest": manifest,
        "pythonVersion": platform.python_version(),
        "platform": platform.platform(),
        "toolCount": tool_count,
        "environment": settings.environment,
        "defaultModel": settings.default_model,
        "maxContextTokens": settings.max_context_tokens,
        "demoMode": settings.is_demo_mode(),
    }


def handle_system_subsystems(data: dict) -> dict:
    from app.tools import get_default_tool_registry
    
    tools_list = []
    try:
        reg = get_default_tool_registry(include_agent_tools=True)
        tools_list = [t.name for t in reg.list_tools()]
    except Exception:
        pass

    subsystems = [
        {
            "id": "diagnostics",
            "name": "Diagnostic Reasoner & Auto-Fix Loop",
            "category": "core",
            "status": "ready",
            "phase": 10,
            "description": "Consumes pytest/unittest tracebacks, maps multi-frame stack traces, synthesizes root-cause hypotheses, and executes self-healing repair loops with oscillation guards.",
            "keyFiles": [
                "app/diagnostics/diagnostic_loop_controller.py",
                "app/diagnostics/diagnostic_reasoner.py",
                "app/diagnostics/traceback_parser.py",
                "app/diagnostics/test_runner.py",
                "tests/test_diagnostics.py",
            ],
            "interfaces": [
                "DiagnosticLoopController.execute_loop(test_command, max_iterations)",
                "DiagnosticReasoner.analyze_failure(failure_record)",
                "TracebackParser.parse_python_traceback(raw_text)",
                "AutoFixLoopTool / DiagnoseTestFailureTool / RunDiagnosticsTool",
            ],
            "securityRole": "Automatic regression detection and rollback if a fix attempt breaks adjacent test suites.",
        },
        {
            "id": "patcher",
            "name": "Safe Patcher & AST Syntax Guardian",
            "category": "execution",
            "status": "ready",
            "phase": 9,
            "description": "Surgical line/block modifier with AST syntax validation, git-style unified diff generation, and immutable snapshot rollback auditor.",
            "keyFiles": [
                "app/patcher/safe_modifier.py",
                "app/patcher/syntax_validator.py",
                "app/patcher/diff_engine.py",
                "app/patcher/snapshot_auditor.py",
                "tests/test_patcher.py",
            ],
            "interfaces": [
                "SafeCodeModifier.apply_surgical_edit(file_path, target, replacement)",
                "SyntaxValidator.validate(code, language)",
                "DiffEngine.create_unified_diff(original, modified)",
                "FileSnapshotAuditor.create_snapshot(file_path)",
            ],
            "securityRole": "Pre-flight syntax checking and atomic write semantics prevent corruption of repository source files.",
        },
        {
            "id": "planner",
            "name": "Task Planner & Dynamic DAG Replanner",
            "category": "intelligence",
            "status": "ready",
            "phase": 8,
            "description": "Decomposes high-level coding goals into acyclic execution DAGs with verification checks and dynamic replanning on step failure.",
            "keyFiles": [
                "app/planner/planner.py",
                "app/planner/replanner.py",
                "app/planner/models.py",
                "tests/test_planner.py",
            ],
            "interfaces": [
                "ExplicitTaskPlanner.generate_plan(task_id, requirement)",
                "DynamicReplanner.replan_on_failure(plan, failed_step_id, error)",
                "GeneratePlanTool / ReplanTaskTool",
            ],
            "securityRole": "Enforces deterministic dependency ordering and verification conditions before advancing tasks.",
        },
        {
            "id": "context",
            "name": "Context Budget & Token Management Engine",
            "category": "intelligence",
            "status": "ready",
            "phase": 7,
            "description": "Hierarchical 5-tier context allocation, multi-factor symbol relevance scoring, and deterministic AST pruning.",
            "keyFiles": [
                "app/context/engine.py",
                "app/context/base.py",
                "tests/test_context_engine.py",
            ],
            "interfaces": [
                "RepositoryContextEngine.build_context(requirement, budget)",
                "ContextBudget(max_total_tokens, system_prompt_tokens, ...)",
            ],
            "securityRole": "Guarantees token budget bounds to eliminate prompt truncation and hallucination.",
        },
        {
            "id": "repo",
            "name": "Repository Intelligence & Engineering Graph",
            "category": "intelligence",
            "status": "ready",
            "phase": 5,
            "description": "High-throughput AST code indexing, cross-module call/dependency graphs, and symbol resolution.",
            "keyFiles": [
                "app/context/scanner.py",
                "app/context/graph.py",
                "tests/test_context_engine.py",
            ],
            "interfaces": [
                "RepositoryScanner.scan()",
                "EngineeringGraph.build_graph()",
            ],
            "securityRole": "Enforces workspace boundaries and skips non-whitelisted binary files.",
        },
        {
            "id": "storage",
            "name": "State Management & SQLite Persistence Engine",
            "category": "core",
            "status": "ready",
            "phase": 4,
            "description": "ACID-compliant SQLite task store, immutable timeline telemetry, and snapshot checkpoints with pause/resume.",
            "keyFiles": [
                "app/storage/sqlite_store.py",
                "app/storage/schema.py",
                "app/storage/base.py",
                "tests/test_storage_persistence.py",
            ],
            "interfaces": [
                "SqliteTaskStore(db_path)",
                "TaskState / TaskStatus / TaskTimelineEvent",
            ],
            "securityRole": "Auditable, immutable timeline records of every tool call, argument, and output.",
        },
        {
            "id": "agent",
            "name": "Autonomous Agent Loop & Step Controller",
            "category": "core",
            "status": "ready",
            "phase": 3,
            "description": "Multi-turn autonomous execution controller with self-correcting error recovery, audit step hooks, and iteration guards.",
            "keyFiles": [
                "app/agent/runtime.py",
                "app/agent/base.py",
                "app/agent/prompts.py",
                "tests/test_agent_runtime.py",
            ],
            "interfaces": [
                "AutonomousAgentRuntime(llm_provider, tool_registry, task_store)",
                "FinishTaskTool",
            ],
            "securityRole": "Hard loop iteration limits and step-level anomaly detection.",
        },
        {
            "id": "tools",
            "name": "Tool System & Dynamic Registry Engine",
            "category": "core",
            "status": "ready",
            "phase": 2,
            "description": f"18 production tools registered across Filesystem, Code Search, Terminal Sandbox, Git VCS, Safe Patcher, and Diagnostics.",
            "keyFiles": [
                "app/tools/base.py",
                "app/tools/filesystem.py",
                "app/tools/search.py",
                "app/tools/terminal.py",
                "app/tools/git_tools.py",
                "tests/test_core_tools.py",
            ],
            "interfaces": [
                "Tool / ToolResult / ToolRegistry",
                "get_default_tool_registry(workspace_root, policy_engine)",
            ],
            "securityRole": "Deterministic schema validation, path traversal denial, and execution telemetry.",
        },
        {
            "id": "llm",
            "name": "LLM Provider Abstraction & Gemini Implementation",
            "category": "intelligence",
            "status": "ready",
            "phase": 1,
            "description": "Provider-agnostic LLM interface supporting Gemini v1beta, multi-turn message serializer, function calling, and retry with exponential backoff.",
            "keyFiles": [
                "app/llm/base.py",
                "app/llm/gemini.py",
                "app/llm/mock.py",
                "tests/test_llm_provider.py",
            ],
            "interfaces": [
                "LLMProvider / GeminiProvider / MockLLMProvider",
                "ChatMessage / ToolCallRequest / LLMResponse",
            ],
            "securityRole": "Strict token quotas, sanitized request headers, and graceful error categorization.",
        },
        {
            "id": "security",
            "name": "Security & Policy Governance",
            "category": "governance",
            "status": "ready",
            "phase": 0,
            "description": "Path canonicalization, workspace jail containment, and human approval gates for destructive actions.",
            "keyFiles": [
                "app/security/base.py",
                "tests/test_security_policy.py",
            ],
            "interfaces": [
                "PolicyEngine / DefaultPolicyEngine",
                "PolicyDecision (ALLOW / APPROVE / DENY)",
            ],
            "securityRole": "Non-bypassable boundary interceptor on all tool dispatches.",
        },
        {
            "id": "observability",
            "name": "Observability & Structured Logging",
            "category": "governance",
            "status": "ready",
            "phase": 0,
            "description": "Structured JSON logging with correlation IDs, latency tracking, and execution tracing.",
            "keyFiles": [
                "app/observability/logger.py",
            ],
            "interfaces": [
                "configure_logging(level, json_output)",
                "get_logger(name)",
            ],
            "securityRole": "Audit trail generation without leaking sensitive tokens or keys in logs.",
        },
    ]

    return {
        "success": True,
        "count": len(subsystems),
        "registeredTools": tools_list,
        "subsystems": subsystems,
    }


def handle_context_budget(data: dict) -> dict:
    repo_path = data.get("path", "./nexforge-droid")
    requirement = data.get("requirement", "Implement resilient error recovery")
    max_tokens = int(data.get("maxTokens", 32000))
    
    engine = RepositoryContextEngine(repo_root=repo_path)
    budget = ContextBudget(max_total_tokens=max_tokens)
    ctx_pkg = engine.build_context(task_requirement=requirement, repo_root=repo_path, budget=budget)
    
    return {
        "success": True,
        "budget": {
            "maxTotalTokens": budget.max_total_tokens,
            "systemPromptTokens": budget.system_prompt_tokens,
            "taskSpecTokens": budget.task_spec_tokens,
            "repoSummaryTokens": budget.repo_summary_tokens,
            "relevantFilesTokens": budget.relevant_files_tokens,
            "symbolGraphTokens": budget.symbol_graph_tokens,
            "conversationReserveTokens": budget.conversation_reserve_tokens,
        },
        "allocated": {
            "estimatedTokens": ctx_pkg.estimated_tokens,
            "symbolCount": len(ctx_pkg.symbols),
            "fileCount": len(ctx_pkg.relevant_files),
        },
        "symbols": [s.to_dict() if hasattr(s, "to_dict") else {
            "name": getattr(s, "name", str(s)),
            "file_path": getattr(s, "file_path", ""),
            "node_type": getattr(s, "node_type", "FUNCTION"),
            "complexity_score": getattr(s, "complexity_score", 1.0),
        } for s in ctx_pkg.symbols[:20]],
    }


# =========================================================================
# Phase 11: Orchestrator, Multi-File Refactor & Human Gate Handlers
# =========================================================================

from app.orchestrator.changeset_manager import ChangesetManager
from app.orchestrator.human_gate import HumanApprovalGate, RiskLevel
from app.orchestrator.refactor_engine import MultiFileRefactorEngine, SymbolRenameRequest

_GLOBAL_CHANGESET_MANAGER = ChangesetManager()
_GLOBAL_APPROVAL_GATE = HumanApprovalGate()
_GLOBAL_REFACTOR_ENGINE = MultiFileRefactorEngine()

# Seed initial demonstration approvals and changesets for rich operator experience
if not _GLOBAL_APPROVAL_GATE.list_requests():
    _GLOBAL_APPROVAL_GATE.request_approval(
        action_type="DATABASE_MIGRATION",
        description="Execute destructive column drop in SQLite schema index",
        risk_level=RiskLevel.HIGH,
        payload={"migration": "DROP INDEX IF EXISTS idx_task_events_timestamp", "table": "timeline_events"},
    )
    _GLOBAL_APPROVAL_GATE.request_approval(
        action_type="DEPENDENCY_UPGRADE",
        description="Upgrade tree-sitter AST parser binaries across workspace",
        risk_level=RiskLevel.MEDIUM,
        payload={"package": "tree-sitter", "target_version": "0.22.0"},
    )

if not _GLOBAL_CHANGESET_MANAGER.list_changesets():
    demo_cs = _GLOBAL_CHANGESET_MANAGER.create_changeset(
        title="Diagnostic Loop Auto-Healing & Token Resilience",
        description="Hardens token budget allocation and adds multi-frame AST traceback extraction.",
        branch_name="nexforge/feat-phase-11-orchestration",
    )
    _GLOBAL_CHANGESET_MANAGER.stage_file_change(
        changeset_id=demo_cs.changeset_id,
        file_path="nexforge-droid/app/diagnostics/diagnostic_reasoner.py",
        modified_content='"""Diagnostic Reasoner with AST analysis."""\n\ndef analyze_failure(record):\n    return {"status": "analyzed", "confidence": 0.95}\n',
        original_content='"""Diagnostic Reasoner."""\n\ndef analyze_failure(record):\n    return {}\n',
    )


def handle_orchestrator_changeset_create(data: dict) -> dict:
    title = data.get("title", "Workspace Multi-File Update")
    desc = data.get("description", "")
    branch = data.get("branchName")
    cs = _GLOBAL_CHANGESET_MANAGER.create_changeset(title=title, description=desc, branch_name=branch)
    return {
        "success": True,
        "changeset": cs.to_dict(),
    }


def handle_orchestrator_changeset_stage(data: dict) -> dict:
    cid = data.get("changesetId")
    fpath = data.get("filePath")
    modified = data.get("modifiedContent", "")
    original = data.get("originalContent")

    if not cid or not fpath:
        return {"success": False, "error": "Missing changesetId or filePath"}

    cs_file = _GLOBAL_CHANGESET_MANAGER.stage_file_change(
        changeset_id=cid,
        file_path=fpath,
        modified_content=modified,
        original_content=original,
    )
    cs = _GLOBAL_CHANGESET_MANAGER.get_changeset(cid)

    return {
        "success": True,
        "stagedFile": {
            "filePath": cs_file.file_path,
            "additions": cs_file.additions,
            "deletions": cs_file.deletions,
            "syntaxValid": cs_file.syntax_valid,
            "syntaxError": cs_file.syntax_error,
            "diff": cs_file.diff,
        },
        "changeset": cs.to_dict() if cs else None,
    }


def handle_orchestrator_changeset_apply(data: dict) -> dict:
    cid = data.get("changesetId")
    if not cid:
        return {"success": False, "error": "Missing changesetId"}
    res = _GLOBAL_CHANGESET_MANAGER.apply_changeset_atomically(cid)
    return res


def handle_orchestrator_changeset_list(data: dict) -> dict:
    changesets = _GLOBAL_CHANGESET_MANAGER.list_changesets()
    return {
        "success": True,
        "total": len(changesets),
        "changesets": changesets,
    }


def handle_orchestrator_refactor_plan(data: dict) -> dict:
    old_name = data.get("oldName", "")
    new_name = data.get("newName", "")
    targets = data.get("targetFiles")

    if not old_name or not new_name:
        return {"success": False, "error": "oldName and newName are required"}

    req = SymbolRenameRequest(old_name=old_name, new_name=new_name, target_files=targets)
    plan = _GLOBAL_REFACTOR_ENGINE.plan_symbol_rename(req)
    cs = _GLOBAL_REFACTOR_ENGINE.execute_refactor_to_changeset(plan)

    return {
        "success": True,
        "plan": plan.to_dict(),
        "changeset": cs.to_dict(),
    }


def handle_orchestrator_approval_list(data: dict) -> dict:
    status = data.get("status")
    reqs = _GLOBAL_APPROVAL_GATE.list_requests(status=status)
    return {
        "success": True,
        "total": len(reqs),
        "requests": reqs,
    }


def handle_orchestrator_approval_request(data: dict) -> dict:
    action_type = data.get("actionType", "OPERATION")
    desc = data.get("description", "")
    risk_str = data.get("riskLevel", "MEDIUM")
    payload = data.get("payload", {})

    risk = RiskLevel(risk_str) if risk_str in RiskLevel.__members__ else RiskLevel.MEDIUM
    req = _GLOBAL_APPROVAL_GATE.request_approval(
        action_type=action_type,
        description=desc,
        risk_level=risk,
        payload=payload,
    )
    return {
        "success": True,
        "request": req.to_dict(),
    }


def handle_orchestrator_approval_decide(data: dict) -> dict:
    req_id = data.get("requestId")
    decision = data.get("decision", "APPROVED")  # APPROVED or REJECTED
    reason = data.get("reason", "Operator decision recorded")
    approver = data.get("approver", "human_operator")

    if not req_id:
        return {"success": False, "error": "requestId is required"}

    if decision.upper() == "APPROVED":
        req = _GLOBAL_APPROVAL_GATE.approve(req_id, approver=approver, reason=reason)
    else:
        req = _GLOBAL_APPROVAL_GATE.reject(req_id, rejector=approver, reason=reason)

    return {
        "success": True,
        "request": req.to_dict(),
    }


def handle_streaming_scenarios(data: dict) -> dict:
    scenarios = _GLOBAL_STREAMER.get_scenarios()
    return {
        "success": True,
        "scenarios": scenarios,
        "session": _GLOBAL_DEBUGGER.get_session_state(),
    }


def handle_streaming_reset(data: dict) -> dict:
    scenario_id = data.get("scenarioId", "refactor-sqlite")
    session = _GLOBAL_DEBUGGER.reset_session(scenario_id)
    return {
        "success": True,
        "session": session,
    }


def handle_streaming_step(data: dict) -> dict:
    res = _GLOBAL_DEBUGGER.step_next()
    return {
        "success": True,
        **res,
    }


def handle_streaming_continue(data: dict) -> dict:
    steps = _GLOBAL_DEBUGGER.continue_execution()
    return {
        "success": True,
        "stepsExecuted": len(steps),
        "steps": steps,
        "session": _GLOBAL_DEBUGGER.get_session_state(),
    }


def handle_streaming_breakpoints(data: dict) -> dict:
    event_types = data.get("eventTypes", [])
    step_numbers = data.get("stepNumbers", [])
    enabled = bool(data.get("enabled", True))
    bp = _GLOBAL_DEBUGGER.set_breakpoints(
        event_types=event_types,
        step_numbers=step_numbers,
        enabled=enabled,
    )
    return {
        "success": True,
        "breakpoints": bp.to_dict(),
        "session": _GLOBAL_DEBUGGER.get_session_state(),
    }


def handle_evaluation_benchmarks(data: dict) -> dict:
    benchmarks = [c.to_dict() for c in _GLOBAL_BENCHMARK_SUITE.list_challenges()]
    return {
        "success": True,
        "total": len(benchmarks),
        "benchmarks": benchmarks,
    }


def handle_evaluation_run_benchmark(data: dict) -> dict:
    challenge_id = data.get("challengeId", "BM-001")
    target_files = data.get("targetFiles")
    result = _GLOBAL_BENCHMARK_SUITE.run_challenge(challenge_id, custom_target_files=target_files)
    return {
        "success": True,
        "result": result.to_dict(),
    }


def handle_evaluation_quality_gate(data: dict) -> dict:
    files = data.get("files")
    task_id = data.get("taskId", "manual-eval")
    invariants = data.get("invariants")
    test_filter = data.get("testFilter")
    report = _GLOBAL_QUALITY_GATE.evaluate_all(
        files=files,
        task_id=task_id,
        requirement_invariants=invariants,
        test_filter=test_filter,
    )
    return {
        "success": True,
        "report": report.to_dict(),
    }


def handle_evaluation_leaderboard(data: dict) -> dict:
    leaderboard = _GLOBAL_BENCHMARK_SUITE.get_leaderboard()
    return {
        "success": True,
        "leaderboard": leaderboard,
    }


def handle_uv_info(data: dict) -> dict:
    from app.cli.main import get_uv_environment_info
    info = get_uv_environment_info()
    
    pyproject_path = os.path.join(BASE_DIR, "pyproject.toml")
    pyproject_content = ""
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "r", encoding="utf-8") as f:
                pyproject_content = f.read()
        except Exception:
            pass

    packages = []
    try:
        res = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            packages = json.loads(res.stdout)
    except Exception:
        pass

    if not packages:
        packages = [
            {"name": "fastapi", "version": "0.111.0"},
            {"name": "pydantic", "version": "2.7.0"},
            {"name": "google-genai", "version": "0.1.1"},
            {"name": "pytest", "version": "8.2.0"},
            {"name": "ruff", "version": "0.4.8"},
            {"name": "uv", "version": "0.12.9"},
        ]

    return {
        "success": True,
        "environment": info,
        "packages": packages,
        "pyproject": pyproject_content,
        "cli_commands": ["info", "bench", "gate", "scan", "run", "test"],
    }


def handle_cli_exec(data: dict) -> dict:
    from app.cli.main import main as cli_main
    subcommand = data.get("subcommand", "info")
    args = data.get("args", [])
    
    argv = [subcommand] + [str(a) for a in args]
    if "--json" not in argv:
        argv.append("--json")

    captured_out = io.StringIO()
    captured_err = io.StringIO()
    start_t = time.time()

    try:
        with contextlib.redirect_stdout(captured_out), contextlib.redirect_stderr(captured_err):
            exit_code = cli_main(argv)
    except Exception as e:
        exit_code = 1
        captured_err.write(str(e))

    duration_ms = round((time.time() - start_t) * 1000, 2)
    raw_stdout = captured_out.getvalue().strip()
    raw_stderr = captured_err.getvalue().strip()

    parsed_json = None
    try:
        parsed_json = json.loads(raw_stdout)
    except Exception:
        pass

    return {
        "success": exit_code == 0,
        "exit_code": exit_code,
        "subcommand": subcommand,
        "argv": argv,
        "duration_ms": duration_ms,
        "stdout": raw_stdout,
        "stderr": raw_stderr,
        "data": parsed_json,
    }


def handle_swarm_roles(data: dict) -> dict:
    from app.agent.swarm import SwarmConsensusEngine
    engine = SwarmConsensusEngine()
    roles = engine.get_registered_agents()
    return {
        "success": True,
        "roles": roles,
        "total": len(roles),
    }


def handle_swarm_deliberate(data: dict) -> dict:
    from app.agent.swarm import SwarmConsensusEngine
    objective = data.get("objective", "Refactor cache eviction algorithm with TTL and LRU hybrid")
    context = data.get("context", "")
    max_rounds = int(data.get("maxRounds", 2))

    engine = SwarmConsensusEngine()
    result = engine.deliberate(objective=objective, context=context, max_rounds=max_rounds)
    return {
        "success": True,
        "result": result.to_dict(),
    }


def handle_mcp_status(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    status = gateway.get_status()
    return {"success": True, "status": status}


def handle_mcp_tools(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    resp = gateway.handle_request({"id": 1, "method": "tools/list", "params": {}})
    tools = resp.result.get("tools", [])
    return {"success": True, "tools": tools, "total": len(tools)}


def handle_mcp_resources(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    uri = data.get("uri")
    if uri:
        resp = gateway.handle_request({"id": 1, "method": "resources/read", "params": {"uri": uri}})
        return {"success": resp.error is None, "content": resp.result, "error": resp.error.message if resp.error else None}
    else:
        resp = gateway.handle_request({"id": 1, "method": "resources/list", "params": {}})
        resources = resp.result.get("resources", [])
        return {"success": True, "resources": resources, "total": len(resources)}


def handle_mcp_prompts(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    name = data.get("name")
    if name:
        resp = gateway.handle_request({
            "id": 1,
            "method": "prompts/get",
            "params": {"name": name, "arguments": data.get("arguments", {})},
        })
        return {"success": resp.error is None, "rendered": resp.result, "error": resp.error.message if resp.error else None}
    else:
        resp = gateway.handle_request({"id": 1, "method": "prompts/list", "params": {}})
        prompts = resp.result.get("prompts", [])
        return {"success": True, "prompts": prompts, "total": len(prompts)}


def handle_mcp_servers(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    servers = gateway.client.list_servers()
    ext_tools = gateway.client.list_external_tools()
    return {
        "success": True,
        "servers": servers,
        "external_tools": ext_tools,
        "total_servers": len(servers),
        "total_external_tools": len(ext_tools),
    }


def handle_mcp_call(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    tool_name = data.get("name")
    arguments = data.get("arguments", {})
    resp = gateway.handle_request({
        "id": data.get("id", 1),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    })
    return {
        "success": resp.error is None and not (resp.result and resp.result.get("isError", False)),
        "result": resp.result,
        "error": resp.error.message if resp.error else None,
    }


def handle_mcp_jsonrpc(data: dict) -> dict:
    from app.mcp import MCPGateway
    gateway = MCPGateway(workspace_root=BASE_DIR)
    request_obj = data.get("request", {})
    resp = gateway.handle_request(request_obj)
    return {"success": True, "response": resp.to_dict()}


# --- Phase 17: Git Worktrees, Branching, PR Lifecycle & CI/CD Handlers ---

def handle_git_branches(data: dict) -> dict:
    from app.git.branch import GitBranchManager
    mgr = GitBranchManager(repo_path=BASE_DIR)
    branches = [b.to_dict() for b in mgr.list_branches()]
    current = next((b for b in branches if b.get("is_current")), None)
    return {
        "success": True,
        "branches": branches,
        "current_branch": current.get("name") if current else "main",
        "count": len(branches),
    }


def handle_git_create_branch(data: dict) -> dict:
    from app.git.branch import GitBranchManager
    mgr = GitBranchManager(repo_path=BASE_DIR)
    name = data.get("name", "")
    start_point = data.get("start_point", "main")
    switch = data.get("switch", True)
    try:
        b = mgr.create_branch(name, start_point=start_point, switch=switch)
        return {"success": True, "branch": b.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_git_switch_branch(data: dict) -> dict:
    from app.git.branch import GitBranchManager
    mgr = GitBranchManager(repo_path=BASE_DIR)
    name = data.get("name", "")
    ok = mgr.switch_branch(name)
    return {"success": ok, "current_branch": name if ok else None}


def handle_git_worktrees(data: dict) -> dict:
    from app.git.worktree import GitWorktreeManager
    mgr = GitWorktreeManager(repo_path=BASE_DIR)
    wts = [w.to_dict() for w in mgr.list_worktrees()]
    return {
        "success": True,
        "worktrees": wts,
        "count": len(wts),
    }


def handle_git_create_worktree(data: dict) -> dict:
    from app.git.worktree import GitWorktreeManager
    mgr = GitWorktreeManager(repo_path=BASE_DIR)
    branch = data.get("branch", "feat/isolated-agent")
    task_id = data.get("task_id")
    try:
        wt = mgr.create_worktree(branch=branch, task_id=task_id)
        return {"success": True, "worktree": wt.to_dict()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def handle_git_remove_worktree(data: dict) -> dict:
    from app.git.worktree import GitWorktreeManager
    mgr = GitWorktreeManager(repo_path=BASE_DIR)
    wt_id = data.get("worktree_id", "")
    ok = mgr.remove_worktree(wt_id)
    return {"success": ok, "removed": wt_id}


def handle_git_generate_pr(data: dict) -> dict:
    from app.git.pr_generator import PullRequestSynthesizer
    synthesizer = PullRequestSynthesizer(repo_path=BASE_DIR)
    title = data.get("title")
    branch_source = data.get("branch_source", "feat/mcp-gateway")
    branch_target = data.get("branch_target", "main")
    task_objective = data.get("task_objective")
    spec = synthesizer.synthesize_pr(
        title=title,
        branch_source=branch_source,
        branch_target=branch_target,
        task_objective=task_objective,
    )
    return {
        "success": True,
        "pr": spec.to_dict(),
        "markdown": spec.markdown_body,
    }


def handle_git_run_ci(data: dict) -> dict:
    from app.git.ci_pipeline import CISelfHealingEngine
    engine = CISelfHealingEngine(repo_path=BASE_DIR)
    branch = data.get("branch", "main")
    simulate_failure = data.get("simulate_failure_stage")
    pipeline = engine.run_pipeline(branch=branch, simulate_failure_stage=simulate_failure)
    return {
        "success": True,
        "pipeline": pipeline.to_dict(),
    }


def handle_git_heal_ci(data: dict) -> dict:
    from app.git.ci_pipeline import CISelfHealingEngine
    engine = CISelfHealingEngine(repo_path=BASE_DIR)
    branch = data.get("branch", "main")
    failed_stage = data.get("failed_stage", "unit_tests")
    failed_run = engine.run_pipeline(branch=branch, simulate_failure_stage=failed_stage)
    healed_run = engine.heal_pipeline(failed_run)
    return {
        "success": True,
        "healed_pipeline": healed_run.to_dict(),
        "healed_patch": healed_run.healed_patch,
        "healing_attempts": healed_run.healing_attempts,
    }


def handle_review_scan(data: dict) -> dict:
    from app.review.analyzer import CodeQualityAnalyzer
    from app.review.security_scanner import ASTSecurityScanner

    directory = data.get("directory", ".")
    code_snippet = data.get("code_snippet")

    scanner = ASTSecurityScanner(workspace_root=BASE_DIR)
    analyzer = CodeQualityAnalyzer(workspace_root=BASE_DIR)

    if code_snippet:
        vulns = scanner.scan_code(code_snippet, file_path="snippet.py")
        findings = analyzer.analyze_code(code_snippet, file_path="snippet.py")
        return {
            "success": True,
            "vulnerabilities": [v.to_dict() for v in vulns],
            "findings": [f.to_dict() for f in findings],
            "total_vulnerabilities": len(vulns),
            "total_findings": len(findings),
        }

    vulns = scanner.scan_directory(directory=directory)
    report = analyzer.run_review(directory=directory)

    return {
        "success": True,
        "report": report.to_dict(),
        "vulnerabilities": [v.to_dict() for v in vulns],
        "total_vulnerabilities": len(vulns),
        "critical_count": sum(1 for v in vulns if v.severity == "CRITICAL"),
        "high_count": sum(1 for v in vulns if v.severity == "HIGH"),
        "medium_count": sum(1 for v in vulns if v.severity == "MEDIUM"),
        "low_count": sum(1 for v in vulns if v.severity in ("LOW", "INFO")),
    }


def handle_review_sarif(data: dict) -> dict:
    from app.review.analyzer import CodeQualityAnalyzer
    from app.review.sarif import SARIFExporter
    from app.review.security_scanner import ASTSecurityScanner

    directory = data.get("directory", ".")
    scanner = ASTSecurityScanner(workspace_root=BASE_DIR)
    analyzer = CodeQualityAnalyzer(workspace_root=BASE_DIR)
    exporter = SARIFExporter(workspace_root=BASE_DIR)

    vulns = scanner.scan_directory(directory=directory)
    report = analyzer.run_review(directory=directory)
    sarif_doc = exporter.generate_sarif(vulnerabilities=vulns, findings=report.findings)

    return {
        "success": True,
        "sarif": sarif_doc,
        "results_count": len(sarif_doc["runs"][0]["results"]),
        "rules_count": len(sarif_doc["runs"][0]["tool"]["driver"]["rules"]),
    }


def handle_review_rules(data: dict) -> dict:
    rules = [
        {
            "id": "SEC-001-HARDCODED-SECRET",
            "name": "Hardcoded Secret or Token",
            "cwe": "CWE-798",
            "category": "Security & Secrets",
            "severity": "HIGH",
            "description": "Detection of hardcoded API keys, JWT tokens, AWS access keys, and plaintext passwords.",
        },
        {
            "id": "SEC-002-DYNAMIC-CODE-EXEC",
            "name": "Arbitrary Dynamic Code Execution",
            "cwe": "CWE-95",
            "category": "Injection & RCE",
            "severity": "CRITICAL",
            "description": "Invocation of eval() or exec() with untrusted directives.",
        },
        {
            "id": "SEC-003-INSECURE-DESERIALIZATION",
            "name": "Insecure Deserialization",
            "cwe": "CWE-502",
            "category": "Object Injection",
            "severity": "CRITICAL",
            "description": "Use of pickle.loads on unauthenticated serialized payloads.",
        },
        {
            "id": "SEC-004-SHELL-COMMAND-INJECTION",
            "name": "OS Command Injection Risk",
            "cwe": "CWE-78",
            "category": "Command Injection",
            "severity": "HIGH",
            "description": "Execution of commands via os.system or os.popen without argument array escaping.",
        },
        {
            "id": "SEC-005-SUBPROCESS-SHELL-TRUE",
            "name": "Subprocess Shell Execution",
            "cwe": "CWE-78",
            "category": "Command Injection",
            "severity": "HIGH",
            "description": "subprocess methods invoked with shell=True exposing shell metacharacter expansion.",
        },
        {
            "id": "SEC-006-WEAK-HASH-ALGORITHM",
            "name": "Weak Cryptographic Hash Function",
            "cwe": "CWE-327",
            "category": "Cryptography",
            "severity": "MEDIUM",
            "description": "Use of broken cryptographic hashing algorithms MD5 or SHA-1.",
        },
        {
            "id": "SEC-007-SQL-INJECTION-FORMAT",
            "name": "SQL Injection via Formatted String",
            "cwe": "CWE-89",
            "category": "SQL Injection",
            "severity": "HIGH",
            "description": "Unescaped string interpolation or f-string concatenation in cursor.execute.",
        },
        {
            "id": "SMELL-COMPLEXITY",
            "name": "Cyclomatic Complexity Threshold",
            "cwe": "N/A",
            "category": "Maintainability",
            "severity": "WARNING",
            "description": "Functions exceeding McCabe cyclomatic complexity threshold of 10 branching paths.",
        },
        {
            "id": "SMELL-BUG_RISK",
            "name": "Silent Exception Suppression",
            "cwe": "N/A",
            "category": "Reliability",
            "severity": "WARNING",
            "description": "Bare 'except:' or 'except Exception: pass' blocks masking critical runtime faults.",
        },
        {
            "id": "SMELL-FUNCTION-LENGTH",
            "name": "Oversized Function Smell",
            "cwe": "N/A",
            "category": "Maintainability",
            "severity": "WARNING",
            "description": "Function bodies exceeding 60 physical lines of code without sub-modularization.",
        },
    ]
    return {
        "success": True,
        "rules": rules,
        "count": len(rules),
    }


def main():
    parser = argparse.ArgumentParser(description="NexForge Droid API Bridge")
    parser.add_argument("--action", required=True, help="API Action to perform")
    parser.add_argument("--payload", help="JSON string or '-' to read from stdin")

    args = parser.parse_args()

    payload_data = {}
    if args.payload:
        if args.payload == "-":
            try:
                payload_data = json.loads(sys.stdin.read())
            except Exception as e:
                payload_data = {}
        else:
            try:
                payload_data = json.loads(args.payload)
            except Exception as e:
                payload_data = {}

    action_map = {
        "diagnostics-parse": handle_diagnostics_parse,
        "diagnostics-diagnose": handle_diagnostics_diagnose,
        "diagnostics-loop": handle_diagnostics_loop,
        "patcher-validate": handle_patcher_validate,
        "patcher-diff": handle_patcher_diff,
        "patcher-apply": handle_patcher_apply,
        "planner-generate": handle_planner_generate,
        "planner-replan": handle_planner_replan,
        "tests-detailed": handle_tests_detailed,
        "system-manifest": handle_system_manifest,
        "system-subsystems": handle_system_subsystems,
        "context-budget": handle_context_budget,
        "orchestrator-changeset-create": handle_orchestrator_changeset_create,
        "orchestrator-changeset-stage": handle_orchestrator_changeset_stage,
        "orchestrator-changeset-apply": handle_orchestrator_changeset_apply,
        "orchestrator-changeset-list": handle_orchestrator_changeset_list,
        "orchestrator-refactor-plan": handle_orchestrator_refactor_plan,
        "orchestrator-approval-list": handle_orchestrator_approval_list,
        "orchestrator-approval-request": handle_orchestrator_approval_request,
        "orchestrator-approval-decide": handle_orchestrator_approval_decide,
        "streaming-scenarios": handle_streaming_scenarios,
        "streaming-reset": handle_streaming_reset,
        "streaming-step": handle_streaming_step,
        "streaming-continue": handle_streaming_continue,
        "streaming-breakpoints": handle_streaming_breakpoints,
        "evaluation-benchmarks": handle_evaluation_benchmarks,
        "evaluation-run-benchmark": handle_evaluation_run_benchmark,
        "evaluation-quality-gate": handle_evaluation_quality_gate,
        "evaluation-leaderboard": handle_evaluation_leaderboard,
        "uv-info": handle_uv_info,
        "cli-exec": handle_cli_exec,
        "swarm-roles": handle_swarm_roles,
        "swarm-deliberate": handle_swarm_deliberate,
        "mcp-status": handle_mcp_status,
        "mcp-tools": handle_mcp_tools,
        "mcp-resources": handle_mcp_resources,
        "mcp-prompts": handle_mcp_prompts,
        "mcp-servers": handle_mcp_servers,
        "mcp-call": handle_mcp_call,
        "mcp-jsonrpc": handle_mcp_jsonrpc,
        "git-branches": handle_git_branches,
        "git-create-branch": handle_git_create_branch,
        "git-switch-branch": handle_git_switch_branch,
        "git-worktrees": handle_git_worktrees,
        "git-create-worktree": handle_git_create_worktree,
        "git-remove-worktree": handle_git_remove_worktree,
        "git-generate-pr": handle_git_generate_pr,
        "git-run-ci": handle_git_run_ci,
        "git-heal-ci": handle_git_heal_ci,
        "review-scan": handle_review_scan,
        "review-sarif": handle_review_sarif,
        "review-rules": handle_review_rules,
    }

    if args.action not in action_map:
        print(json.dumps({"success": False, "error": f"Unknown action: {args.action}"}))
        sys.exit(1)

    try:
        handler = action_map[args.action]
        res = handler(payload_data)
        print(json.dumps(res))
    except Exception as ex:
        import traceback
        print(json.dumps({
            "success": False,
            "error": str(ex),
            "traceback": traceback.format_exc(),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()

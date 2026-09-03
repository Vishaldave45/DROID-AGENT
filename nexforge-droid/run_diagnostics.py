#!/usr/bin/env python3
"""CLI utility for test failure consumption, traceback diagnosis, and autonomous fix loops."""

import argparse
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.diagnostics.diagnostic_loop_controller import DiagnosticLoopController
from app.diagnostics.diagnostic_reasoner import DiagnosticReasoner
from app.diagnostics.test_runner import TestRunner
from app.diagnostics.traceback_parser import TracebackParser


def cmd_test(args):
    """Run test command and output structured diagnostic report."""
    runner = TestRunner()
    cmd = args.cmd or "python3 -m unittest discover -s ./tests -t ."
    print(f"=== Running Diagnostics: {cmd} ===")
    report = runner.run_command(cmd)

    print(f"Total Tests:  {report.total_tests}")
    print(f"Passed:       {report.passed_count}")
    print(f"Failed:       {report.failed_count}")
    print(f"Errors:       {report.error_count}")
    print(f"Skipped:      {report.skipped_count}")
    print(f"Duration:     {report.duration_seconds:.3f}s")
    print(f"All Passed:   {'YES' if report.all_passed else 'NO'}")

    if report.failures:
        print(f"\n--- Diagnostic Failures ({len(report.failures)}) ---")
        for i, f in enumerate(report.failures, 1):
            print(f"[{i}] {f.test_name} -> {f.error_type} ({f.category.value})")
            print(f"    Message: {f.error_message}")
            if f.innermost_frame:
                print(f"    Target:  {f.innermost_frame.file_path}:{f.innermost_frame.line_number} in {f.innermost_frame.function_name}()")
                if f.innermost_frame.code_snippet:
                    print(f"    Code:    {f.innermost_frame.code_snippet}")

    if not report.all_passed:
        sys.exit(1)


def cmd_parse(args):
    """Parse raw traceback into structured stack frames."""
    text = ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    failures = TracebackParser.parse_python_traceback(text)
    print(f"=== Parsed Failures ({len(failures)}) ===")
    for i, f in enumerate(failures, 1):
        print(f"\nFailure #{i}:")
        print(f"  Test:     {f.test_name}")
        print(f"  Type:     {f.error_type}")
        print(f"  Category: {f.category.value}")
        print(f"  Message:  {f.error_message}")
        print(f"  Frames:   {len(f.frames)}")
        for j, frame in enumerate(f.frames, 1):
            ws_tag = "[Workspace]" if frame.is_workspace_file else "[External]"
            print(f"    Frame {j} {ws_tag}: {frame.file_path}:{frame.line_number} in {frame.function_name}()")


def cmd_diagnose(args):
    """Perform root cause analysis and patch strategy generation."""
    text = ""
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    failures = TracebackParser.parse_python_traceback(text)
    if not failures:
        print("Error: Could not parse failure from traceback.", file=sys.stderr)
        sys.exit(1)

    reasoner = DiagnosticReasoner()
    print("=== Diagnostic Root Cause Analysis ===")
    for f in failures:
        hyp = reasoner.analyze_failure(f)
        print(f"\nFailure ID:    {hyp.failure_id}")
        print(f"Target Test:   {hyp.test_name}")
        print(f"Error Type:    {hyp.error_type} ({hyp.category})")
        print(f"Primary File:  {hyp.primary_file}:{hyp.target_line}")
        print(f"Strategy:      {hyp.suggested_fix_strategy}")
        print(f"Confidence:    {hyp.confidence_score * 100:.0f}%")
        print(f"Summary:       {hyp.root_cause_summary}")
        if hyp.suspect_symbols:
            print(f"Suspects:      {', '.join(hyp.suspect_symbols)}")
        if hyp.proposed_replacement_content:
            print(f"Proposed Fix:  {hyp.proposed_replacement_content}")


def cmd_autofix(args):
    """Execute autonomous test-observe-fix loop."""
    cmd = args.cmd or "python3 -m unittest discover -s ./tests -t ."
    controller = DiagnosticLoopController()

    print(f"=== Autonomous Test / Observe / Fix Diagnostic Loop ===")
    print(f"Command:        {cmd}")
    print(f"Max Iterations: {args.max_iter}")
    print(f"Auto Rollback:  {not args.no_rollback}")

    res = controller.execute_loop(
        test_command=cmd,
        max_iterations=args.max_iter,
        auto_rollback_on_regression=not args.no_rollback,
    )

    print(f"\nResult:         {'SUCCESS' if res.success else 'FAILED'}")
    print(f"Termination:    {res.termination_reason.value}")
    print(f"Iterations:     {res.total_iterations}")
    print(f"Initial Fails:  {res.initial_failures_count}")
    print(f"Final Fails:    {res.final_failures_count}")
    print(f"Snapshots:      {res.snapshots_taken}")
    print(f"Rollbacks:      {res.rollbacks_triggered}")
    print(f"Summary:        {res.summary}")

    if not res.success:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NexForge Droid Test & Diagnostic Loop CLI")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # test
    t_parser = subparsers.add_parser("test", help="Run tests and parse diagnostic report")
    t_parser.add_argument("--cmd", help="Test command to run")
    t_parser.set_defaults(func=cmd_test)

    # parse
    p_parser = subparsers.add_parser("parse", help="Parse traceback into stack frames")
    p_parser.add_argument("--file", "-f", help="Traceback file path")
    p_parser.add_argument("--text", "-t", help="Raw traceback string")
    p_parser.set_defaults(func=cmd_parse)

    # diagnose
    d_parser = subparsers.add_parser("diagnose", help="Analyze failure and formulate fix hypothesis")
    d_parser.add_argument("--file", "-f", help="Traceback file path")
    d_parser.add_argument("--text", "-t", help="Raw traceback string")
    d_parser.set_defaults(func=cmd_diagnose)

    # autofix
    a_parser = subparsers.add_parser("autofix", help="Run autonomous closed-loop test repair")
    a_parser.add_argument("--cmd", help="Test command to run")
    a_parser.add_argument("--max-iter", type=int, default=4, help="Max iterations")
    a_parser.add_argument("--no-rollback", action="store_true", help="Disable automatic rollback on regression")
    a_parser.set_defaults(func=cmd_autofix)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

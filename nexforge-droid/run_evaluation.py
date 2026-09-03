#!/usr/bin/env python3
"""Evaluation and Benchmark runner CLI for NexForge Droid."""

import argparse
import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.evaluation.quality_gate import MultiCriteriaQualityGate
from app.evaluation.benchmark_runner import SWEBenchmarkSuite


def main():
    parser = argparse.ArgumentParser(description="NexForge Droid Evaluation & Benchmark Suite")
    parser.add_argument(
        "--op",
        choices=["list-benchmarks", "run-benchmark", "quality-gate", "leaderboard"],
        default="list-benchmarks",
        help="Operation to perform",
    )
    parser.add_argument("--id", type=str, default="BM-001", help="Benchmark challenge ID")
    parser.add_argument("--path", type=str, default=None, help="Optional workspace path")
    args = parser.parse_args()

    workspace_root = args.path or os.path.dirname(os.path.abspath(__file__))

    # Direct logging to stderr
    import logging
    r_logger = logging.getLogger()
    for h in list(r_logger.handlers):
        r_logger.removeHandler(h)
    r_logger.addHandler(logging.StreamHandler(sys.stderr))

    suite = SWEBenchmarkSuite(workspace_root=workspace_root)
    gate = MultiCriteriaQualityGate(workspace_root=workspace_root)

    try:
        if args.op == "list-benchmarks":
            challenges = [c.to_dict() for c in suite.list_challenges()]
            print(json.dumps({"success": True, "total": len(challenges), "benchmarks": challenges}, indent=2))

        elif args.op == "run-benchmark":
            res = suite.run_challenge(args.id)
            print(json.dumps({"success": True, "result": res.to_dict()}, indent=2))

        elif args.op == "quality-gate":
            rep = gate.evaluate_all(task_id="cli-quality-gate")
            print(json.dumps({"success": True, "report": rep.to_dict()}, indent=2))

        elif args.op == "leaderboard":
            board = suite.get_leaderboard()
            print(json.dumps({"success": True, "leaderboard": board}, indent=2))

    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

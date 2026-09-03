#!/usr/bin/env python3
"""CLI utility for Repository Intelligence & Engineering Graph queries (Phase 5 & 6)."""

import argparse
import json
import os
import sys

# Ensure nexforge-droid is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.context.engine import RepositoryContextEngine
from app.context.engineering_graph import EngineeringGraph
from app.context.scanner import RepositoryScanner


def main() -> None:
    parser = argparse.ArgumentParser(description="NexForge Droid Repository & Code Intelligence CLI")
    parser.add_argument(
        "--op",
        choices=["scan", "graph", "search-symbols", "symbol-details", "context", "stats"],
        required=True,
        help="Operation to perform",
    )
    parser.add_argument("--path", default="./nexforge-droid", help="Target repository directory path")
    parser.add_argument("--query", default="", help="Search query for symbols")
    parser.add_argument("--symbol", default="", help="Symbol ID or name for detailed inspection")
    parser.add_argument("--requirement", default="", help="Task requirement for context assembly")
    parser.add_argument("--max-nodes", type=int, default=150, help="Max nodes to export for graph visualizer")

    args = parser.parse_args()
    target_path = os.path.abspath(args.path)

    if args.op == "scan":
        scanner = RepositoryScanner(target_path)
        summary = scanner.scan()
        print(json.dumps(summary.to_dict(), indent=2))

    elif args.op == "graph":
        graph = EngineeringGraph()
        graph.build_from_repository(target_path)
        data = graph.export_graph_data(max_nodes=args.max_nodes)
        print(json.dumps(data, indent=2))

    elif args.op == "search-symbols":
        graph = EngineeringGraph()
        graph.build_from_repository(target_path)
        matches = graph.search_symbols(args.query, limit=30)
        print(json.dumps([m.to_dict() for m in matches], indent=2))

    elif args.op == "symbol-details":
        graph = EngineeringGraph()
        graph.build_from_repository(target_path)
        node = graph.get_node(args.symbol)
        if not node:
            matches = graph.find_symbols_by_name(args.symbol)
            if matches:
                node = matches[0]

        if not node:
            print(json.dumps({"error": f"Symbol '{args.symbol}' not found in graph"}, indent=2))
            return

        callers = [c.to_dict() for c in graph.get_callers(node.node_id)]
        callees = graph.get_callees(node.node_id)
        dependencies = graph.get_dependencies(node.node_id)

        res = {
            "symbol": node.to_dict(),
            "callers": callers,
            "callees": callees,
            "dependencies": dependencies,
        }
        print(json.dumps(res, indent=2))

    elif args.op == "context":
        engine = RepositoryContextEngine(target_path)
        req = args.requirement or "Analyze codebase structure and verify test suites."
        pkg = engine.build_context(req, target_path)
        print(json.dumps(pkg.to_dict(), indent=2))

    elif args.op == "stats":
        scanner = RepositoryScanner(target_path)
        summary = scanner.scan()
        graph = EngineeringGraph()
        graph.build_from_repository(target_path)
        stats = graph.get_stats()

        combined = {
            "root_path": summary.root_path,
            "total_files": summary.total_files,
            "total_loc": summary.total_lines_of_code,
            "languages": summary.languages,
            "frameworks": summary.frameworks,
            "entry_points": summary.entry_points,
            "graph_stats": stats,
        }
        print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()

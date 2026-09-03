#!/usr/bin/env python3
"""
NexForge MCP Standalone Runner & Stdio Server (Phase 16).
Provides stdio JSON-RPC loop and diagnostic subcommands.
"""

import sys
import os
import json
import argparse

# Ensure nexforge-droid is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.mcp import MCPGateway, NexForgeMCPServer


def run_stdio_server():
    """Runs a standard MCP stdio JSON-RPC server loop."""
    server = NexForgeMCPServer(workspace_root=BASE_DIR)
    # Read lines from stdin and write to stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            resp_str = server.handle_raw_message(line)
            sys.stdout.write(resp_str + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_payload = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)},
            }
            sys.stdout.write(json.dumps(err_payload) + "\n")
            sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="NexForge MCP Runner & Stdio Server")
    subparsers = parser.add_subparsers(dest="subcommand", help="MCP Subcommand")

    subparsers.add_parser("serve", help="Run stdio JSON-RPC server loop")
    subparsers.add_parser("status", help="Display MCP Gateway and Server status")
    subparsers.add_parser("tools", help="List all exposed MCP tools")
    subparsers.add_parser("resources", help="List all exposed MCP resources")
    subparsers.add_parser("prompts", help="List all exposed MCP prompt workflows")
    subparsers.add_parser("servers", help="List connected external MCP servers")

    p_call = subparsers.add_parser("call", help="Call a tool via JSON-RPC")
    p_call.add_argument("tool_name", help="Name of tool")
    p_call.add_argument("arguments", nargs="?", default="{}", help="JSON encoded arguments")

    p_read = subparsers.add_parser("read", help="Read a resource URI")
    p_read.add_argument("uri", help="Resource URI (e.g. nexforge://workspace/tree)")

    args = parser.parse_args()

    gateway = MCPGateway(workspace_root=BASE_DIR)

    if args.subcommand == "serve":
        run_stdio_server()
    elif args.subcommand == "status":
        print(json.dumps(gateway.get_status(), indent=2))
    elif args.subcommand == "tools":
        resp = gateway.handle_request({"id": 1, "method": "tools/list", "params": {}})
        print(json.dumps(resp.result, indent=2))
    elif args.subcommand == "resources":
        resp = gateway.handle_request({"id": 1, "method": "resources/list", "params": {}})
        print(json.dumps(resp.result, indent=2))
    elif args.subcommand == "prompts":
        resp = gateway.handle_request({"id": 1, "method": "prompts/list", "params": {}})
        print(json.dumps(resp.result, indent=2))
    elif args.subcommand == "servers":
        servers = gateway.client.list_servers()
        tools = gateway.client.list_external_tools()
        print(json.dumps({"servers": servers, "bridged_tools": tools}, indent=2))
    elif args.subcommand == "call":
        try:
            parsed_args = json.loads(args.arguments)
        except Exception:
            parsed_args = {}
        resp = gateway.handle_request({
            "id": 1,
            "method": "tools/call",
            "params": {"name": args.tool_name, "arguments": parsed_args},
        })
        if resp.error:
            print(f"Error [{resp.error.code}]: {resp.error.message}")
        else:
            print(json.dumps(resp.result, indent=2))
    elif args.subcommand == "read":
        resp = gateway.handle_request({
            "id": 1,
            "method": "resources/read",
            "params": {"uri": args.uri},
        })
        if resp.error:
            print(f"Error [{resp.error.code}]: {resp.error.message}")
        else:
            print(json.dumps(resp.result, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Universal MCP Client and External Server Connector (Phase 16).
Discovers and integrates external MCP tool servers into NexForge Droid.
Zero-dependency standard library implementation.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

from app.mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    MCPTool,
    MCPToolResult,
    MCPContentItem,
)
from app.tools.base import Tool, ToolResult


@dataclass
class ExternalMCPServerConfig:
    server_id: str
    name: str
    transport: str = "mock"  # "mock" | "stdio" | "http-sse"
    endpoint_or_command: str = "mock://internal"
    status: str = "connected"
    enabled: bool = True
    description: str = "External MCP Tool Provider"
    tools_count: int = 0
    latency_ms: float = 1.2

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


class DelegatedExternalTool(Tool):
    """Wraps an external MCP tool into NexForge's native Tool contract."""

    def __init__(
        self,
        namespaced_name: str,
        original_name: str,
        description: str,
        parameters: Dict[str, Any],
        client: Any,
        server_id: str,
    ):
        self.name = namespaced_name
        self.description = f"[MCP External: {server_id}] {description}"
        self.input_schema = parameters
        self.requires_permission = False
        self.original_name = original_name
        self.server_id = server_id
        self.client = client

    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        try:
            resp = self.client.call_external_tool(self.server_id, self.original_name, kwargs)
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                success=not resp.get("isError", False),
                data=resp.get("content", []),
                execution_time_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            return ToolResult(
                success=False,
                data=None,
                error=f"External MCP server error: {str(e)}",
                execution_time_ms=duration_ms,
            )


class UniversalMCPClient:
    """
    Client managing external MCP server discovery, connections, and tool bridging.
    """

    def __init__(self):
        self.connected_servers: Dict[str, ExternalMCPServerConfig] = {}
        self._mock_server_catalogs: Dict[str, List[Dict[str, Any]]] = {}
        self._init_default_external_servers()

    def _init_default_external_servers(self):
        """Pre-configures popular development MCP servers in sandbox/mock mode."""
        self.register_server(
            ExternalMCPServerConfig(
                server_id="github",
                name="GitHub MCP Server",
                transport="mock",
                endpoint_or_command="github://api.github.com",
                description="Repository operations, pull requests, issue tracking, and commits",
                status="connected",
                enabled=True,
                latency_ms=12.4,
            ),
            mock_tools=[
                {
                    "name": "list_pull_requests",
                    "description": "Lists recent pull requests with status and branch details",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "owner/repo"},
                            "state": {"type": "string", "enum": ["open", "closed", "all"]},
                        },
                        "required": ["repo"],
                    },
                },
                {
                    "name": "create_pull_request",
                    "description": "Creates a new pull request for verified changesets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo": {"type": "string", "description": "owner/repo"},
                            "title": {"type": "string", "description": "PR Title"},
                            "head": {"type": "string", "description": "Feature branch name"},
                            "base": {"type": "string", "description": "Target branch, default main"},
                            "body": {"type": "string", "description": "Markdown PR summary"},
                        },
                        "required": ["repo", "title", "head"],
                    },
                },
            ]
        )

        self.register_server(
            ExternalMCPServerConfig(
                server_id="postgres",
                name="PostgreSQL MCP Server",
                transport="mock",
                endpoint_or_command="postgres://localhost:5432/app_db",
                description="Relational database schema inspection, query explain, and table metadata",
                status="connected",
                enabled=True,
                latency_ms=4.8,
            ),
            mock_tools=[
                {
                    "name": "describe_tables",
                    "description": "Returns list of database tables and column definitions",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "schema": {"type": "string", "default": "public"},
                        },
                    },
                },
                {
                    "name": "explain_query",
                    "description": "Generates query plan cost and index usage diagnostics",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string", "description": "SQL statement to analyze"},
                        },
                        "required": ["sql"],
                    },
                },
            ]
        )

        self.register_server(
            ExternalMCPServerConfig(
                server_id="sentry",
                name="Sentry Error Tracking MCP Server",
                transport="mock",
                endpoint_or_command="sentry://app.sentry.io",
                description="Live production error telemetry, issue tracebacks, and frequency",
                status="connected",
                enabled=True,
                latency_ms=8.5,
            ),
            mock_tools=[
                {
                    "name": "get_unresolved_issues",
                    "description": "Lists top unresolved runtime exceptions and frequency",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "project": {"type": "string", "description": "Sentry project slug"},
                        },
                        "required": ["project"],
                    },
                },
            ]
        )

        self.register_server(
            ExternalMCPServerConfig(
                server_id="brave_search",
                name="Brave Search MCP Server",
                transport="mock",
                endpoint_or_command="https://api.search.brave.com/res/v1/web/search",
                description="Real-time web search and technical documentation grounding",
                status="connected",
                enabled=True,
                latency_ms=18.1,
            ),
            mock_tools=[
                {
                    "name": "web_search",
                    "description": "Searches the web for developer documentation, errors, and APIs",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query terms"},
                            "count": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            ]
        )

    def register_server(
        self,
        config: ExternalMCPServerConfig,
        mock_tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """Registers an external MCP server configuration."""
        if mock_tools:
            config.tools_count = len(mock_tools)
            self._mock_server_catalogs[config.server_id] = mock_tools
        self.connected_servers[config.server_id] = config

    def list_servers(self) -> List[Dict[str, Any]]:
        return [s.model_dump() for s in self.connected_servers.values()]

    def list_external_tools(self, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns discovered external tools with namespacing."""
        tools = []
        target_servers = [server_id] if server_id else list(self.connected_servers.keys())

        for sid in target_servers:
            srv = self.connected_servers.get(sid)
            if not srv or not srv.enabled:
                continue
            raw_tools = self._mock_server_catalogs.get(sid, [])
            for t in raw_tools:
                namespaced_name = f"{sid}__{t['name']}"
                tools.append({
                    "name": namespaced_name,
                    "original_name": t["name"],
                    "server_id": sid,
                    "server_name": srv.name,
                    "description": t.get("description", ""),
                    "inputSchema": t.get("inputSchema", {}),
                })
        return tools

    def bridge_tools_into_registry(self, registry: Any) -> int:
        """Registers all enabled external tools into the provided ToolRegistry."""
        added = 0
        all_ext_tools = self.list_external_tools()
        for t in all_ext_tools:
            if registry.get(t["name"]):
                continue
            tool_obj = DelegatedExternalTool(
                namespaced_name=t["name"],
                original_name=t["original_name"],
                description=t["description"],
                parameters=t["inputSchema"],
                client=self,
                server_id=t["server_id"],
            )
            registry.register(tool_obj)
            added += 1
        return added

    def call_external_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatches tool execution to the designated external server."""
        if server_id not in self.connected_servers:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown external server '{server_id}'"}]
            }

        srv = self.connected_servers[server_id]
        if not srv.enabled:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Server '{server_id}' is currently disabled"}]
            }

        # Mock responses simulating remote execution
        if server_id == "github":
            if tool_name == "list_pull_requests":
                data = [
                    {"number": 42, "title": "feat: Phase 15 multi-agent swarm deliberation", "state": "open", "author": "nexforge-droid"},
                    {"number": 41, "title": "fix(eval): 6D quality gate complexity threshold", "state": "merged", "author": "kage-critic"},
                ]
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}
            elif tool_name == "create_pull_request":
                data = {
                    "number": 43,
                    "title": arguments.get("title", "Automated PR"),
                    "url": f"https://github.com/{arguments.get('repo', 'org/repo')}/pull/43",
                    "status": "created",
                    "branch": arguments.get("head", "feature/auto-patch"),
                }
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

        elif server_id == "postgres":
            if tool_name == "describe_tables":
                data = {
                    "schema": arguments.get("schema", "public"),
                    "tables": [
                        {"name": "tasks", "columns": 7, "rows_estimate": 1420},
                        {"name": "task_timeline_events", "columns": 6, "rows_estimate": 18240},
                        {"name": "task_checkpoints", "columns": 5, "rows_estimate": 230},
                    ],
                }
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}
            elif tool_name == "explain_query":
                data = {
                    "query": arguments.get("sql"),
                    "plan": "Seq Scan on tasks (cost=0.00..32.50 rows=10 width=64)",
                    "execution_time": "0.042 ms",
                }
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

        elif server_id == "sentry":
            if tool_name == "get_unresolved_issues":
                data = [
                    {"id": "ISSUE-901", "error": "RateLimitError: 429 Resource Exhausted", "count": 14, "last_seen": "3m ago"},
                    {"id": "ISSUE-882", "error": "SyntaxError: Unexpected token in JSON", "count": 2, "last_seen": "1h ago"},
                ]
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

        elif server_id == "brave_search":
            if tool_name == "web_search":
                q = arguments.get("query", "")
                data = {
                    "query": q,
                    "results": [
                        {"title": "Model Context Protocol (MCP) Quickstart", "url": "https://modelcontextprotocol.io/quickstart", "snippet": "Build interoperable agents with standard JSON-RPC 2.0 tools and resources."},
                        {"title": "Astral UV Python Package Manager", "url": "https://astral.sh/uv", "snippet": "An extremely fast Python package and project manager written in Rust."},
                    ]
                }
                return {"isError": False, "content": [{"type": "text", "text": json.dumps(data, indent=2)}]}

        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Unimplemented tool '{tool_name}' on server '{server_id}'"}]
        }

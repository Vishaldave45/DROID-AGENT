"""
MCP Gateway Coordinator (Phase 16).
Harmonizes local MCP Server capabilities with the external tool client pool.
"""

import time
from typing import Dict, Any, List, Optional

from app.mcp.server import NexForgeMCPServer
from app.mcp.client import UniversalMCPClient, ExternalMCPServerConfig
from app.mcp.protocol import JSONRPCRequest, JSONRPCResponse, JSONRPCError, INTERNAL_ERROR
from app.tools import get_default_tool_registry, ToolRegistry


class MCPGateway:
    """
    Central gateway coordinating NexForge's MCP Server and connected external servers.
    """

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.tool_registry = tool_registry or get_default_tool_registry()
        self.client = UniversalMCPClient()
        # Bridge external tools into local registry so agent can call them
        self.client.bridge_tools_into_registry(self.tool_registry)

        self.server = NexForgeMCPServer(
            workspace_root=workspace_root,
            tool_registry=self.tool_registry,
        )

        self.stats = {
            "requests_handled": 0,
            "tool_calls": 0,
            "resources_read": 0,
            "prompts_rendered": 0,
            "errors": 0,
            "started_at": time.time(),
        }

    def handle_request(self, payload: Dict[str, Any]) -> JSONRPCResponse:
        self.stats["requests_handled"] += 1
        method = payload.get("method", "")

        if method == "tools/call":
            self.stats["tool_calls"] += 1
        elif method == "resources/read":
            self.stats["resources_read"] += 1
        elif method == "prompts/get":
            self.stats["prompts_rendered"] += 1

        response = self.server.handle_request(payload)
        if response.error:
            self.stats["errors"] += 1

        return response

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive status of the MCP gateway, server, and client pool."""
        local_tools = len(self.server.tool_registry.list_tools())
        external_servers = self.client.list_servers()
        external_tools = len(self.client.list_external_tools())

        return {
            "gateway_status": "ONLINE",
            "protocol_version": self.server.PROTOCOL_VERSION,
            "server_info": self.server.server_info.model_dump(),
            "local_tools_count": local_tools,
            "external_servers_count": len(external_servers),
            "external_tools_count": external_tools,
            "total_available_tools": local_tools,
            "connected_servers": external_servers,
            "telemetry": self.stats,
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
                "logging": True,
            },
        }

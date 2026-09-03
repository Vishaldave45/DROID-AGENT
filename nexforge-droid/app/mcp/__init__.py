"""
MCP Package Exports (Phase 16: Universal Model Context Protocol Server & Gateway).
"""

from app.mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCPImplementation,
    MCPTool,
    MCPResource,
    MCPPrompt,
    MCPToolResult,
)
from app.mcp.server import NexForgeMCPServer
from app.mcp.client import UniversalMCPClient, ExternalMCPServerConfig
from app.mcp.gateway import MCPGateway

__all__ = [
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCError",
    "MCPImplementation",
    "MCPTool",
    "MCPResource",
    "MCPPrompt",
    "MCPToolResult",
    "NexForgeMCPServer",
    "UniversalMCPClient",
    "ExternalMCPServerConfig",
    "MCPGateway",
]

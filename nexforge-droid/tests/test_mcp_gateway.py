"""
Unit tests for Phase 16: Model Context Protocol (MCP) Server & Universal Tool Gateway.
"""

import unittest
import json
from app.mcp import (
    NexForgeMCPServer,
    UniversalMCPClient,
    ExternalMCPServerConfig,
    MCPGateway,
    JSONRPCRequest,
    JSONRPCResponse,
)
from app.tools import get_default_tool_registry


class TestMCPGateway(unittest.TestCase):
    def setUp(self):
        self.gateway = MCPGateway()
        self.server = self.gateway.server
        self.client = self.gateway.client

    def test_mcp_handshake_initialize(self):
        """Verifies JSON-RPC initialize handshake returns protocol version and capabilities."""
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {"clientInfo": {"name": "test-client", "version": "1.0.0"}},
        })
        self.assertEqual(resp.id, "init-1")
        self.assertIsNone(resp.error)
        self.assertIsNotNone(resp.result)
        self.assertEqual(resp.result["protocolVersion"], "2024-11-05")
        self.assertIn("tools", resp.result["capabilities"])
        self.assertIn("resources", resp.result["capabilities"])
        self.assertIn("prompts", resp.result["capabilities"])

    def test_mcp_tools_list_schema(self):
        """Verifies tools/list exposes tools with compliant JSON Schema."""
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        })
        self.assertIsNone(resp.error)
        tools = resp.result.get("tools", [])
        self.assertGreater(len(tools), 15)

        tool_names = {t["name"] for t in tools}
        self.assertIn("read_file", tool_names)
        self.assertIn("edit_file", tool_names)
        self.assertIn("run_diagnostics", tool_names)

        # Verify schema structure
        for t in tools:
            self.assertIn("name", t)
            self.assertIn("description", t)
            self.assertIn("inputSchema", t)
            self.assertIn("type", t["inputSchema"])

    def test_mcp_tool_call_execution(self):
        """Verifies executing a tool through tools/call returns structured MCP content."""
        target_file = __file__
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"path": target_file, "start_line": 1, "end_line": 5},
            },
        })
        self.assertIsNone(resp.error)
        result = resp.result
        self.assertFalse(result.get("isError"))
        content = result.get("content", [])
        self.assertGreaterEqual(len(content), 1)
        self.assertEqual(content[0]["type"], "text")
        self.assertIn("Phase 16", content[0]["text"])

    def test_mcp_resources_list_and_read(self):
        """Verifies listing and reading resources like tree, metrics, and quality-gate."""
        list_resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/list",
            "params": {},
        })
        self.assertIsNone(list_resp.error)
        resources = list_resp.result.get("resources", [])
        uris = {r["uri"] for r in resources}
        self.assertIn("nexforge://workspace/tree", uris)
        self.assertIn("nexforge://workspace/metrics", uris)
        self.assertIn("nexforge://governance/quality-gate", uris)

        # Read tree
        read_resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": "nexforge://workspace/tree"},
        })
        self.assertIsNone(read_resp.error)
        contents = read_resp.result.get("contents", [])
        self.assertEqual(len(contents), 1)
        parsed = json.loads(contents[0]["text"])
        self.assertIn("files", parsed)

    def test_mcp_prompts_list_and_get(self):
        """Verifies prompt workflow templates can be listed and rendered with arguments."""
        list_resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/list",
            "params": {},
        })
        self.assertIsNone(list_resp.error)
        prompts = list_resp.result.get("prompts", [])
        prompt_names = {p["name"] for p in prompts}
        self.assertIn("surgical_refactor", prompt_names)
        self.assertIn("swarm_peer_review", prompt_names)

        # Render prompt
        get_resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 7,
            "method": "prompts/get",
            "params": {
                "name": "surgical_refactor",
                "arguments": {"file_path": "src/cache.py", "refactor_objective": "Fix LRU eviction leak"},
            },
        })
        self.assertIsNone(get_resp.error)
        messages = get_resp.result.get("messages", [])
        self.assertGreaterEqual(len(messages), 1)
        self.assertIn("src/cache.py", messages[0]["content"]["text"])
        self.assertIn("Fix LRU eviction leak", messages[0]["content"]["text"])

    def test_external_server_tool_bridging(self):
        """Verifies external MCP servers are discovered and bridged into the ToolRegistry."""
        servers = self.client.list_servers()
        self.assertGreaterEqual(len(servers), 4)

        ext_tools = self.client.list_external_tools()
        ext_tool_names = {t["name"] for t in ext_tools}
        self.assertIn("github__list_pull_requests", ext_tool_names)
        self.assertIn("postgres__describe_tables", ext_tool_names)
        self.assertIn("sentry__get_unresolved_issues", ext_tool_names)

        # Call external tool through client
        resp = self.client.call_external_tool("github", "list_pull_requests", {"repo": "nexforge/agent"})
        self.assertFalse(resp.get("isError"))
        self.assertIn("deliberation", resp["content"][0]["text"])

    def test_mcp_gateway_telemetry_and_status(self):
        """Verifies MCP Gateway aggregates metrics and tracks request volume."""
        status = self.gateway.get_status()
        self.assertEqual(status["gateway_status"], "ONLINE")
        self.assertGreater(status["local_tools_count"], 15)
        self.assertGreater(status["external_servers_count"], 3)
        self.assertIn("telemetry", status)

    def test_json_rpc_error_handling(self):
        """Verifies invalid methods and missing params return standard JSON-RPC 2.0 errors."""
        # Method not found
        resp = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 8,
            "method": "invalid/method_name",
            "params": {},
        })
        self.assertIsNotNone(resp.error)
        self.assertEqual(resp.error.code, -32601)

        # Raw string parse error
        err_str = self.server.handle_raw_message("{not_valid_json")
        parsed_err = json.loads(err_str)
        self.assertEqual(parsed_err["error"]["code"], -32700)


if __name__ == "__main__":
    unittest.main()

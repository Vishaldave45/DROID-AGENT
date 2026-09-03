"""
NexForge MCP Server Implementation (Phase 16).
Exposes NexForge Droid tools, resources, and prompt workflows over standard JSON-RPC 2.0.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional

from app.mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    MCPImplementation,
    MCPTool,
    MCPResource,
    MCPResourceContent,
    MCPPrompt,
    MCPPromptArgument,
    MCPPromptMessage,
    MCPPromptMessageContent,
    MCPToolResult,
    MCPContentItem,
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    INVALID_PARAMS,
    INTERNAL_ERROR,
)
from app.tools import get_default_tool_registry, ToolRegistry
from app.context.scanner import RepositoryScanner
from app.evaluation.benchmark_runner import SWEBenchmarkSuite
from app.evaluation.quality_gate import MultiCriteriaQualityGate
from app.agent.swarm import SwarmConsensusEngine


class NexForgeMCPServer:
    """
    Standard Model Context Protocol (MCP) Server for NexForge Droid.
    Complies with Anthropic/Open MCP 2024-11-05 specification.
    """

    PROTOCOL_VERSION = "2024-11-05"

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.workspace_root = workspace_root or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.tool_registry = tool_registry or get_default_tool_registry()
        self.scanner = RepositoryScanner(root_path=self.workspace_root)
        self.benchmarks = SWEBenchmarkSuite()
        self.quality_gate = MultiCriteriaQualityGate()
        self.swarm = SwarmConsensusEngine()
        self.server_info = MCPImplementation(
            name="nexforge-droid-mcp",
            version="0.1.0"
        )
        self.is_initialized = False

    def handle_raw_message(self, raw_json: str) -> str:
        """Parses and handles a raw JSON-RPC 2.0 string request."""
        try:
            payload = json.loads(raw_json)
        except Exception as e:
            err_resp = JSONRPCResponse(
                id=None,
                error=JSONRPCError(code=PARSE_ERROR, message=f"Parse error: {str(e)}")
            )
            return err_resp.model_dump_json()

        response = self.handle_request(payload)
        return response.model_dump_json()

    def handle_request(self, payload: Dict[str, Any]) -> JSONRPCResponse:
        """Routes a parsed JSON-RPC 2.0 request to the appropriate MCP handler."""
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        if not method or not isinstance(method, str):
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_REQUEST, message="Missing or invalid method")
            )

        try:
            # Handshake & Core Handlers
            if method == "initialize":
                return self._handle_initialize(req_id, params)
            elif method == "notifications/initialized":
                self.is_initialized = True
                return JSONRPCResponse(id=req_id, result={"status": "ready"})
            elif method == "ping":
                return JSONRPCResponse(id=req_id, result={})

            # Tools
            elif method == "tools/list":
                return self._handle_tools_list(req_id, params)
            elif method == "tools/call":
                return self._handle_tools_call(req_id, params)

            # Resources
            elif method == "resources/list":
                return self._handle_resources_list(req_id, params)
            elif method == "resources/read":
                return self._handle_resources_read(req_id, params)

            # Prompts
            elif method == "prompts/list":
                return self._handle_prompts_list(req_id, params)
            elif method == "prompts/get":
                return self._handle_prompts_get(req_id, params)

            else:
                return JSONRPCResponse(
                    id=req_id,
                    error=JSONRPCError(
                        code=METHOD_NOT_FOUND,
                        message=f"Unknown or unsupported method '{method}'"
                    )
                )
        except Exception as e:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INTERNAL_ERROR, message=f"Server error: {str(e)}")
            )

    # ==========================================================================
    # Protocol Handlers
    # ==========================================================================

    def _handle_initialize(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        self.is_initialized = True
        return JSONRPCResponse(
            id=req_id,
            result={
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                    "logging": {},
                },
                "serverInfo": self.server_info.model_dump(),
            }
        )

    def _handle_tools_list(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        tools: List[Dict[str, Any]] = []
        for tool_obj in self.tool_registry.list_tools():
            schema = getattr(tool_obj, "input_schema", getattr(tool_obj, "parameters", {}))
            if "type" not in schema:
                schema = {"type": "object", "properties": schema.get("properties", {})}
            tools.append({
                "name": tool_obj.name,
                "description": getattr(tool_obj, "description", f"Tool {tool_obj.name}"),
                "inputSchema": schema,
            })
        return JSONRPCResponse(id=req_id, result={"tools": tools})

    def _handle_tools_call(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message="Missing tool name in arguments")
            )

        if not self.tool_registry.get(tool_name):
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message=f"Tool '{tool_name}' not found")
            )

        result = self.tool_registry.dispatch(tool_name, arguments)
        output_data = getattr(result, "data", getattr(result, "result", None))
        output_text = json.dumps(output_data, indent=2) if isinstance(output_data, (dict, list)) else str(output_data)
        if not result.success:
            output_text = f"Tool Error: {result.error}\n{output_text}"

        mcp_result = MCPToolResult(
            content=[MCPContentItem(type="text", text=output_text)],
            isError=not result.success,
            metadata={
                "execution_time_ms": result.execution_time_ms,
                "tool_name": tool_name,
            }
        )
        return JSONRPCResponse(id=req_id, result=mcp_result.model_dump())

    def _handle_resources_list(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        resources = [
            MCPResource(
                uri="nexforge://workspace/tree",
                name="Workspace Directory Tree",
                description="List of files and directories within the current workspace root",
                mimeType="application/json"
            ).model_dump(),
            MCPResource(
                uri="nexforge://workspace/metrics",
                name="Repository Metrics & Summary",
                description="Aggregated lines of code, language breakdown, and discovered framework manifests",
                mimeType="application/json"
            ).model_dump(),
            MCPResource(
                uri="nexforge://benchmarks/challenges",
                name="SWE-bench Challenges Catalog",
                description="All standardized SWE-bench autonomous coding challenges",
                mimeType="application/json"
            ).model_dump(),
            MCPResource(
                uri="nexforge://governance/quality-gate",
                name="Multi-Criteria Quality Gate Status",
                description="6-dimensional quality metrics, test results, and compliance scores",
                mimeType="application/json"
            ).model_dump(),
            MCPResource(
                uri="nexforge://swarm/roles",
                name="Swarm Agent Roles",
                description="Registered multi-agent swarm specialist roles and their consensus weight",
                mimeType="application/json"
            ).model_dump(),
        ]
        return JSONRPCResponse(id=req_id, result={"resources": resources})

    def _handle_resources_read(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        uri = params.get("uri")
        if not uri:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message="Missing resource URI")
            )

        if uri == "nexforge://workspace/tree":
            files = []
            for root, _, filenames in os.walk(self.workspace_root):
                if any(ignored in root for ignored in [".git", "node_modules", ".venv", "__pycache__", "dist"]):
                    continue
                for f in filenames:
                    rel = os.path.relpath(os.path.join(root, f), self.workspace_root)
                    files.append(rel)
            content = json.dumps({"workspace": self.workspace_root, "files": sorted(files)}, indent=2)
            return JSONRPCResponse(id=req_id, result={"contents": [MCPResourceContent(uri=uri, text=content).model_dump()]})

        elif uri == "nexforge://workspace/metrics":
            summary = self.scanner.scan()
            content = json.dumps(summary.to_dict(), indent=2)
            return JSONRPCResponse(id=req_id, result={"contents": [MCPResourceContent(uri=uri, text=content).model_dump()]})

        elif uri == "nexforge://benchmarks/challenges":
            challenges = [c.to_dict() for c in self.benchmarks.list_challenges()]
            content = json.dumps({"count": len(challenges), "challenges": challenges}, indent=2)
            return JSONRPCResponse(id=req_id, result={"contents": [MCPResourceContent(uri=uri, text=content).model_dump()]})

        elif uri == "nexforge://governance/quality-gate":
            report = self.quality_gate.evaluate_all(task_id="mcp-resource-read")
            content = json.dumps(report.to_dict(), indent=2)
            return JSONRPCResponse(id=req_id, result={"contents": [MCPResourceContent(uri=uri, text=content).model_dump()]})

        elif uri == "nexforge://swarm/roles":
            agents = self.swarm.get_registered_agents()
            content = json.dumps({"roles": agents}, indent=2)
            return JSONRPCResponse(id=req_id, result={"contents": [MCPResourceContent(uri=uri, text=content).model_dump()]})

        else:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message=f"Resource URI '{uri}' not found")
            )

    def _handle_prompts_list(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        prompts = [
            MCPPrompt(
                name="surgical_refactor",
                description="Structured AST-validated surgical code modification workflow",
                arguments=[
                    MCPPromptArgument(name="file_path", description="Target source code path", required=True),
                    MCPPromptArgument(name="refactor_objective", description="Refactoring goal or requirement", required=True),
                ]
            ).model_dump(),
            MCPPrompt(
                name="diagnostic_fix_loop",
                description="Autonomous test failure diagnosis and closed repair cycle",
                arguments=[
                    MCPPromptArgument(name="test_command", description="Command to execute test suite", required=True),
                    MCPPromptArgument(name="error_trace", description="Initial traceback or failure log", required=False),
                ]
            ).model_dump(),
            MCPPrompt(
                name="swarm_peer_review",
                description="5-agent adversarial deliberation and quorum synthesis",
                arguments=[
                    MCPPromptArgument(name="objective", description="Engineering task objective", required=True),
                    MCPPromptArgument(name="proposal", description="Proposed implementation or diff", required=True),
                ]
            ).model_dump(),
            MCPPrompt(
                name="quality_gate_audit",
                description="6-dimensional multi-criteria software engineering audit",
                arguments=[
                    MCPPromptArgument(name="task_id", description="Task identifier to audit", required=False),
                ]
            ).model_dump(),
        ]
        return JSONRPCResponse(id=req_id, result={"prompts": prompts})

    def _handle_prompts_get(self, req_id: Any, params: Dict[str, Any]) -> JSONRPCResponse:
        name = params.get("name")
        args = params.get("arguments", {})

        if not name:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message="Missing prompt name")
            )

        if name == "surgical_refactor":
            file_path = args.get("file_path", "<target_file>")
            objective = args.get("refactor_objective", "Refactor target component")
            messages = [
                MCPPromptMessage(
                    role="user",
                    content=MCPPromptMessageContent(
                        type="text",
                        text=f"Please analyze {file_path} and perform an AST-verified surgical refactoring to achieve: {objective}.\n"
                             f"1. Read the target file.\n2. Formulate patch with exact chunks.\n3. Validate syntax before saving."
                    )
                ).model_dump()
            ]
            return JSONRPCResponse(id=req_id, result={"description": "Surgical Refactor", "messages": messages})

        elif name == "diagnostic_fix_loop":
            cmd = args.get("test_command", "npm run uv:test")
            trace = args.get("error_trace", "No trace provided.")
            messages = [
                MCPPromptMessage(
                    role="user",
                    content=MCPPromptMessageContent(
                        type="text",
                        text=f"Execute diagnostic fix loop for failed test suite: `{cmd}`.\nTrace:\n{trace}\n"
                             f"Diagnose root cause, apply patch, and ensure regression guard passes."
                    )
                ).model_dump()
            ]
            return JSONRPCResponse(id=req_id, result={"description": "Diagnostic Fix Loop", "messages": messages})

        elif name == "swarm_peer_review":
            obj = args.get("objective", "Multi-agent review")
            proposal = args.get("proposal", "Default implementation proposal")
            messages = [
                MCPPromptMessage(
                    role="user",
                    content=MCPPromptMessageContent(
                        type="text",
                        text=f"Convene the 5-agent swarm consensus panel for objective: {obj}.\nProposal:\n{proposal}\n"
                             f"Solicit critiques from Kage-Critic, security review from Iris-Reviewer, and synthesis from Sol-Synthesizer."
                    )
                ).model_dump()
            ]
            return JSONRPCResponse(id=req_id, result={"description": "Swarm Peer Review", "messages": messages})

        elif name == "quality_gate_audit":
            task_id = args.get("task_id", "mcp-audit")
            messages = [
                MCPPromptMessage(
                    role="user",
                    content=MCPPromptMessageContent(
                        type="text",
                        text=f"Audit workspace quality against 6 dimensions: Test Suite, AST Integrity, Security Audit, "
                             f"Lint Style, Cyclomatic Complexity, and Invariant Contracts. Task ID: {task_id}."
                    )
                ).model_dump()
            ]
            return JSONRPCResponse(id=req_id, result={"description": "Quality Gate Audit", "messages": messages})

        else:
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(code=INVALID_PARAMS, message=f"Prompt '{name}' not found")
            )

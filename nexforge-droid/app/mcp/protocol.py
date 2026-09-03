"""
Model Context Protocol (MCP) Schemas and JSON-RPC 2.0 Primitives.
Phase 16: Universal Model Context Protocol (MCP) Server & External Tool Gateway.
Zero-dependency Python 3.10 standard library implementation.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Union


# ==============================================================================
# JSON-RPC 2.0 Standard Specifications
# ==============================================================================

@dataclass
class JSONRPCError:
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


@dataclass
class JSONRPCRequest:
    method: str
    id: Optional[Union[str, int]] = None
    params: Optional[Dict[str, Any]] = field(default_factory=dict)
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.id is not None:
            d["id"] = self.id
        if self.params is not None:
            d["params"] = self.params
        return d


@dataclass
class JSONRPCResponse:
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> Dict[str, Any]:
        d = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result
        return d

    def model_dump(self) -> Dict[str, Any]:
        return self.to_dict()

    def model_dump_json(self) -> str:
        import json
        return json.dumps(self.to_dict())


# Standard JSON-RPC 2.0 Error Codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ==============================================================================
# Model Context Protocol (MCP) Primitives (Spec 2024-11-05)
# ==============================================================================

@dataclass
class MCPImplementation:
    name: str = "nexforge-droid-mcp"
    version: str = "0.1.0"

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPTool:
    name: str
    description: str
    inputSchema: Dict[str, Any] = field(default_factory=dict)

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPResource:
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = "application/json"

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPResourceContent:
    uri: str
    mimeType: Optional[str] = "application/json"
    text: Optional[str] = None
    blob: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPPromptArgument:
    name: str
    description: Optional[str] = None
    required: bool = False

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPPrompt:
    name: str
    description: Optional[str] = None
    arguments: List[MCPPromptArgument] = field(default_factory=list)

    def model_dump(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": [a.model_dump() for a in self.arguments],
        }


@dataclass
class MCPPromptMessageContent:
    type: str = "text"
    text: str = ""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPPromptMessage:
    role: str  # "user" | "assistant" | "system"
    content: MCPPromptMessageContent

    def model_dump(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content.model_dump(),
        }


@dataclass
class MCPContentItem:
    type: str = "text"
    text: str = ""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MCPToolResult:
    content: List[MCPContentItem] = field(default_factory=list)
    isError: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def model_dump(self) -> Dict[str, Any]:
        d = {
            "content": [c.model_dump() for c in self.content],
            "isError": self.isError,
        }
        if self.metadata is not None:
            d["metadata"] = self.metadata
        return d

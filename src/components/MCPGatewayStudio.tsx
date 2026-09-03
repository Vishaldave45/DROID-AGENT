import React, { useState, useEffect } from 'react';
import {
  Network,
  Server,
  Cpu,
  Terminal,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  ArrowRight,
  RefreshCw,
  ExternalLink,
  Code2,
  Copy,
  Check,
  Zap,
  Globe,
  Database,
  FileCode,
  Shield,
  Layers,
  Search,
} from 'lucide-react';

interface ExternalServer {
  server_id: string;
  name: string;
  transport: string;
  endpoint_or_command: string;
  status: string;
  enabled: boolean;
  description: string;
  tools_count: number;
  latency_ms: number;
}

interface MCPStatus {
  gateway_status: string;
  protocol_version: string;
  server_info: {
    name: string;
    version: string;
  };
  local_tools_count: number;
  external_servers_count: number;
  external_tools_count: number;
  total_available_tools: number;
  connected_servers: ExternalServer[];
  telemetry: {
    requests_handled: number;
    tool_calls: number;
    resources_read: number;
    prompts_rendered: number;
    errors: number;
  };
}

interface MCPTool {
  name: string;
  description: string;
  inputSchema: any;
}

interface MCPResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
}

interface MCPPrompt {
  name: string;
  description: string;
  arguments: { name: string; description: string; required: boolean }[];
}

export const MCPGatewayStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'federation' | 'tools' | 'resources' | 'jsonrpc' | 'integration'>('federation');
  const [status, setStatus] = useState<MCPStatus | null>(null);
  const [tools, setTools] = useState<MCPTool[]>([]);
  const [externalTools, setExternalTools] = useState<any[]>([]);
  const [resources, setResources] = useState<MCPResource[]>([]);
  const [prompts, setPrompts] = useState<MCPPrompt[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [toolSearch, setToolSearch] = useState<string>('');
  const [copiedText, setCopiedText] = useState<string | null>(null);

  // Playground / Execution states
  const [selectedTool, setSelectedTool] = useState<string>('run_diagnostics');
  const [toolArgsJson, setToolArgsJson] = useState<string>('{\n  "test_command": "echo Verified NexForge MCP"\n}');
  const [toolExecResult, setToolExecResult] = useState<any | null>(null);
  const [toolExecuting, setToolExecuting] = useState<boolean>(false);

  // Resource viewer
  const [selectedResourceUri, setSelectedResourceUri] = useState<string>('nexforge://workspace/metrics');
  const [resourceContent, setResourceContent] = useState<any | null>(null);
  const [resourceLoading, setResourceLoading] = useState<boolean>(false);

  // Raw JSON-RPC state
  const [rawRpcInput, setRawRpcInput] = useState<string>(
    JSON.stringify(
      {
        jsonrpc: '2.0',
        id: 'rpc-101',
        method: 'initialize',
        params: { clientInfo: { name: 'web-dashboard-client', version: '1.0.0' } },
      },
      null,
      2
    )
  );
  const [rawRpcResponse, setRawRpcResponse] = useState<string | null>(null);
  const [rawRpcLoading, setRawRpcLoading] = useState<boolean>(false);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/mcp/status');
      const data = await res.json();
      if (data.success && data.status) {
        setStatus(data.status);
      }
    } catch (err) {
      console.error('Failed to load MCP status:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTools = async () => {
    try {
      const res = await fetch('/api/mcp/tools');
      const data = await res.json();
      if (data.success && data.tools) {
        setTools(data.tools);
      }
    } catch (err) {
      console.error('Failed to load MCP tools:', err);
    }
  };

  const fetchServers = async () => {
    try {
      const res = await fetch('/api/mcp/servers');
      const data = await res.json();
      if (data.success) {
        if (data.servers && status) {
          setStatus((prev) => (prev ? { ...prev, connected_servers: data.servers } : prev));
        }
        if (data.external_tools) {
          setExternalTools(data.external_tools);
        }
      }
    } catch (err) {
      console.error('Failed to load MCP servers:', err);
    }
  };

  const fetchResourcesAndPrompts = async () => {
    try {
      const [resRes, resPrompts] = await Promise.all([
        fetch('/api/mcp/resources'),
        fetch('/api/mcp/prompts'),
      ]);
      const dataRes = await resRes.json();
      const dataPrompts = await resPrompts.json();
      if (dataRes.success && dataRes.resources) setResources(dataRes.resources);
      if (dataPrompts.success && dataPrompts.prompts) setPrompts(dataPrompts.prompts);
    } catch (err) {
      console.error('Failed to load MCP resources/prompts:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
    fetchTools();
    fetchServers();
    fetchResourcesAndPrompts();
  }, []);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(id);
    setTimeout(() => setCopiedText(null), 2000);
  };

  const executeToolCall = async (toolName: string, args: any) => {
    try {
      setToolExecuting(true);
      setToolExecResult(null);
      const res = await fetch('/api/mcp/call', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: toolName, arguments: args }),
      });
      const data = await res.json();
      setToolExecResult(data);
    } catch (err: any) {
      setToolExecResult({ success: false, error: err.message });
    } finally {
      setToolExecuting(false);
    }
  };

  const readResource = async (uri: string) => {
    try {
      setResourceLoading(true);
      setSelectedResourceUri(uri);
      const res = await fetch(`/api/mcp/resources?uri=${encodeURIComponent(uri)}`);
      const data = await res.json();
      setResourceContent(data.content || data);
    } catch (err: any) {
      setResourceContent({ error: err.message });
    } finally {
      setResourceLoading(false);
    }
  };

  const executeRawRpc = async () => {
    try {
      setRawRpcLoading(true);
      setRawRpcResponse(null);
      let parsed = {};
      try {
        parsed = JSON.parse(rawRpcInput);
      } catch (err) {
        setRawRpcResponse(JSON.stringify({ error: 'Invalid client JSON payload' }, null, 2));
        return;
      }
      const res = await fetch('/api/mcp/jsonrpc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsed),
      });
      const data = await res.json();
      setRawRpcResponse(JSON.stringify(data.response || data, null, 2));
    } catch (err: any) {
      setRawRpcResponse(JSON.stringify({ error: err.message }, null, 2));
    } finally {
      setRawRpcLoading(false);
    }
  };

  const filteredTools = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
      t.description.toLowerCase().includes(toolSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
                <Network className="w-5 h-5" />
              </span>
              <h2 className="text-xl font-bold text-white tracking-tight">
                Universal Model Context Protocol (MCP) Gateway & Server
              </h2>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                Spec 2024-11-05 Compliant
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-3xl">
              Bidirectional JSON-RPC 2.0 protocol hub. Exposes NexForge workspace tools, resources, and prompt
              templates to external AI clients (Claude Desktop, Cursor, Copilot) while federating external tool servers
              (GitHub, Postgres, Sentry, Brave Search).
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                fetchStatus();
                fetchTools();
                fetchServers();
                fetchResourcesAndPrompts();
              }}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 flex items-center gap-1.5 border border-slate-700 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              GATEWAY ONLINE
            </span>
          </div>
        </div>

        {/* Telemetry Metric Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6">
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Protocol</span>
            <span className="text-base font-bold text-indigo-300 font-mono mt-0.5 block">2024-11-05</span>
            <span className="text-[10px] text-slate-500">JSON-RPC 2.0 stdio</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Local Tools</span>
            <span className="text-base font-bold text-emerald-400 font-mono mt-0.5 block">
              {status?.local_tools_count ?? 28}
            </span>
            <span className="text-[10px] text-slate-500">Fully schema-typed</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">External Servers</span>
            <span className="text-base font-bold text-amber-400 font-mono mt-0.5 block">
              {status?.external_servers_count ?? 4}
            </span>
            <span className="text-[10px] text-slate-500">Federated clients</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Bridged Tools</span>
            <span className="text-base font-bold text-sky-400 font-mono mt-0.5 block">
              {status?.external_tools_count ?? 6}
            </span>
            <span className="text-[10px] text-slate-500">Namespaced proxy</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Resources</span>
            <span className="text-base font-bold text-purple-400 font-mono mt-0.5 block">{resources.length || 3}</span>
            <span className="text-[10px] text-slate-500">URI state providers</span>
          </div>
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block">Prompts</span>
            <span className="text-base font-bold text-teal-400 font-mono mt-0.5 block">{prompts.length || 3}</span>
            <span className="text-[10px] text-slate-500">Workflow templates</span>
          </div>
        </div>
      </div>

      {/* Sub-Tab Navigation */}
      <div className="flex border-b border-slate-800 gap-1 overflow-x-auto">
        {[
          { id: 'federation', label: 'External MCP Federation', icon: Globe },
          { id: 'tools', label: `Exposed Tools (${tools.length})`, icon: Server },
          { id: 'resources', label: `Resources & Prompts (${resources.length + prompts.length})`, icon: FileCode },
          { id: 'jsonrpc', label: 'JSON-RPC 2.0 Playground', icon: Terminal },
          { id: 'integration', label: 'Claude / Cursor Setup', icon: Code2 },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 text-xs font-semibold flex items-center gap-2 border-b-2 transition-all whitespace-nowrap ${
                isActive
                  ? 'border-indigo-500 text-indigo-300 bg-indigo-950/20'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-500'}`} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: EXTERNAL TOOL FEDERATION */}
      {activeTab === 'federation' && (
        <div className="space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
              <Globe className="w-4 h-4 text-indigo-400" />
              Connected External MCP Tool Servers
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              NexForge acts as an MCP Client discovering external MCP tool capabilities and delegating them
              automatically into the autonomous engineering agent loop.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(status?.connected_servers || []).map((srv) => (
                <div
                  key={srv.server_id}
                  className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-slate-300 border border-slate-700">
                          {srv.server_id}
                        </span>
                        <h4 className="text-sm font-semibold text-white">{srv.name}</h4>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        {srv.status.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-400 mb-3">{srv.description}</p>

                    <div className="space-y-1.5 text-xs text-slate-300 mb-3 font-mono bg-slate-900/80 p-2.5 rounded border border-slate-800/80">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Transport:</span>
                        <span>{srv.transport} (mock sandbox)</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Endpoint:</span>
                        <span className="truncate max-w-[200px] text-slate-400">{srv.endpoint_or_command}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Ping Latency:</span>
                        <span className="text-emerald-400">{srv.latency_ms} ms</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">
                      <strong>{srv.tools_count}</strong> bridged tools
                    </span>
                    <button
                      onClick={() => {
                        let sampleArgs = {};
                        let sampleTool = `${srv.server_id}__`;
                        if (srv.server_id === 'github') {
                          sampleTool += 'list_pull_requests';
                          sampleArgs = { repo: 'nexforge/droid' };
                        } else if (srv.server_id === 'postgres') {
                          sampleTool += 'describe_tables';
                          sampleArgs = { schema: 'public' };
                        } else if (srv.server_id === 'sentry') {
                          sampleTool += 'get_unresolved_issues';
                          sampleArgs = { project: 'frontend-core' };
                        } else {
                          sampleTool += 'web_search';
                          sampleArgs = { query: 'Model Context Protocol' };
                        }
                        setSelectedTool(sampleTool);
                        setToolArgsJson(JSON.stringify(sampleArgs, null, 2));
                        executeToolCall(sampleTool, sampleArgs);
                      }}
                      className="text-xs px-2.5 py-1 rounded bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 flex items-center gap-1 transition-colors"
                    >
                      <Play className="w-3 h-3" />
                      Test Bridge Call
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Test Execution Console for Federation */}
          {toolExecResult && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <h4 className="text-sm font-semibold text-white">
                    Execution Output for Tool: <span className="font-mono text-indigo-300">{selectedTool}</span>
                  </h4>
                </div>
                <button
                  onClick={() => setToolExecResult(null)}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Clear Output
                </button>
              </div>
              <pre className="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-200 overflow-x-auto border border-slate-800">
                {JSON.stringify(toolExecResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EXPOSED TOOLS & SCHEMAS */}
      {activeTab === 'tools' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                placeholder="Search tools by name or description..."
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
            <span className="text-xs text-slate-400">
              Showing {filteredTools.length} of {tools.length} exposed MCP tools
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredTools.map((tool) => (
              <div
                key={tool.name}
                className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs font-bold text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-900/60">
                      {tool.name}
                    </span>
                    <button
                      onClick={() => handleCopy(JSON.stringify(tool.inputSchema, null, 2), `schema-${tool.name}`)}
                      className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1"
                    >
                      {copiedText === `schema-${tool.name}` ? (
                        <Check className="w-3 h-3 text-emerald-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                      Copy Schema
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">{tool.description}</p>
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500 font-mono">
                    Required: {tool.inputSchema?.required?.join(', ') || 'none'}
                  </span>
                  <button
                    onClick={() => {
                      setSelectedTool(tool.name);
                      // Generate default arguments skeleton from schema properties
                      const props = tool.inputSchema?.properties || {};
                      const sample: Record<string, any> = {};
                      Object.keys(props).forEach((k) => {
                        sample[k] = props[k]?.default !== undefined ? props[k].default : props[k]?.type === 'string' ? '' : 0;
                      });
                      setToolArgsJson(JSON.stringify(sample, null, 2));
                      setActiveTab('jsonrpc');
                      setRawRpcInput(
                        JSON.stringify(
                          {
                            jsonrpc: '2.0',
                            id: `call-${tool.name}`,
                            method: 'tools/call',
                            params: { name: tool.name, arguments: sample },
                          },
                          null,
                          2
                        )
                      );
                    }}
                    className="text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1 transition-colors"
                  >
                    Open in Playground
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: RESOURCES & PROMPT TEMPLATES */}
      {activeTab === 'resources' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* MCP Resources */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-purple-400" />
              Exposed Workspace Resources
            </h3>
            <p className="text-xs text-slate-400">
              URIs allowing external AI assistants to read repository tree structures, workspace metrics, and quality
              gate scorecards.
            </p>

            <div className="space-y-3">
              {resources.map((res) => (
                <div
                  key={res.uri}
                  className={`p-3.5 rounded-lg border transition-all cursor-pointer ${
                    selectedResourceUri === res.uri
                      ? 'bg-purple-950/20 border-purple-800/80 text-white'
                      : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                  }`}
                  onClick={() => readResource(res.uri)}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs text-purple-300 font-semibold">{res.uri}</span>
                    <span className="text-[10px] text-slate-500 font-mono">{res.mimeType}</span>
                  </div>
                  <p className="text-xs text-slate-400">{res.description}</p>
                </div>
              ))}
            </div>

            {resourceContent && (
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono text-purple-300">Live Resource Content</span>
                  <span className="text-[10px] text-slate-500">{selectedResourceUri}</span>
                </div>
                <pre className="text-xs font-mono text-slate-300 overflow-x-auto max-h-64">
                  {typeof resourceContent === 'string'
                    ? resourceContent
                    : JSON.stringify(resourceContent, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Prompt Templates */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <FileCode className="w-4 h-4 text-teal-400" />
              Parameterized Prompt Workflows
            </h3>
            <p className="text-xs text-slate-400">
              Pre-configured engineering prompt templates that can be fetched and populated by external MCP clients.
            </p>

            <div className="space-y-3">
              {prompts.map((p) => (
                <div key={p.name} className="bg-slate-900 border border-slate-800 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-xs text-teal-300 font-semibold">{p.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                      {p.arguments?.length || 0} arguments
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">{p.description}</p>

                  <div className="space-y-1 text-[11px] font-mono bg-slate-950 p-2.5 rounded border border-slate-800/80 mb-3">
                    <span className="text-slate-500 block mb-1">Arguments:</span>
                    {(p.arguments || []).map((arg) => (
                      <div key={arg.name} className="flex items-center justify-between text-slate-300">
                        <span>{arg.name}</span>
                        <span className="text-slate-500">{arg.required ? 'required' : 'optional'}</span>
                      </div>
                    ))}
                  </div>

                  <button
                    onClick={() => {
                      setActiveTab('jsonrpc');
                      const sampleArgs: Record<string, string> = {};
                      (p.arguments || []).forEach((a) => {
                        sampleArgs[a.name] = `[${a.name}]`;
                      });
                      setRawRpcInput(
                        JSON.stringify(
                          {
                            jsonrpc: '2.0',
                            id: `prompt-${p.name}`,
                            method: 'prompts/get',
                            params: { name: p.name, arguments: sampleArgs },
                          },
                          null,
                          2
                        )
                      );
                    }}
                    className="w-full py-1 text-xs text-center rounded bg-teal-600/20 hover:bg-teal-600/30 text-teal-300 border border-teal-500/30 transition-colors"
                  >
                    Render in JSON-RPC Playground
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: RAW JSON-RPC 2.0 PLAYGROUND */}
      {activeTab === 'jsonrpc' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-indigo-400" />
                JSON-RPC 2.0 Request Payload
              </h3>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    setRawRpcInput(
                      JSON.stringify(
                        {
                          jsonrpc: '2.0',
                          id: 1,
                          method: 'tools/call',
                          params: {
                            name: 'run_diagnostics',
                            arguments: { test_command: 'echo Testing MCP Gateway' },
                          },
                        },
                        null,
                        2
                      )
                    );
                  }}
                  className="text-[11px] text-slate-400 hover:text-slate-200"
                >
                  Load Tool Call
                </button>
                <button
                  onClick={() => {
                    setRawRpcInput(
                      JSON.stringify(
                        {
                          jsonrpc: '2.0',
                          id: 2,
                          method: 'resources/list',
                          params: {},
                        },
                        null,
                        2
                      )
                    );
                  }}
                  className="text-[11px] text-slate-400 hover:text-slate-200"
                >
                  Load Resources
                </button>
              </div>
            </div>

            <textarea
              value={rawRpcInput}
              onChange={(e) => setRawRpcInput(e.target.value)}
              rows={12}
              className="w-full bg-slate-950 font-mono text-xs text-slate-200 p-4 rounded-xl border border-slate-800 focus:outline-none focus:border-indigo-500"
              placeholder="Paste JSON-RPC 2.0 request here..."
            />

            <button
              onClick={executeRawRpc}
              disabled={rawRpcLoading}
              className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs flex items-center justify-center gap-2 shadow-sm transition-colors"
            >
              {rawRpcLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Send JSON-RPC Message to Gateway
            </button>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Gateway Response Payload
            </h3>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 h-[285px] overflow-y-auto font-mono text-xs text-slate-300">
              {rawRpcResponse ? (
                <pre>{rawRpcResponse}</pre>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-500 text-center">
                  <Terminal className="w-8 h-8 mb-2 opacity-40" />
                  <p>Send a request to see the gateway JSON-RPC 2.0 response</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: CLAUDE DESKTOP & CURSOR INTEGRATION */}
      {activeTab === 'integration' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-base font-bold text-white mb-1">External Client Integration Guide</h3>
            <p className="text-xs text-slate-400">
              Easily connect Claude Desktop, Cursor, or any MCP-compliant AI tool to NexForge Droid using the stdio
              runner.
            </p>
          </div>

          {/* Claude Desktop Config */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-indigo-300">
                1. Claude Desktop Configuration (claude_desktop_config.json)
              </span>
              <button
                onClick={() =>
                  handleCopy(
                    JSON.stringify(
                      {
                        mcpServers: {
                          nexforge: {
                            command: 'python3',
                            args: ['/path/to/nexforge-droid/run_mcp.py', 'serve'],
                            env: {
                              PYTHONPATH: '/path/to/nexforge-droid',
                            },
                          },
                        },
                      },
                      null,
                      2
                    ),
                    'claude-config'
                  )
                }
                className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1"
              >
                {copiedText === 'claude-config' ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                Copy Config
              </button>
            </div>
            <pre className="bg-slate-950 p-4 rounded-lg font-mono text-xs text-slate-300 border border-slate-800">
              {JSON.stringify(
                {
                  mcpServers: {
                    nexforge: {
                      command: 'python3',
                      args: ['/absolute/path/to/nexforge-droid/run_mcp.py', 'serve'],
                      env: {
                        PYTHONPATH: '/absolute/path/to/nexforge-droid',
                      },
                    },
                  },
                },
                null,
                2
              )}
            </pre>
          </div>

          {/* CLI Commands */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-200">2. CLI Verification Commands</span>
            <div className="space-y-2 font-mono text-xs">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                <span className="text-emerald-400">nexforge mcp status</span>
                <span className="text-slate-500 text-[11px]">Inspect gateway and server health</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                <span className="text-emerald-400">nexforge mcp servers</span>
                <span className="text-slate-500 text-[11px]">List discovered external MCP servers</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                <span className="text-emerald-400">python3 run_mcp.py call read_file &#39;&#123;&quot;path&quot;: &quot;pyproject.toml&quot;&#125;&#39;</span>
                <span className="text-slate-500 text-[11px]">Execute tool directly via MCP transport</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect, useMemo } from 'react';
import {
  Layers,
  Cpu,
  Database,
  Wrench,
  Terminal,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  Eye,
  ArrowRight,
  Search,
  Filter,
  Boxes,
  Code2,
  Sparkles,
  Network,
  GitBranch,
  ExternalLink,
  ShieldCheck,
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronRight,
  FileCode,
} from 'lucide-react';
import { repoApi, GraphData, GraphNode, GraphLink } from '../api/repo';
import { useSystem } from '../context/SystemContext';

export const ArchitectureGraph: React.FC = () => {
  const { manifest, subsystems, demoMode } = useSystem();

  const [activeTab, setActiveTab] = useState<'ast' | 'subsystems'>('ast');
  const [loadingGraph, setLoadingGraph] = useState(false);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [maxNodes, setMaxNodes] = useState<number>(75);
  const [repoPath, setRepoPath] = useState<string>('./nexforge-droid');

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [activeNode, setActiveNode] = useState<GraphNode | null>(null);

  // SVG viewport zoom/pan
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const fetchLiveGraph = async () => {
    setLoadingGraph(true);
    try {
      const data = await repoApi.graph(repoPath, maxNodes);
      setGraphData(data);
      if (data.nodes && data.nodes.length > 0 && !activeNode) {
        // Select an entry point or first class by default
        const defaultNode = data.nodes.find((n) => n.node_type === 'CLASS') || data.nodes[0];
        setActiveNode(defaultNode);
      }
    } catch (err) {
      console.error('Failed to load real AST graph:', err);
    } finally {
      setLoadingGraph(false);
    }
  };

  useEffect(() => {
    fetchLiveGraph();
  }, [repoPath, maxNodes]);

  // Compute filtered nodes
  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.filter((node) => {
      const matchesType = selectedType === 'ALL' || node.node_type === selectedType;
      const matchesQuery =
        !searchQuery.trim() ||
        node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.file_path.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesType && matchesQuery;
    });
  }, [graphData, selectedType, searchQuery]);

  // Calculate dynamic node coordinates in a multi-tier architectural layout
  const nodePositions = useMemo(() => {
    const positions: Record<string, { x: number; y: number; node: GraphNode }> = {};
    if (!filteredNodes.length) return positions;

    // Group filtered nodes by type
    const groups: Record<string, GraphNode[]> = {
      FILE: [],
      CLASS: [],
      FUNCTION: [],
      METHOD: [],
      TEST: [],
      OTHER: [],
    };

    filteredNodes.forEach((node) => {
      const t = node.node_type;
      if (groups[t]) groups[t].push(node);
      else groups.OTHER.push(node);
    });

    const tierYMap: Record<string, number> = {
      FILE: 90,
      CLASS: 230,
      FUNCTION: 370,
      METHOD: 490,
      TEST: 610,
      OTHER: 700,
    };

    const canvasWidth = 1100;

    Object.entries(groups).forEach(([type, nodesInGroup]) => {
      if (!nodesInGroup.length) return;
      const y = tierYMap[type] || 400;
      const spacing = canvasWidth / (nodesInGroup.length + 1);

      nodesInGroup.forEach((node, idx) => {
        positions[node.node_id] = {
          x: Math.round(spacing * (idx + 1)),
          y,
          node,
        };
      });
    });

    return positions;
  }, [filteredNodes]);

  // Connected links between visible nodes
  const visibleLinks = useMemo(() => {
    if (!graphData?.links) return [];
    return graphData.links.filter(
      (link) => nodePositions[link.source_id] && nodePositions[link.target_id]
    );
  }, [graphData, nodePositions]);

  // Highlighted connected node IDs
  const connectedIds = useMemo(() => {
    if (!activeNode || !graphData?.links) return new Set<string>();
    const ids = new Set<string>();
    ids.add(activeNode.node_id);

    graphData.links.forEach((l) => {
      if (l.source_id === activeNode.node_id) ids.add(l.target_id);
      if (l.target_id === activeNode.node_id) ids.add(l.source_id);
    });
    return ids;
  }, [activeNode, graphData]);

  // Subsystem Architecture Definition
  const architecturalSubsystems = useMemo(() => {
    return [
      {
        id: 'agent_loop',
        name: 'Autonomous Agent Loop',
        module: 'app.agent.loop',
        icon: Cpu,
        tier: 'Runtime Core',
        desc: 'Coordinating perception, planning, tool dispatch, and iterative loop governance.',
        contracts: ['run_task', 'run_iteration', 'step_execution'],
        status: 'VALIDATED',
      },
      {
        id: 'policy_gateway',
        name: 'Policy Gateway & Sandbox',
        module: 'app.security.base',
        icon: ShieldCheck,
        tier: 'Security Perimeter',
        desc: 'Deterministic ALLOW / APPROVE / DENY policy enforcement preventing escapes and unauthorized mutations.',
        contracts: ['verify_command', 'verify_read', 'verify_write'],
        status: 'ENFORCING',
      },
      {
        id: 'context_ast',
        name: 'AST Context Engine',
        module: 'app.context.engine',
        icon: Eye,
        tier: 'Intelligence',
        desc: 'Extracts real symbol hierarchies, token budgets, and builds dependency-aware prompt context.',
        contracts: ['build_context', 'scan_repository', 'calculate_tokens'],
        status: 'ACTIVE',
      },
      {
        id: 'engineering_graph',
        name: 'Engineering Code Graph',
        module: 'app.context.engineering_graph',
        icon: Network,
        tier: 'Intelligence',
        desc: 'Multi-relational graph of 1,850+ symbols, callers, callees, inheritance, and test coverage.',
        contracts: ['get_callers', 'get_callees', 'get_file_symbols'],
        status: 'INDEXED',
      },
      {
        id: 'tools_registry',
        name: 'Tool Registry & Dispatcher',
        module: 'app.tools.registry',
        icon: Wrench,
        tier: 'Execution',
        desc: 'Strict typed tool execution: read_file, edit_file, run_command, git diff, and directory indexing.',
        contracts: ['dispatch_tool', 'list_schemas', 'validate_args'],
        status: 'OPERATIONAL',
      },
      {
        id: 'diagnostic_loop',
        name: 'Diagnostic Fix Loop & Patcher',
        module: 'app.diagnostics.loop',
        icon: RefreshCw,
        tier: 'Self-Correction',
        desc: 'Automated test failure parsing, rollback on regression, and progressive candidate evaluation.',
        contracts: ['run_diagnostic_cycle', 'rollback_on_regression'],
        status: 'TESTED',
      },
      {
        id: 'storage_persistence',
        name: 'Task State Store & Checkpoints',
        module: 'app.storage.sqlite_store',
        icon: Database,
        tier: 'Storage',
        desc: 'SQLite durable task state, iteration journals, tool audit trails, and snapshot rollback checkpoints.',
        contracts: ['save_task', 'create_checkpoint', 'restore_checkpoint'],
        status: 'PERSISTED',
      },
      {
        id: 'orchestrator',
        name: 'Multi-File Orchestrator',
        module: 'app.orchestrator',
        icon: Boxes,
        tier: 'Refactoring',
        desc: 'Coordinates multi-file patch plans, AST renames, dependency ordering, and human approval gates.',
        contracts: ['create_changeset', 'apply_changeset', 'require_approval'],
        status: 'SYNCHRONIZED',
      },
      {
        id: 'streaming_debugger',
        name: 'Live Streaming & Debugger',
        module: 'app.streaming',
        icon: Terminal,
        tier: 'Observability',
        desc: 'Real-time JSON event streaming, step-by-step debugger, breakpoint hooks, and inspection frames.',
        contracts: ['stream_events', 'step_pause', 'set_breakpoint'],
        status: 'STREAMING',
      },
    ];
  }, []);

  return (
    <div
      id="architecture-graph-container"
      className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl space-y-6"
    >
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <h2 className="text-xl font-semibold text-white tracking-tight">
              NexForge Architecture &amp; Code Graph
            </h2>
          </div>
          <p className="text-sm text-slate-400 mt-0.5">
            Streaming real AST symbols, caller/callee relationships, and subsystem contracts directly from disk
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex p-1 bg-slate-950 border border-slate-800 rounded-lg text-xs">
            <button
              onClick={() => setActiveTab('ast')}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === 'ast'
                  ? 'bg-emerald-600 text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Network className="w-3.5 h-3.5" />
              Live AST Code Graph
            </button>
            <button
              onClick={() => setActiveTab('subsystems')}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                activeTab === 'subsystems'
                  ? 'bg-indigo-600 text-white font-medium shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              Subsystem Architecture DAG
            </button>
          </div>
        </div>
      </div>

      {activeTab === 'ast' ? (
        /* AST Graph Mode */
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 p-3 bg-slate-950/80 border border-slate-800 rounded-lg">
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter symbols by name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-900 border border-slate-800 rounded-md pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 w-48 sm:w-64"
                />
              </div>

              {/* Type Filter Buttons */}
              <div className="flex items-center gap-1 text-xs">
                {['ALL', 'CLASS', 'FUNCTION', 'METHOD', 'TEST', 'FILE'].map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedType(t)}
                    className={`px-2 py-1 rounded transition-colors text-[11px] font-mono ${
                      selectedType === t
                        ? 'bg-slate-800 text-emerald-400 font-semibold border border-slate-700'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-2 self-end lg:self-auto text-xs">
              <span className="text-slate-400">Node Cap:</span>
              <select
                value={maxNodes}
                onChange={(e) => setMaxNodes(Number(e.target.value))}
                className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none"
              >
                <option value={50}>50 Nodes</option>
                <option value={75}>75 Nodes</option>
                <option value={120}>120 Nodes</option>
              </select>

              <button
                onClick={fetchLiveGraph}
                disabled={loadingGraph}
                className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs flex items-center gap-1 border border-slate-700 transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${loadingGraph ? 'animate-spin' : ''}`} />
                Reload
              </button>

              <div className="flex items-center border border-slate-800 rounded bg-slate-900 ml-1">
                <button
                  onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.1))}
                  className="p-1 text-slate-400 hover:text-slate-200"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-3.5 h-3.5" />
                </button>
                <span className="text-[10px] font-mono text-slate-400 px-1.5">
                  {Math.round(zoomLevel * 100)}%
                </span>
                <button
                  onClick={() => setZoomLevel((z) => Math.min(1.8, z + 0.1))}
                  className="p-1 text-slate-400 hover:text-slate-200"
                  title="Zoom In"
                >
                  <ZoomIn className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Stats Header */}
          {graphData?.stats && (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
              <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Total Codebase AST Nodes</span>
                <div className="text-sm font-bold text-emerald-400 font-mono mt-0.5">
                  {graphData.stats.total_nodes.toLocaleString()}
                </div>
              </div>
              <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Total Dependency Edges</span>
                <div className="text-sm font-bold text-indigo-400 font-mono mt-0.5">
                  {graphData.stats.total_edges.toLocaleString()}
                </div>
              </div>
              <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Classes Parsed</span>
                <div className="text-sm font-bold text-emerald-300 font-mono mt-0.5">
                  {graphData.stats.node_distribution?.CLASS || 0}
                </div>
              </div>
              <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Methods &amp; Functions</span>
                <div className="text-sm font-bold text-cyan-300 font-mono mt-0.5">
                  {(graphData.stats.node_distribution?.METHOD || 0) +
                    (graphData.stats.node_distribution?.FUNCTION || 0)}
                </div>
              </div>
              <div className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg">
                <span className="text-slate-400">Unit &amp; Contract Tests</span>
                <div className="text-sm font-bold text-rose-400 font-mono mt-0.5">
                  {graphData.stats.node_distribution?.TEST || 0}
                </div>
              </div>
            </div>
          )}

          {/* Main Visual SVG Canvas & Side Inspector */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* SVG Visual Canvas */}
            <div className="lg:col-span-8 bg-slate-950/90 border border-slate-800 rounded-xl p-2 relative overflow-hidden min-h-[500px]">
              {loadingGraph && (
                <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center z-10">
                  <div className="flex items-center gap-2 text-xs text-slate-300">
                    <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                    Parsing AST symbols and building graph...
                  </div>
                </div>
              )}

              <div className="w-full h-[520px] overflow-auto border border-slate-900 rounded-lg bg-slate-950">
                <svg
                  width={1120 * zoomLevel}
                  height={760 * zoomLevel}
                  viewBox="0 0 1120 760"
                  className="select-none transition-transform"
                >
                  <defs>
                    <marker
                      id="arrow-calls"
                      viewBox="0 0 10 10"
                      refX="18"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#818cf8" />
                    </marker>
                    <marker
                      id="arrow-inherits"
                      viewBox="0 0 10 10"
                      refX="18"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#38bdf8" />
                    </marker>
                    <marker
                      id="arrow-tests"
                      viewBox="0 0 10 10"
                      refX="18"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto-start-reverse"
                    >
                      <path d="M 0 0 L 10 5 L 0 10 z" fill="#fb7185" />
                    </marker>
                  </defs>

                  {/* Tier Horizontal Guidelines */}
                  <g opacity="0.15">
                    <line x1="40" y1="90" x2="1080" y2="90" stroke="#94a3b8" strokeDasharray="4 4" />
                    <text x="45" y="80" fill="#94a3b8" fontSize="10" fontFamily="monospace">TIER 1: SOURCE FILES</text>

                    <line x1="40" y1="230" x2="1080" y2="230" stroke="#94a3b8" strokeDasharray="4 4" />
                    <text x="45" y="220" fill="#94a3b8" fontSize="10" fontFamily="monospace">TIER 2: CLASSES &amp; PROTOCOLS</text>

                    <line x1="40" y1="370" x2="1080" y2="370" stroke="#94a3b8" strokeDasharray="4 4" />
                    <text x="45" y="360" fill="#94a3b8" fontSize="10" fontFamily="monospace">TIER 3: FUNCTIONS &amp; ENTRYPOINTS</text>

                    <line x1="40" y1="490" x2="1080" y2="490" stroke="#94a3b8" strokeDasharray="4 4" />
                    <text x="45" y="480" fill="#94a3b8" fontSize="10" fontFamily="monospace">TIER 4: METHODS</text>

                    <line x1="40" y1="610" x2="1080" y2="610" stroke="#94a3b8" strokeDasharray="4 4" />
                    <text x="45" y="600" fill="#94a3b8" fontSize="10" fontFamily="monospace">TIER 5: UNIT TESTS &amp; CONTRACTS</text>
                  </g>

                  {/* Relationship Edges */}
                  {visibleLinks.map((link, idx) => {
                    const src = nodePositions[link.source_id];
                    const tgt = nodePositions[link.target_id];
                    if (!src || !tgt) return null;

                    const isHighlight =
                      activeNode &&
                      (link.source_id === activeNode.node_id || link.target_id === activeNode.node_id);

                    const edgeColor =
                      link.edge_type === 'CALLS'
                        ? '#818cf8'
                        : link.edge_type === 'INHERITS'
                        ? '#38bdf8'
                        : link.edge_type === 'TESTS'
                        ? '#fb7185'
                        : '#64748b';

                    const markerId =
                      link.edge_type === 'CALLS'
                        ? 'url(#arrow-calls)'
                        : link.edge_type === 'INHERITS'
                        ? 'url(#arrow-inherits)'
                        : link.edge_type === 'TESTS'
                        ? 'url(#arrow-tests)'
                        : undefined;

                    return (
                      <line
                        key={`edge-${idx}`}
                        x1={src.x}
                        y1={src.y}
                        x2={tgt.x}
                        y2={tgt.y}
                        stroke={edgeColor}
                        strokeWidth={isHighlight ? 2.5 : 1}
                        strokeOpacity={isHighlight ? 0.9 : 0.25}
                        markerEnd={markerId}
                        className="transition-all duration-200"
                      />
                    );
                  })}

                  {/* Nodes */}
                  {Object.values(nodePositions).map(({ x, y, node }) => {
                    const isSelected = activeNode?.node_id === node.node_id;
                    const isConnected = connectedIds.has(node.node_id);

                    let fillColor = '#10b981'; // CLASS
                    if (node.node_type === 'FUNCTION') fillColor = '#6366f1';
                    if (node.node_type === 'METHOD') fillColor = '#06b6d4';
                    if (node.node_type === 'TEST') fillColor = '#f43f5e';
                    if (node.node_type === 'FILE') fillColor = '#f59e0b';

                    return (
                      <g
                        key={node.node_id}
                        transform={`translate(${x}, ${y})`}
                        onClick={() => setActiveNode(node)}
                        className="cursor-pointer group"
                      >
                        {/* Glow halo for selected */}
                        {isSelected && (
                          <circle r="22" fill={fillColor} fillOpacity="0.25" className="animate-pulse" />
                        )}

                        <circle
                          r={isSelected ? 16 : isConnected ? 13 : 11}
                          fill="#0f172a"
                          stroke={fillColor}
                          strokeWidth={isSelected ? 3 : isConnected ? 2 : 1.5}
                          className="transition-all duration-200 hover:scale-125"
                        />

                        {/* Center dot */}
                        <circle r={3.5} fill={fillColor} />

                        {/* Node Name Label */}
                        <text
                          y={26}
                          textAnchor="middle"
                          fill={isSelected ? '#ffffff' : '#cbd5e1'}
                          fontSize={isSelected ? '11' : '10'}
                          fontWeight={isSelected ? '600' : '400'}
                          fontFamily="monospace"
                          className="pointer-events-none"
                        >
                          {node.name.length > 18 ? node.name.substring(0, 16) + '…' : node.name}
                        </text>
                      </g>
                    );
                  })}
                </svg>
              </div>

              <div className="absolute bottom-4 left-4 p-2 bg-slate-900/90 border border-slate-800 rounded-lg text-[10px] text-slate-400 flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Class
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-indigo-400"></span> Function
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-cyan-400"></span> Method
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-rose-400"></span> Test
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-amber-400"></span> File
                </span>
              </div>
            </div>

            {/* Right Node Detail Inspector */}
            <div className="lg:col-span-4 bg-slate-950/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
              {activeNode ? (
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono font-semibold uppercase tracking-wider bg-slate-800 text-emerald-400">
                        {activeNode.node_type}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        Complexity: {activeNode.complexity_score}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-white font-mono mt-1.5 break-all">
                      {activeNode.name}
                    </h3>
                    <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono mt-1 truncate">
                      <FileCode className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate">{activeNode.file_path}</span>
                      <span className="text-slate-500">
                        (L{activeNode.line_start}-{activeNode.line_end})
                      </span>
                    </div>
                  </div>

                  {activeNode.signature && (
                    <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg">
                      <div className="text-[10px] font-semibold text-slate-500 uppercase">Signature</div>
                      <div className="text-xs font-mono text-indigo-300 mt-0.5 break-all">
                        {activeNode.signature}
                      </div>
                    </div>
                  )}

                  {activeNode.docstring && (
                    <div className="p-2.5 bg-slate-900 border border-slate-800 rounded-lg">
                      <div className="text-[10px] font-semibold text-slate-500 uppercase">Docstring</div>
                      <p className="text-xs text-slate-300 mt-0.5 leading-relaxed italic">
                        "{activeNode.docstring}"
                      </p>
                    </div>
                  )}

                  {/* Connected Callees & Callers */}
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Connected Relationships
                    </div>
                    <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
                      {visibleLinks
                        .filter(
                          (l) =>
                            l.source_id === activeNode.node_id ||
                            l.target_id === activeNode.node_id
                        )
                        .map((link, i) => {
                          const isOutgoing = link.source_id === activeNode.node_id;
                          const otherId = isOutgoing ? link.target_id : link.source_id;
                          const otherNode = nodePositions[otherId]?.node;

                          return (
                            <div
                              key={`rel-${i}`}
                              onClick={() => otherNode && setActiveNode(otherNode)}
                              className="p-2 rounded bg-slate-900/80 border border-slate-800 hover:border-slate-700 cursor-pointer flex items-center justify-between text-xs font-mono"
                            >
                              <div className="flex items-center gap-1.5 truncate">
                                <span className="text-[10px] px-1 py-0.2 rounded bg-slate-800 text-slate-400">
                                  {isOutgoing ? 'OUT' : 'IN'}
                                </span>
                                <span className="text-slate-300 truncate">
                                  {otherNode?.name || otherId}
                                </span>
                              </div>
                              <span className="text-[10px] text-indigo-400 shrink-0 ml-1">
                                {link.edge_type}
                              </span>
                            </div>
                          );
                        })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-20 text-center text-xs text-slate-500">
                  Select any node in the SVG canvas to inspect its AST properties.
                </div>
              )}

              <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Displaying {filteredNodes.length} / {graphData?.nodes?.length || 0} nodes</span>
                <span className="font-mono text-emerald-400">Live Disk Stream</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Subsystem Architecture DAG */
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {architecturalSubsystems.map((sub) => {
              const Icon = sub.icon;
              return (
                <div
                  key={sub.id}
                  className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-emerald-400">
                        <Icon className="w-4 h-4" />
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                        {sub.status}
                      </span>
                    </div>

                    <div className="font-semibold text-sm text-slate-200">{sub.name}</div>
                    <div className="text-xs font-mono text-slate-500 mt-0.5">{sub.module}</div>
                    <p className="text-xs text-slate-400 mt-2 leading-relaxed">{sub.desc}</p>
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-900">
                    <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                      Verified Core Contracts
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {sub.contracts.map((c) => (
                        <span
                          key={c}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800"
                        >
                          {c}()
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Dataflow Pipeline */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              Verified Execution &amp; Control Flow DAG
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300 font-mono">
              <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-200">User Goal</span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800">
                Context &amp; AST Engine
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-200">
                Planner &amp; Reasoner
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-amber-950/80 text-amber-300 border border-amber-800">
                Security Policy Gateway
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                Tool Router Dispatch
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-rose-950/80 text-rose-300 border border-rose-800">
                Sandbox Execution
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                Diagnostic Fix Loop
              </span>
              <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-200">
                State Checkpoint &amp; Verification
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from "react";
import {
  Compass,
  GitFork,
  Search,
  Code2,
  Layers,
  FileCode,
  FolderTree,
  Boxes,
  Cpu,
  RefreshCw,
  Zap,
  ArrowRight,
  ExternalLink,
  ShieldCheck,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  BookOpen,
  Filter,
  Network,
  HelpCircle,
} from "lucide-react";

interface RepoSummary {
  root_path: string;
  languages: string[];
  total_files: number;
  total_lines_of_code: number;
  entry_points: string[];
  test_frameworks: string[];
  key_directories: string[];
  language_breakdown: Record<string, number>;
  frameworks: string[];
  manifests: Array<{
    manifest_file: string;
    manifest_type: string;
    packages: Record<string, string>;
    dev_packages: Record<string, string>;
  }>;
  files_sample: Array<{
    path: string;
    relative_path: string;
    language: string;
    size_bytes: number;
    lines_of_code: number;
    is_test: boolean;
    is_entry_point: boolean;
  }>;
}

interface GraphNode {
  node_id: string;
  node_type: string;
  name: string;
  file_path: string;
  line_start: number;
  line_end: number;
  dependencies: string[];
  docstring: string | null;
  signature: string | null;
  async_function: boolean;
  decorators: string[];
  parent_id: string | null;
  complexity_score: number;
  metadata: Record<string, any>;
}

interface GraphLink {
  source_id: string;
  target_id: string;
  edge_type: string;
  weight: number;
  metadata: Record<string, any>;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  stats: {
    total_nodes: number;
    total_edges: number;
    node_distribution: Record<string, number>;
    edge_distribution: Record<string, number>;
    total_files: number;
  };
}

interface SymbolDetails {
  symbol: GraphNode;
  callers: GraphNode[];
  callees: Array<{
    target_id: string;
    target_name: string;
    target_node: GraphNode | null;
    resolved: boolean;
  }>;
  dependencies: Array<{
    edge_type: string;
    target_id: string;
    target_name: string;
    target_type: string;
  }>;
}

interface ContextPackage {
  task_id: string;
  repository_summary: RepoSummary;
  relevant_files: Record<string, string>;
  symbols: GraphNode[];
  estimated_tokens: number;
  metadata: Record<string, any>;
}

export const RepoIntelligenceStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"summary" | "graph" | "symbols" | "context">("summary");
  const [repoPath, setRepoPath] = useState("./nexforge-droid");
  const [loading, setLoading] = useState(false);

  const [summary, setSummary] = useState<RepoSummary | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);

  // Symbol Search & Inspector
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<GraphNode[]>([]);
  const [selectedSymbolId, setSelectedSymbolId] = useState<string | null>(null);
  const [symbolDetails, setSymbolDetails] = useState<SymbolDetails | null>(null);
  const [symbolLoading, setSymbolLoading] = useState(false);

  // Graph Filtering
  const [selectedTypeFilter, setSelectedTypeFilter] = useState<string>("ALL");
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNode | null>(null);

  // Context Engine Simulator
  const [taskRequirement, setTaskRequirement] = useState("Implement resilient exponential backoff for Gemini API rate limits");
  const [contextPkg, setContextPkg] = useState<ContextPackage | null>(null);
  const [contextLoading, setContextLoading] = useState(false);

  const fetchRepoData = async () => {
    setLoading(true);
    try {
      const [scanRes, graphRes] = await Promise.all([
        fetch(`/api/repo/scan?path=${encodeURIComponent(repoPath)}`),
        fetch(`/api/repo/graph?path=${encodeURIComponent(repoPath)}&maxNodes=160`),
      ]);

      if (scanRes.ok) {
        const scanJson = await scanRes.json();
        setSummary(scanJson);
      }

      if (graphRes.ok) {
        const graphJson = await graphRes.json();
        setGraphData(graphJson);
      }
    } catch (err) {
      console.error("Failed to load repo intelligence:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSymbols = async (q: string) => {
    setSearchQuery(q);
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await fetch(`/api/repo/symbols?path=${encodeURIComponent(repoPath)}&query=${encodeURIComponent(q)}`);
      if (res.ok) {
        const data = await res.json();
        setSearchResults(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      console.error("Search failed:", err);
    }
  };

  const handleSelectSymbol = async (sym: GraphNode) => {
    setSelectedSymbolId(sym.node_id);
    setSelectedGraphNode(sym);
    setSymbolLoading(true);
    try {
      const res = await fetch(`/api/repo/symbol-details?path=${encodeURIComponent(repoPath)}&symbol=${encodeURIComponent(sym.node_id)}`);
      if (res.ok) {
        const data = await res.json();
        setSymbolDetails(data);
      }
    } catch (err) {
      console.error("Failed to fetch symbol details:", err);
    } finally {
      setSymbolLoading(false);
    }
  };

  const handleSimulateContext = async () => {
    if (!taskRequirement.trim()) return;
    setContextLoading(true);
    try {
      const res = await fetch("/api/repo/context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: repoPath, requirement: taskRequirement }),
      });
      if (res.ok) {
        const data = await res.json();
        setContextPkg(data);
      }
    } catch (err) {
      console.error("Context simulation failed:", err);
    } finally {
      setContextLoading(false);
    }
  };

  useEffect(() => {
    fetchRepoData();
  }, [repoPath]);

  const getNodeBadgeClass = (type: string) => {
    switch (type) {
      case "CLASS":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      case "FUNCTION":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "METHOD":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "TEST":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "FILE":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "IMPORT":
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/30";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  const filteredGraphNodes = (graphData?.nodes || []).filter((n) => {
    if (selectedTypeFilter === "ALL") return true;
    return n.node_type === selectedTypeFilter;
  });

  return (
    <div id="repo-intelligence-studio" className="space-y-6">
      {/* Top Banner & High-Level KPIs */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-xs font-semibold uppercase tracking-wider rounded-full flex items-center gap-1.5">
                <Compass className="w-3.5 h-3.5" />
                Phase 5 &amp; 6 Live
              </span>
              <span className="text-xs text-slate-400 font-mono">
                AST Symbol Extraction &amp; Engineering Graph
              </span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Repository Intelligence &amp; Code Graph Engine
            </h2>
            <p className="text-sm text-slate-400 mt-1">
              Autonomous codebase structure discovery, framework &amp; dependency scanners, Python AST symbol extraction, and multi-relational code engineering graph.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
              <FolderTree className="w-3.5 h-3.5 text-slate-500 mr-2" />
              <input
                type="text"
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                className="bg-transparent text-slate-200 focus:outline-none w-36 font-mono"
                placeholder="./repo_path"
              />
            </div>
            <button
              onClick={fetchRepoData}
              disabled={loading}
              className="px-3.5 py-2 text-xs font-semibold text-white bg-cyan-600 hover:bg-cyan-700 rounded-lg transition-colors flex items-center gap-2 shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Scan Repository
            </button>
          </div>
        </div>

        {/* Metric Cards Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3.5 mt-6 pt-6 border-t border-slate-800/80">
          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <div className="text-[11px] text-slate-400 font-medium">Source Files</div>
            <div className="text-xl font-bold text-white mt-0.5">
              {summary?.total_files || 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5 font-mono">
              {summary?.languages?.slice(0, 3).join(", ") || "Python"}
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <div className="text-[11px] text-slate-400 font-medium">Total Lines of Code</div>
            <div className="text-xl font-bold text-cyan-400 font-mono mt-0.5">
              {summary?.total_lines_of_code?.toLocaleString() || 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Across repository</div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <div className="text-[11px] text-slate-400 font-medium">AST Code Symbols</div>
            <div className="text-xl font-bold text-purple-400 font-mono mt-0.5">
              {graphData?.stats?.total_nodes || 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              {graphData?.stats?.node_distribution?.CLASS || 0} classes, {graphData?.stats?.node_distribution?.FUNCTION || 0} fns
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
            <div className="text-[11px] text-slate-400 font-medium">Graph Relationships</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-0.5">
              {graphData?.stats?.total_edges || 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">
              Calls, inherits, contains
            </div>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 col-span-2 sm:col-span-1">
            <div className="text-[11px] text-slate-400 font-medium">Detected Frameworks</div>
            <div className="text-sm font-bold text-white mt-1 truncate" title={summary?.frameworks?.join(", ")}>
              {summary?.frameworks?.length || 0} Active
            </div>
            <div className="text-[10px] text-slate-500 truncate mt-0.5">
              {summary?.frameworks?.slice(0, 2).join(", ") || "Pytest, SQLite"}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 overflow-x-auto">
        <button
          onClick={() => setActiveTab("summary")}
          className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
            activeTab === "summary"
              ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
              : "text-slate-400 hover:text-white bg-slate-900/50 hover:bg-slate-900 border border-slate-800"
          }`}
        >
          <Compass className="w-4 h-4" />
          Repository Intelligence (Phase 5)
        </button>
        <button
          onClick={() => setActiveTab("graph")}
          className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
            activeTab === "graph"
              ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
              : "text-slate-400 hover:text-white bg-slate-900/50 hover:bg-slate-900 border border-slate-800"
          }`}
        >
          <Network className="w-4 h-4" />
          Engineering Code Graph (Phase 6)
        </button>
        <button
          onClick={() => setActiveTab("symbols")}
          className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
            activeTab === "symbols"
              ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
              : "text-slate-400 hover:text-white bg-slate-900/50 hover:bg-slate-900 border border-slate-800"
          }`}
        >
          <Code2 className="w-4 h-4" />
          Symbol Inspector &amp; Callers
        </button>
        <button
          onClick={() => setActiveTab("context")}
          className={`px-3.5 py-2 text-xs font-semibold rounded-xl transition-all flex items-center gap-2 ${
            activeTab === "context"
              ? "bg-cyan-500 text-slate-950 shadow-md font-bold"
              : "text-slate-400 hover:text-white bg-slate-900/50 hover:bg-slate-900 border border-slate-800"
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Context Engine &amp; Token Budget
        </button>
      </div>

      {/* Tab 1: Repository Intelligence Summary (Phase 5) */}
      {activeTab === "summary" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left: Languages & Frameworks */}
            <div className="space-y-4">
              {/* Languages Breakdown */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-cyan-400" />
                  Languages Breakdown
                </h3>
                <div className="space-y-2.5 pt-1">
                  {summary?.language_breakdown &&
                    Object.entries(summary.language_breakdown).map(([lang, count]) => {
                      const fileCount = Number(count) || 0;
                      const total = summary.total_files || 1;
                      const pct = Math.round((fileCount / total) * 100);
                      return (
                        <div key={lang} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="font-medium text-slate-300">{lang}</span>
                            <span className="text-slate-400 font-mono">
                              {fileCount} files ({pct}%)
                            </span>
                          </div>
                          <div className="w-full h-1.5 bg-slate-950 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-cyan-500 rounded-full"
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Detected Frameworks */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Boxes className="w-4 h-4 text-purple-400" />
                  Inferred Tech Stack
                </h3>
                <div className="flex flex-wrap gap-2 pt-1">
                  {summary?.frameworks?.map((fw) => (
                    <span
                      key={fw}
                      className="px-2.5 py-1 bg-purple-500/10 text-purple-300 border border-purple-500/20 text-xs rounded-lg font-medium"
                    >
                      {fw}
                    </span>
                  ))}
                  {summary?.test_frameworks?.map((tf) => (
                    <span
                      key={tf}
                      className="px-2.5 py-1 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs rounded-lg font-medium"
                    >
                      {tf}
                    </span>
                  ))}
                </div>
              </div>

              {/* Entry Points & Test Suites */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Key Entry Points ({summary?.entry_points?.length || 0})
                </h3>
                <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                  {summary?.entry_points?.map((ep) => (
                    <div
                      key={ep}
                      className="px-2.5 py-1.5 bg-slate-950 text-slate-300 font-mono text-[11px] rounded-lg border border-slate-800/80 flex items-center gap-2"
                    >
                      <ArrowRight className="w-3 h-3 text-amber-400 shrink-0" />
                      <span className="truncate">{ep}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Middle & Right: Dependency Manifests & File Catalog (2 Cols) */}
            <div className="lg:col-span-2 space-y-4">
              {/* Manifests Parser */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  Parsed Dependency Manifests ({summary?.manifests?.length || 0})
                </h3>

                {summary?.manifests?.length === 0 ? (
                  <div className="text-xs text-slate-500 py-4 text-center border border-dashed border-slate-800 rounded-xl">
                    No package manifests found in root.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {summary?.manifests?.map((man) => (
                      <div
                        key={man.manifest_file}
                        className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2.5"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs font-bold text-white">
                            {man.manifest_file}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 bg-cyan-500/10 text-cyan-400 rounded-full border border-cyan-500/20">
                            {man.manifest_type}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 max-h-48 overflow-y-auto space-y-1 font-mono">
                          {Object.entries(man.packages).map(([pkg, ver]) => (
                            <div
                              key={pkg}
                              className="flex justify-between py-0.5 border-b border-slate-900"
                            >
                              <span className="text-slate-300 truncate">{pkg}</span>
                              <span className="text-slate-500 text-[10px]">{ver}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Discovered Files Sample */}
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <FolderTree className="w-4 h-4 text-slate-400" />
                    Discovered Code Files ({summary?.total_files || 0})
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">
                    Sample View
                  </span>
                </div>

                <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
                  {summary?.files_sample?.map((f) => (
                    <div
                      key={f.relative_path}
                      className="p-2.5 bg-slate-950/70 hover:bg-slate-950 border border-slate-800/80 rounded-xl flex items-center justify-between text-xs transition-colors"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span className="font-mono text-slate-200 truncate">
                          {f.relative_path}
                        </span>
                        {f.is_test && (
                          <span className="text-[9px] px-1.5 py-0.2 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded">
                            TEST
                          </span>
                        )}
                        {f.is_entry_point && (
                          <span className="text-[9px] px-1.5 py-0.2 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">
                            ENTRY
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-slate-500 font-mono text-[11px] shrink-0">
                        <span>{f.lines_of_code} LOC</span>
                        <span className="text-slate-600">{f.language}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Interactive Engineering Code Graph (Phase 6) */}
      {activeTab === "graph" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Graph Controls & Node List (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div>
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Network className="w-4 h-4 text-cyan-400" />
                    Engineering Graph Nodes ({filteredGraphNodes.length})
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Multi-relational AST code elements with call and inheritance relationships
                  </p>
                </div>

                {/* Filter Selector */}
                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-500" />
                  <select
                    value={selectedTypeFilter}
                    onChange={(e) => setSelectedTypeFilter(e.target.value)}
                    className="text-xs bg-slate-950 text-slate-200 border border-slate-800 rounded-lg px-2.5 py-1.5 focus:outline-none"
                  >
                    <option value="ALL">All Types</option>
                    <option value="CLASS">Classes</option>
                    <option value="FUNCTION">Functions</option>
                    <option value="METHOD">Methods</option>
                    <option value="TEST">Tests</option>
                    <option value="FILE">Files</option>
                  </select>
                </div>
              </div>

              {/* Node Cards */}
              <div className="space-y-2 max-h-[560px] overflow-y-auto pr-1">
                {filteredGraphNodes.map((n) => {
                  const isSelected = selectedGraphNode?.node_id === n.node_id;
                  return (
                    <div
                      key={n.node_id}
                      onClick={() => {
                        setSelectedGraphNode(n);
                        handleSelectSymbol(n);
                      }}
                      className={`p-3 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? "bg-cyan-500/10 border-cyan-500/50 shadow-sm"
                          : "bg-slate-950/60 hover:bg-slate-950 border-slate-800/80"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getNodeBadgeClass(
                                n.node_type
                              )}`}
                            >
                              {n.node_type}
                            </span>
                            <span className="font-mono text-xs font-bold text-white truncate">
                              {n.name}
                            </span>
                            {n.async_function && (
                              <span className="text-[9px] text-cyan-400 font-mono">async</span>
                            )}
                          </div>
                          {n.signature && (
                            <div className="text-[11px] font-mono text-slate-300 truncate bg-slate-900/80 px-2 py-0.5 rounded">
                              {n.signature}
                            </div>
                          )}
                          <div className="text-[11px] text-slate-500 font-mono mt-1 truncate">
                            {n.file_path}:{n.line_start}-{n.line_end}
                          </div>
                        </div>
                        <ChevronRight
                          className={`w-4 h-4 text-slate-500 shrink-0 ${
                            isSelected ? "text-cyan-400 translate-x-0.5" : ""
                          }`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Node & Relationships Inspector (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            {selectedGraphNode ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
                <div className="flex items-start justify-between gap-2 pb-3 border-b border-slate-800">
                  <div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getNodeBadgeClass(
                        selectedGraphNode.node_type
                      )}`}
                    >
                      {selectedGraphNode.node_type}
                    </span>
                    <h4 className="text-base font-bold text-white font-mono mt-1">
                      {selectedGraphNode.name}
                    </h4>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      {selectedGraphNode.file_path}:{selectedGraphNode.line_start}-{selectedGraphNode.line_end}
                    </div>
                  </div>
                </div>

                {/* Signature & Docstring */}
                {selectedGraphNode.signature && (
                  <div className="space-y-1">
                    <div className="text-[11px] text-slate-400 font-medium">Signature</div>
                    <pre className="p-2.5 bg-slate-950 text-cyan-300 font-mono text-xs rounded-xl overflow-x-auto border border-slate-800">
                      {selectedGraphNode.signature}
                    </pre>
                  </div>
                )}

                {selectedGraphNode.docstring && (
                  <div className="space-y-1">
                    <div className="text-[11px] text-slate-400 font-medium">Docstring</div>
                    <div className="p-2.5 bg-slate-950 text-slate-300 text-xs rounded-xl border border-slate-800 leading-relaxed italic">
                      "{selectedGraphNode.docstring}"
                    </div>
                  </div>
                )}

                {/* Callers & Callees */}
                {symbolDetails && (
                  <div className="space-y-3 pt-2 border-t border-slate-800">
                    <div className="text-xs font-semibold text-white">Call Hierarchy</div>

                    <div className="space-y-2">
                      <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
                        <span>Called By ({symbolDetails.callers.length})</span>
                      </div>
                      {symbolDetails.callers.length === 0 ? (
                        <div className="text-[11px] text-slate-500 italic">No incoming calls in graph</div>
                      ) : (
                        <div className="space-y-1 max-h-28 overflow-y-auto">
                          {symbolDetails.callers.map((c) => (
                            <div
                              key={c.node_id}
                              onClick={() => handleSelectSymbol(c)}
                              className="px-2 py-1 bg-slate-950 hover:bg-slate-850 rounded border border-slate-800 text-[11px] font-mono text-slate-300 flex items-center gap-1.5 cursor-pointer"
                            >
                              <ArrowRight className="w-3 h-3 text-cyan-400 shrink-0" />
                              <span className="truncate">{c.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="space-y-2">
                      <div className="text-[11px] text-slate-400 font-medium flex items-center justify-between">
                        <span>Calls Out To ({symbolDetails.callees.length})</span>
                      </div>
                      {symbolDetails.callees.length === 0 ? (
                        <div className="text-[11px] text-slate-500 italic">No outgoing function calls</div>
                      ) : (
                        <div className="space-y-1 max-h-28 overflow-y-auto">
                          {symbolDetails.callees.map((callee, idx) => (
                            <div
                              key={callee.target_id || idx}
                              className="px-2 py-1 bg-slate-950 rounded border border-slate-800 text-[11px] font-mono text-slate-300 flex items-center justify-between"
                            >
                              <span className="truncate text-slate-200">{callee.target_name}</span>
                              {callee.resolved ? (
                                <span className="text-[9px] text-emerald-400">RESOLVED</span>
                              ) : (
                                <span className="text-[9px] text-slate-500">EXT</span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center shadow-sm">
                <Network className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <div className="text-sm font-semibold text-white">Select a Graph Node</div>
                <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                  Click any class, function, method, or file from the list to inspect its AST signatures, docstrings, call hierarchy, and relationships.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Symbol Search & Call Hierarchy (Phase 6) */}
      {activeTab === "symbols" && (
        <div className="space-y-5">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Search className="w-4 h-4 text-cyan-400" />
              Symbol Search &amp; AST Discovery
            </h3>

            <div className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearchSymbols(e.target.value)}
                placeholder="Search symbol by name, docstring, or signature (e.g., 'AutonomousAgentRuntime', 'execute_task', 'TaskStore')..."
                className="w-full text-xs bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
            </div>

            {searchResults.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
                {searchResults.map((sym) => (
                  <div
                    key={sym.node_id}
                    onClick={() => handleSelectSymbol(sym)}
                    className="p-3.5 bg-slate-950/70 hover:bg-slate-950 border border-slate-800 rounded-xl cursor-pointer transition-colors space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-white truncate">
                        {sym.name}
                      </span>
                      <span
                        className={`text-[9px] font-semibold px-2 py-0.5 rounded-full border ${getNodeBadgeClass(
                          sym.node_type
                        )}`}
                      >
                        {sym.node_type}
                      </span>
                    </div>
                    {sym.signature && (
                      <div className="text-[11px] font-mono text-cyan-400 truncate">
                        {sym.signature}
                      </div>
                    )}
                    <div className="text-[10px] text-slate-500 font-mono truncate">
                      {sym.file_path}:{sym.line_start}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 4: Context Engine & Token Budget Assembler */}
      {activeTab === "context" && (
        <div className="space-y-5">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                Task-Specific Context Engine &amp; Token Budget Assembler
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Simulates how the Droid analyzes natural language tasks to assemble high-signal repository summaries, symbols, and code excerpts within strict token limits.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={taskRequirement}
                onChange={(e) => setTaskRequirement(e.target.value)}
                placeholder="Enter engineering task requirement..."
                className="flex-1 text-xs bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleSimulateContext}
                disabled={contextLoading}
                className="px-4 py-2.5 text-xs font-semibold bg-cyan-600 hover:bg-cyan-700 text-white rounded-xl transition-colors flex items-center gap-2 shrink-0 shadow-sm"
              >
                <Sparkles className={`w-4 h-4 ${contextLoading ? "animate-spin" : ""}`} />
                Assemble Context
              </button>
            </div>

            {contextPkg && (
              <div className="space-y-4 pt-4 border-t border-slate-800">
                {/* Budget Summary Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Estimated Tokens</div>
                    <div className="text-lg font-bold text-cyan-400 font-mono mt-0.5">
                      {contextPkg.estimated_tokens.toLocaleString()}
                    </div>
                    <div className="text-[10px] text-slate-500">Target Budget: 32,000</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Matched Symbols</div>
                    <div className="text-lg font-bold text-purple-400 font-mono mt-0.5">
                      {contextPkg.symbols.length}
                    </div>
                    <div className="text-[10px] text-slate-500">From Engineering Graph</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Relevant Files Injected</div>
                    <div className="text-lg font-bold text-emerald-400 font-mono mt-0.5">
                      {Object.keys(contextPkg.relevant_files).length}
                    </div>
                    <div className="text-[10px] text-slate-500">Ranked by relevance</div>
                  </div>

                  <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Repository Files</div>
                    <div className="text-lg font-bold text-white font-mono mt-0.5">
                      {contextPkg.repository_summary.total_files}
                    </div>
                    <div className="text-[10px] text-slate-500">Indexed for Droid</div>
                  </div>
                </div>

                {/* Injected Symbols & File Excerpts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* Symbols */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                    <div className="text-xs font-semibold text-white">Injected AST Symbols</div>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                      {contextPkg.symbols.map((sym) => (
                        <div
                          key={sym.node_id}
                          className="p-2 bg-slate-900 rounded-lg text-xs font-mono flex items-center justify-between"
                        >
                          <span className="text-cyan-300 font-bold truncate">{sym.name}</span>
                          <span className="text-[10px] text-slate-500">{sym.file_path}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* File Excerpts */}
                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
                    <div className="text-xs font-semibold text-white">Relevant File Payloads</div>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                      {Object.entries(contextPkg.relevant_files).map(([fPath, content]) => (
                        <div key={fPath} className="p-2 bg-slate-900 rounded-lg text-xs space-y-1">
                          <div className="font-mono text-slate-300 font-bold">{fPath}</div>
                          <pre className="text-[10px] font-mono text-slate-400 max-h-20 overflow-hidden text-ellipsis">
                            {String(content).slice(0, 160)}...
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

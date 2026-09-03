import React, { useState, useEffect } from 'react';
import {
  GitBranch,
  GitPullRequest,
  FolderGit2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Wrench,
  RefreshCw,
  Copy,
  Check,
  Plus,
  Trash2,
  ShieldCheck,
  Zap,
  Terminal,
  FileCode,
  Layers,
  ArrowRight,
} from 'lucide-react';

interface BranchItem {
  name: string;
  is_current: boolean;
  commit_hash: string;
  upstream?: string;
  ahead?: number;
  behind?: number;
}

interface WorktreeItem {
  worktree_id: string;
  branch: string;
  path: string;
  is_locked: boolean;
  task_id?: string;
  created_at: number;
}

interface CIStage {
  stage_id: string;
  name: string;
  command: string;
  status: 'passed' | 'failed' | 'healed' | 'pending';
  duration_ms: number;
  logs: string;
  error_signature?: string;
  healed_diff?: string;
}

interface CIPipeline {
  pipeline_id: string;
  branch: string;
  commit_hash: string;
  status: 'passed' | 'failed' | 'healed' | 'running';
  stages: CIStage[];
  healing_attempts: number;
  healed_patch?: string;
  duration_sec: number;
}

interface PRSpec {
  pr_id: string;
  title: string;
  branch_source: string;
  branch_target: string;
  problem_statement: string;
  architectural_approach: string;
  files_changed: Array<{
    path: string;
    action: string;
    ast_symbols: string[];
    risk: string;
  }>;
  test_verification: {
    total_tests: number;
    passed_tests: number;
    coverage_pct: number;
    duration_sec: number;
  };
  risk_assessment: {
    risk_level: string;
    breaking_changes: boolean;
    security_audited: boolean;
    rollback_plan: string;
  };
  checklist: string[];
  markdown_body: string;
}

export function GitPRStudio() {
  const [activeSubTab, setActiveSubTab] = useState<'ci' | 'pr' | 'branches' | 'worktrees'>('ci');
  const [branches, setBranches] = useState<BranchItem[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string>('main');
  const [worktrees, setWorktrees] = useState<WorktreeItem[]>([]);
  const [pipeline, setPipeline] = useState<CIPipeline | null>(null);
  const [prSpec, setPrSpec] = useState<PRSpec | null>(null);
  const [prMarkdown, setPrMarkdown] = useState<string>('');

  const [loading, setLoading] = useState<boolean>(false);
  const [ciLoading, setCiLoading] = useState<boolean>(false);
  const [healLoading, setHealLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  // Form states
  const [newBranchName, setNewBranchName] = useState<string>('feat/smart-retries');
  const [newWorktreeBranch, setNewWorktreeBranch] = useState<string>('feat/isolated-agent');
  const [prTitle, setPrTitle] = useState<string>('feat(mcp): universal client tool gateway');
  const [prSourceBranch, setPrSourceBranch] = useState<string>('feat/mcp-gateway');
  const [prObjective, setPrObjective] = useState<string>(
    'Implement dual-role MCP server and external tool federation for remote microservices.'
  );
  const [selectedSimulateFailure, setSelectedSimulateFailure] = useState<string>('unit_tests');

  useEffect(() => {
    fetchBranches();
    fetchWorktrees();
    runCIPipeline('main');
    generatePR();
  }, []);

  const fetchBranches = async () => {
    try {
      const res = await fetch('/api/git/branches');
      const data = await res.json();
      if (data.success && data.branches) {
        setBranches(data.branches);
        setCurrentBranch(data.current_branch || 'main');
      }
    } catch (err) {
      console.error('Failed to fetch branches:', err);
    }
  };

  const fetchWorktrees = async () => {
    try {
      const res = await fetch('/api/git/worktrees');
      const data = await res.json();
      if (data.success && data.worktrees) {
        setWorktrees(data.worktrees);
      }
    } catch (err) {
      console.error('Failed to fetch worktrees:', err);
    }
  };

  const createBranch = async () => {
    if (!newBranchName.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/git/create-branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newBranchName.trim(), switch: true }),
      });
      const data = await res.json();
      if (data.success) {
        fetchBranches();
        setNewBranchName('');
      }
    } catch (err) {
      console.error('Failed to create branch:', err);
    } finally {
      setLoading(false);
    }
  };

  const switchBranch = async (name: string) => {
    setLoading(true);
    try {
      const res = await fetch('/api/git/switch-branch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (data.success) {
        fetchBranches();
      }
    } catch (err) {
      console.error('Failed to switch branch:', err);
    } finally {
      setLoading(false);
    }
  };

  const createWorktree = async () => {
    if (!newWorktreeBranch.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/git/create-worktree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch: newWorktreeBranch.trim(),
          task_id: `task-${Date.now().toString().slice(-4)}`,
        }),
      });
      const data = await res.json();
      if (data.success) {
        fetchWorktrees();
      }
    } catch (err) {
      console.error('Failed to create worktree:', err);
    } finally {
      setLoading(false);
    }
  };

  const removeWorktree = async (worktreeId: string) => {
    try {
      const res = await fetch('/api/git/remove-worktree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ worktree_id: worktreeId }),
      });
      const data = await res.json();
      if (data.success) {
        fetchWorktrees();
      }
    } catch (err) {
      console.error('Failed to remove worktree:', err);
    }
  };

  const runCIPipeline = async (branchName: string, simFailure?: string) => {
    setCiLoading(true);
    try {
      const res = await fetch('/api/git/run-ci', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch: branchName,
          simulate_failure_stage: simFailure || undefined,
        }),
      });
      const data = await res.json();
      if (data.success && data.pipeline) {
        setPipeline(data.pipeline);
      }
    } catch (err) {
      console.error('Failed to run CI pipeline:', err);
    } finally {
      setCiLoading(false);
    }
  };

  const healCIPipeline = async () => {
    if (!pipeline) return;
    setHealLoading(true);
    try {
      const failedStage =
        pipeline.stages.find((s) => s.status === 'failed')?.stage_id || 'unit_tests';
      const res = await fetch('/api/git/heal-ci', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch: pipeline.branch,
          failed_stage: failedStage,
        }),
      });
      const data = await res.json();
      if (data.success && data.healed_pipeline) {
        setPipeline(data.healed_pipeline);
      }
    } catch (err) {
      console.error('Failed to heal CI pipeline:', err);
    } finally {
      setHealLoading(false);
    }
  };

  const generatePR = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/git/generate-pr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: prTitle,
          branch_source: prSourceBranch,
          branch_target: 'main',
          task_objective: prObjective,
        }),
      });
      const data = await res.json();
      if (data.success && data.pr) {
        setPrSpec(data.pr);
        setPrMarkdown(data.markdown);
      }
    } catch (err) {
      console.error('Failed to synthesize PR:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyMarkdown = () => {
    if (!prMarkdown) return;
    navigator.clipboard.writeText(prMarkdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 font-mono">Active Branch</span>
            <GitBranch className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-lg font-bold text-white font-mono flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            {currentBranch}
          </div>
          <p className="text-xs text-slate-500 mt-1">Upstream: origin/{currentBranch}</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 font-mono">Worktree Sandboxes</span>
            <FolderGit2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-white font-mono">
            {worktrees.length} <span className="text-xs font-normal text-slate-400">Isolated Roots</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">Zero-collision agent execution</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 font-mono">CI/CD Engine</span>
            <ShieldCheck className="w-4 h-4 text-blue-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-white font-mono flex items-center gap-2">
            {pipeline?.status === 'passed' && (
              <span className="text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> PASSED
              </span>
            )}
            {pipeline?.status === 'healed' && (
              <span className="text-amber-400 flex items-center gap-1">
                <Wrench className="w-4 h-4" /> HEALED
              </span>
            )}
            {pipeline?.status === 'failed' && (
              <span className="text-rose-400 flex items-center gap-1">
                <XCircle className="w-4 h-4" /> FAILED
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">5-Stage matrix with closed-loop heal</p>
        </div>

        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400 font-mono">PR Synthesizer</span>
            <GitPullRequest className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-2 text-xl font-bold text-white font-mono">
            AST Risk: <span className="text-emerald-400 font-bold">{prSpec?.risk_assessment.risk_level || 'LOW'}</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">{prSpec?.files_changed.length || 0} modified AST files</p>
        </div>
      </div>

      {/* Sub-Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          id="tab-ci"
          onClick={() => setActiveSubTab('ci')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeSubTab === 'ci'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          5-Stage CI/CD Matrix &amp; Self-Healing
        </button>

        <button
          id="tab-pr"
          onClick={() => setActiveSubTab('pr')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeSubTab === 'pr'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <GitPullRequest className="w-4 h-4 text-purple-400" />
          Autonomous PR Synthesizer &amp; Markdown
        </button>

        <button
          id="tab-branches"
          onClick={() => setActiveSubTab('branches')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeSubTab === 'branches'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <GitBranch className="w-4 h-4 text-emerald-400" />
          Git Branches ({branches.length})
        </button>

        <button
          id="tab-worktrees"
          onClick={() => setActiveSubTab('worktrees')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all ${
            activeSubTab === 'worktrees'
              ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
          }`}
        >
          <FolderGit2 className="w-4 h-4 text-indigo-400" />
          Worktree Sandboxes ({worktrees.length})
        </button>
      </div>

      {/* SUB-VIEW 1: CI/CD Runner & Closed-Loop Healing */}
      {activeSubTab === 'ci' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-blue-400" />
                  Continuous Integration &amp; Autonomous Self-Healing Pipeline
                </h3>
                <p className="text-xs text-slate-400 mt-1">
                  Executes AST validation, path security audit, 145 unit tests, 6D quality gate, and build packaging.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-lg text-xs">
                  <span className="text-slate-400">Simulate Breakage:</span>
                  <select
                    value={selectedSimulateFailure}
                    onChange={(e) => setSelectedSimulateFailure(e.target.value)}
                    className="bg-transparent text-slate-200 font-mono focus:outline-none"
                  >
                    <option value="unit_tests" className="bg-slate-900">Unit Tests (AssertionError)</option>
                    <option value="syntax_ast" className="bg-slate-900">Syntax / AST (SyntaxError)</option>
                    <option value="security_audit" className="bg-slate-900">Security Audit (Traversal)</option>
                    <option value="quality_gate" className="bg-slate-900">Quality Gate (&lt;80.0)</option>
                  </select>
                </div>

                <button
                  id="btn-run-ci-break"
                  onClick={() => runCIPipeline(currentBranch, selectedSimulateFailure)}
                  disabled={ciLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/60 text-rose-300 border border-rose-800/80 hover:bg-rose-900/60 flex items-center gap-1.5 transition-all"
                >
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Simulate Failure
                </button>

                <button
                  id="btn-run-ci-clean"
                  onClick={() => runCIPipeline(currentBranch)}
                  disabled={ciLoading}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 text-white hover:bg-blue-500 flex items-center gap-1.5 transition-all shadow-sm"
                >
                  {ciLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  Run All 5 Stages
                </button>

                {pipeline?.status === 'failed' && (
                  <button
                    id="btn-heal-ci"
                    onClick={healCIPipeline}
                    disabled={healLoading}
                    className="px-4 py-1.5 rounded-lg text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 text-white hover:from-emerald-500 hover:to-teal-500 flex items-center gap-1.5 transition-all shadow-md shadow-emerald-950 animate-pulse"
                  >
                    {healLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Wrench className="w-3.5 h-3.5" />}
                    Autonomous Self-Heal
                  </button>
                )}
              </div>
            </div>

            {/* Pipeline Stage Cards */}
            {pipeline && (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between text-xs text-slate-400 font-mono border-b border-slate-800 pb-2">
                  <div>Pipeline Run ID: <span className="text-white">{pipeline.pipeline_id}</span></div>
                  <div>Status: <span className={`font-bold ${pipeline.status === 'passed' ? 'text-emerald-400' : pipeline.status === 'healed' ? 'text-amber-400' : 'text-rose-400'}`}>{pipeline.status.toUpperCase()}</span></div>
                  <div>Repairs Applied: <span className="text-indigo-400 font-bold">{pipeline.healing_attempts}</span></div>
                </div>

                <div className="grid grid-cols-1 gap-3">
                  {pipeline.stages.map((st) => {
                    const isPassed = st.status === 'passed';
                    const isHealed = st.status === 'healed';
                    const isFailed = st.status === 'failed';

                    return (
                      <div
                        key={st.stage_id}
                        className={`p-4 rounded-xl border transition-all ${
                          isPassed
                            ? 'bg-slate-950/80 border-slate-800/80'
                            : isHealed
                            ? 'bg-amber-950/20 border-amber-800/60'
                            : 'bg-rose-950/20 border-rose-800/60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {isPassed && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                            {isHealed && <Wrench className="w-4 h-4 text-amber-400" />}
                            {isFailed && <XCircle className="w-4 h-4 text-rose-400" />}
                            <div>
                              <div className="text-sm font-semibold text-white">{st.name}</div>
                              <div className="text-xs text-slate-500 font-mono">{st.command}</div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <span className="text-xs font-mono text-slate-400">{st.duration_ms.toFixed(1)}ms</span>
                            <span
                              className={`text-xs font-bold font-mono px-2 py-0.5 rounded ${
                                isPassed
                                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/50'
                                  : isHealed
                                  ? 'bg-amber-950/80 text-amber-400 border border-amber-800/50'
                                  : 'bg-rose-950/80 text-rose-400 border border-rose-800/50'
                              }`}
                            >
                              {st.status.toUpperCase()}
                            </span>
                          </div>
                        </div>

                        <div className="mt-3 bg-slate-950 rounded-lg p-3 font-mono text-xs text-slate-300 border border-slate-900 leading-relaxed whitespace-pre-wrap">
                          {st.logs}
                        </div>

                        {st.error_signature && isFailed && (
                          <div className="mt-2 bg-rose-950/40 border border-rose-900/60 rounded-lg p-3 text-xs font-mono text-rose-200">
                            <div className="font-bold flex items-center gap-1.5 text-rose-400 mb-1">
                              <AlertTriangle className="w-3.5 h-3.5" /> Error Signature Detected:
                            </div>
                            {st.error_signature}
                          </div>
                        )}

                        {st.healed_diff && (
                          <div className="mt-2 bg-emerald-950/30 border border-emerald-900/50 rounded-lg p-3 text-xs font-mono text-emerald-200">
                            <div className="font-bold flex items-center gap-1.5 text-emerald-400 mb-1">
                              <Zap className="w-3.5 h-3.5" /> Autonomous Self-Healing Patch Applied:
                            </div>
                            <pre className="overflow-x-auto text-[11px] text-emerald-300">{st.healed_diff}</pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-VIEW 2: PR Synthesizer & Markdown */}
      {activeSubTab === 'pr' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Controls & Spec Form */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <GitPullRequest className="w-5 h-5 text-purple-400" />
              Autonomous PR Synthesizer Parameters
            </h3>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-300">PR Title</label>
                <input
                  type="text"
                  value={prTitle}
                  onChange={(e) => setPrTitle(e.target.value)}
                  className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold text-slate-300">Source Branch</label>
                  <input
                    type="text"
                    value={prSourceBranch}
                    onChange={(e) => setPrSourceBranch(e.target.value)}
                    className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-purple-500"
                  />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-300">Target Branch</label>
                  <input
                    type="text"
                    disabled
                    value="main"
                    className="mt-1 w-full bg-slate-950/60 border border-slate-800/60 rounded-lg px-3 py-2 text-xs font-mono text-slate-400"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Task Objective</label>
                <textarea
                  rows={3}
                  value={prObjective}
                  onChange={(e) => setPrObjective(e.target.value)}
                  className="mt-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-purple-500"
                />
              </div>

              <button
                id="btn-synth-pr"
                onClick={generatePR}
                disabled={loading}
                className="w-full py-2 rounded-lg text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white flex items-center justify-center gap-2 transition-all shadow-md shadow-purple-950"
              >
                {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Synthesize AST-Backed Pull Request
              </button>
            </div>

            {/* AST Symbol Impact Table */}
            {prSpec && (
              <div className="pt-3 border-t border-slate-800 space-y-2">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
                  Modified Files &amp; AST Symbols ({prSpec.files_changed.length})
                </div>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {prSpec.files_changed.map((f, i) => (
                    <div key={i} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-mono text-white font-semibold flex items-center gap-1.5">
                          <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                          {f.path}
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900">
                          {f.risk} RISK
                        </span>
                      </div>
                      <div className="mt-1 text-slate-400 text-[11px] font-mono">
                        Symbols: {f.ast_symbols.join(', ')}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Rendered Markdown Preview & Copy */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3 flex flex-col">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Terminal className="w-5 h-5 text-indigo-400" />
                Synthesized PR Markdown
              </h3>
              <button
                id="btn-copy-pr"
                onClick={handleCopyMarkdown}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? 'Copied' : 'Copy Markdown'}
              </button>
            </div>

            <div className="flex-1 bg-slate-950 p-4 rounded-xl border border-slate-800 font-mono text-xs text-slate-300 overflow-y-auto max-h-[540px] leading-relaxed whitespace-pre-wrap">
              {prMarkdown || 'Click "Synthesize AST-Backed Pull Request" to generate markdown...'}
            </div>
          </div>
        </div>
      )}

      {/* SUB-VIEW 3: Git Branch Operations */}
      {activeSubTab === 'branches' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <GitBranch className="w-5 h-5 text-emerald-400" />
                Autonomous Branch Management
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Conventional branch naming validation, upstream tracking, and branch switching.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="feat/new-branch-name"
                value={newBranchName}
                onChange={(e) => setNewBranchName(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-emerald-500"
              />
              <button
                id="btn-create-branch"
                onClick={createBranch}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                Create &amp; Switch
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 pt-2">
            {branches.map((b) => (
              <div
                key={b.name}
                className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                  b.is_current
                    ? 'bg-slate-950 border-emerald-600/60 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      b.is_current ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'
                    }`}
                  ></span>
                  <div>
                    <div className="font-mono text-sm text-white font-semibold flex items-center gap-2">
                      {b.name}
                      {b.is_current && (
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                          Active HEAD
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 font-mono">
                      Commit: {b.commit_hash} | Upstream: {b.upstream || 'none'}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!b.is_current && (
                    <button
                      id={`btn-switch-${b.name.replace('/', '-')}`}
                      onClick={() => switchBranch(b.name)}
                      disabled={loading}
                      className="px-3 py-1 rounded text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
                    >
                      Switch To
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SUB-VIEW 4: Worktree Sandboxes */}
      {activeSubTab === 'worktrees' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FolderGit2 className="w-5 h-5 text-indigo-400" />
                Git Worktree Sandboxes for Isolated Multi-Agent Execution
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                Allows autonomous agents to perform refactorings, test diagnostics, and builds without mutating main workspace.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="feat/isolated-agent"
                value={newWorktreeBranch}
                onChange={(e) => setNewWorktreeBranch(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-indigo-500"
              />
              <button
                id="btn-create-worktree"
                onClick={createWorktree}
                disabled={loading}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-all shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                Spawn Sandbox
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-2 pt-2">
            {worktrees.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-xs font-mono bg-slate-950 rounded-xl border border-slate-800">
                No active worktree sandboxes. Click &quot;Spawn Sandbox&quot; to initialize an isolated filesystem sandbox.
              </div>
            ) : (
              worktrees.map((w) => (
                <div
                  key={w.worktree_id}
                  className="p-3.5 rounded-lg border border-slate-800 bg-slate-950 flex items-center justify-between"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold text-white">{w.branch}</span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-900">
                        {w.worktree_id}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 font-mono truncate max-w-md">Path: {w.path}</div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      id={`btn-remove-worktree-${w.worktree_id}`}
                      onClick={() => removeWorktree(w.worktree_id)}
                      className="p-1.5 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-950/40 transition-all"
                      title="Prune Sandbox"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

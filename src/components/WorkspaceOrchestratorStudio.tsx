import React, { useState, useEffect } from 'react';
import {
  GitPullRequest,
  GitBranch,
  GitCommit,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  FileCode2,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  Send,
  Sliders,
  Layers,
  FileDiff,
  Flame,
  ArrowRight,
  ShieldCheck,
  Lock,
} from 'lucide-react';
import { Changeset, ApprovalRequest, RefactorPlan } from '../types';

export const WorkspaceOrchestratorStudio: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'refactor' | 'changesets' | 'approvals' | 'pr_preview'>('refactor');
  
  // Refactor State
  const [oldSymbol, setOldSymbol] = useState('DiagnosticReasoner');
  const [newSymbol, setNewSymbol] = useState('SmartDiagnosticReasoner');
  const [targetScope, setTargetScope] = useState('workspace');
  const [refactorLoading, setRefactorLoading] = useState(false);
  const [refactorPlan, setRefactorPlan] = useState<RefactorPlan | null>(null);

  // Changesets State
  const [changesets, setChangesets] = useState<Changeset[]>([]);
  const [selectedChangeset, setSelectedChangeset] = useState<Changeset | null>(null);
  const [changesetLoading, setChangesetLoading] = useState(false);
  const [commitLoading, setCommitLoading] = useState(false);
  const [commitResult, setCommitResult] = useState<any | null>(null);

  // New Changeset Modal / Form
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newBranch, setNewBranch] = useState('');

  // Human Approvals State
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [approvalFilter, setApprovalFilter] = useState<'ALL' | 'PENDING' | 'APPROVED' | 'REJECTED'>('ALL');
  const [approvalsLoading, setApprovalsLoading] = useState(false);
  const [operatorReason, setOperatorReason] = useState('Authorized by Lead Software Architect');
  const [copiedPr, setCopiedPr] = useState(false);

  // Load initial data
  useEffect(() => {
    fetchChangesets();
    fetchApprovals();
  }, []);

  const fetchChangesets = async () => {
    setChangesetLoading(true);
    try {
      const res = await fetch('/api/orchestrator/changesets');
      const data = await res.json();
      if (data.success && data.changesets) {
        setChangesets(data.changesets);
        if (data.changesets.length > 0 && !selectedChangeset) {
          setSelectedChangeset(data.changesets[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch changesets:', e);
    } finally {
      setChangesetLoading(false);
    }
  };

  const fetchApprovals = async () => {
    setApprovalsLoading(true);
    try {
      const res = await fetch('/api/orchestrator/approvals');
      const data = await res.json();
      if (data.success && data.requests) {
        setApprovals(data.requests);
      }
    } catch (e) {
      console.error('Failed to fetch approvals:', e);
    } finally {
      setApprovalsLoading(false);
    }
  };

  const handlePlanRefactor = async () => {
    if (!oldSymbol || !newSymbol) return;
    setRefactorLoading(true);
    try {
      const res = await fetch('/api/orchestrator/refactor/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          oldName: oldSymbol,
          newName: newSymbol,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setRefactorPlan(data.plan);
        if (data.changeset) {
          setSelectedChangeset(data.changeset);
          fetchChangesets();
        }
      }
    } catch (e) {
      console.error('Refactor planning failed:', e);
    } finally {
      setRefactorLoading(false);
    }
  };

  const handleCreateChangeset = async () => {
    if (!newTitle) return;
    try {
      const res = await fetch('/api/orchestrator/changesets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle,
          description: newDesc,
          branchName: newBranch || undefined,
        }),
      });
      const data = await res.json();
      if (data.success && data.changeset) {
        setNewTitle('');
        setNewDesc('');
        setNewBranch('');
        fetchChangesets();
        setSelectedChangeset(data.changeset);
        setActiveTab('changesets');
      }
    } catch (e) {
      console.error('Create changeset failed:', e);
    }
  };

  const handleApplyChangeset = async (cid: string) => {
    setCommitLoading(true);
    try {
      const res = await fetch('/api/orchestrator/changesets/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ changesetId: cid }),
      });
      const data = await res.json();
      setCommitResult(data);
      fetchChangesets();
    } catch (e) {
      console.error('Apply changeset failed:', e);
    } finally {
      setCommitLoading(false);
    }
  };

  const handleDecideApproval = async (requestId: string, decision: 'APPROVED' | 'REJECTED') => {
    try {
      const res = await fetch('/api/orchestrator/approvals/decide', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requestId,
          decision,
          reason: operatorReason,
          approver: 'lead_security_architect',
        }),
      });
      const data = await res.json();
      if (data.success) {
        fetchApprovals();
      }
    } catch (e) {
      console.error('Approval decision failed:', e);
    }
  };

  const handleCopyPr = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPr(true);
    setTimeout(() => setCopiedPr(false), 2000);
  };

  const filteredApprovals = approvals.filter(
    (a) => approvalFilter === 'ALL' || a.status === approvalFilter
  );

  return (
    <div id="workspace-orchestrator-root" className="space-y-6">
      {/* Top Banner */}
      <div id="orchestrator-header" className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden shadow-lg">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <GitPullRequest className="w-48 h-48 text-indigo-400" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                <GitBranch className="w-3.5 h-3.5" /> Phase 11 & 12 Autonomous Engine
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" /> AST-Validated Atomic Staging
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Autonomous Workspace Orchestrator & Refactoring Studio
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              End-to-end multi-file refactoring, atomic staging changesets, AST syntax safety gates, and Human-in-the-Loop governance.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              id="refresh-orchestrator-btn"
              onClick={() => {
                fetchChangesets();
                fetchApprovals();
              }}
              className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-sm font-medium flex items-center gap-2 transition"
            >
              <RefreshCw className="w-4 h-4" /> Sync Registry
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-800 overflow-x-auto">
          <button
            id="tab-refactor-btn"
            onClick={() => setActiveTab('refactor')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              activeTab === 'refactor'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Sliders className="w-4 h-4" /> Multi-File Refactor
          </button>
          <button
            id="tab-changesets-btn"
            onClick={() => setActiveTab('changesets')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              activeTab === 'changesets'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <Layers className="w-4 h-4" /> Atomic Changesets
            <span className="px-1.5 py-0.5 rounded-full text-xs bg-slate-800 text-slate-300 border border-slate-700">
              {changesets.length}
            </span>
          </button>
          <button
            id="tab-approvals-btn"
            onClick={() => setActiveTab('approvals')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              activeTab === 'approvals'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <ShieldAlert className="w-4 h-4" /> Human Review Gates
            {approvals.filter((a) => a.status === 'PENDING').length > 0 && (
              <span className="px-1.5 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {approvals.filter((a) => a.status === 'PENDING').length} pending
              </span>
            )}
          </button>
          <button
            id="tab-pr-preview-btn"
            onClick={() => setActiveTab('pr_preview')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition flex items-center gap-2 ${
              activeTab === 'pr_preview'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <GitPullRequest className="w-4 h-4" /> PR & Changelog Synthesizer
          </button>
        </div>
      </div>

      {/* Tab 1: Multi-File Refactoring Engine */}
      {activeTab === 'refactor' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2 text-white font-semibold text-base border-b border-slate-800 pb-3">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <span>Symbol Renamer & AST Plan</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Target Old Symbol
              </label>
              <input
                id="refactor-old-symbol-input"
                type="text"
                value={oldSymbol}
                onChange={(e) => setOldSymbol(e.target.value)}
                placeholder="e.g. DiagnosticReasoner"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Replacement Symbol Name
              </label>
              <input
                id="refactor-new-symbol-input"
                type="text"
                value={newSymbol}
                onChange={(e) => setNewSymbol(e.target.value)}
                placeholder="e.g. SmartDiagnosticReasoner"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Scan Scope
              </label>
              <select
                value={targetScope}
                onChange={(e) => setTargetScope(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
              >
                <option value="workspace">Entire Workspace Repository (*.py, *.ts)</option>
                <option value="diagnostics">app/diagnostics/ only</option>
                <option value="tools">app/tools/ only</option>
              </select>
            </div>

            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-400 space-y-1">
              <div className="font-medium text-slate-300 flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-indigo-400" /> Safety Invariants:
              </div>
              <div>• Exact identifier word boundary matching (`\b`)</div>
              <div>• Pre-execution AST parse verification per file</div>
              <div>• Staged into atomic rollback-capable changeset</div>
            </div>

            <button
              id="execute-refactor-plan-btn"
              onClick={handlePlanRefactor}
              disabled={refactorLoading || !oldSymbol || !newSymbol}
              className="w-full py-2.5 px-4 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition flex items-center justify-center gap-2 shadow"
            >
              {refactorLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Analyzing AST Traces...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" /> Plan & Stage Multi-File Refactor
                </>
              )}
            </button>
          </div>

          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <FileCode2 className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-white">Refactor Plan & AST Verification Matrix</h3>
              </div>
              {refactorPlan && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  {refactorPlan.total_modifications} occurrences across {refactorPlan.affected_files.length} files
                </span>
              )}
            </div>

            {refactorPlan ? (
              <div className="space-y-4">
                <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-lg">
                  <div className="text-xs font-medium text-slate-400 uppercase">Operation Target</div>
                  <div className="text-sm font-mono text-indigo-300 mt-0.5">{refactorPlan.details}</div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="w-3.5 h-3.5" /> AST Validated: {refactorPlan.all_syntax_valid ? '100% Passed' : 'Failures Detected'}
                    </span>
                    <span>Refactor ID: {refactorPlan.refactor_id}</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Affected Repository Files
                  </div>
                  {refactorPlan.affected_files.map((file, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <FileDiff className="w-4 h-4 text-slate-400" />
                        <span className="font-mono text-slate-200 text-xs">{file.file_path}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="px-2 py-0.5 rounded text-xs bg-indigo-500/20 text-indigo-300 font-mono">
                          {file.occurrences_found} replacements
                        </span>
                        {file.syntax_valid ? (
                          <span className="px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 flex items-center gap-1">
                            <Check className="w-3 h-3" /> Syntax OK
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-xs bg-rose-500/20 text-rose-300 flex items-center gap-1">
                            <XCircle className="w-3 h-3" /> Syntax Error
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                  <span className="text-xs text-slate-400">
                    Staged into changeset ready for atomic write or PR generation.
                  </span>
                  <button
                    onClick={() => setActiveTab('changesets')}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 transition"
                  >
                    View in Changeset Explorer <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center py-16 text-center text-slate-500">
                <FileCode2 className="w-12 h-12 text-slate-600 mb-3" />
                <p className="text-sm font-medium text-slate-400">No active refactoring plan generated</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Specify an old identifier and replacement symbol on the left to analyze dependencies and stage changes across the repository.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Atomic Changesets Explorer */}
      {activeTab === 'changesets' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Changeset List */}
          <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" /> Active Changesets
              </h3>
              <span className="text-xs text-slate-400">{changesets.length} total</span>
            </div>

            {/* Quick Create Changeset */}
            <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
              <div className="text-xs font-semibold text-slate-300">Create New Changeset</div>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Title e.g. Fix SQLite Cascade Deletion"
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-indigo-500"
              />
              <input
                type="text"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Description of changes"
                className="w-full px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
              />
              <button
                onClick={handleCreateChangeset}
                disabled={!newTitle}
                className="w-full py-1.5 px-3 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 text-xs font-medium rounded border border-slate-700 transition"
              >
                + Initialize Changeset
              </button>
            </div>

            <div className="space-y-2 max-h-[420px] overflow-y-auto">
              {changesets.map((cs) => (
                <div
                  key={cs.changeset_id}
                  onClick={() => setSelectedChangeset(cs)}
                  className={`p-3 rounded-lg border text-left cursor-pointer transition ${
                    selectedChangeset?.changeset_id === cs.changeset_id
                      ? 'bg-indigo-950/40 border-indigo-500/50 shadow-sm'
                      : 'bg-slate-950 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-mono text-indigo-400 font-semibold">{cs.changeset_id}</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        cs.status === 'COMMITTED'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {cs.status}
                    </span>
                  </div>
                  <div className="text-sm font-medium text-white line-clamp-1">{cs.title}</div>
                  <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                    <span>{cs.total_files} files</span>
                    <span className="text-emerald-400">+{cs.total_additions}</span>
                    <span className="text-rose-400">-{cs.total_deletions}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Changeset Detail & Unified Diff */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            {selectedChangeset ? (
              <>
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-indigo-400 bg-indigo-950/50 px-2 py-0.5 rounded border border-indigo-800">
                        {selectedChangeset.changeset_id}
                      </span>
                      <h3 className="font-bold text-white text-lg">{selectedChangeset.title}</h3>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-mono">
                      <span className="flex items-center gap-1">
                        <GitBranch className="w-3.5 h-3.5 text-indigo-400" /> {selectedChangeset.branch_name}
                      </span>
                      <span>• Created: {new Date(selectedChangeset.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      id="apply-changeset-btn"
                      onClick={() => handleApplyChangeset(selectedChangeset.changeset_id)}
                      disabled={commitLoading || selectedChangeset.status === 'COMMITTED'}
                      className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                    >
                      {commitLoading ? (
                        <>
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Applying Atomically...
                        </>
                      ) : selectedChangeset.status === 'COMMITTED' ? (
                        <>
                          <Check className="w-3.5 h-3.5" /> Committed to Workspace
                        </>
                      ) : (
                        <>
                          <GitCommit className="w-3.5 h-3.5" /> Atomic Commit to Workspace
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {commitResult && (
                  <div className="p-3 bg-emerald-950/40 border border-emerald-500/40 rounded-lg text-xs text-emerald-200">
                    ✅ Changeset successfully applied! {commitResult.files_written?.length || 0} files written atomically.
                  </div>
                )}

                {/* Staged Files List with Diffs */}
                <div className="space-y-3">
                  <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Staged Unified Diffs & AST Invariants ({selectedChangeset.files.length} files)
                  </div>
                  {selectedChangeset.files.map((file, idx) => (
                    <div key={idx} className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden">
                      <div className="p-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2 font-mono text-slate-200 font-medium">
                          <FileCode2 className="w-4 h-4 text-indigo-400" />
                          <span>{file.file_path}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-emerald-400 font-mono">+{file.additions}</span>
                          <span className="text-rose-400 font-mono">-{file.deletions}</span>
                          {file.syntax_valid ? (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-medium">
                              AST Valid
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 font-medium">
                              Syntax Error: {file.syntax_error}
                            </span>
                          )}
                        </div>
                      </div>

                      {file.diff ? (
                        <pre className="p-3 text-xs font-mono text-slate-300 overflow-x-auto max-h-60 leading-relaxed">
                          {file.diff.split('\n').map((line, lIdx) => {
                            if (line.startsWith('+') && !line.startsWith('+++')) {
                              return (
                                <div key={lIdx} className="bg-emerald-950/40 text-emerald-300 px-1 -mx-1">
                                  {line}
                                </div>
                              );
                            }
                            if (line.startsWith('-') && !line.startsWith('---')) {
                              return (
                                <div key={lIdx} className="bg-rose-950/40 text-rose-300 px-1 -mx-1">
                                  {line}
                                </div>
                              );
                            }
                            if (line.startsWith('@@')) {
                              return (
                                <div key={lIdx} className="text-indigo-400 font-bold">
                                  {line}
                                </div>
                              );
                            }
                            return <div key={lIdx}>{line}</div>;
                          })}
                        </pre>
                      ) : (
                        <div className="p-3 text-xs text-slate-500 italic">No diff contents recorded</div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-slate-500 text-center">
                <Layers className="w-12 h-12 text-slate-600 mb-3" />
                <p className="text-sm font-medium text-slate-400">No Changeset Selected</p>
                <p className="text-xs text-slate-500 mt-1">Select a changeset from the left column to view unified diffs.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Human Review Gates */}
      {activeTab === 'approvals' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-semibold text-white flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-amber-400" /> Human-in-the-Loop Approval Queue
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Critical operations (destructive commands, database migrations, package upgrades) are paused until authorized.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setApprovalFilter('ALL')}
                className={`px-3 py-1 rounded text-xs font-medium transition ${
                  approvalFilter === 'ALL' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
                }`}
              >
                All ({approvals.length})
              </button>
              <button
                onClick={() => setApprovalFilter('PENDING')}
                className={`px-3 py-1 rounded text-xs font-medium transition ${
                  approvalFilter === 'PENDING' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-300'
                }`}
              >
                Pending ({approvals.filter((a) => a.status === 'PENDING').length})
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {filteredApprovals.map((req) => (
              <div
                key={req.request_id}
                className="p-4 bg-slate-950 border border-slate-800 rounded-lg space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-bold font-mono ${
                        req.risk_level === 'CRITICAL' || req.risk_level === 'HIGH'
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {req.risk_level} RISK
                    </span>
                    <span className="font-mono text-xs text-indigo-400">{req.action_type}</span>
                    <span className="text-xs text-slate-500">• ID: {req.request_id}</span>
                  </div>

                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-semibold self-start sm:self-auto ${
                      req.status === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : req.status === 'REJECTED'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}
                  >
                    {req.status}
                  </span>
                </div>

                <div className="text-sm font-medium text-white">{req.description}</div>

                {req.payload && Object.keys(req.payload).length > 0 && (
                  <div className="p-2.5 bg-slate-900 border border-slate-800 rounded text-xs font-mono text-slate-300">
                    <div className="text-slate-500 text-[10px] uppercase font-semibold mb-1">Payload Parameters:</div>
                    <pre className="overflow-x-auto">{JSON.stringify(req.payload, null, 2)}</pre>
                  </div>
                )}

                {req.status === 'PENDING' ? (
                  <div className="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <input
                      type="text"
                      value={operatorReason}
                      onChange={(e) => setOperatorReason(e.target.value)}
                      placeholder="Operator authorization note..."
                      className="px-3 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-white focus:outline-none focus:border-indigo-500 flex-1"
                    />
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleDecideApproval(req.request_id, 'REJECTED')}
                        className="px-3.5 py-1.5 rounded bg-rose-950/60 hover:bg-rose-900 text-rose-300 border border-rose-800 text-xs font-semibold transition"
                      >
                        Reject Action
                      </button>
                      <button
                        onClick={() => handleDecideApproval(req.request_id, 'APPROVED')}
                        className="px-3.5 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" /> Authorize & Proceed
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 flex items-center gap-2">
                    <span className="font-medium text-slate-300">Decided by:</span> {req.resolved_by || 'system'}
                    <span>• Reason: {req.reason || 'No reason recorded'}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 4: PR & Changelog Generator */}
      {activeTab === 'pr_preview' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h3 className="font-semibold text-white flex items-center gap-2">
                <GitPullRequest className="w-5 h-5 text-indigo-400" /> Pull Request Markdown Synthesizer
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Automatically formats rich Markdown for GitHub / GitLab pull requests with risk checklists.
              </p>
            </div>

            {selectedChangeset?.pr_body && (
              <button
                onClick={() => handleCopyPr(selectedChangeset.pr_body || '')}
                className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 transition shadow"
              >
                {copiedPr ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copiedPr ? 'Copied Markdown!' : 'Copy PR Markdown'}
              </button>
            )}
          </div>

          {selectedChangeset?.pr_body ? (
            <div className="space-y-4">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Synthesized Git Commit Message
                </div>
                <pre className="p-2.5 bg-slate-900 rounded font-mono text-xs text-indigo-200 whitespace-pre-wrap">
                  {selectedChangeset.commit_message}
                </pre>
              </div>

              <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Markdown PR Description
                </div>
                <div className="prose prose-invert max-w-none text-xs leading-relaxed text-slate-300 whitespace-pre-wrap font-mono bg-slate-900 p-4 rounded-lg border border-slate-800">
                  {selectedChangeset.pr_body}
                </div>
              </div>
            </div>
          ) : (
            <div className="py-16 text-center text-slate-500">
              <GitPullRequest className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-sm font-medium text-slate-400">No Changeset Available for PR Generation</p>
              <p className="text-xs text-slate-500 mt-1">Create or select a changeset with staged files first.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { TestCaseResult } from '../types';
import { testsApi, DetailedTestCase } from '../api/tests';
import {
  CheckCircle,
  Play,
  RefreshCw,
  Clock,
  ShieldCheck,
  CheckCheck,
  XCircle,
  AlertTriangle,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
  Terminal,
} from 'lucide-react';

interface Props {
  initialResults?: TestCaseResult[];
}

export const TestResultsViewer: React.FC<Props> = () => {
  const [tests, setTests] = useState<DetailedTestCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<'all' | 'diagnostics' | 'patcher' | 'planner' | 'context' | 'storage' | 'agent' | 'tools' | 'security' | 'llm'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTestId, setExpandedTestId] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchTests = async () => {
    setIsRunning(true);
    setErrorMsg(null);
    const t0 = performance.now();
    try {
      const res = await testsApi.getDetailed();
      if (res.tests) {
        setTests(res.tests);
      }
      setExecutionTime(Math.round(performance.now() - t0));
    } catch (err: any) {
      console.error('Failed to load test results:', err);
      setErrorMsg(err.message || 'Failed to execute Python test suite.');
    } finally {
      setIsRunning(false);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTests();
  }, []);

  const filteredTests = tests.filter((t) => {
    const matchesSearch =
      searchQuery === '' ||
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.module.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (activeTab === 'all') return true;
    if (activeTab === 'diagnostics') return t.module.includes('diagnostics');
    if (activeTab === 'patcher') return t.module.includes('patcher');
    if (activeTab === 'planner') return t.module.includes('planner');
    if (activeTab === 'context') return t.module.includes('context');
    if (activeTab === 'storage') return t.module.includes('storage');
    if (activeTab === 'agent') return t.module.includes('agent');
    if (activeTab === 'tools') return t.module.includes('tools');
    if (activeTab === 'security') return t.module.includes('security');
    if (activeTab === 'llm') return t.module.includes('llm');
    return true;
  });

  const passedCount = tests.filter((t) => t.status === 'passed').length;
  const failedCount = tests.filter((t) => t.status === 'failed' || t.status === 'error').length;
  const totalDuration = tests.reduce((acc, t) => acc + (t.durationMs || 0), 0);

  return (
    <div id="test-results-container" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Live Verification &amp; Test Suite Engine
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Real Python unit &amp; regression tests dynamically executed against the runtime workspace
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            id="run-tests-btn"
            onClick={fetchTests}
            disabled={isRunning}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition-all shadow-md active:scale-95 disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Executing Suite...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Execute All Tests
              </>
            )}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Metrics Summary Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg">
          <div className="text-xs text-slate-400">Total Tests Discovered</div>
          <div className="text-xl font-bold text-white font-mono mt-0.5">
            {loading ? '...' : tests.length}
          </div>
        </div>
        <div className="p-3.5 bg-emerald-950/30 border border-emerald-900/40 rounded-lg">
          <div className="text-xs text-emerald-400">Passed Tests</div>
          <div className="text-xl font-bold text-emerald-300 font-mono mt-0.5 flex items-center gap-1.5">
            <CheckCircle className="w-4 h-4" />
            {loading ? '...' : passedCount}
          </div>
        </div>
        <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg">
          <div className="text-xs text-slate-400">Failures / Errors</div>
          <div className={`text-xl font-bold font-mono mt-0.5 ${failedCount > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
            {loading ? '...' : failedCount}
          </div>
        </div>
        <div className="p-3.5 bg-slate-950/80 border border-slate-800 rounded-lg">
          <div className="text-xs text-slate-400">Suite Execution Time</div>
          <div className="text-xl font-bold text-slate-300 font-mono mt-0.5 flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-slate-400" />
            {loading ? '...' : `${(totalDuration / 1000).toFixed(3)}s`}
          </div>
        </div>
      </div>

      {/* Search and Tabs Filter */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs font-medium">
            {[
              { id: 'all', label: 'All Modules' },
              { id: 'diagnostics', label: 'Diagnostics (Phase 10)' },
              { id: 'patcher', label: 'Safe Patcher' },
              { id: 'planner', label: 'Planner & DAG' },
              { id: 'context', label: 'Context Engine' },
              { id: 'storage', label: 'SQLite Store' },
              { id: 'agent', label: 'Agent Runtime' },
              { id: 'tools', label: 'Tools (18)' },
              { id: 'llm', label: 'LLM & Gemini' },
              { id: 'security', label: 'Security' },
            ].map((tab) => (
              <button
                key={tab.id}
                id={`filter-tab-${tab.id}`}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-colors ${
                  activeTab === tab.id
                    ? 'bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 font-semibold'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative min-w-[220px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              id="test-search-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tests or modules..."
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Tests Table */}
        <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
          {loading ? (
            <div className="p-8 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
              Discovering and executing test suites dynamically...
            </div>
          ) : filteredTests.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No test cases found matching the active filter.
            </div>
          ) : (
            filteredTests.map((t) => {
              const isExpanded = expandedTestId === t.id;
              const isPassed = t.status === 'passed';
              return (
                <div
                  key={t.id}
                  id={`test-case-${t.id}`}
                  className={`rounded-lg border transition-colors ${
                    isPassed
                      ? 'bg-slate-950/60 border-slate-800/90 hover:border-slate-700'
                      : 'bg-rose-950/20 border-rose-800/60'
                  }`}
                >
                  <div
                    onClick={() => setExpandedTestId(isExpanded ? null : t.id)}
                    className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer"
                  >
                    <div className="flex items-start gap-2.5">
                      {isPassed ? (
                        <CheckCircle className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                      )}
                      <div>
                        <div className="text-xs font-mono font-medium text-slate-200 flex items-center gap-2">
                          <span>{t.name}</span>
                          {t.className && (
                            <span className="text-[10px] font-sans px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                              {t.className}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                          {t.description}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 self-end sm:self-center shrink-0">
                      <span className="text-[11px] font-mono text-slate-500">{t.durationMs}ms</span>
                      <span className="text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        {t.module}
                      </span>
                      <span
                        className={`text-[11px] px-2 py-0.5 rounded font-mono border ${
                          isPassed
                            ? 'bg-emerald-950/80 text-emerald-300 border-emerald-800/60'
                            : 'bg-rose-950 text-rose-300 border-rose-800'
                        }`}
                      >
                        {t.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-3 pt-0 border-t border-slate-800/60 bg-slate-950/40 text-xs font-mono space-y-2 mt-2">
                      <div className="text-slate-400 text-[11px]">Full Identifier: <span className="text-slate-200">{t.id}</span></div>
                      {t.errorMessage && (
                        <div className="p-2.5 rounded bg-rose-950/30 border border-rose-900 text-rose-300 text-[11px] whitespace-pre-wrap">
                          {t.errorMessage}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="pt-3 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs text-slate-400 font-mono">
        <span className="flex items-center gap-1.5">
          <Terminal className="w-3.5 h-3.5 text-indigo-400" />
          Bridge Execution: <span className="text-slate-300">python3 ./nexforge-droid/run_api_bridge.py --action tests-detailed</span>
        </span>
        <span className="flex items-center gap-1 text-emerald-400 font-semibold">
          <CheckCheck className="w-3.5 h-3.5" /> Dynamic Live Verification
        </span>
      </div>
    </div>
  );
};

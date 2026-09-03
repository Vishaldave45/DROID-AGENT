import React, { useState } from 'react';
import {
  Play,
  RotateCcw,
  Sparkles,
  Bot,
  Terminal,
  FileCode,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Layers,
  ShieldCheck,
  Cpu,
  ChevronRight,
  ChevronDown,
  FileCheck2,
  FileEdit,
  Flame,
  ArrowRight,
  Bug,
  Search,
} from 'lucide-react';
import { agentApi } from '../api/agent';

interface AgentStep {
  event_type: string;
  task_id: string;
  iteration: number;
  tool_name: string | null;
  arguments: any;
  tool_success: boolean | null;
  thought_summary: string | null;
  is_terminal: boolean;
  final_output: string | null;
  errors: string[];
  status: string;
  files_read: string[];
  files_changed: string[];
}

interface AgentRunSummary {
  event_type: string;
  task_id: string;
  status: string;
  iteration: number;
  requirement: string;
  files_read: string[];
  files_changed: string[];
  test_runs_count: number;
  test_failures_count: number;
  errors: string[];
  final_output: string | null;
  steps: AgentStep[];
}

const PRESET_TASKS = [
  {
    id: 'patch_bug',
    title: 'Patch Zero-Division Bug in Math Utils',
    requirement: 'Locate math_utils.py, analyze calculate_total function, and surgically patch it to safely handle empty items.',
    scenario: 'patch_bug',
    icon: Bug,
    tag: 'Code Modification',
  },
  {
    id: 'explore_repo',
    title: 'Explore Repository Hierarchy & Modules',
    requirement: 'Discover all python source files across the workspace and generate an architecture summary.',
    scenario: 'explore_repo',
    icon: Search,
    tag: 'Discovery & Indexing',
  },
  {
    id: 'direct_verify',
    title: 'Direct Question & Verification',
    requirement: 'Evaluate system security policies and verify path traversal isolation parameters.',
    scenario: 'direct_verify',
    icon: ShieldCheck,
    tag: 'Direct Reasoning',
  },
];

export const AgentLoopStudio: React.FC = () => {
  const [requirement, setRequirement] = useState(
    'Locate math_utils.py, analyze calculate_total function, and surgically patch it to safely handle empty items.'
  );
  const [provider, setProvider] = useState<'gemini' | 'mock'>('mock');
  const [mockScenario, setMockScenario] = useState('patch_bug');
  const [maxIterations, setMaxIterations] = useState(10);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<AgentRunSummary | null>(null);
  const [selectedStepIndex, setSelectedStepIndex] = useState<number | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const toggleStepExpand = (idx: number) => {
    setExpandedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleRunAgent = async () => {
    setIsRunning(true);
    setErrorMessage(null);
    setRunResult(null);
    setSelectedStepIndex(null);

    try {
      const data = await agentApi.run({
        requirement,
        provider: provider as 'gemini' | 'mock',
        mockScenario,
        maxIterations,
      });

      if (data.error) {
        setErrorMessage(data.error || 'Agent run execution failed.');
      } else {
        setRunResult(data as any);
        if (data.steps && data.steps.length > 0) {
          setSelectedStepIndex(data.steps.length - 1);
          // Auto-expand all steps by default
          const exp: Record<number, boolean> = {};
          data.steps.forEach((_: any, i: number) => {
            exp[i] = true;
          });
          setExpandedSteps(exp);
        }
      }
    } catch (e: any) {
      setErrorMessage(e.message || 'Network error running agent task.');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div id="agent-loop-studio-container" className="space-y-6">
      {/* Studio Header Card */}
      <div
        id="agent-studio-header-card"
        className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900"
      >
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/50 dark:text-indigo-400">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-50">
                  Autonomous Agent Loop & Step Controller
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  Multi-turn reasoning orchestration, tool dispatch, self-correcting error recovery, and iteration safety gates.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Phase 3 Active Loop Engine
            </span>
          </div>
        </div>

        {/* Preset Task Cards */}
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {PRESET_TASKS.map((preset) => {
            const Icon = preset.icon;
            const isSelected = requirement === preset.requirement;
            return (
              <button
                key={preset.id}
                id={`preset-btn-${preset.id}`}
                onClick={() => {
                  setRequirement(preset.requirement);
                  setMockScenario(preset.scenario);
                }}
                className={`flex flex-col items-start rounded-xl border p-3.5 text-left transition-all ${
                  isSelected
                    ? 'border-indigo-500 bg-indigo-50/50 ring-1 ring-indigo-500 dark:border-indigo-400 dark:bg-indigo-950/30'
                    : 'border-slate-200 bg-slate-50/50 hover:border-slate-300 hover:bg-slate-100/60 dark:border-slate-800 dark:bg-slate-800/40 dark:hover:bg-slate-800/70'
                }`}
              >
                <div className="flex w-full items-center justify-between">
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-white/80 px-2 py-0.5 text-xs font-medium text-slate-700 shadow-2xs dark:bg-slate-800 dark:text-slate-300">
                    <Icon className="h-3.5 w-3.5 text-indigo-500" />
                    {preset.tag}
                  </span>
                  {isSelected && <CheckCircle2 className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />}
                </div>
                <div className="mt-2 text-sm font-medium text-slate-900 dark:text-slate-100">
                  {preset.title}
                </div>
              </button>
            );
          })}
        </div>

        {/* Task Formulation & Execution Config */}
        <div className="mt-5 space-y-4 rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-800/60 dark:bg-slate-800/30">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Task Requirement / Objective
            </label>
            <textarea
              id="agent-task-requirement-input"
              rows={2}
              value={requirement}
              onChange={(e) => setRequirement(e.target.value)}
              placeholder="Describe the software engineering goal..."
              className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-900 placeholder-slate-400 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Execution Backend
              </label>
              <select
                id="agent-provider-select"
                value={provider}
                onChange={(e) => setProvider(e.target.value as any)}
                className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              >
                <option value="mock">Deterministic Mock Provider (Scripted scenarios)</option>
                <option value="gemini">Live Gemini 2.5 Provider (Via Server API Key)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Mock Scenario
              </label>
              <select
                id="agent-scenario-select"
                disabled={provider !== 'mock'}
                value={mockScenario}
                onChange={(e) => setMockScenario(e.target.value)}
                className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:opacity-50 focus:border-indigo-500 focus:outline-hidden focus:ring-1 focus:ring-indigo-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
              >
                <option value="patch_bug">patch_bug (search -&gt; read -&gt; edit -&gt; diff -&gt; finish)</option>
                <option value="explore_repo">explore_repo (list_dir -&gt; find_files -&gt; finish)</option>
                <option value="direct_verify">direct_verify (single-turn direct resolution)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Max Iteration Limit: {maxIterations}
              </label>
              <input
                id="agent-max-iter-slider"
                type="range"
                min={3}
                max={20}
                value={maxIterations}
                onChange={(e) => setMaxIterations(parseInt(e.target.value, 10))}
                className="mt-3 w-full accent-indigo-600"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>PolicyEngine Active: Sandboxed execution &amp; path containment enforced</span>
            </div>

            <button
              id="run-agent-task-btn"
              onClick={handleRunAgent}
              disabled={isRunning || !requirement.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-indigo-500 dark:hover:bg-indigo-400"
            >
              {isRunning ? (
                <>
                  <RotateCcw className="h-4 w-4 animate-spin" />
                  Running Autonomous Loop...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Launch Autonomous Task
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div
          id="agent-run-error-alert"
          className="flex items-center gap-3 rounded-xl border border-rose-200 bg-rose-50/80 p-4 text-sm text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300"
        >
          <AlertCircle className="h-5 w-5 shrink-0 text-rose-600 dark:text-rose-400" />
          <div>
            <div className="font-semibold">Agent Execution Error</div>
            <div>{errorMessage}</div>
          </div>
        </div>
      )}

      {/* Execution Results Overview */}
      {runResult && (
        <div id="agent-run-results-section" className="space-y-6">
          {/* Status Metric Strip */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Task Status
              </div>
              <div className="mt-1 flex items-center gap-1.5">
                {runResult.status === 'COMPLETED' ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-rose-500" />
                )}
                <span className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {runResult.status}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Total Turns / Iterations
              </div>
              <div className="mt-1 flex items-center gap-1.5">
                <RotateCcw className="h-5 w-5 text-indigo-500" />
                <span className="text-base font-bold text-slate-900 dark:text-slate-100">
                  {runResult.iteration} / {maxIterations}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Files Read / Changed
              </div>
              <div className="mt-1 flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <span className="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400">
                  <FileCheck2 className="h-4 w-4" /> {runResult.files_read.length}
                </span>
                <span>/</span>
                <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                  <FileEdit className="h-4 w-4" /> {runResult.files_changed.length}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-slate-200/80 bg-white p-4 shadow-2xs dark:border-slate-800 dark:bg-slate-900">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Task ID
              </div>
              <div className="mt-1 font-mono text-xs font-medium text-slate-700 dark:text-slate-300 truncate">
                {runResult.task_id}
              </div>
            </div>
          </div>

          {/* Final Output Summary Card */}
          {runResult.final_output && (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-5 dark:border-emerald-900/60 dark:bg-emerald-950/20">
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800 dark:text-emerald-300">
                <CheckCircle2 className="h-4 w-4" />
                Final Agent Resolution &amp; Summary
              </div>
              <div className="mt-2 text-sm text-emerald-950 dark:text-emerald-100 leading-relaxed whitespace-pre-wrap">
                {runResult.final_output}
              </div>
            </div>
          )}

          {/* Step-by-Step Reasoning Timeline */}
          <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h3 className="text-base font-semibold text-slate-900 dark:text-slate-50 flex items-center gap-2">
              <Layers className="h-4 w-4 text-indigo-500" />
              Autonomous Step Execution Timeline ({runResult.steps.length} Steps)
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Detailed breakdown of model reasoning, tool invocations, and workspace observations.
            </p>

            <div className="mt-5 space-y-4">
              {runResult.steps.map((step, idx) => {
                const isExpanded = expandedSteps[idx] ?? true;
                const isFinal = step.is_terminal;

                return (
                  <div
                    key={idx}
                    id={`step-trace-${step.iteration}`}
                    className={`rounded-xl border transition-all ${
                      isFinal
                        ? 'border-emerald-300 bg-emerald-50/30 dark:border-emerald-900/60 dark:bg-emerald-950/10'
                        : 'border-slate-200 bg-slate-50/50 dark:border-slate-800 dark:bg-slate-800/30'
                    }`}
                  >
                    {/* Step Card Header */}
                    <div
                      onClick={() => toggleStepExpand(idx)}
                      className="flex cursor-pointer items-center justify-between p-4 select-none"
                    >
                      <div className="flex items-center gap-3">
                        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-100 text-xs font-bold text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300">
                          {step.iteration}
                        </span>

                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                            {step.tool_name ? (
                              <span className="font-mono text-indigo-600 dark:text-indigo-400">
                                tool: {step.tool_name}
                              </span>
                            ) : (
                              'Direct Text Response'
                            )}
                          </span>

                          {step.tool_success !== null && (
                            <span
                              className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${
                                step.tool_success
                                  ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                                  : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                              }`}
                            >
                              {step.tool_success ? 'Success' : 'Error'}
                            </span>
                          )}

                          {isFinal && (
                            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500 px-2 py-0.5 text-xs font-medium text-white">
                              <CheckCircle2 className="h-3 w-3" /> Terminal Completion
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 text-slate-400">
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </div>
                    </div>

                    {/* Step Details Body */}
                    {isExpanded && (
                      <div className="border-t border-slate-200/60 p-4 space-y-3 dark:border-slate-700/60">
                        {/* Model Thought / Plan */}
                        {step.thought_summary && (
                          <div>
                            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                              Reasoning &amp; Intent
                            </div>
                            <div className="mt-1 text-sm text-slate-800 dark:text-slate-200 bg-white p-3 rounded-lg border border-slate-200/80 dark:bg-slate-900 dark:border-slate-800">
                              {step.thought_summary}
                            </div>
                          </div>
                        )}

                        {/* Tool Arguments */}
                        {step.arguments && Object.keys(step.arguments).length > 0 && (
                          <div>
                            <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                              Dispatched Arguments
                            </div>
                            <pre className="mt-1 max-h-48 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs font-mono text-slate-100">
                              {JSON.stringify(step.arguments, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Errors if any */}
                        {step.errors && step.errors.length > 0 && (
                          <div className="rounded-lg border border-rose-200 bg-rose-50/70 p-3 text-xs text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
                            <span className="font-semibold">Step Feedback / Errors:</span>
                            <ul className="mt-1 list-disc list-inside">
                              {step.errors.map((err, i) => (
                                <li key={i}>{err}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

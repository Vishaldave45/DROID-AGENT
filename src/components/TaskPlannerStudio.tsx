import React, { useState } from 'react';
import {
  ListOrdered,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  GitPullRequest,
  Check,
  Clock,
  ArrowRight,
  ShieldCheck,
  Wrench,
  Search,
  Code2,
  FileSearch,
  Terminal,
  RefreshCw,
  Zap,
} from 'lucide-react';

export type StepStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'SKIPPED';
export type StepType = 'DISCOVERY' | 'INVESTIGATION' | 'IMPLEMENTATION' | 'VERIFICATION' | 'REFACTOR' | 'DOCUMENTATION';

export interface PlanStepItem {
  id: string;
  title: string;
  description: string;
  stepType: StepType;
  status: StepStatus;
  dependencies: string[];
  acceptanceCriteria: string;
  targetFiles?: string[];
  targetSymbols?: string[];
  requiredTools?: string[];
  executionEvidence?: string;
  isRemediation?: boolean;
}

interface Scenario {
  id: string;
  title: string;
  objective: string;
  initialSteps: PlanStepItem[];
}

const PRESET_SCENARIOS: Scenario[] = [
  {
    id: 'race-condition',
    title: 'Fix SQLite Connection Pool Race Condition',
    objective: 'Eliminate deadlocks during concurrent write transactions in SQLite connection pool by acquiring immediate write locks.',
    initialSteps: [
      {
        id: 'step-1',
        title: 'Discover SQLite Pool Callers',
        description: 'Scan codebase for database connection acquisitions, transaction scopes, and pool lifecycle hooks.',
        stepType: 'DISCOVERY',
        status: 'PENDING',
        dependencies: [],
        acceptanceCriteria: 'Locate pool initialization and all connection checkout call sites in app/storage/.',
        targetFiles: ['app/storage/pool.py', 'app/storage/sqlite.py'],
        targetSymbols: ['SQLitePool.get_connection', 'SQLitePool.release_connection'],
        requiredTools: ['find_files', 'search_code'],
      },
      {
        id: 'step-2',
        title: 'Investigate Lock Contention Trace',
        description: 'Analyze thread-locking mechanism and isolation levels in SQLitePool to isolate race condition root cause.',
        stepType: 'INVESTIGATION',
        status: 'PENDING',
        dependencies: ['step-1'],
        acceptanceCriteria: 'Identify missing asyncio.Lock during transaction start and dirty read window.',
        targetFiles: ['app/storage/pool.py'],
        targetSymbols: ['SQLitePool._acquire_lock'],
        requiredTools: ['read_file', 'ast_graph'],
      },
      {
        id: 'step-3',
        title: 'Implement Mutexed Connection Checkout',
        description: 'Add reentrant async mutex locking around pool checkout and configure WAL mode with immediate transactions.',
        stepType: 'IMPLEMENTATION',
        status: 'PENDING',
        dependencies: ['step-2'],
        acceptanceCriteria: 'Mutex safeguards all write operations; pool returns verified connection handles.',
        targetFiles: ['app/storage/pool.py'],
        targetSymbols: ['SQLitePool.get_connection'],
        requiredTools: ['edit_file', 'syntax_validate'],
      },
      {
        id: 'step-4',
        title: 'Run Concurrent Stress Test Suite',
        description: 'Execute automated stress test with 50 concurrent async workers writing simultaneous records.',
        stepType: 'VERIFICATION',
        status: 'PENDING',
        dependencies: ['step-3'],
        acceptanceCriteria: 'All 50 workers complete without DatabaseLocked or Deadlock exceptions (0 failures).',
        targetFiles: ['tests/test_storage_pool.py'],
        requiredTools: ['run_command'],
      },
      {
        id: 'step-5',
        title: 'Final Documentation & Metric Snapshot',
        description: 'Update pool concurrency invariants in architecture documentation and generate task audit checkpoint.',
        stepType: 'DOCUMENTATION',
        status: 'PENDING',
        dependencies: ['step-4'],
        acceptanceCriteria: 'Pool concurrency guarantees documented with audit log recorded.',
        targetFiles: ['docs/storage_architecture.md'],
        requiredTools: ['finish_task'],
      },
    ],
  },
  {
    id: 'jwt-auth',
    title: 'Implement JWT Token Authentication Middleware',
    objective: 'Add secure JWT verification middleware with RS256 signature checking and role-based route guard decorators.',
    initialSteps: [
      {
        id: 'step-1',
        title: 'Discover API Routes & Middleware Chain',
        description: 'Locate FastAPI route handlers and identify middleware dispatch points.',
        stepType: 'DISCOVERY',
        status: 'PENDING',
        dependencies: [],
        acceptanceCriteria: 'Catalog all public vs protected API endpoints in app/api/.',
        targetFiles: ['app/api/router.py', 'app/main.py'],
        requiredTools: ['find_files'],
      },
      {
        id: 'step-2',
        title: 'Design JWT Signature Verifier',
        description: 'Implement token decoder with RS256 public key verification and expiry claims validation.',
        stepType: 'IMPLEMENTATION',
        status: 'PENDING',
        dependencies: ['step-1'],
        acceptanceCriteria: 'Token decoder handles expired, malformed, and valid RSA tokens.',
        targetFiles: ['app/security/jwt.py'],
        targetSymbols: ['verify_jwt_token'],
        requiredTools: ['write_file', 'edit_file'],
      },
      {
        id: 'step-3',
        title: 'Mount Auth Guard on Protected Endpoints',
        description: 'Attach authentication dependency to sensitive task creation and deletion endpoints.',
        stepType: 'IMPLEMENTATION',
        status: 'PENDING',
        dependencies: ['step-2'],
        acceptanceCriteria: '401 Unauthorized returned for missing/invalid bearer tokens.',
        targetFiles: ['app/api/tasks.py'],
        requiredTools: ['edit_file'],
      },
      {
        id: 'step-4',
        title: 'Verify Auth Test Suite',
        description: 'Run unit and integration tests verifying token lifecycle and role authorization.',
        stepType: 'VERIFICATION',
        status: 'PENDING',
        dependencies: ['step-3'],
        acceptanceCriteria: '100% auth test pass rate including expired token rejection.',
        targetFiles: ['tests/test_auth.py'],
        requiredTools: ['run_command'],
      },
    ],
  },
];

export function TaskPlannerStudio() {
  const [selectedScenario, setSelectedScenario] = useState<Scenario>(PRESET_SCENARIOS[0]);
  const [steps, setSteps] = useState<PlanStepItem[]>(PRESET_SCENARIOS[0].initialSteps);
  const [selectedStepId, setSelectedStepId] = useState<string>(PRESET_SCENARIOS[0].initialSteps[0].id);
  const [replanHistory, setReplanHistory] = useState<string[]>([]);
  const [customPrompt, setCustomPrompt] = useState<string>('Refactor context compression to use LRU caching with priority eviction');
  const [isGeneratingPlan, setIsGeneratingPlan] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  const selectedStep = steps.find((s) => s.id === selectedStepId) || steps[0];

  const handleSelectScenario = (scenario: Scenario) => {
    setSelectedScenario(scenario);
    setSteps(scenario.initialSteps);
    setSelectedStepId(scenario.initialSteps[0].id);
    setReplanHistory([]);
  };

  const handleReset = () => {
    setSteps(selectedScenario.initialSteps);
    setSelectedStepId(selectedScenario.initialSteps[0].id);
    setReplanHistory([]);
  };

  // Generate dynamic plan from backend API
  const handleGenerateDynamicPlan = async () => {
    if (!customPrompt.trim()) return;
    setIsGeneratingPlan(true);
    setGenerationError(null);

    try {
      const res = await fetch('/api/planner/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requirement: customPrompt,
        }),
      });

      const data = await res.json();
      if (data.success && data.plan?.steps) {
        const mappedSteps: PlanStepItem[] = data.plan.steps.map((s: any, idx: number) => ({
          id: s.step_id || `step-${idx + 1}`,
          title: s.title || `Task Step ${idx + 1}`,
          description: s.description || '',
          stepType: (s.step_type || 'IMPLEMENTATION').toUpperCase() as StepType,
          status: 'PENDING' as StepStatus,
          dependencies: s.dependencies || [],
          acceptanceCriteria: s.acceptance_criteria || 'Verify step completion criteria',
          targetFiles: s.target_files || [],
          targetSymbols: s.target_symbols || [],
          requiredTools: s.required_tools || [],
        }));

        const newScenario: Scenario = {
          id: `custom-${Date.now()}`,
          title: `Dynamic Plan: ${customPrompt.slice(0, 45)}...`,
          objective: customPrompt,
          initialSteps: mappedSteps,
        };

        setSelectedScenario(newScenario);
        setSteps(mappedSteps);
        if (mappedSteps.length > 0) {
          setSelectedStepId(mappedSteps[0].id);
        }
        setReplanHistory([
          `Generated dynamic DAG plan (${mappedSteps.length} nodes) from RepositoryContextEngine via API Bridge.`,
        ]);
      } else {
        setGenerationError(data.error || 'Failed to generate plan.');
      }
    } catch (err: any) {
      setGenerationError(err.message);
    } finally {
      setIsGeneratingPlan(false);
    }
  };

  const isStepRunnable = (step: PlanStepItem) => {
    if (step.status === 'COMPLETED') return false;
    if (step.dependencies.length === 0) return true;
    return step.dependencies.every((depId) => {
      const depStep = steps.find((s) => s.id === depId);
      return depStep && depStep.status === 'COMPLETED';
    });
  };

  const handleAdvanceStep = (stepId: string) => {
    const updated = steps.map((s) => {
      if (s.id === stepId) {
        return {
          ...s,
          status: 'COMPLETED' as StepStatus,
          executionEvidence: `Completed successfully at ${new Date().toLocaleTimeString()} - All assertions satisfied.`,
        };
      }
      return s;
    });
    setSteps(updated);

    const nextPending = updated.find((s) => s.status === 'PENDING' && isStepRunnable(s));
    if (nextPending) {
      setSelectedStepId(nextPending.id);
    }
  };

  // Perform dynamic replanning on step failure
  const handleSimulateFailure = async (stepId: string, errorMsg: string) => {
    const failedStep = steps.find((s) => s.id === stepId);
    if (!failedStep) return;

    try {
      const res = await fetch('/api/planner/replan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requirement: selectedScenario.objective,
          failedStepId: stepId,
          error: errorMsg,
        }),
      });

      const data = await res.json();
      if (data.success && data.remediatedPlan?.steps) {
        const mappedSteps: PlanStepItem[] = data.remediatedPlan.steps.map((s: any) => ({
          id: s.step_id,
          title: s.title,
          description: s.description,
          stepType: (s.step_type || 'IMPLEMENTATION').toUpperCase() as StepType,
          status: (s.status || 'PENDING').toUpperCase() as StepStatus,
          dependencies: s.dependencies || [],
          acceptanceCriteria: s.acceptance_criteria || '',
          targetFiles: s.target_files || [],
          targetSymbols: s.target_symbols || [],
          requiredTools: s.required_tools || [],
          isRemediation: s.step_id.includes('diag') || s.step_id.includes('fix') || s.step_id.includes('verify'),
        }));
        setSteps(mappedSteps);
        setReplanHistory((prev) => [
          `Dynamic Replanner API returned remediated DAG for ${stepId}: Injected diagnostic & fix recovery chain.`,
          ...prev,
        ]);
        return;
      }
    } catch (e) {
      // Fallback to local deterministic replanner
    }

    const diagId = `${stepId}-diag`;
    const fixId = `${stepId}-fix`;
    const verifyId = `${stepId}-reverify`;

    const diagStep: PlanStepItem = {
      id: diagId,
      title: `[Remediation] Diagnostic Inspection of ${failedStep.title}`,
      description: `Synthesize failure traceback and analyze root cause of: "${errorMsg}".`,
      stepType: 'INVESTIGATION',
      status: 'PENDING',
      dependencies: [stepId],
      acceptanceCriteria: `Root cause identified for error: ${errorMsg}`,
      targetFiles: failedStep.targetFiles,
      requiredTools: ['read_file', 'search_code'],
      isRemediation: true,
    };

    const fixStep: PlanStepItem = {
      id: fixId,
      title: `[Remediation] Apply Targeted Patch for ${failedStep.title}`,
      description: `Execute surgical fix addressing diagnostic findings for ${failedStep.title}.`,
      stepType: 'IMPLEMENTATION',
      status: 'PENDING',
      dependencies: [diagId],
      acceptanceCriteria: 'Corrective patch applied and syntax validated.',
      targetFiles: failedStep.targetFiles,
      requiredTools: ['edit_file', 'syntax_validator'],
      isRemediation: true,
    };

    const reVerifyStep: PlanStepItem = {
      id: verifyId,
      title: `[Remediation] Re-verify Acceptance of ${failedStep.title}`,
      description: `Execute regression assertions to confirm corrective fix resolved the failure.`,
      stepType: 'VERIFICATION',
      status: 'PENDING',
      dependencies: [fixId],
      acceptanceCriteria: failedStep.acceptanceCriteria,
      targetFiles: failedStep.targetFiles,
      requiredTools: ['run_command'],
      isRemediation: true,
    };

    const updatedSteps = steps.map((s) => {
      if (s.id === stepId) {
        return {
          ...s,
          status: 'FAILED' as StepStatus,
          executionEvidence: `Encountered error: ${errorMsg}`,
        };
      }
      if (s.dependencies.includes(stepId) && s.id !== diagId) {
        return {
          ...s,
          dependencies: s.dependencies.map((d) => (d === stepId ? verifyId : d)),
        };
      }
      return s;
    });

    const insertIdx = updatedSteps.findIndex((s) => s.id === stepId);
    updatedSteps.splice(insertIdx + 1, 0, diagStep, fixStep, reVerifyStep);

    setSteps(updatedSteps);
    setSelectedStepId(diagId);
    setReplanHistory((prev) => [
      `Dynamic Replanner mutated DAG: Injected 3 recovery nodes for failed ${failedStep.id} ("${errorMsg}")`,
      ...prev,
    ]);
  };

  const completedCount = steps.filter((s) => s.status === 'COMPLETED').length;
  const progressPercent = Math.round((completedCount / (steps.length || 1)) * 100);

  const getStepTypeBadge = (type: StepType) => {
    switch (type) {
      case 'DISCOVERY':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-950 text-sky-300 border border-sky-800">DISCOVERY</span>;
      case 'INVESTIGATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">INVESTIGATION</span>;
      case 'IMPLEMENTATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950 text-amber-300 border border-amber-800">IMPLEMENTATION</span>;
      case 'VERIFICATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-800">VERIFICATION</span>;
      case 'DOCUMENTATION':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950 text-purple-300 border border-purple-800">DOCUMENTATION</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">{type}</span>;
    }
  };

  const getStatusIcon = (status: StepStatus) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      case 'IN_PROGRESS':
        return <Clock className="w-4 h-4 text-amber-400 animate-spin" />;
      default:
        return <div className="w-3.5 h-3.5 rounded-full border border-slate-600 bg-slate-800"></div>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Dynamic Requirement Input */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
                Phase 8: Dynamic Explicit Task Planner &amp; Replanner
              </span>
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight">
              Deterministic DAG Execution Engine &amp; Self-Healing Planner
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl">
              Decomposes requirements into atomic, verifiable DAG steps. Dynamic replanning automatically inserts diagnostic and fix chains on failure.
            </p>
          </div>

          {/* Scenario Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            {PRESET_SCENARIOS.map((sc) => (
              <button
                key={sc.id}
                onClick={() => handleSelectScenario(sc)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                  selectedScenario.id === sc.id
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {sc.title}
              </button>
            ))}
            <button
              onClick={handleReset}
              className="flex items-center gap-1 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono border border-slate-700 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reset
            </button>
          </div>
        </div>

        {/* Dynamic AI Prompt Bar */}
        <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" /> Generate Custom Plan via Backend DAG Engine:
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={customPrompt}
              onChange={(e) => setCustomPrompt(e.target.value)}
              placeholder="e.g., Implement Redis token caching with exponential backoff..."
              className="flex-1 px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white font-mono focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
            <button
              onClick={handleGenerateDynamicPlan}
              disabled={isGeneratingPlan}
              className={`px-4 py-2 rounded-lg text-xs font-bold font-mono transition flex items-center gap-2 ${
                isGeneratingPlan
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm'
              }`}
            >
              {isGeneratingPlan ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Generating...
                </>
              ) : (
                <>
                  <Zap className="w-3.5 h-3.5" /> Plan Task DAG
                </>
              )}
            </button>
          </div>
          {generationError && (
            <p className="text-xs text-rose-400 font-mono">{generationError}</p>
          )}
        </div>
      </div>

      {/* Plan Objective & Execution Progress Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="space-y-0.5">
            <div className="text-xs font-mono text-slate-400">Active Task Objective:</div>
            <div className="text-sm font-semibold text-white">{selectedScenario.objective}</div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-xs font-mono text-slate-400">DAG Completion</div>
              <div className="text-base font-bold font-mono text-emerald-400">{progressPercent}%</div>
            </div>
            <div className="px-3 py-1 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono text-slate-300">
              {completedCount} / {steps.length} Steps
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden">
          <div
            style={{ width: `${progressPercent}%` }}
            className="h-full bg-emerald-500 transition-all duration-300 rounded-full"
          />
        </div>
      </div>

      {/* Main Grid: DAG Steps List (Left) vs Step Inspector & Actions (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Interactive DAG Step Pipeline */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ListOrdered className="w-4 h-4 text-emerald-400" />
              Plan Execution DAG ({steps.length} Nodes)
            </h3>
            <span className="text-xs font-mono text-slate-400">Click node to inspect</span>
          </div>

          <div className="space-y-2.5">
            {steps.map((step, idx) => {
              const isSelected = selectedStepId === step.id;
              const runnable = isStepRunnable(step);
              return (
                <div
                  key={step.id}
                  onClick={() => setSelectedStepId(step.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-slate-800/90 border-emerald-500/80 ring-1 ring-emerald-500/40'
                      : step.isRemediation
                      ? 'bg-amber-950/20 border-amber-800/60 hover:bg-amber-950/40'
                      : 'bg-slate-900 border-slate-800 hover:bg-slate-800/50'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2.5">
                      {getStatusIcon(step.status)}
                      <span className="font-mono text-xs font-bold text-slate-400">#{idx + 1}</span>
                      <span className="text-xs font-bold text-white tracking-tight">{step.title}</span>
                    </div>
                    {getStepTypeBadge(step.stepType)}
                  </div>

                  <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                    {step.description}
                  </p>

                  <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-2.5 border-t border-slate-800/80 text-[11px] font-mono">
                    <div className="text-slate-500 flex items-center gap-1">
                      {step.dependencies.length > 0 ? (
                        <span>Deps: {step.dependencies.join(', ')}</span>
                      ) : (
                        <span className="text-emerald-400 font-semibold">[Root Step]</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {step.status === 'PENDING' && runnable && (
                        <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 font-bold border border-emerald-800 animate-pulse">
                          RUNNABLE
                        </span>
                      )}
                      {step.status === 'COMPLETED' && (
                        <span className="text-emerald-400 font-semibold flex items-center gap-1">
                          <Check className="w-3 h-3" /> Done
                        </span>
                      )}
                      {step.status === 'FAILED' && (
                        <span className="text-rose-400 font-semibold">FAILED</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Step Inspector & Dynamic Replanning Trigger */}
        <div className="lg:col-span-6 space-y-6">
          {/* Active Step Details */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileSearch className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold text-white">Step Inspector: {selectedStep.id}</h3>
              </div>
              {getStepTypeBadge(selectedStep.stepType)}
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <div className="font-semibold text-slate-300">Description:</div>
                <div className="text-slate-400 leading-relaxed">{selectedStep.description}</div>
              </div>

              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <div className="font-semibold text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> Acceptance Criteria:
                </div>
                <div className="text-slate-300 font-mono leading-relaxed">{selectedStep.acceptanceCriteria}</div>
              </div>

              {selectedStep.targetFiles && selectedStep.targetFiles.length > 0 && (
                <div className="space-y-1">
                  <div className="font-semibold text-slate-400">Target Files:</div>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                    {selectedStep.targetFiles.map((f) => (
                      <span key={f} className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedStep.requiredTools && selectedStep.requiredTools.length > 0 && (
                <div className="space-y-1">
                  <div className="font-semibold text-slate-400">Required Tools:</div>
                  <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                    {selectedStep.requiredTools.map((t) => (
                      <span key={t} className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedStep.executionEvidence && (
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                  <div className="font-semibold text-amber-400">Execution Evidence:</div>
                  <div className="text-slate-300 font-mono text-[11px]">{selectedStep.executionEvidence}</div>
                </div>
              )}
            </div>

            {/* Step Action Buttons */}
            <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-3">
              {selectedStep.status !== 'COMPLETED' && (
                <button
                  onClick={() => handleAdvanceStep(selectedStep.id)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold font-mono transition shadow-lg shadow-emerald-950"
                >
                  <Play className="w-3.5 h-3.5" /> Mark Completed &amp; Advance
                </button>
              )}

              {selectedStep.status !== 'FAILED' && (
                <button
                  onClick={() =>
                    handleSimulateFailure(
                      selectedStep.id,
                      'AssertionError: Expected deadlock timeout < 50ms, but connection hung'
                    )
                  }
                  className="flex items-center gap-1.5 px-3 py-2 bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800 rounded-lg text-xs font-bold font-mono transition"
                >
                  <AlertTriangle className="w-3.5 h-3.5" /> Trigger Failure &amp; Replan
                </button>
              )}
            </div>
          </div>

          {/* Dynamic Replanning Telemetry Log */}
          {replanHistory.length > 0 && (
            <div className="bg-slate-900 border border-amber-500/30 rounded-xl p-5 space-y-3">
              <h4 className="text-xs font-bold text-amber-400 font-mono flex items-center gap-2">
                <Sparkles className="w-4 h-4" /> Dynamic Replanner Event Log
              </h4>
              <div className="space-y-2">
                {replanHistory.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-amber-300 leading-relaxed"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

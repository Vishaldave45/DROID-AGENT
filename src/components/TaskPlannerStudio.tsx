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
  const [simulating, setSimulating] = useState(false);

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

  // Helper to check if step dependencies are met
  const isStepRunnable = (step: PlanStepItem): boolean => {
    if (step.status === 'COMPLETED' || step.status === 'SKIPPED') return false;
    return step.dependencies.every((depId) => {
      const parent = steps.find((s) => s.id === depId);
      return parent && parent.status === 'COMPLETED';
    });
  };

  // Execute or complete next step
  const handleAdvanceStep = (stepId: string) => {
    setSteps((prev) =>
      prev.map((s) => {
        if (s.id === stepId) {
          return {
            ...s,
            status: 'COMPLETED',
            executionEvidence: `Successfully verified acceptance criteria at ${new Date().toLocaleTimeString()}.`,
          };
        }
        return s;
      })
    );

    // Auto select next runnable step
    setTimeout(() => {
      setSteps((currentSteps) => {
        const next = currentSteps.find((s) => s.status === 'PENDING' && isStepRunnable(s));
        if (next) setSelectedStepId(next.id);
        return currentSteps;
      });
    }, 100);
  };

  // Simulate failure and trigger Phase 8 Dynamic Replanner
  const handleSimulateFailure = (stepId: string, errorMsg: string) => {
    const failedStep = steps.find((s) => s.id === stepId);
    if (!failedStep) return;

    // 1. Mark failed step as FAILED
    const diagId = `replan-${stepId}-diag`;
    const fixId = `replan-${stepId}-fix`;
    const verifyId = `replan-${stepId}-verify`;

    const diagStep: PlanStepItem = {
      id: diagId,
      title: `[Remediation] Diagnose Failure in ${failedStep.title}`,
      description: `Investigate root cause of runtime error: "${errorMsg}". Inspect stack traces and edge cases.`,
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

    // 2. Rewire any step that previously depended on failedStep to now depend on reVerifyStep
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

    // Insert remediation steps directly after the failed step
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
  const progressPercent = Math.round((completedCount / steps.length) * 100);

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
      {/* Header & Scenario Selection */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
              Phase 8: Explicit Task Planner &amp; Dynamic Replanner
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            Deterministic DAG Execution Engine &amp; Self-Healing Planner
          </h2>
          <p className="text-xs text-slate-400 max-w-2xl">
            Breaks engineering objectives into atomic, verifiable DAG steps. Upon test or syntax failure, dynamically rewires the plan graph with diagnostic and remediation nodes.
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
            <RotateCcw className="w-3.5 h-3.5" /> Reset Plan
          </button>
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

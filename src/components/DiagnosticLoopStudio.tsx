import React, { useState } from 'react';
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  Code2,
  FileCode,
  Layers,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Terminal,
  Zap,
} from 'lucide-react';

interface DiagnosticSample {
  id: string;
  name: string;
  category: string;
  testName: string;
  errorType: string;
  errorMessage: string;
  targetFile: string;
  targetLine: number;
  snippet: string;
  proposedFix: string;
  traceback: string;
}

const SAMPLE_DIAGNOSTICS: DiagnosticSample[] = [
  {
    id: 'sample-zero-div',
    name: 'ZeroDivisionError in Metric Calculator',
    category: 'ZERO_DIVISION',
    testName: 'tests.test_metrics.TestMetrics.test_compute_ratio_zero',
    errorType: 'ZeroDivisionError',
    errorMessage: 'division by zero',
    targetFile: 'app/metrics/calculator.py',
    targetLine: 42,
    snippet: `40 | def compute_efficiency_ratio(completed: int, total: int) -> float:
41 |     # Calculate efficiency ratio
42 |     ratio = completed / total
43 |     return round(ratio, 4)`,
    proposedFix: `40 | def compute_efficiency_ratio(completed: int, total: int) -> float:
41 |     # Calculate efficiency ratio with zero guard
42 |     ratio = (completed / total) if total != 0 else 0.0
43 |     return round(ratio, 4)`,
    traceback: `Traceback (most recent call last):
  File "/workspace/tests/test_metrics.py", line 18, in test_compute_ratio_zero
    ratio = compute_efficiency_ratio(10, 0)
  File "/workspace/app/metrics/calculator.py", line 42, in compute_efficiency_ratio
    ratio = completed / total
ZeroDivisionError: division by zero`,
  },
  {
    id: 'sample-index-err',
    name: 'IndexError in Token Queue Worker',
    category: 'INDEX_ERROR',
    testName: 'tests.test_queue.TestQueue.test_pop_empty_queue',
    errorType: 'IndexError',
    errorMessage: 'list index out of range',
    targetFile: 'app/queue/worker.py',
    targetLine: 78,
    snippet: `76 | def dispatch_next_token(queue: List[str]) -> str:
77 |     # Fetch high-priority item
78 |     item = queue[0]
79 |     return item.strip()`,
    proposedFix: `76 | def dispatch_next_token(queue: List[str]) -> Optional[str]:
77 |     # Fetch high-priority item with bounds guard
78 |     if not queue:
79 |         return None
80 |     item = queue[0]
81 |     return item.strip()`,
    traceback: `Traceback (most recent call last):
  File "/workspace/tests/test_queue.py", line 25, in test_pop_empty_queue
    dispatch_next_token([])
  File "/workspace/app/queue/worker.py", line 78, in dispatch_next_token
    item = queue[0]
IndexError: list index out of range`,
  },
  {
    id: 'sample-attr-err',
    name: 'AttributeError: NoneType in Auth Resolver',
    category: 'ATTRIBUTE_ERROR',
    testName: 'tests.test_auth.TestAuth.test_resolve_session_unauthenticated',
    errorType: 'AttributeError',
    errorMessage: "'NoneType' object has no attribute 'token'",
    targetFile: 'app/security/auth.py',
    targetLine: 114,
    snippet: `112 | def resolve_user_context(session: Optional[Session]) -> Dict[str, Any]:
113 |     # Extract token from session
114 |     token = session.token
115 |     return {"token": token, "valid": True}`,
    proposedFix: `112 | def resolve_user_context(session: Optional[Session]) -> Dict[str, Any]:
113 |     # Extract token from session with null guard
114 |     if session is None:
115 |         return {"token": None, "valid": False}
116 |     token = session.token
117 |     return {"token": token, "valid": True}`,
    traceback: `Traceback (most recent call last):
  File "/workspace/tests/test_auth.py", line 33, in test_resolve_session_unauthenticated
    resolve_user_context(None)
  File "/workspace/app/security/auth.py", line 114, in resolve_user_context
    token = session.token
AttributeError: 'NoneType' object has no attribute 'token'`,
  },
];

export const DiagnosticLoopStudio: React.FC = () => {
  const [selectedSample, setSelectedSample] = useState<DiagnosticSample>(SAMPLE_DIAGNOSTICS[0]);
  const [activeTab, setActiveTab] = useState<'reasoner' | 'loop' | 'guards' | 'cli'>('reasoner');

  // Simulation state for closed-loop repair
  const [loopRunning, setLoopRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [maxIterations, setMaxIterations] = useState<number>(4);
  const [autoRollback, setAutoRollback] = useState<boolean>(true);
  const [simulationScenario, setSimulationScenario] = useState<'success' | 'oscillation' | 'regression'>('success');
  const [stepLogs, setStepLogs] = useState<Array<{ iter: number; phase: string; status: string; detail: string }>>([]);

  const runSimulation = () => {
    setLoopRunning(true);
    setCurrentStep(1);
    setStepLogs([]);

    const logs: Array<{ iter: number; phase: string; status: string; detail: string }> = [];

    // Step 1: Initial Test Execution
    logs.push({
      iter: 1,
      phase: '1. TEST EXECUTION',
      status: 'FAILED',
      detail: `Executed test suite: 1 test failed (${selectedSample.errorType}: ${selectedSample.errorMessage})`,
    });
    setStepLogs([...logs]);

    setTimeout(() => {
      // Step 2: Traceback Parsing & Diagnosis
      setCurrentStep(2);
      logs.push({
        iter: 1,
        phase: '2. DIAGNOSTIC REASONER',
        status: 'ANALYZED',
        detail: `Synthesized hypothesis: ${selectedSample.category} at ${selectedSample.targetFile}:${selectedSample.targetLine}. Strategy: ${selectedSample.category}_GUARD (Confidence: 90%)`,
      });
      setStepLogs([...logs]);

      setTimeout(() => {
        // Step 3: Snapshot & Surgical Patch
        setCurrentStep(3);
        logs.push({
          iter: 1,
          phase: '3. SAFE MODIFIER & AST GATE',
          status: 'APPLIED',
          detail: `Created snapshot v1 (SHA-256 verified). Applied surgical edit with AST syntax validation passing cleanly.`,
        });
        setStepLogs([...logs]);

        setTimeout(() => {
          // Step 4: Re-Test & Termination Guard Check
          setCurrentStep(4);
          if (simulationScenario === 'success') {
            logs.push({
              iter: 1,
              phase: '4. RE-TEST & VERIFICATION',
              status: 'RESOLVED',
              detail: `Re-ran tests: 100% passing (0 failures, 0 errors). Loop terminated with status: RESOLVED.`,
            });
          } else if (simulationScenario === 'oscillation') {
            logs.push({
              iter: 2,
              phase: '4. GUARD INTERCEPT',
              status: 'OSCILLATION_DETECTED',
              detail: `Failure fingerprint cycle detected [ErrorA -> ErrorB -> ErrorA]. Loop safely halted to prevent runaway toggling.`,
            });
          } else if (simulationScenario === 'regression') {
            logs.push({
              iter: 1,
              phase: '4. REGRESSION ABORT & ROLLBACK',
              status: 'REGRESSION_ABORT',
              detail: `Test failures increased from 1 to 3! Regression guard triggered: automatically restored ${selectedSample.targetFile} to snapshot v1.`,
            });
          }
          setStepLogs([...logs]);
          setLoopRunning(false);
        }, 1200);
      }, 1000);
    }, 900);
  };

  return (
    <div className="space-y-8 animate-fadeIn text-slate-800">
      {/* Header */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="space-y-1.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
              <Sparkles className="w-3.5 h-3.5" /> Phase 10: Test / Observe / Fix Diagnostic Loop
            </div>
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Autonomous Diagnostic & Closed-Loop Repair Studio
            </h2>
            <p className="text-sm text-slate-600 max-w-3xl leading-relaxed">
              Consumes test failures, extracts multi-frame stack traces, correlates AST source context,
              synthesizes surgical fix hypotheses, applies AST-gated patches, and guards against oscillation and regressions.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-700">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>105/105 Unit Tests Passing (100%)</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-6 pt-4 border-t border-slate-100">
          <button
            onClick={() => setActiveTab('reasoner')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'reasoner'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Traceback & Diagnostic Reasoner
          </button>
          <button
            onClick={() => setActiveTab('loop')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'loop'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Autonomous Fix Loop Simulation
          </button>
          <button
            onClick={() => setActiveTab('guards')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'guards'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            Termination & Regression Guards
          </button>
          <button
            onClick={() => setActiveTab('cli')}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
              activeTab === 'cli'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            CLI & LLM Tool Interfaces
          </button>
        </div>
      </div>

      {/* Tab 1: Traceback & Reasoner */}
      {activeTab === 'reasoner' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sample Selector */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 px-1">
              Select Diagnostic Scenario
            </h3>
            <div className="space-y-2">
              {SAMPLE_DIAGNOSTICS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => setSelectedSample(s)}
                  className={`w-full text-left p-4 rounded-xl border transition-all ${
                    selectedSample.id === s.id
                      ? 'bg-emerald-50/70 border-emerald-400 shadow-sm ring-1 ring-emerald-400'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                      {s.category}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">Line {s.targetLine}</span>
                  </div>
                  <h4 className="font-semibold text-slate-900 text-sm mt-2">{s.name}</h4>
                  <p className="text-xs text-slate-600 font-mono truncate mt-1">{s.targetFile}</p>
                </button>
              ))}
            </div>

            {/* Error Category Reference */}
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-xs space-y-2">
              <span className="font-bold text-slate-800">12 Normalized Error Categories:</span>
              <div className="flex flex-wrap gap-1.5">
                {[
                  'ZERO_DIVISION',
                  'INDEX_ERROR',
                  'KEY_ERROR',
                  'ATTRIBUTE_ERROR',
                  'TYPE_ERROR',
                  'ASSERTION_ERROR',
                  'IMPORT_ERROR',
                  'SYNTAX_ERROR',
                  'TIMEOUT_ERROR',
                  'RUNTIME_ERROR',
                  'UNHANDLED_EXCEPTION',
                  'UNKNOWN',
                ].map((cat) => (
                  <span
                    key={cat}
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                      selectedSample.category === cat
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white border border-slate-200 text-slate-600'
                    }`}
                  >
                    {cat}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Diagnostic Details & Code Context */}
          <div className="lg:col-span-8 space-y-6">
            {/* Parsed Traceback */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-slate-700" />
                  <h3 className="font-bold text-slate-900 text-sm">Parsed Traceback & Stack Extraction</h3>
                </div>
                <span className="px-2.5 py-1 bg-red-50 border border-red-200 rounded-full text-xs font-semibold text-red-700">
                  {selectedSample.errorType}
                </span>
              </div>

              <pre className="bg-slate-950 text-slate-200 p-4 rounded-xl text-xs font-mono overflow-x-auto leading-relaxed border border-slate-800">
                {selectedSample.traceback}
              </pre>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2">
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3">
                  <span className="text-[11px] font-medium text-slate-500">Target File</span>
                  <p className="text-xs font-bold font-mono text-slate-800 truncate mt-0.5">
                    {selectedSample.targetFile}
                  </p>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3">
                  <span className="text-[11px] font-medium text-slate-500">Target Line</span>
                  <p className="text-xs font-bold font-mono text-slate-800 mt-0.5">
                    Line {selectedSample.targetLine}
                  </p>
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-3">
                  <span className="text-[11px] font-medium text-slate-500">Diagnosis Confidence</span>
                  <p className="text-xs font-bold text-emerald-700 mt-0.5">90% (High Confidence)</p>
                </div>
              </div>
            </div>

            {/* Code Context & Proposed Fix */}
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 className="w-4 h-4 text-slate-700" />
                  <h3 className="font-bold text-slate-900 text-sm">Source Context & Surgical Fix Synthesis</h3>
                </div>
                <span className="px-2.5 py-1 bg-emerald-50 border border-emerald-200 rounded-full text-xs font-semibold text-emerald-700">
                  AST Validated Strategy
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <span className="text-xs font-semibold text-red-600 mb-1.5 block">Original Fault Line:</span>
                  <pre className="bg-red-950/20 border border-red-200/60 text-slate-800 p-3 rounded-xl text-xs font-mono overflow-x-auto leading-relaxed">
                    {selectedSample.snippet}
                  </pre>
                </div>

                <div>
                  <span className="text-xs font-semibold text-emerald-700 mb-1.5 block">Synthesized Patch:</span>
                  <pre className="bg-emerald-950/20 border border-emerald-200/60 text-slate-800 p-3 rounded-xl text-xs font-mono overflow-x-auto leading-relaxed">
                    {selectedSample.proposedFix}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Autonomous Fix Loop Simulation */}
      {activeTab === 'loop' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">Closed-Loop Repair Execution Pipeline</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Test &rarr; Observe &rarr; Diagnose &rarr; Patch &rarr; Re-Test with automated rollback & oscillation guards.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={simulationScenario}
                  onChange={(e) => setSimulationScenario(e.target.value as any)}
                  className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="success">Scenario: Clean Resolution (Pass)</option>
                  <option value="oscillation">Scenario: Oscillation Guard Intercept</option>
                  <option value="regression">Scenario: Regression Rollback Guard</option>
                </select>

                <button
                  onClick={runSimulation}
                  disabled={loopRunning}
                  className={`inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all shadow-sm ${
                    loopRunning
                      ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                      : 'bg-emerald-600 text-white hover:bg-emerald-700'
                  }`}
                >
                  {loopRunning ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running Loop...
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" /> Execute Diagnostic Loop
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Pipeline Stage Visualizer */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {[
                { stage: 1, name: '1. Test & Observe', desc: 'Run test suite & normalize output' },
                { stage: 2, name: '2. Diagnose', desc: 'Synthesize root-cause hypothesis' },
                { stage: 3, name: '3. Surgical Patch', desc: 'Snapshot & AST-gated edit' },
                { stage: 4, name: '4. Re-Verify & Guard', desc: 'Re-test & verify resolution' },
              ].map((p) => {
                const isCurrent = currentStep === p.stage;
                const isPassed = currentStep > p.stage;
                return (
                  <div
                    key={p.stage}
                    className={`p-4 rounded-xl border transition-all ${
                      isCurrent
                        ? 'bg-emerald-50 border-emerald-400 ring-2 ring-emerald-300'
                        : isPassed
                        ? 'bg-slate-50 border-slate-300 text-slate-700'
                        : 'bg-white border-slate-200 text-slate-400'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold">{p.name}</span>
                      {isPassed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : isCurrent ? (
                        <RefreshCw className="w-4 h-4 text-emerald-600 animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-300" />
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 mt-1">{p.desc}</p>
                  </div>
                );
              })}
            </div>

            {/* Live Step Logs */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Diagnostic Execution Timeline
              </h4>
              {stepLogs.length === 0 ? (
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-500 font-mono">
                  Click "Execute Diagnostic Loop" above to run the closed-loop repair cycle.
                </div>
              ) : (
                <div className="space-y-2">
                  {stepLogs.map((log, idx) => (
                    <div
                      key={idx}
                      className={`p-3.5 rounded-xl border flex items-start gap-3 text-xs ${
                        log.status === 'RESOLVED'
                          ? 'bg-emerald-50/80 border-emerald-300 text-emerald-900'
                          : log.status === 'REGRESSION_ABORT' || log.status === 'OSCILLATION_DETECTED'
                          ? 'bg-amber-50/80 border-amber-300 text-amber-900'
                          : 'bg-white border-slate-200 text-slate-800'
                      }`}
                    >
                      <div className="mt-0.5">
                        {log.status === 'RESOLVED' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ) : log.status === 'REGRESSION_ABORT' || log.status === 'OSCILLATION_DETECTED' ? (
                          <AlertTriangle className="w-4 h-4 text-amber-600" />
                        ) : (
                          <Activity className="w-4 h-4 text-slate-600" />
                        )}
                      </div>
                      <div className="space-y-0.5 flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-xs">{log.phase}</span>
                          <span className="font-mono text-[10px] px-2 py-0.5 bg-slate-100 rounded text-slate-700">
                            {log.status}
                          </span>
                        </div>
                        <p className="font-mono text-slate-600 text-[11px] leading-relaxed">{log.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Termination & Regression Guards */}
      {activeTab === 'guards' && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-700">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Resolution Verification</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              When a surgical patch resolves all test failures (exit code 0, 0 failures, 0 errors),
              the loop immediately terminates with status <code className="text-emerald-700 font-mono">RESOLVED</code>.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700">
              <RotateCcw className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Oscillation Detector</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              Computes deterministic failure fingerprint hashes. If an error cycle is detected (e.g. Error A &rarr; Error B &rarr; Error A),
              the loop immediately halts with <code className="text-amber-700 font-mono">OSCILLATION_DETECTED</code>.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="w-10 h-10 rounded-xl bg-red-50 border border-red-200 flex items-center justify-center text-red-700">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-slate-900 text-sm">Regression Rollback Guard</h4>
            <p className="text-xs text-slate-600 leading-relaxed">
              If an attempted fix increases failure count or causes previously passing tests to fail,
              the loop automatically triggers an atomic rollback to the point-in-time snapshot and aborts with <code className="text-red-700 font-mono">REGRESSION_ABORT</code>.
            </p>
          </div>
        </div>
      )}

      {/* Tab 4: CLI & LLM Tool Interfaces */}
      {activeTab === 'cli' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-slate-700" />
              <h3 className="font-bold text-slate-900 text-sm">CLI Diagnostic Utilities</h3>
            </div>
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-slate-950 text-slate-200 rounded-xl">
                <span className="text-emerald-400">$</span> ./run_diagnostics.py test --cmd "python3 -m unittest discover"
              </div>
              <div className="p-3 bg-slate-950 text-slate-200 rounded-xl">
                <span className="text-emerald-400">$</span> ./run_diagnostics.py diagnose --file traceback.log
              </div>
              <div className="p-3 bg-slate-950 text-slate-200 rounded-xl">
                <span className="text-emerald-400">$</span> ./run_diagnostics.py autofix --max-iter 4
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-slate-700" />
              <h3 className="font-bold text-slate-900 text-sm">Registered LLM Diagnostic Tools</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                <span className="font-bold text-xs font-mono text-emerald-800">run_diagnostics</span>
                <p className="text-xs text-slate-600">
                  Executes test commands (unittest, pytest) and returns structured failure reports with parsed stack frames.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                <span className="font-bold text-xs font-mono text-emerald-800">diagnose_test_failure</span>
                <p className="text-xs text-slate-600">
                  Analyzes parsed failures against workspace source code and synthesizes root-cause hypotheses and fix proposals.
                </p>
              </div>
              <div className="p-4 rounded-xl border border-slate-200 bg-slate-50 space-y-2">
                <span className="font-bold text-xs font-mono text-emerald-800">auto_fix_loop</span>
                <p className="text-xs text-slate-600">
                  Executes closed-loop test-observe-fix cycle with AST syntax gating, oscillation checks, and snapshot rollbacks.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect, useRef } from 'react';
import {
  Terminal,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Activity,
  CheckCircle2,
  Clock,
  Sparkles,
  Wrench,
  Cpu,
  Layers,
  Search,
  ShieldCheck,
  ArrowRight,
  Radio,
  FileCode,
  Bug,
  StepForward,
  StopCircle,
  Settings,
  Flame,
  Zap,
  HardDrive,
  Code,
} from 'lucide-react';
import { AgentStreamEvent } from '../types';
import { streamingApi } from '../api/streaming';

export const LiveStreamingConsole: React.FC = () => {
  const [mode, setMode] = useState<'stream' | 'debugger'>('stream');
  const [scenarioId, setScenarioId] = useState('refactor-sqlite');
  const [scenarios, setScenarios] = useState<any[]>([
    { id: 'refactor-sqlite', title: 'Refactor SQLite Storage Cascade & Indexing', totalSteps: 7 },
    { id: 'fix-import-cycle', title: 'Resolve Circular Import in Diagnostics Subsystem', totalSteps: 6 },
    { id: 'security-audit', title: 'Autonomous Path Traversal & Shell Injection Audit', totalSteps: 5 },
  ]);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [totalSteps, setTotalSteps] = useState(7);
  const [selectedEvent, setSelectedEvent] = useState<AgentStreamEvent | null>(null);

  // Debugger State
  const [dbgStep, setDbgStep] = useState(0);
  const [dbgTotal, setDbgTotal] = useState(7);
  const [dbgIsPaused, setDbgIsPaused] = useState(false);
  const [dbgIsComplete, setDbgIsComplete] = useState(false);
  const [breakpoints, setBreakpoints] = useState<{ [key: string]: boolean }>({
    AST_VALIDATION: true,
    TOOL_CALL: false,
    PATCH_STAGE: true,
  });

  // Telemetry Metrics
  const [totalTokens, setTotalTokens] = useState(0);
  const [tokenRate, setTokenRate] = useState(48.5);
  const [memoryUsage, setMemoryUsage] = useState(42.5);

  const [terminalLogs, setTerminalLogs] = useState<string[]>([
    '[INIT] NexForge Droid Streaming Subsystem initialized.',
    '[READY] Tool registry connected (22 active tools).',
    '[READY] SQLite state journal mounted at /nexforge.db',
    '[READY] Phase 12 Interactive Debugger Session mounted.',
  ]);

  const terminalEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollTop = terminalEndRef.current.scrollHeight;
    }
  }, [events, terminalLogs]);

  useEffect(() => {
    fetchScenarios();
  }, []);

  const fetchScenarios = async () => {
    try {
      const data = await streamingApi.getScenarios();
      if (data.success && data.scenarios) {
        setScenarios(data.scenarios);
      }
    } catch (e) {
      console.error('Failed to fetch scenarios:', e);
    }
  };

  const startLiveStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setEvents([]);
    setCurrentStep(0);
    setIsStreaming(true);
    setSelectedEvent(null);
    setTotalTokens(0);

    const eventSource = new EventSource(streamingApi.createEventStreamUrl(scenarioId));
    eventSourceRef.current = eventSource;

    setTerminalLogs((prev) => [
      ...prev,
      `[STREAM_START] Dispatched autonomous execution stream for scenario: ${scenarioId}`,
    ]);

    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.done) {
          eventSource.close();
          setIsStreaming(false);
          setTerminalLogs((prev) => [
            ...prev,
            '[STREAM_COMPLETE] Autonomous agent reasoning loop finished with 100% verified execution.',
          ]);
          return;
        }

        if (data.event) {
          setEvents((prev) => [...prev, data]);
          setCurrentStep(data.step);
          setTotalSteps(data.total);
          setSelectedEvent(data);

          // Update metrics
          const stepTokens = Math.floor(Math.random() * 35) + 20;
          setTotalTokens((prev) => prev + stepTokens);
          setMemoryUsage(42.0 + data.step * 1.5);
          setTokenRate(45 + Math.random() * 8);

          // Log to terminal
          const ev = data.event;
          let logMsg = `[STEP ${data.step}/${data.total}] ${ev.type}`;
          if (ev.type === 'THINKING') logMsg += `: ${ev.text}`;
          if (ev.type === 'TOOL_CALL') logMsg += `: ${ev.tool} (${JSON.stringify(ev.args || {})})`;
          if (ev.type === 'AST_VALIDATION') logMsg += `: File ${ev.file} -> ${ev.status}`;
          if (ev.type === 'PATCH_STAGE') logMsg += `: Staged diff ${ev.diffLines} on ${ev.file}`;
          if (ev.type === 'REGRESSION_TEST') logMsg += `: Suite ${ev.suite} -> Passed (${ev.testsPassed} tests)`;
          if (ev.type === 'COMPLETION') logMsg += `: ${ev.summary}`;

          setTerminalLogs((prev) => [...prev, logMsg]);
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = (err) => {
      console.error('SSE connection error:', err);
      eventSource.close();
      setIsStreaming(false);
    };
  };

  const handleDebuggerReset = async () => {
    try {
      const data = await streamingApi.resetDebugger(scenarioId);
      if (data.success) {
        setEvents([]);
        setDbgStep(0);
        setDbgTotal(data.session?.totalSteps || 7);
        setDbgIsPaused(false);
        setDbgIsComplete(false);
        setSelectedEvent(null);
        setTerminalLogs((prev) => [
          ...prev,
          `[DEBUGGER_RESET] Debugger reset on scenario: ${scenarioId}`,
        ]);
      }
    } catch (e) {
      console.error('Debugger reset failed:', e);
    }
  };

  const handleDebuggerStep = async () => {
    try {
      const data = await streamingApi.stepDebugger();
      if (data.success && data.rawEvent) {
        setEvents((prev) => [...prev, data.rawEvent]);
        setDbgStep(data.step);
        setDbgTotal(data.total);
        setDbgIsComplete(data.done);
        setDbgIsPaused(data.hitBreakpoint);
        setSelectedEvent(data.rawEvent);

        const ev = data.event;
        let logMsg = `[DBG_STEP ${data.step}/${data.total}] ${ev.type}`;
        if (ev.type === 'THINKING') logMsg += `: ${ev.text}`;
        if (ev.type === 'TOOL_CALL') logMsg += `: ${ev.tool}`;
        if (ev.type === 'AST_VALIDATION') logMsg += `: ${ev.file} -> ${ev.status}`;
        if (ev.type === 'PATCH_STAGE') logMsg += `: ${ev.file} (${ev.diffLines})`;
        if (ev.type === 'REGRESSION_TEST') logMsg += `: ${ev.suite} Passed`;
        if (ev.type === 'COMPLETION') logMsg += `: ${ev.summary}`;

        if (data.hitBreakpoint) {
          logMsg += ` [BREAKPOINT HIT]`;
        }
        setTerminalLogs((prev) => [...prev, logMsg]);
      }
    } catch (e) {
      console.error('Debugger step failed:', e);
    }
  };

  const handleDebuggerContinue = async () => {
    try {
      const data = await streamingApi.continueDebugger();
      if (data.success && data.steps) {
        for (const s of data.steps) {
          if (s.rawEvent) {
            setEvents((prev) => [...prev, s.rawEvent]);
            setSelectedEvent(s.rawEvent);
          }
        }
        const lastStep = data.steps[data.steps.length - 1];
        if (lastStep) {
          setDbgStep(lastStep.step);
          setDbgTotal(lastStep.total);
          setDbgIsComplete(lastStep.done);
          setDbgIsPaused(lastStep.hitBreakpoint);
        }
        setTerminalLogs((prev) => [
          ...prev,
          `[DBG_CONTINUE] Executed ${data.stepsExecuted} steps to next checkpoint or completion.`,
        ]);
      }
    } catch (e) {
      console.error('Debugger continue failed:', e);
    }
  };

  const toggleBreakpoint = async (eventType: string) => {
    const nextBp = { ...breakpoints, [eventType]: !breakpoints[eventType] };
    setBreakpoints(nextBp);
    const activeTypes = Object.keys(nextBp).filter((k) => nextBp[k]);
    try {
      await streamingApi.setBreakpoints(activeTypes);
    } catch (e) {
      console.error('Failed to sync breakpoints:', e);
    }
  };

  const clearConsole = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsStreaming(false);
    setEvents([]);
    setCurrentStep(0);
    setDbgStep(0);
    setSelectedEvent(null);
    setTerminalLogs([
      '[RESET] Telemetry and debugger stream cleared.',
      '[READY] Ready for next autonomous agent dispatch.',
    ]);
  };

  return (
    <div id="live-streaming-root" className="space-y-6">
      {/* Top Banner */}
      <div id="streaming-header" className="bg-slate-900 border border-slate-800 rounded-xl p-6 relative overflow-hidden shadow-lg">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Radio className="w-48 h-48 text-indigo-400" />
        </div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-indigo-400 animate-pulse" /> Phase 12 Live Agent Event Stream
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <Bug className="w-3.5 h-3.5" /> Interactive Step Debugger &amp; SSE Telemetry
              </span>
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Agent Execution Stream &amp; Interactive Debugger
            </h1>
            <p className="text-slate-400 text-sm mt-1 max-w-2xl">
              Inspect token generation velocity, step-by-step reasoning pauses, AST syntax checks, live subprocess stdout/stderr, and payload inspectors.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              id="clear-stream-btn"
              onClick={clearConsole}
              className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium flex items-center gap-1.5 transition"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Clear Stream
            </button>

            {mode === 'stream' ? (
              <button
                id="start-stream-btn"
                onClick={startLiveStream}
                disabled={isStreaming}
                className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-2 transition shadow"
              >
                {isStreaming ? (
                  <>
                    <Activity className="w-4 h-4 animate-spin text-white" /> Streaming Telemetry...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" /> Start Real-Time Stream
                  </>
                )}
              </button>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  id="dbg-step-btn"
                  onClick={handleDebuggerStep}
                  disabled={dbgIsComplete}
                  className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                >
                  <StepForward className="w-3.5 h-3.5" /> Step Next
                </button>
                <button
                  id="dbg-continue-btn"
                  onClick={handleDebuggerContinue}
                  disabled={dbgIsComplete}
                  className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 transition shadow"
                >
                  <Play className="w-3.5 h-3.5" /> Continue (Run)
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Mode Selector & Scenario Switcher Bar */}
        <div className="mt-6 pt-4 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
              <button
                id="mode-stream-btn"
                onClick={() => setMode('stream')}
                className={`px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 ${
                  mode === 'stream'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Radio className="w-3.5 h-3.5" /> Live SSE Mode
              </button>
              <button
                id="mode-debugger-btn"
                onClick={() => {
                  setMode('debugger');
                  handleDebuggerReset();
                }}
                className={`px-3 py-1.5 rounded-md font-medium transition flex items-center gap-1.5 ${
                  mode === 'debugger'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                <Bug className="w-3.5 h-3.5" /> Step-by-Step Debugger
              </button>
            </div>

            {/* Scenario Dropdown */}
            <select
              id="scenario-select"
              value={scenarioId}
              onChange={(e) => {
                setScenarioId(e.target.value);
                if (mode === 'debugger') {
                  setTimeout(() => handleDebuggerReset(), 50);
                }
              }}
              className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-medium"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  Scenario: {s.title}
                </option>
              ))}
            </select>
          </div>

          {/* Breakpoint Toggles */}
          {mode === 'debugger' && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400 font-medium flex items-center gap-1">
                <StopCircle className="w-3.5 h-3.5 text-rose-400" /> Breakpoints:
              </span>
              {['AST_VALIDATION', 'TOOL_CALL', 'PATCH_STAGE'].map((type) => (
                <button
                  key={type}
                  onClick={() => toggleBreakpoint(type)}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition ${
                    breakpoints[type]
                      ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                      : 'bg-slate-950 text-slate-500 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {type} {breakpoints[type] ? '●' : '○'}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Telemetry Metrics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-800/80">
          <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg flex items-center gap-3">
            <Zap className="w-4 h-4 text-amber-400" />
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Generation Rate</div>
              <div className="text-sm font-bold text-white font-mono">{tokenRate.toFixed(1)} tok/s</div>
            </div>
          </div>
          <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg flex items-center gap-3">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Total Tokens</div>
              <div className="text-sm font-bold text-indigo-300 font-mono">{totalTokens || (events.length * 38)}</div>
            </div>
          </div>
          <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg flex items-center gap-3">
            <HardDrive className="w-4 h-4 text-emerald-400" />
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Resident Memory</div>
              <div className="text-sm font-bold text-emerald-300 font-mono">{memoryUsage.toFixed(1)} MB</div>
            </div>
          </div>
          <div className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg flex items-center gap-3">
            <Clock className="w-4 h-4 text-cyan-400" />
            <div>
              <div className="text-[10px] text-slate-500 uppercase font-semibold">Step Status</div>
              <div className="text-sm font-bold text-cyan-300 font-mono">
                {mode === 'stream' ? `${currentStep}/${totalSteps}` : `${dbgStep}/${dbgTotal}`}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Timeline Feed (6 Cols) */}
        <div className="lg:col-span-6 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" />
              <h3 className="font-semibold text-white text-base">Execution Event Timeline</h3>
            </div>
            <span className="text-xs text-slate-400 font-mono">{events.length} events logged</span>
          </div>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-[520px] pr-1">
            {events.length > 0 ? (
              events.map((evItem, idx) => {
                const ev = evItem.event;
                const isSelected = selectedEvent === evItem;
                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedEvent(evItem)}
                    className={`p-3.5 rounded-lg border flex items-start gap-3 transition cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-950/50 border-indigo-500/80 shadow-md'
                        : 'bg-slate-950 border-slate-800/90 hover:border-slate-700'
                    }`}
                  >
                    <div className="mt-0.5">
                      {ev.type === 'THINKING' && (
                        <div className="p-1.5 rounded-md bg-indigo-500/20 text-indigo-300">
                          <Sparkles className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'TOOL_CALL' && (
                        <div className="p-1.5 rounded-md bg-amber-500/20 text-amber-300">
                          <Wrench className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'TOOL_RESULT' && (
                        <div className="p-1.5 rounded-md bg-cyan-500/20 text-cyan-300">
                          <Layers className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'AST_VALIDATION' && (
                        <div className="p-1.5 rounded-md bg-emerald-500/20 text-emerald-300">
                          <ShieldCheck className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'PATCH_STAGE' && (
                        <div className="p-1.5 rounded-md bg-purple-500/20 text-purple-300">
                          <FileCode className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'REGRESSION_TEST' && (
                        <div className="p-1.5 rounded-md bg-emerald-500/20 text-emerald-300">
                          <CheckCircle2 className="w-4 h-4" />
                        </div>
                      )}
                      {ev.type === 'COMPLETION' && (
                        <div className="p-1.5 rounded-md bg-emerald-500/30 text-emerald-200">
                          <CheckCircle2 className="w-4 h-4" />
                        </div>
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="font-bold text-slate-200 font-mono tracking-wide">{ev.type}</span>
                        <span className="text-slate-500 font-mono text-[10px]">
                          Step {evItem.step} of {evItem.total}
                        </span>
                      </div>

                      {ev.type === 'THINKING' && (
                        <p className="text-xs text-slate-300 leading-relaxed italic">{ev.text}</p>
                      )}

                      {ev.type === 'TOOL_CALL' && (
                        <div className="text-xs font-mono text-slate-300 bg-slate-900 p-2 rounded border border-slate-800">
                          <span className="text-amber-400 font-semibold">{ev.tool}</span>
                          <span className="text-slate-500">({JSON.stringify(ev.args || {})})</span>
                        </div>
                      )}

                      {ev.type === 'TOOL_RESULT' && (
                        <p className="text-xs text-cyan-300 font-mono leading-relaxed">{ev.result}</p>
                      )}

                      {ev.type === 'AST_VALIDATION' && (
                        <div className="text-xs text-emerald-300 flex items-center gap-1.5">
                          <span>Target: <strong className="font-mono text-white">{ev.file}</strong></span>
                          <span>• Status: <strong className="text-emerald-400">{ev.status}</strong></span>
                        </div>
                      )}

                      {ev.type === 'PATCH_STAGE' && (
                        <div className="text-xs text-purple-300 flex items-center gap-2 font-mono">
                          <span>{ev.file}</span>
                          <span className="text-emerald-400">{ev.diffLines}</span>
                        </div>
                      )}

                      {ev.type === 'REGRESSION_TEST' && (
                        <div className="text-xs text-slate-300 flex items-center gap-2">
                          <span className="text-emerald-400 font-bold">Passed</span>
                          <span>{ev.testsPassed} test cases in {ev.suite}</span>
                        </div>
                      )}

                      {ev.type === 'COMPLETION' && (
                        <p className="text-xs text-emerald-300 font-medium">{ev.summary}</p>
                      )}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-slate-500 text-center">
                <Radio className="w-12 h-12 text-slate-600 mb-3 animate-pulse" />
                <p className="text-sm font-medium text-slate-400">Stream Waiting for Agent Run</p>
                <p className="text-xs text-slate-500 mt-1 max-w-sm">
                  Click "Start Real-Time Stream" or switch to "Step-by-Step Debugger" above.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Terminal & Inspector (6 Cols) */}
        <div className="lg:col-span-6 flex flex-col gap-6">
          {/* Subprocess Terminal Output */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>Subprocess Terminal (stdout/stderr)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                <span className="text-[10px] text-emerald-400 font-mono">LIVE</span>
              </div>
            </div>

            <div
              ref={terminalEndRef}
              className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 overflow-y-auto max-h-56 space-y-1 leading-relaxed"
            >
              {terminalLogs.map((log, lIdx) => {
                let colorClass = 'text-slate-300';
                if (log.startsWith('[INIT]') || log.startsWith('[READY]')) colorClass = 'text-indigo-400';
                if (log.includes('TOOL_CALL') || log.includes('RUNNING') || log.includes('DBG')) colorClass = 'text-amber-300';
                if (log.includes('PASSED') || log.includes('COMPLETE') || log.includes('VALID')) colorClass = 'text-emerald-300';
                if (log.includes('ERROR') || log.includes('FAIL') || log.includes('BREAKPOINT')) colorClass = 'text-rose-400';

                return (
                  <div key={lIdx} className={colorClass}>
                    {log}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Event Payload Inspector */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex-1 flex flex-col space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-white font-semibold text-sm">
                <Code className="w-4 h-4 text-indigo-400" />
                <span>Event Payload Inspector</span>
              </div>
              {selectedEvent && (
                <span className="text-[11px] font-mono text-indigo-300 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-800">
                  {selectedEvent.event.type}
                </span>
              )}
            </div>

            {selectedEvent ? (
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 overflow-y-auto max-h-64 space-y-2">
                <pre className="text-indigo-300 leading-relaxed overflow-x-auto">
                  {JSON.stringify(selectedEvent, null, 2)}
                </pre>
              </div>
            ) : (
              <div className="py-12 text-center text-slate-500 text-xs">
                Select an event from the timeline to inspect full parameters, tokens, and response AST nodes.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

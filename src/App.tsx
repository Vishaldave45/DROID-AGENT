import React, { useState, useEffect } from 'react';
import { ArchitectureGraph } from './components/ArchitectureGraph';
import { SubsystemCard } from './components/SubsystemCard';
import { TestResultsViewer } from './components/TestResultsViewer';
import { RoadmapTimeline } from './components/RoadmapTimeline';
import { FileTreeViewer } from './components/FileTreeViewer';
import { LLMPlayground } from './components/LLMPlayground';
import { ToolSystemExplorer } from './components/ToolSystemExplorer';
import { AgentLoopStudio } from './components/AgentLoopStudio';
import { StatePersistenceStudio } from './components/StatePersistenceStudio';
import { RepoIntelligenceStudio } from './components/RepoIntelligenceStudio';
import { ContextBudgetStudio } from './components/ContextBudgetStudio';
import { TaskPlannerStudio } from './components/TaskPlannerStudio';
import { SafePatchingStudio } from './components/SafePatchingStudio';
import { DiagnosticLoopStudio } from './components/DiagnosticLoopStudio';
import { WorkspaceOrchestratorStudio } from './components/WorkspaceOrchestratorStudio';
import { LiveStreamingConsole } from './components/LiveStreamingConsole';
import { SUBSYSTEMS, PHASE_ROADMAP } from './data/architectureData';
import { SubsystemInfo } from './types';
import { systemApi, SystemManifestResponse } from './api';
import {
  Cpu,
  ShieldCheck,
  Terminal,
  Layers,
  Milestone,
  CheckCircle2,
  Bot,
  Wrench,
  PlayCircle,
  Database,
  Compass,
  Gauge,
  ListOrdered,
  FileEdit,
  Activity,
  GitPullRequest,
  Radio,
} from 'lucide-react';

export default function App() {
  const [activeView, setActiveView] = useState<
    | 'orchestrator'
    | 'streaming'
    | 'diagnostics'
    | 'patcher'
    | 'planner'
    | 'context'
    | 'repo'
    | 'storage'
    | 'agent'
    | 'tools'
    | 'llm'
    | 'architecture'
    | 'subsystems'
    | 'tests'
    | 'files'
    | 'roadmap'
  >('orchestrator');

  const [subsystems, setSubsystems] = useState<SubsystemInfo[]>(SUBSYSTEMS);
  const [manifest, setManifest] = useState<SystemManifestResponse | null>(null);

  useEffect(() => {
    // Dynamically fetch live system manifest and real subsystems from Python backend
    systemApi
      .getManifest()
      .then((data) => {
        if (data && data.success) {
          setManifest(data);
        }
      })
      .catch(console.error);

    systemApi
      .getSubsystems()
      .then((data) => {
        if (data && data.subsystems && data.subsystems.length > 0) {
          setSubsystems(data.subsystems);
        }
      })
      .catch(console.error);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 via-emerald-500 to-indigo-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-indigo-950">
              N
            </div>
            <div>
              <div className="font-bold text-base text-white tracking-tight flex items-center gap-2">
                NexForge Droid
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  Phase 11 &amp; 12 Live
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Software Engineering Agent Platform</p>
            </div>
          </div>

          {/* Navigation Bar */}
          <nav className="flex items-center gap-1 overflow-x-auto max-w-[65%] py-2">
            {[
              { id: 'orchestrator', label: 'Orchestrator (Phase 11)', icon: GitPullRequest, highlight: true },
              { id: 'streaming', label: 'Live Stream (Phase 12)', icon: Radio, highlight: true },
              { id: 'diagnostics', label: 'Fix Loop (Phase 10)', icon: Activity },
              { id: 'patcher', label: 'Safe Patcher (AST)', icon: FileEdit },
              { id: 'planner', label: 'Task Planner (DAG)', icon: ListOrdered },
              { id: 'context', label: 'Context & Budget', icon: Gauge },
              { id: 'repo', label: 'Repo & Code Graph', icon: Compass },
              { id: 'storage', label: 'State & SQLite DB', icon: Database },
              { id: 'agent', label: 'Agent Loop Studio', icon: PlayCircle },
              { id: 'tools', label: `Core Tools (${manifest?.toolCount || 22})`, icon: Wrench },
              { id: 'llm', label: 'LLM & Gemini', icon: Bot },
              { id: 'architecture', label: 'Architecture', icon: Layers },
              { id: 'subsystems', label: `Subsystems (${subsystems.length})`, icon: Cpu },
              { id: 'tests', label: 'Verification (109 Tests)', icon: ShieldCheck },
              { id: 'files', label: 'Filesystem', icon: Terminal },
              { id: 'roadmap', label: 'Roadmap', icon: Milestone },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeView === tab.id;
              return (
                <button
                  key={tab.id}
                  id={`nav-btn-${tab.id}`}
                  onClick={() => setActiveView(tab.id as any)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-slate-800 text-white shadow-sm border border-slate-700'
                      : tab.highlight
                      ? 'text-indigo-300 hover:text-white hover:bg-slate-800/60 bg-indigo-950/30 border border-indigo-900/50'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon
                    className={`w-3.5 h-3.5 ${
                      isActive
                        ? 'text-emerald-400'
                        : tab.highlight
                        ? 'text-indigo-400'
                        : 'text-slate-500'
                    }`}
                  />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Phase Status Banner */}
        <section
          id="phase-banner"
          className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4"
        >
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-indigo-400 font-mono">
                Phase 11 &amp; 12: End-to-End Orchestration &amp; Live Streaming Active
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Autonomous Workspace Orchestrator, Multi-File Refactor &amp; Live Telemetry Engine
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              Coordinates multi-file AST symbol renaming, atomic staged changesets, automated PR Markdown synthesis, Human-in-the-Loop review gates, and real-time SSE execution telemetry with 109 verified unit tests.
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-xs text-slate-400">Runtime Status</div>
              <div className="text-lg font-bold text-emerald-400 font-mono flex items-center gap-1 justify-end">
                <CheckCircle2 className="w-4 h-4" /> 109/109 Tests Passing
              </div>
            </div>
          </div>
        </section>

        {/* Dynamic View Sections */}
        {activeView === 'orchestrator' && <WorkspaceOrchestratorStudio />}

        {activeView === 'streaming' && <LiveStreamingConsole />}

        {activeView === 'diagnostics' && <DiagnosticLoopStudio />}

        {activeView === 'patcher' && <SafePatchingStudio />}

        {activeView === 'planner' && <TaskPlannerStudio />}

        {activeView === 'context' && <ContextBudgetStudio />}

        {activeView === 'repo' && <RepoIntelligenceStudio />}

        {activeView === 'storage' && <StatePersistenceStudio />}

        {activeView === 'agent' && <AgentLoopStudio />}

        {activeView === 'tools' && <ToolSystemExplorer />}

        {activeView === 'llm' && <LLMPlayground />}

        {activeView === 'architecture' && (
          <div className="space-y-8">
            <ArchitectureGraph />
            <SubsystemCard subsystems={subsystems} />
          </div>
        )}

        {activeView === 'subsystems' && <SubsystemCard subsystems={subsystems} />}

        {activeView === 'tests' && <TestResultsViewer />}

        {activeView === 'files' && <FileTreeViewer />}

        {activeView === 'roadmap' && <RoadmapTimeline roadmap={PHASE_ROADMAP} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-400">
        <p>NexForge Droid — Autonomous Software Engineering Platform • Phase 11 &amp; 12 Autonomous Orchestration</p>
      </footer>
    </div>
  );
}

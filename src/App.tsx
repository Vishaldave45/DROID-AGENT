import React, { useState } from 'react';
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
import { EvaluationBenchmarkStudio } from './components/EvaluationBenchmarkStudio';
import { UvCliDistributionStudio } from './components/UvCliDistributionStudio';
import { SwarmCollaborationStudio } from './components/SwarmCollaborationStudio';
import { PhaseDocsStudio } from './components/PhaseDocsStudio';
import { PHASE_ROADMAP } from './data/architectureData';
import { SystemProvider, useSystem } from './context/SystemContext';
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
  FlaskConical,
  Zap,
  Award,
  BookOpen,
  Users,
  Package,
} from 'lucide-react';

function MainApp() {
  const [activeView, setActiveView] = useState<
    | 'uv-cli'
    | 'swarm'
    | 'docs'
    | 'evaluation'
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
  >('uv-cli');

  const { manifest, subsystems, demoMode, health } = useSystem();

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
                  Phase {health?.phase || 12} Live
                </span>
                {demoMode ? (
                  <span
                    id="demo-mode-badge"
                    className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 border border-amber-800/80 flex items-center gap-1 shadow-sm"
                    title="Demo Mode is ACTIVE: Mock/sample scenarios available"
                  >
                    <FlaskConical className="w-3 h-3 text-amber-400" />
                    DEMO MODE
                  </span>
                ) : (
                  <span
                    id="live-mode-badge"
                    className="text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-800/80 flex items-center gap-1 shadow-sm"
                    title="Live Execution Mode: Direct workspace tools and real AST"
                  >
                    <Zap className="w-3 h-3 text-indigo-400" />
                    PRODUCTION RUNTIME
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">Autonomous Software Engineering Agent Platform</p>
            </div>
          </div>

          {/* Navigation Bar */}
          <nav className="flex items-center gap-1 overflow-x-auto max-w-[65%] py-2">
            {[
              { id: 'uv-cli', label: 'UV & CLI Packaging (Phase 14)', icon: Terminal, highlight: true },
              { id: 'swarm', label: 'Swarm Consensus (Phase 15)', icon: Users, highlight: true },
              { id: 'docs', label: 'Phase Docs (1-15)', icon: BookOpen, highlight: true },
              { id: 'evaluation', label: 'Evaluation & Benchmarks (Phase 13)', icon: Award, highlight: true },
              { id: 'orchestrator', label: 'Orchestrator (Phase 11)', icon: GitPullRequest },
              { id: 'streaming', label: 'Live Stream (Phase 12)', icon: Radio },
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
              { id: 'tests', label: 'Verification (129 Tests)', icon: ShieldCheck },
              { id: 'files', label: 'Filesystem', icon: Package },
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
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">
                Phase 14 &amp; Phase 15: UV Engine, Global CLI &amp; Swarm Consensus Active
              </span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Astral UV Full-Stack Engine, Global NexForge CLI &amp; Autonomous Multi-Agent Swarm
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              Complete migration of the entire platform to Astral UV package manager, global <code className="text-emerald-400 font-mono">nexforge</code> CLI distribution, interactive multi-phase architectural documentation, and Phase 15 multi-agent swarm collaboration with 129 verified unit tests.
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-xs text-slate-400">Runtime Status</div>
              <div className="text-lg font-bold text-emerald-400 font-mono flex items-center gap-1 justify-end">
                <CheckCircle2 className="w-4 h-4" /> 129/129 Tests Passing
              </div>
            </div>
          </div>
        </section>

        {/* Dynamic View Sections */}
        {activeView === 'uv-cli' && <UvCliDistributionStudio />}

        {activeView === 'swarm' && <SwarmCollaborationStudio />}

        {activeView === 'docs' && (
          <PhaseDocsStudio onNavigatePhase={(tab) => setActiveView(tab as any)} />
        )}

        {activeView === 'evaluation' && <EvaluationBenchmarkStudio />}

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

export default function App() {
  return (
    <SystemProvider>
      <MainApp />
    </SystemProvider>
  );
}

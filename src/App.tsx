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
import { SUBSYSTEMS, PHASE_ROADMAP, INITIAL_TEST_RESULTS } from './data/architectureData';
import { Cpu, ShieldCheck, Terminal, Layers, Milestone, CheckCircle2, Bot, Wrench, PlayCircle, Database } from 'lucide-react';

export default function App() {
  const [activeView, setActiveView] = useState<'agent' | 'storage' | 'tools' | 'llm' | 'architecture' | 'subsystems' | 'tests' | 'files' | 'roadmap'>('storage');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-emerald-500 to-indigo-600 flex items-center justify-center text-white font-black text-lg shadow-md shadow-emerald-950">
              N
            </div>
            <div>
              <div className="font-bold text-base text-white tracking-tight flex items-center gap-2">
                NexForge Droid
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                  Phase 4 Live
                </span>
              </div>
              <p className="text-xs text-slate-400">Autonomous Software Engineering Agent Platform</p>
            </div>
          </div>

          {/* Navigation Bar */}
          <nav className="flex items-center gap-1 overflow-x-auto">
            {[
              { id: 'storage', label: 'State & SQLite DB', icon: Database },
              { id: 'agent', label: 'Agent Loop Studio', icon: PlayCircle },
              { id: 'tools', label: 'Core Tools (11)', icon: Wrench },
              { id: 'llm', label: 'LLM & Gemini', icon: Bot },
              { id: 'architecture', label: 'Architecture', icon: Layers },
              { id: 'subsystems', label: 'Subsystems (10)', icon: Cpu },
              { id: 'tests', label: 'Verification (67/67)', icon: ShieldCheck },
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
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
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
        <section id="phase-banner" className="bg-gradient-to-r from-slate-900 via-slate-900 to-indigo-950 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400 font-mono">Phase 4 Status: Complete &amp; Verified</span>
            </div>
            <h1 className="text-lg sm:text-xl font-bold text-white tracking-tight">
              Droid State &amp; SQLite Persistence Engine
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl leading-relaxed">
              Production SQLite storage layer with schema DDL migrations, immutable execution timeline event logging, point-in-time state rollback checkpoints, and pause/resume lifecycle.
            </p>
          </div>

          <div className="flex items-center gap-4 shrink-0">
            <div className="text-right">
              <div className="text-xs text-slate-400">Total Unit Tests Passed</div>
              <div className="text-lg font-bold text-emerald-400 font-mono flex items-center gap-1 justify-end">
                <CheckCircle2 className="w-4 h-4" /> 100% (67/67)
              </div>
            </div>
          </div>
        </section>

        {/* Dynamic View Sections */}
        {activeView === 'storage' && (
          <StatePersistenceStudio />
        )}

        {activeView === 'agent' && (
          <AgentLoopStudio />
        )}

        {activeView === 'tools' && (
          <ToolSystemExplorer />
        )}

        {activeView === 'llm' && (
          <LLMPlayground />
        )}

        {activeView === 'architecture' && (
          <div className="space-y-8">
            <ArchitectureGraph />
            <SubsystemCard subsystems={SUBSYSTEMS} />
          </div>
        )}

        {activeView === 'subsystems' && (
          <SubsystemCard subsystems={SUBSYSTEMS} />
        )}

        {activeView === 'tests' && (
          <TestResultsViewer initialResults={INITIAL_TEST_RESULTS} />
        )}

        {activeView === 'files' && (
          <FileTreeViewer />
        )}

        {activeView === 'roadmap' && (
          <RoadmapTimeline roadmap={PHASE_ROADMAP} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-400">
        <p>NexForge Droid — Autonomous Software Engineering Platform • Phase 4 Completed &amp; Verified</p>
      </footer>
    </div>
  );
}

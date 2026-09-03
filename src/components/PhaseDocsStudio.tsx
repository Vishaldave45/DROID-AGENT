import React, { useState } from "react";
import {
  BookOpen,
  Search,
  CheckCircle2,
  Terminal,
  ExternalLink,
  Copy,
  Check,
  Code,
  Layers,
  ShieldCheck,
  Cpu,
  Zap,
} from "lucide-react";
import { PHASES_DOCUMENTATION, PhaseDoc } from "../data/phaseDocumentation";

interface PhaseDocsStudioProps {
  onNavigatePhase?: (phaseTabId: string) => void;
}

export const PhaseDocsStudio: React.FC<PhaseDocsStudioProps> = ({ onNavigatePhase }) => {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedPhaseId, setSelectedPhaseId] = useState<string>("phase-14");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  const categories = ["ALL", "Core Engine", "Agent Core", "Code Intelligence", "Code Modification", "Diagnostics", "Planning", "Orchestration", "Distribution", "Swarm Intelligence"];

  const filteredPhases = PHASES_DOCUMENTATION.filter((phase) => {
    const matchesSearch =
      phase.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phase.summary.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phase.architectureDetails.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phase.keyModules.some((m) => m.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesCategory =
      selectedCategory === "ALL" || phase.category.toLowerCase() === selectedCategory.toLowerCase();

    return matchesSearch && matchesCategory;
  });

  const activePhase =
    PHASES_DOCUMENTATION.find((p) => p.id === selectedPhaseId) || PHASES_DOCUMENTATION[0];

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(text);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-100">
                  Comprehensive Multi-Phase Architectural Documentation
                </h2>
                <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
                  15 Full Phases
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Complete engineering specifications, CLI patterns, security gates, and implementation guides alongside every phase.
              </p>
            </div>
          </div>
        </div>

        {/* Search & Category Filter */}
        <div className="flex flex-wrap items-center gap-3 mt-4 pt-4 border-t border-slate-800/80">
          <div className="relative flex-1 min-w-[240px]">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search across all 15 phases (e.g. UV, AST, Swarm, Quality Gate)..."
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex flex-wrap gap-1.5">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors ${
                  selectedCategory === cat
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Grid: Phase Selector List + Active Phase Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Phase Selector Cards */}
        <div className="lg:col-span-4 space-y-2 max-h-[720px] overflow-y-auto pr-1">
          {filteredPhases.map((phase) => {
            const isSelected = phase.id === selectedPhaseId;
            return (
              <button
                key={phase.id}
                onClick={() => setSelectedPhaseId(phase.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  isSelected
                    ? "bg-indigo-950/40 border-indigo-500/60 shadow-sm"
                    : "bg-slate-900/80 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900"
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-indigo-400">
                    Phase {phase.number}
                  </span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                      phase.status === "Next Phase"
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : phase.status === "Active"
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {phase.status}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-slate-200 truncate">
                  {phase.title}
                </h4>
                <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                  {phase.summary}
                </p>
              </button>
            );
          })}
        </div>

        {/* Right Column: Detailed Architectural Specification */}
        <div className="lg:col-span-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
            {/* Header of Active Phase */}
            <div className="border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                  Phase {activePhase.number} Specification
                </span>
                <span className="text-xs font-medium text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                  {activePhase.category}
                </span>
              </div>
              <h3 className="text-lg font-bold text-slate-100">{activePhase.title}</h3>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">
                {activePhase.summary}
              </p>
            </div>

            {/* Architecture Details Section */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                Architectural Architecture & Design Invariants
              </h4>
              <p className="text-xs text-slate-300 bg-slate-950 p-3.5 rounded-lg border border-slate-800 leading-relaxed font-sans">
                {activePhase.architectureDetails}
              </p>
            </div>

            {/* Key Python/TS Modules */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Code className="w-3.5 h-3.5 text-sky-400" />
                Key Engine Modules
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {activePhase.keyModules.map((mod, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 bg-slate-950 px-3 py-2 rounded-lg border border-slate-800 font-mono text-xs text-slate-300"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    <span className="truncate">{mod}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* CLI Execution Examples */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                Verified CLI Execution Commands
              </h4>
              <div className="space-y-2">
                {activePhase.cliExamples.map((cmd, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between bg-slate-950 px-3 py-2 rounded-lg border border-slate-800 font-mono text-xs text-emerald-400"
                  >
                    <span className="truncate mr-2">$ {cmd}</span>
                    <button
                      onClick={() => handleCopy(cmd)}
                      className="text-slate-500 hover:text-slate-300 transition-colors"
                      title="Copy command"
                    >
                      {copiedCmd === cmd ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* API Endpoints */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 text-purple-400" />
                REST / SSE API Surface
              </h4>
              <div className="flex flex-wrap gap-2">
                {activePhase.apiEndpoints.map((ep, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 bg-slate-950 border border-slate-800 rounded text-xs font-mono text-purple-300"
                  >
                    {ep}
                  </span>
                ))}
              </div>
            </div>

            {/* Verification Steps */}
            <div>
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                Phase Verification Checklist
              </h4>
              <ul className="space-y-1.5">
                {activePhase.verificationSteps.map((step, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-2 text-xs text-slate-300"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                    <span>{step}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

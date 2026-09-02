import React, { useState } from 'react';
import { ShieldCheck, Cpu, Database, Wrench, Terminal, GitBranch, CheckCircle2, RefreshCw, AlertTriangle, Eye, ArrowRight, Layers } from 'lucide-react';

export const ArchitectureGraph: React.FC = () => {
  const [activeNode, setActiveNode] = useState<string | null>(null);

  const nodes = [
    { id: 'user', label: 'User / Task', icon: Cpu, type: 'input', desc: 'Accepts natural language software-engineering objectives & repository context.' },
    { id: 'runtime', label: 'Droid Runtime', icon: Layers, type: 'core', desc: 'Central autonomous agent loop coordinating perception, planning, and action.' },
    { id: 'state', label: 'Task State Store', icon: Database, type: 'core', desc: 'PostgreSQL & in-memory state tracking plan, iterations, files read/changed, errors.' },
    { id: 'context', label: 'Context Engine', icon: Eye, type: 'intelligence', desc: 'Assembles repository summaries, AST symbols, dependencies within token budget.' },
    { id: 'planner', label: 'Planner & Reasoner', icon: RefreshCw, type: 'intelligence', desc: 'Breaks complex objectives into sequenced sub-tasks and analyzes failures.' },
    { id: 'security', label: 'Policy Gateway', icon: ShieldCheck, type: 'security', desc: 'Strict ALLOW / APPROVE / DENY policy engine preventing path escapes & unsafe actions.' },
    { id: 'tools', label: 'Tool Router & Registry', icon: Wrench, type: 'tools', desc: 'Structured dispatch for filesystem, code search (ripgrep), and git tools.' },
    { id: 'sandbox', label: 'Sandbox / Terminal', icon: Terminal, type: 'execution', desc: 'Docker/VM execution boundary with CPU, memory, and timeout limits.' },
    { id: 'tests', label: 'Test & Fix Loop', icon: CheckCircle2, type: 'execution', desc: 'Executes pytest/unittest, parses tracebacks, and drives self-correction.' },
    { id: 'eval', label: 'Evaluation Engine', icon: ShieldCheck, type: 'governance', desc: 'Objective verification of test pass rates, linting, security, and diffs.' },
  ];

  return (
    <div id="architecture-graph-container" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            NexForge Droid End-to-End Architecture
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">Interactive data flow, decision boundaries, and security perimeters</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">Phase 0 Foundation</span>
        </div>
      </div>

      {/* Grid Layout of Architectural Nodes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3.5 my-6">
        {nodes.map((node) => {
          const Icon = node.icon;
          const isSelected = activeNode === node.id;
          return (
            <div
              key={node.id}
              id={`arch-node-${node.id}`}
              onClick={() => setActiveNode(isSelected ? null : node.id)}
              className={`p-4 rounded-lg border transition-all cursor-pointer select-none flex flex-col justify-between ${
                isSelected
                  ? 'bg-slate-800/90 border-emerald-500 ring-2 ring-emerald-500/30 shadow-lg'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-800/40'
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className={`p-2 rounded-md ${
                    node.type === 'security' ? 'bg-amber-500/20 text-amber-400' :
                    node.type === 'intelligence' ? 'bg-indigo-500/20 text-indigo-400' :
                    node.type === 'execution' ? 'bg-rose-500/20 text-rose-400' :
                    node.type === 'tools' ? 'bg-cyan-500/20 text-cyan-400' :
                    'bg-emerald-500/20 text-emerald-400'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-slate-500">{node.type}</span>
                </div>
                <div className="font-medium text-sm text-slate-200">{node.label}</div>
              </div>
              <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">{node.desc}</p>
            </div>
          );
        })}
      </div>

      {/* Detailed Flow Explanation when clicked or default preview */}
      <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-emerald-400" />
          Data &amp; Control Flow Path
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300 font-mono">
          <span className="px-2 py-1 rounded bg-slate-800 text-slate-200">Requirement</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800">Context Engine</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-slate-800 text-slate-200">Planner / Reasoner</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-amber-950/60 text-amber-300 border border-amber-800">Policy Gateway</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-cyan-950/60 text-cyan-300 border border-cyan-800">Tool Router</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-rose-950/60 text-rose-300 border border-rose-800">Sandbox Exec</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800">Test / Fix Loop</span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-slate-800 text-slate-200">Evaluator &amp; Report</span>
        </div>
      </div>
    </div>
  );
};

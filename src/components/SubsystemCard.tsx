import React, { useState } from 'react';
import { SubsystemInfo } from '../types';
import { Shield, FileCode, CheckCircle, Terminal, Layers } from 'lucide-react';

interface Props {
  subsystems: SubsystemInfo[];
}

export const SubsystemCard: React.FC<Props> = ({ subsystems }) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [activeSubsystem, setActiveSubsystem] = useState<SubsystemInfo>(subsystems[0]);

  const categories = [
    { id: 'all', label: 'All Subsystems' },
    { id: 'core', label: 'Core & Agent' },
    { id: 'intelligence', label: 'Intelligence & LLM' },
    { id: 'execution', label: 'Execution & Git' },
    { id: 'governance', label: 'Security & Telemetry' },
  ];

  const filtered = selectedCategory === 'all'
    ? subsystems
    : subsystems.filter((s) => s.category === selectedCategory);

  return (
    <div id="subsystem-matrix-container" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-400" />
            Phase 0 Subsystem Contract Registry
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">Foundational modules, base protocols, and security roles implemented in Python</p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
          {categories.map((c) => (
            <button
              key={c.id}
              id={`filter-btn-${c.id}`}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
                selectedCategory === c.id
                  ? 'bg-emerald-600 text-white shadow'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 hover:bg-slate-750'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
        {/* Left Column: List */}
        <div className="lg:col-span-5 space-y-2 max-h-[460px] overflow-y-auto pr-1">
          {filtered.map((item) => {
            const isSelected = activeSubsystem.id === item.id;
            return (
              <div
                key={item.id}
                id={`subsystem-item-${item.id}`}
                onClick={() => setActiveSubsystem(item)}
                className={`p-3.5 rounded-lg border transition-all cursor-pointer flex items-center justify-between ${
                  isSelected
                    ? 'bg-slate-800 border-emerald-500 text-white shadow-md'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-850 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="text-sm font-medium">{item.name}</div>
                  <div className="text-xs text-slate-400 mt-0.5 font-mono">{item.keyFiles[0]}</div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800/60 flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" /> Phase 0
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right Column: Detailed Inspector */}
        <div className="lg:col-span-7 bg-slate-950/80 border border-slate-800 rounded-lg p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <FileCode className="w-4 h-4 text-emerald-400" />
                {activeSubsystem.name}
              </h3>
              <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {activeSubsystem.category}
              </span>
            </div>

            <p className="text-sm text-slate-300 mt-3 leading-relaxed">
              {activeSubsystem.description}
            </p>

            <div className="mt-4 space-y-3">
              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                  Key Abstract Interfaces &amp; Types
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {activeSubsystem.interfaces.map((intf) => (
                    <span key={intf} className="text-xs px-2.5 py-1 rounded bg-slate-800/90 text-emerald-300 font-mono border border-slate-700">
                      {intf}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-amber-400" />
                  Security &amp; Policy Role
                </div>
                <div className="text-xs bg-amber-950/30 border border-amber-900/50 rounded p-2.5 text-amber-200/90 leading-relaxed">
                  {activeSubsystem.securityRole}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Verified in: {activeSubsystem.keyFiles.join(', ')}</span>
            <span className="text-emerald-400 font-semibold">100% Contract Pass</span>
          </div>
        </div>
      </div>
    </div>
  );
};

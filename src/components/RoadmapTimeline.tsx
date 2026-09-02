import React from 'react';
import { PhaseRoadmapItem } from '../types';
import { Milestone, CheckCircle2, Clock, ArrowRight } from 'lucide-react';

interface Props {
  roadmap: PhaseRoadmapItem[];
}

export const RoadmapTimeline: React.FC<Props> = ({ roadmap }) => {
  return (
    <div id="roadmap-timeline-container" className="bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-100 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white tracking-tight flex items-center gap-2">
            <Milestone className="w-5 h-5 text-indigo-400" />
            NexForge Droid Multi-Phase Roadmap
          </h2>
          <p className="text-sm text-slate-400 mt-0.5">Incremental progression from Phase 0 Foundation to Phase 22 Production Fabric</p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 font-mono">
          Phase 0 Complete
        </span>
      </div>

      <div className="space-y-4">
        {roadmap.map((item) => {
          const isCompleted = item.status === 'completed';
          return (
            <div
              key={item.phase}
              id={`roadmap-phase-${item.phase}`}
              className={`p-4 rounded-xl border transition-all ${
                isCompleted
                  ? 'bg-slate-950/80 border-emerald-500/60 ring-1 ring-emerald-500/20'
                  : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <div className={`p-1.5 rounded-lg ${
                    isCompleted ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-400'
                  }`}>
                    {isCompleted ? <CheckCircle2 className="w-4 h-4" /> : <Clock className="w-4 h-4" />}
                  </div>
                  <div>
                    <span className="text-xs font-mono font-semibold uppercase text-emerald-400 mr-2">
                      Phase {item.phase}
                    </span>
                    <span className="font-semibold text-slate-100 text-sm">{item.title}</span>
                  </div>
                </div>

                <span className={`text-xs px-2.5 py-0.5 rounded-full font-mono self-start sm:self-center ${
                  isCompleted
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                }`}>
                  {isCompleted ? 'VERIFIED' : 'NEXT'}
                </span>
              </div>

              <p className="text-xs text-slate-300 mt-2.5 leading-relaxed">{item.objective}</p>

              <div className="mt-3 pt-3 border-t border-slate-800/60">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Deliverables &amp; Artifacts
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                  {item.deliverables.map((deliv, i) => (
                    <div key={i} className="text-xs text-slate-300 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500"></span>
                      {deliv}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

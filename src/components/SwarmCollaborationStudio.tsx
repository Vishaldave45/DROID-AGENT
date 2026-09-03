import React, { useState, useEffect } from "react";
import {
  Users,
  ShieldAlert,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Copy,
  Check,
  Code2,
  Sparkles,
  Layers,
  Vote,
  FileCheck,
  Scale,
} from "lucide-react";

interface SwarmRole {
  role: string;
  name: string;
  temperament: string;
  expertise: string[];
  system_prompt: string;
}

interface Contribution {
  agent_role: string;
  agent_name: string;
  round_number: number;
  thought_process: string;
  proposal: string;
  critique: string | null;
  suggested_patch: string | null;
  confidence: number;
  vote: string;
}

interface DeliberationRound {
  round_number: number;
  focus_topic: string;
  contributions: Contribution[];
  consensus_score: number;
  verdict: string;
}

interface SwarmResult {
  objective: string;
  rounds: DeliberationRound[];
  verdict: string;
  consensus_score: number;
  quorum_reached: boolean;
  final_synthesis: string;
  approved_patch: string | null;
  voting_summary: Record<string, string>;
  duration_ms: number;
}

export const SwarmCollaborationStudio: React.FC = () => {
  const [roles, setRoles] = useState<SwarmRole[]>([]);
  const [loadingRoles, setLoadingRoles] = useState<boolean>(true);
  const [objective, setObjective] = useState<string>(
    "Refactor cache eviction algorithm with TTL and LRU hybrid"
  );
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [deliberating, setDeliberating] = useState<boolean>(false);
  const [swarmResult, setSwarmResult] = useState<SwarmResult | null>(null);
  const [copiedPatch, setCopiedPatch] = useState<boolean>(false);
  const [activeRoundTab, setActiveRoundTab] = useState<number>(1);

  const presetObjectives = [
    "Refactor cache eviction algorithm with TTL and LRU hybrid",
    "Implement distributed rate limiter with sliding window counter",
    "Design zero-downtime database migration schema with rollback guards",
    "Optimize AST patcher to support asynchronous atomic transactions",
  ];

  const fetchRoles = async () => {
    setLoadingRoles(true);
    try {
      const res = await fetch("/api/swarm/roles");
      const data = await res.json();
      if (data.success) {
        setRoles(data.roles || []);
      }
    } catch (err) {
      console.error("Failed to load swarm roles:", err);
    } finally {
      setLoadingRoles(false);
    }
  };

  const runDeliberation = async (customObj?: string) => {
    setDeliberating(true);
    const targetObj = customObj || objective;
    try {
      const res = await fetch("/api/swarm/deliberate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ objective: targetObj, maxRounds }),
      });
      const data = await res.json();
      if (data.success && data.result) {
        setSwarmResult(data.result);
        if (data.result.rounds?.length > 0) {
          setActiveRoundTab(data.result.rounds[data.result.rounds.length - 1].round_number);
        }
      }
    } catch (err) {
      console.error("Failed to execute swarm deliberation:", err);
    } finally {
      setDeliberating(false);
    }
  };

  useEffect(() => {
    fetchRoles();
    runDeliberation();
  }, []);

  const handleCopyPatch = () => {
    if (swarmResult?.approved_patch) {
      navigator.clipboard.writeText(swarmResult.approved_patch);
      setCopiedPatch(true);
      setTimeout(() => setCopiedPatch(false), 2000);
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role.toLowerCase()) {
      case "architect":
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/30";
      case "coder":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "critic":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "reviewer":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "synthesizer":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getVoteBadge = (vote: string) => {
    if (vote === "APPROVE") {
      return (
        <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
          <CheckCircle2 className="w-3 h-3" /> APPROVE
        </span>
      );
    }
    if (vote === "REQUEST_CHANGES") {
      return (
        <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
          <AlertTriangle className="w-3 h-3" /> REQUEST CHANGES
        </span>
      );
    }
    return (
      <span className="text-[11px] font-semibold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800">
        {vote}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 text-indigo-400 rounded-lg">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-100">
                  Phase 15: Multi-Agent Swarm Collaboration & Autonomous Peer Review
                </h2>
                <span className="px-2 py-0.5 text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full">
                  Swarm Consensus
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                5 specialized agent personas orchestrating multi-round deliberation, adversarial critiques, and quorum voting.
              </p>
            </div>
          </div>

          <button
            onClick={() => runDeliberation()}
            disabled={deliberating}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 shadow-sm"
          >
            <RotateCw className={`w-3.5 h-3.5 ${deliberating ? "animate-spin" : ""}`} />
            {deliberating ? "Deliberating..." : "Run Swarm Deliberation"}
          </button>
        </div>

        {/* 5 Swarm Personas Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 mt-4 pt-4 border-t border-slate-800/80">
          {roles.map((role, idx) => (
            <div
              key={idx}
              className="bg-slate-950 p-3 rounded-lg border border-slate-800/80 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <span
                  className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${getRoleBadgeColor(
                    role.role
                  )}`}
                >
                  {role.role}
                </span>
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
              </div>
              <div className="text-xs font-semibold text-slate-200 truncate">
                {role.name}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                {role.temperament}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Deliberation Controls & Objective Picker */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
        <label className="block text-xs font-semibold text-slate-300">
          Swarm Engineering Objective & Invariants
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            type="text"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            placeholder="Specify high-level engineering objective..."
            className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <select
            value={maxRounds}
            onChange={(e) => setMaxRounds(Number(e.target.value))}
            className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-indigo-500"
          >
            <option value={1}>1 Round (Fast)</option>
            <option value={2}>2 Rounds (Consensus & Quorum)</option>
            <option value={3}>3 Rounds (Deep Adversarial)</option>
          </select>
        </div>

        {/* Preset chips */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {presetObjectives.map((preset, idx) => (
            <button
              key={idx}
              onClick={() => {
                setObjective(preset);
                runDeliberation(preset);
              }}
              className="text-[11px] px-2.5 py-1 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-md transition-colors truncate max-w-xs"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* Deliberation Debate & Consensus Results */}
      {swarmResult && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Deliberation Debate Stream */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Vote className="w-4 h-4 text-indigo-400" />
                    Multi-Turn Deliberation Rounds
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Structured debate, adversarial challenges, and vote casting.
                  </p>
                </div>

                {/* Round Switcher Tabs */}
                <div className="flex gap-1.5">
                  {swarmResult.rounds.map((rnd) => (
                    <button
                      key={rnd.round_number}
                      onClick={() => setActiveRoundTab(rnd.round_number)}
                      className={`px-3 py-1 text-xs font-medium rounded-lg transition-colors ${
                        activeRoundTab === rnd.round_number
                          ? "bg-indigo-600 text-white"
                          : "bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800"
                      }`}
                    >
                      Round {rnd.round_number}
                    </button>
                  ))}
                </div>
              </div>

              {/* Active Round Contributions */}
              {swarmResult.rounds
                .filter((r) => r.round_number === activeRoundTab)
                .map((round) => (
                  <div key={round.round_number} className="space-y-4">
                    <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
                      <span className="text-xs font-mono text-slate-300">
                        Focus: {round.focus_topic}
                      </span>
                      <span className="text-xs font-semibold text-indigo-400">
                        Agreement: {(round.consensus_score * 100).toFixed(0)}%
                      </span>
                    </div>

                    <div className="space-y-3">
                      {round.contributions.map((contrib, cIdx) => (
                        <div
                          key={cIdx}
                          className="bg-slate-950 p-3.5 rounded-lg border border-slate-800/90 space-y-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${getRoleBadgeColor(
                                  contrib.agent_role
                                )}`}
                              >
                                {contrib.agent_role}
                              </span>
                              <span className="text-xs font-bold text-slate-200">
                                {contrib.agent_name}
                              </span>
                            </div>
                            {getVoteBadge(contrib.vote)}
                          </div>

                          {/* Thought trace */}
                          <p className="text-[11px] text-slate-400 italic">
                            "{contrib.thought_process}"
                          </p>

                          {/* Proposal */}
                          <div className="text-xs text-slate-200 bg-slate-900/80 p-2.5 rounded border border-slate-800">
                            {contrib.proposal}
                          </div>

                          {/* Critique if present */}
                          {contrib.critique && (
                            <div className="text-xs text-amber-300 bg-amber-950/30 p-2.5 rounded border border-amber-800/40 flex items-start gap-2">
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                              <span>{contrib.critique}</span>
                            </div>
                          )}

                          {/* Suggested patch if present */}
                          {contrib.suggested_patch && (
                            <pre className="text-[11px] font-mono text-emerald-300 bg-slate-900 p-2 rounded border border-slate-800 overflow-x-auto whitespace-pre-wrap">
                              {contrib.suggested_patch}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
            </div>
          </div>

          {/* Right Column: Quorum Verdict & Certified Patch */}
          <div className="lg:col-span-5 space-y-4">
            {/* Verdict Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Scale className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-slate-200">
                    Swarm Quorum Verdict
                  </h3>
                </div>
                <span className="px-2.5 py-1 text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {swarmResult.verdict}
                </span>
              </div>

              <div>
                <div className="text-xs text-slate-400 font-medium">Consensus Agreement</div>
                <div className="text-2xl font-extrabold text-emerald-400 mt-1">
                  {(swarmResult.consensus_score * 100).toFixed(0)}%
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-1.5">
                  <div
                    className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${swarmResult.consensus_score * 100}%` }}
                  />
                </div>
              </div>

              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs text-slate-300 leading-relaxed">
                {swarmResult.final_synthesis}
              </div>

              {/* Voting Summary Tally */}
              <div>
                <div className="text-xs font-semibold text-slate-400 mb-2">
                  Final Vote Breakdown
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(swarmResult.voting_summary).map(([agent, vote]) => (
                    <div
                      key={agent}
                      className="bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between"
                    >
                      <span className="text-xs text-slate-300 truncate">{agent}</span>
                      <span className="text-[10px] font-bold text-emerald-400">{vote}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Certified Consensus Patch */}
            {swarmResult.approved_patch && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-xs font-semibold text-slate-200">
                      Certified Swarm Consensus Patch
                    </h3>
                  </div>
                  <button
                    onClick={handleCopyPatch}
                    className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 px-2.5 py-1 rounded transition-colors"
                  >
                    {copiedPatch ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                    Copy Patch
                  </button>
                </div>

                <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-xs text-emerald-300 overflow-x-auto leading-relaxed max-h-60">
                  {swarmResult.approved_patch}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

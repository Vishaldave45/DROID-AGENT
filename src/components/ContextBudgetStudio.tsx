import React, { useState, useMemo } from 'react';
import {
  Sliders,
  Sparkles,
  Layers,
  FileCode,
  Network,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  Scissors,
  BarChart3,
  Gauge,
  HelpCircle,
  Terminal,
} from 'lucide-react';

interface TierAllocation {
  id: string;
  name: string;
  tokens: number;
  max: number;
  description: string;
  color: string;
  bgLight: string;
}

interface SimulatedSymbolScore {
  name: string;
  type: string;
  file: string;
  score: number;
  hops: number;
  breakdown: {
    nameMatch: number;
    graphProximity: number;
    pathMatch: number;
    docSigMatch: number;
    recency: number;
  };
}

const SAMPLE_SYMBOLS: SimulatedSymbolScore[] = [
  {
    name: 'process_payment_transaction',
    type: 'FUNCTION',
    file: 'app/payment/processor.py',
    score: 0.94,
    hops: 0,
    breakdown: { nameMatch: 1.0, graphProximity: 1.0, pathMatch: 0.8, docSigMatch: 0.9, recency: 1.0 },
  },
  {
    name: 'PaymentGatewayClient',
    type: 'CLASS',
    file: 'app/payment/client.py',
    score: 0.82,
    hops: 1,
    breakdown: { nameMatch: 0.8, graphProximity: 0.8, pathMatch: 0.8, docSigMatch: 0.7, recency: 0.8 },
  },
  {
    name: 'test_payment_zero_amount_exception',
    type: 'TEST',
    file: 'tests/test_payment.py',
    score: 0.76,
    hops: 1,
    breakdown: { nameMatch: 0.7, graphProximity: 0.8, pathMatch: 0.5, docSigMatch: 0.8, recency: 0.0 },
  },
  {
    name: 'format_currency_string',
    type: 'FUNCTION',
    file: 'app/utils/formatting.py',
    score: 0.42,
    hops: 2,
    breakdown: { nameMatch: 0.3, graphProximity: 0.6, pathMatch: 0.2, docSigMatch: 0.4, recency: 0.0 },
  },
  {
    name: 'DatabaseConnectionPool',
    type: 'CLASS',
    file: 'app/storage/pool.py',
    score: 0.28,
    hops: 3,
    breakdown: { nameMatch: 0.0, graphProximity: 0.3, pathMatch: 0.1, docSigMatch: 0.2, recency: 0.7 },
  },
];

const RAW_CODE_SAMPLE = `"""Payment transaction processing module."""

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, Optional

from app.storage.base import TaskState
from app.payment.client import PaymentGatewayClient
from app.observability.logger import get_logger

logger = get_logger("nexforge.payment")

# ... lines 15 to 45 (internal configuration and connection initialization) ...

class TransactionValidator:
    """Validates raw customer balance and credit tokens."""
    def __init__(self, currency: str = "USD") -> None:
        self.currency = currency

    def validate_amount(self, amount: float) -> bool:
        if amount <= 0:
            raise ValueError(f"Invalid payment amount: {amount}")
        return True

# ... lines 58 to 110 (legacy payment gateway adapters) ...

async def process_payment_transaction(
    order_id: str,
    amount: float,
    currency: str = "USD",
    client: Optional[PaymentGatewayClient] = None,
) -> Dict[str, Any]:
    """Processes customer payment transaction with idempotent key locking."""
    validator = TransactionValidator(currency=currency)
    validator.validate_amount(amount)
    
    logger.info(f"Initiating payment of {amount} {currency} for order {order_id}")
    gateway = client or PaymentGatewayClient()
    
    try:
        response = await gateway.charge(order_id=order_id, amount=amount)
        return {"status": "SUCCESS", "tx_id": response.transaction_id, "amount": amount}
    except Exception as exc:
        logger.error(f"Payment gateway failure: {str(exc)}")
        raise RuntimeError(f"Transaction failed: {str(exc)}") from exc

# ... lines 135 to 220 (batch transaction settlement routines) ...
`;

export function ContextBudgetStudio() {
  const [modelPreset, setModelPreset] = useState<'gemini-2.0-flash' | 'gpt-4o' | 'claude-3.5-sonnet'>('gemini-2.0-flash');
  const [taskQuery, setTaskQuery] = useState('Fix zero amount validation in process_payment_transaction');
  const [maxTotalBudget, setMaxTotalBudget] = useState(32000);

  // Sub-tier token allocations
  const [systemBudget, setSystemBudget] = useState(2000);
  const [taskBudget, setTaskBudget] = useState(1000);
  const [repoSummaryBudget, setRepoSummaryBudget] = useState(2500);
  const [symbolsBudget, setSymbolsBudget] = useState(7000);
  const [fileSlicesBudget, setFileSlicesBudget] = useState(12000);
  const [historyBudget, setHistoryBudget] = useState(4500);
  const [outputReserveBudget, setOutputReserveBudget] = useState(3000);

  const [copiedPayload, setCopiedPayload] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<SimulatedSymbolScore | null>(SAMPLE_SYMBOLS[0]);
  const [foldPreviewMode, setFoldPreviewMode] = useState<'sliced' | 'full'>('sliced');

  const totalAllocated =
    systemBudget + taskBudget + repoSummaryBudget + symbolsBudget + fileSlicesBudget + historyBudget + outputReserveBudget;

  const isOverBudget = totalAllocated > maxTotalBudget;
  const remainingBudget = maxTotalBudget - totalAllocated;

  const tierAllocations: TierAllocation[] = [
    { id: 'system', name: 'System Prompt', tokens: systemBudget, max: 5000, description: 'Safety rules, tool schemas, coding directives', color: '#6366f1', bgLight: 'bg-indigo-500/10' },
    { id: 'task', name: 'Task & Goal', tokens: taskBudget, max: 3000, description: 'Engineering requirement, acceptance criteria', color: '#38bdf8', bgLight: 'bg-sky-500/10' },
    { id: 'repo', name: 'Repo Skeleton', tokens: repoSummaryBudget, max: 6000, description: 'Tech stack, language metrics, manifest deps', color: '#10b981', bgLight: 'bg-emerald-500/10' },
    { id: 'symbols', name: 'Graph AST Symbols', tokens: symbolsBudget, max: 15000, description: 'Matched classes, methods, and call hierarchy', color: '#f59e0b', bgLight: 'bg-amber-500/10' },
    { id: 'slices', name: 'Target File Slices', tokens: fileSlicesBudget, max: 24000, description: 'Focal code windows with semantic line folding', color: '#ec4899', bgLight: 'bg-pink-500/10' },
    { id: 'history', name: 'Tool & Msg History', tokens: historyBudget, max: 10000, description: 'Recent turns, tool inputs, and error telemetry', color: '#8b5cf6', bgLight: 'bg-purple-500/10' },
    { id: 'reserve', name: 'Output Reserve', tokens: outputReserveBudget, max: 8000, description: 'Reserved token margin for model code generation', color: '#06b6d4', bgLight: 'bg-cyan-500/10' },
  ];

  const handleCopy = () => {
    const payload = JSON.stringify(
      {
        task_id: 'task-live-demo',
        model_preset: modelPreset,
        budget: {
          max_total: maxTotalBudget,
          total_allocated: totalAllocated,
          tiers: {
            system: systemBudget,
            task: taskBudget,
            repo_summary: repoSummaryBudget,
            symbols: symbolsBudget,
            file_slices: fileSlicesBudget,
            history: historyBudget,
            reserve: outputReserveBudget,
          },
        },
        ranked_symbols: SAMPLE_SYMBOLS.filter((s) => s.score > 0.3),
        file_slices: {
          'app/payment/processor.py': '... [Folded 35 lines] ...\nasync def process_payment_transaction(...)',
        },
      },
      null,
      2
    );
    navigator.clipboard.writeText(payload);
    setCopiedPayload(true);
    setTimeout(() => setCopiedPayload(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header & Preset Switcher */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400 font-mono">
              Phase 7: Context Engine &amp; Token Budget Governor
            </span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight">
            Multi-Tier Token Allocator &amp; Relevance Scorer
          </h2>
          <p className="text-xs text-slate-400 max-w-2xl">
            Strictly bounds prompt payload dimensions across architectural tiers, preventing context flooding and hallucination while assembling surgical AST slices.
          </p>
        </div>

        {/* Model Calibration Selector */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="bg-slate-950 border border-slate-800 rounded-lg p-1 flex items-center gap-1">
            {[
              { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash (3.8 ch/t)' },
              { id: 'gpt-4o', label: 'GPT-4o (3.7 ch/t)' },
              { id: 'claude-3.5-sonnet', label: 'Claude 3.5 Sonnet (3.6 ch/t)' },
            ].map((m) => (
              <button
                key={m.id}
                onClick={() => setModelPreset(m.id as any)}
                className={`px-2.5 py-1 text-xs rounded font-medium transition-all ${
                  modelPreset === m.id
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-mono font-medium border border-slate-700 transition"
          >
            {copiedPayload ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copiedPayload ? 'Copied' : 'Export Package JSON'}
          </button>
        </div>
      </div>

      {/* Budget Summary Meter */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Gauge className="w-4 h-4 text-amber-400" />
            <span className="text-sm font-bold text-white">Total Context Window Governor</span>
            <span className="text-xs text-slate-400 font-mono">
              ({totalAllocated.toLocaleString()} / {maxTotalBudget.toLocaleString()} tokens)
            </span>
          </div>

          <div className="flex items-center gap-3">
            <span
              className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-bold ${
                isOverBudget
                  ? 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
              }`}
            >
              {isOverBudget ? `OVER BUDGET by ${(totalAllocated - maxTotalBudget).toLocaleString()} tokens` : `Headroom: ${remainingBudget.toLocaleString()} tokens`}
            </span>

            <select
              value={maxTotalBudget}
              onChange={(e) => setMaxTotalBudget(Number(e.target.value))}
              className="bg-slate-950 text-slate-200 border border-slate-800 rounded px-2 py-1 text-xs font-mono focus:outline-none focus:border-amber-500"
            >
              <option value={16000}>16k Window</option>
              <option value={32000}>32k Standard Window</option>
              <option value={64000}>64k Extended Window</option>
              <option value={128000}>128k Deep Context</option>
            </select>
          </div>
        </div>

        {/* Multi-tier Stacked Progress Bar */}
        <div className="space-y-1.5">
          <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden flex">
            {tierAllocations.map((tier) => {
              const widthPct = Math.min(100, (tier.tokens / maxTotalBudget) * 100);
              return (
                <div
                  key={tier.id}
                  style={{ width: `${widthPct}%`, backgroundColor: tier.color }}
                  className="h-full transition-all duration-300 relative group cursor-pointer"
                  title={`${tier.name}: ${tier.tokens.toLocaleString()} tokens (${widthPct.toFixed(1)}%)`}
                />
              );
            })}
          </div>

          {/* Legend */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs pt-1">
            {tierAllocations.map((tier) => (
              <div key={tier.id} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: tier.color }}></span>
                <span className="text-slate-300 font-medium">{tier.name}:</span>
                <span className="text-slate-400 font-mono text-[11px]">{tier.tokens.toLocaleString()}t</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main Studio Grid: Tier Sliders (Left) vs Relevance & Truncation Previews (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Interactive Tier Allocators */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sliders className="w-4 h-4 text-amber-400" />
                Tier Allocation Limits
              </h3>
              <button
                onClick={() => {
                  setSystemBudget(2000);
                  setTaskBudget(1000);
                  setRepoSummaryBudget(2500);
                  setSymbolsBudget(7000);
                  setFileSlicesBudget(12000);
                  setHistoryBudget(4500);
                  setOutputReserveBudget(3000);
                }}
                className="text-xs text-amber-400 hover:text-amber-300 font-mono flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Reset Defaults
              </button>
            </div>

            <div className="space-y-3.5">
              {/* System Prompt Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-indigo-400">1. System Prompt &amp; Tool Schemas</span>
                  <span className="font-mono text-slate-300">{systemBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={500}
                  max={5000}
                  step={250}
                  value={systemBudget}
                  onChange={(e) => setSystemBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                />
                <p className="text-[11px] text-slate-500">Includes core directives, security boundaries, and tool parameter JSON schemas.</p>
              </div>

              {/* Task Requirement Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-sky-400">2. Task Objective &amp; Goal Criteria</span>
                  <span className="font-mono text-slate-300">{taskBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={250}
                  max={3000}
                  step={100}
                  value={taskBudget}
                  onChange={(e) => setTaskBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-sky-500"
                />
                <p className="text-[11px] text-slate-500">User prompt text, explicit acceptance checks, and verification assertions.</p>
              </div>

              {/* Repo Summary Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-emerald-400">3. Repository Structure &amp; Manifests</span>
                  <span className="font-mono text-slate-300">{repoSummaryBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={500}
                  max={6000}
                  step={250}
                  value={repoSummaryBudget}
                  onChange={(e) => setRepoSummaryBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                />
                <p className="text-[11px] text-slate-500">Directory maps, detected tech stacks, package manifests (package.json, requirements.txt).</p>
              </div>

              {/* Graph Symbols AST Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-amber-400">4. Engineering Graph AST Symbols</span>
                  <span className="font-mono text-slate-300">{symbolsBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={1000}
                  max={15000}
                  step={500}
                  value={symbolsBudget}
                  onChange={(e) => setSymbolsBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
                />
                <p className="text-[11px] text-slate-500">Target class definitions, function signatures, docstrings, and call hierarchy relations.</p>
              </div>

              {/* File Slices Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-pink-400">5. Target File Slices &amp; Windows</span>
                  <span className="font-mono text-slate-300">{fileSlicesBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={2000}
                  max={24000}
                  step={1000}
                  value={fileSlicesBudget}
                  onChange={(e) => setFileSlicesBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-pink-500"
                />
                <p className="text-[11px] text-slate-500">Source file lines surrounding focal symbols with folded breadcrumb markers.</p>
              </div>

              {/* Tool History Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-purple-400">6. Conversation &amp; Tool History</span>
                  <span className="font-mono text-slate-300">{historyBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={1000}
                  max={10000}
                  step={500}
                  value={historyBudget}
                  onChange={(e) => setHistoryBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
                <p className="text-[11px] text-slate-500">Recent multi-turn messages, tool calls, and captured terminal stderr outputs.</p>
              </div>

              {/* Output Reserve Slider */}
              <div className="space-y-1.5 p-2.5 bg-slate-950/60 rounded-lg border border-slate-800/80">
                <div className="flex justify-between text-xs">
                  <span className="font-semibold text-cyan-400">7. LLM Output Generation Reserve</span>
                  <span className="font-mono text-slate-300">{outputReserveBudget.toLocaleString()} tokens</span>
                </div>
                <input
                  type="range"
                  min={1000}
                  max={8000}
                  step={500}
                  value={outputReserveBudget}
                  onChange={(e) => setOutputReserveBudget(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
                <p className="text-[11px] text-slate-500">Guaranteed headroom for complete code patches and final tool responses.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Multi-Signal Relevance & Code Chunk Folding */}
        <div className="lg:col-span-7 space-y-6">
          {/* Interactive Relevance Scorer Simulator */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-400" />
                Multi-Signal Relevance Scorer
              </h3>
              <span className="text-xs text-slate-400 font-mono">Weighted Multi-Factor Formula</span>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300">Test Query / Task Requirement:</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={taskQuery}
                  onChange={(e) => setTaskQuery(e.target.value)}
                  className="flex-1 bg-slate-950 text-xs text-slate-200 border border-slate-800 rounded-lg px-3 py-2 font-mono focus:outline-none focus:border-amber-500"
                />
              </div>
            </div>

            {/* Symbols Table */}
            <div className="border border-slate-800 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-950 text-slate-400 border-b border-slate-800 font-mono">
                    <th className="p-2.5">Symbol Name</th>
                    <th className="p-2.5">Type</th>
                    <th className="p-2.5">Distance</th>
                    <th className="p-2.5 text-right">Composite Score</th>
                    <th className="p-2.5 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {SAMPLE_SYMBOLS.map((sym) => {
                    const isSelected = selectedSymbol?.name === sym.name;
                    const isPacked = sym.score >= 0.5;
                    return (
                      <tr
                        key={sym.name}
                        onClick={() => setSelectedSymbol(sym)}
                        className={`cursor-pointer transition ${
                          isSelected ? 'bg-amber-500/10' : 'hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="p-2.5 font-bold text-slate-200">
                          {sym.name}
                          <div className="text-[10px] text-slate-500 font-normal">{sym.file}</div>
                        </td>
                        <td className="p-2.5">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300">
                            {sym.type}
                          </span>
                        </td>
                        <td className="p-2.5 text-slate-400">
                          {sym.hops === 0 ? 'Focal (0-hop)' : `${sym.hops}-hop relation`}
                        </td>
                        <td className="p-2.5 text-right font-bold text-amber-400">
                          {(sym.score * 100).toFixed(0)}%
                        </td>
                        <td className="p-2.5 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              isPacked
                                ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {isPacked ? 'PACKED' : 'PRUNED'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Factor breakdown card */}
            {selectedSymbol && (
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2 text-xs">
                <div className="flex justify-between items-center text-slate-300 font-mono">
                  <span>Score Breakdown: <strong className="text-white">{selectedSymbol.name}</strong></span>
                  <span className="text-amber-400 font-bold">{(selectedSymbol.score * 100).toFixed(1)}%</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-[11px] font-mono">
                  <div className="p-1.5 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-slate-500">Name Match (35%)</div>
                    <div className="font-bold text-slate-200">{(selectedSymbol.breakdown.nameMatch * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-1.5 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-slate-500">Graph Prox (25%)</div>
                    <div className="font-bold text-slate-200">{(selectedSymbol.breakdown.graphProximity * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-1.5 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-slate-500">Path Match (15%)</div>
                    <div className="font-bold text-slate-200">{(selectedSymbol.breakdown.pathMatch * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-1.5 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-slate-500">Doc &amp; Sig (10%)</div>
                    <div className="font-bold text-slate-200">{(selectedSymbol.breakdown.docSigMatch * 100).toFixed(0)}%</div>
                  </div>
                  <div className="p-1.5 bg-slate-900 rounded border border-slate-800 text-center">
                    <div className="text-slate-500">Recency (10%)</div>
                    <div className="font-bold text-slate-200">{(selectedSymbol.breakdown.recency * 100).toFixed(0)}%</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Code Chunk Truncator & Folding Viewer */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Scissors className="w-4 h-4 text-pink-400" />
                <h3 className="text-sm font-bold text-white">Semantic Code Chunk Truncator</h3>
              </div>
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
                <button
                  onClick={() => setFoldPreviewMode('sliced')}
                  className={`px-2 py-0.5 text-xs rounded font-mono ${
                    foldPreviewMode === 'sliced'
                      ? 'bg-pink-500/20 text-pink-300 font-bold border border-pink-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Budget-Folded (18 lines, ~140t)
                </button>
                <button
                  onClick={() => setFoldPreviewMode('full')}
                  className={`px-2 py-0.5 text-xs rounded font-mono ${
                    foldPreviewMode === 'full'
                      ? 'bg-pink-500/20 text-pink-300 font-bold border border-pink-500/40'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Raw File (220 lines, ~1,850t)
                </button>
              </div>
            </div>

            <div className="relative">
              <pre className="p-4 bg-slate-950 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto max-h-72 border border-slate-800 leading-relaxed">
                {RAW_CODE_SAMPLE}
              </pre>
            </div>
            <p className="text-xs text-slate-400">
              Preserves essential imports at file top and target symbol lines, folding out irrelevant blocks into compact semantic breadcrumbs.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

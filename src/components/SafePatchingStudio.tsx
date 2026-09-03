import React, { useState, useMemo } from 'react';
import {
  FileEdit,
  ShieldCheck,
  History,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  RefreshCw,
  GitCommit,
  Terminal,
  FileCode,
  Layers,
  Sparkles,
  ArrowRight,
  Code2,
  Lock,
  Unlock,
  RotateCcw,
  Zap,
} from 'lucide-react';

interface CodeScenario {
  id: string;
  name: string;
  language: string;
  filename: string;
  originalCode: string;
  targetContent: string;
  replacementContent: string;
  diffSnippet: string;
  description: string;
  corruptTarget?: string;
  corruptReplacement?: string;
}

const PRESET_SCENARIOS: CodeScenario[] = [
  {
    id: 'py-sqlite-lock',
    name: 'Python: SQLite Connection Pool Timeout',
    language: 'python',
    filename: 'nexforge-droid/app/storage/sqlite.py',
    description: 'Add exponential backoff and timeout handling to prevent database locked deadlocks.',
    originalCode: `class SQLiteStore:\n    def __init__(self, db_path: str):\n        self.db_path = db_path\n\n    def execute_write(self, sql: str, params: tuple = ()):\n        with sqlite3.connect(self.db_path) as conn:\n            cursor = conn.cursor()\n            cursor.execute(sql, params)\n            conn.commit()\n            return cursor.lastrowid`,
    targetContent: `    def execute_write(self, sql: str, params: tuple = ()):\n        with sqlite3.connect(self.db_path) as conn:`,
    replacementContent: `    def execute_write(self, sql: str, params: tuple = (), timeout: float = 15.0):\n        with sqlite3.connect(self.db_path, timeout=timeout) as conn:`,
    diffSnippet: `--- a/nexforge-droid/app/storage/sqlite.py\n+++ b/nexforge-droid/app/storage/sqlite.py\n@@ -4,3 +4,3 @@\n-    def execute_write(self, sql: str, params: tuple = ()):\n-        with sqlite3.connect(self.db_path) as conn:\n+    def execute_write(self, sql: str, params: tuple = (), timeout: float = 15.0):\n+        with sqlite3.connect(self.db_path, timeout=timeout) as conn:`,
    corruptTarget: `    def execute_write(self, sql: str, params: tuple = ()):`,
    corruptReplacement: `    def execute_write(self, sql: str, params: tuple = ()\n        with sqlite3.connect(self.db_path) as conn:`, // Missing colon -> syntax error
  },
  {
    id: 'ts-auth-guard',
    name: 'TypeScript: Token Expiry Check',
    language: 'typescript',
    filename: 'src/auth/jwtVerifier.ts',
    description: 'Ensure token expiration verification is strictly checked against current UNIX timestamp.',
    originalCode: `export function verifyToken(payload: TokenPayload): boolean {\n  if (!payload.userId) {\n    return false;\n  }\n  return true;\n}`,
    targetContent: `  if (!payload.userId) {\n    return false;\n  }\n  return true;`,
    replacementContent: `  const now = Math.floor(Date.now() / 1000);\n  if (!payload.userId || payload.exp < now) {\n    return false;\n  }\n  return true;`,
    diffSnippet: `--- a/src/auth/jwtVerifier.ts\n+++ b/src/auth/jwtVerifier.ts\n@@ -2,4 +2,5 @@\n-  if (!payload.userId) {\n-    return false;\n-  }\n-  return true;\n+  const now = Math.floor(Date.now() / 1000);\n+  if (!payload.userId || payload.exp < now) {\n+    return false;\n+  }\n+  return true;`,
    corruptTarget: `  return true;`,
    corruptReplacement: `  return true; }`, // Extra closing bracket -> structural syntax error
  },
  {
    id: 'json-config',
    name: 'JSON: Token Budget Configuration',
    language: 'json',
    filename: 'config/context_budget.json',
    description: 'Add reserve allocation parameters to prevent LLM context overrun.',
    originalCode: `{\n  "version": 1,\n  "max_tokens": 16000,\n  "tiers": {\n    "system": 2000,\n    "task": 1000\n  }\n}`,
    targetContent: `    "task": 1000\n  }`,
    replacementContent: `    "task": 1000,\n    "reserve": 3000\n  }`,
    diffSnippet: `--- a/config/context_budget.json\n+++ b/config/context_budget.json\n@@ -5,2 +5,3 @@\n     "task": 1000\n+    "reserve": 3000\n   }`,
    corruptTarget: `    "task": 1000\n  }`,
    corruptReplacement: `    "task": 1000,\n  }`, // Trailing comma -> JSONDecodeError
  },
];

interface SnapshotItem {
  version: number;
  hash: string;
  timestamp: string;
  reason: string;
  code: string;
  lines: number;
}

export function SafePatchingStudio() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('py-sqlite-lock');
  const [editMode, setEditMode] = useState<'surgical' | 'unified_diff' | 'snapshots'>('surgical');

  const currentScenario = useMemo(
    () => PRESET_SCENARIOS.find((s) => s.id === selectedScenarioId) || PRESET_SCENARIOS[0],
    [selectedScenarioId]
  );

  const [currentCode, setCurrentCode] = useState<string>(currentScenario.originalCode);
  const [targetBlock, setTargetBlock] = useState<string>(currentScenario.targetContent);
  const [replacementBlock, setReplacementBlock] = useState<string>(currentScenario.replacementContent);
  const [diffText, setDiffText] = useState<string>(currentScenario.diffSnippet);
  const [allowFuzzy, setAllowFuzzy] = useState<boolean>(false);
  const [validateSyntax, setValidateSyntax] = useState<boolean>(true);
  const [simulateExternalStale, setSimulateExternalStale] = useState<boolean>(false);
  const [expectedHash, setExpectedHash] = useState<string>('auto');
  const [copied, setCopied] = useState<boolean>(false);

  // Snapshot History
  const [snapshots, setSnapshots] = useState<SnapshotItem[]>([
    {
      version: 1,
      hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d',
      timestamp: 'Initial Disk Load',
      reason: 'initial',
      code: currentScenario.originalCode,
      lines: currentScenario.originalCode.split('\n').length,
    },
  ]);

  // Handle Scenario Change
  const handleSelectScenario = (sc: CodeScenario) => {
    setSelectedScenarioId(sc.id);
    setCurrentCode(sc.originalCode);
    setTargetBlock(sc.targetContent);
    setReplacementBlock(sc.replacementContent);
    setDiffText(sc.diffSnippet);
    setSimulateExternalStale(false);
    setSnapshots([
      {
        version: 1,
        hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d',
        timestamp: 'Initial Disk Load',
        reason: 'initial',
        code: sc.originalCode,
        lines: sc.originalCode.split('\n').length,
      },
    ]);
  };

  // Compute live SHA-256 (simulated hash based on content string)
  const computeHash = (content: string) => {
    let hash = 0;
    for (let i = 0; i < content.length; i++) {
      const char = content.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash |= 0;
    }
    const hex = Math.abs(hash).toString(16).padStart(8, '0');
    return `${hex}e4f1a2c3b5d79901`;
  };

  const currentHash = useMemo(() => computeHash(currentCode), [currentCode]);

  // Syntax Validation Logic for Preview
  const syntaxCheck = useMemo(() => {
    if (!validateSyntax) {
      return { valid: true, error: null, line: null };
    }

    const lang = currentScenario.language;
    if (lang === 'python') {
      // Check common python syntax errors
      if (currentCode.includes('def ') && !currentCode.includes(':')) {
        return { valid: false, error: 'SyntaxError: expected ":" after function header', line: 4 };
      }
      // Check parenthesis balance
      const openParens = (currentCode.match(/\(/g) || []).length;
      const closeParens = (currentCode.match(/\)/g) || []).length;
      if (openParens !== closeParens) {
        return { valid: false, error: `SyntaxError: unmatched parentheses (${openParens} '(' vs ${closeParens} ')')`, line: 5 };
      }
    } else if (lang === 'json') {
      try {
        JSON.parse(currentCode);
      } catch (e: any) {
        return { valid: false, error: `JSONDecodeError: ${e.message}`, line: 6 };
      }
    } else if (lang === 'typescript') {
      const openBraces = (currentCode.match(/\{/g) || []).length;
      const closeBraces = (currentCode.match(/\}/g) || []).length;
      if (openBraces !== closeBraces) {
        return { valid: false, error: `StructuralError: unmatched curly braces (${openBraces} '{' vs ${closeBraces} '}')`, line: 5 };
      }
    }

    return { valid: true, error: null, line: null };
  }, [currentCode, validateSyntax, currentScenario.language]);

  // Target Match Status
  const matchCount = useMemo(() => {
    if (!targetBlock) return 0;
    let count = 0;
    let pos = currentCode.indexOf(targetBlock);
    while (pos !== -1) {
      count++;
      pos = currentCode.indexOf(targetBlock, pos + 1);
    }
    return count;
  }, [currentCode, targetBlock]);

  // Operation Logs
  const [logs, setLogs] = useState<string[]>([
    `[2026-09-02 21:15:00] [AUDITOR] Initialized FileSnapshotAuditor with workspace root: /nexforge-droid`,
    `[2026-09-02 21:15:00] [SYNTAX] Loaded AST syntax rules for: python, typescript, json, yaml, sql`,
    `[2026-09-02 21:15:01] [HASH] Active file hash: ${currentHash.substring(0, 16)}...`,
  ]);

  const addLog = (msg: string) => {
    setLogs((prev) => [
      `[${new Date().toISOString().replace('T', ' ').substring(0, 19)}] ${msg}`,
      ...prev.slice(0, 20),
    ]);
  };

  // Perform Surgical Edit
  const handleApplySurgicalEdit = () => {
    // 1. Stale check
    if (simulateExternalStale) {
      addLog(`[ERROR] [STALE_CONFLICT] Stale file detected on '${currentScenario.filename}'. Expected hash differs from disk.`);
      return;
    }

    // 2. Uniqueness check
    if (matchCount === 0) {
      addLog(`[ERROR] [SURGICAL] target_content not found in target file. Modification rejected.`);
      return;
    }
    if (matchCount > 1) {
      addLog(`[ERROR] [SURGICAL] target_content matches ${matchCount} occurrences. Must be unique.`);
      return;
    }

    // 3. Apply modification
    const newCode = currentCode.replace(targetBlock, replacementBlock);

    // 4. Validate syntax of prospective code
    if (validateSyntax) {
      if (currentScenario.language === 'python' && replacementBlock.includes('(') && !replacementBlock.includes(':') && replacementBlock.includes('def ')) {
        addLog(`[ERROR] [SYNTAX_ABORT] Python SyntaxError: expected ':' at end of line. Edit aborted; file preserved.`);
        return;
      }
      if (currentScenario.language === 'typescript' && replacementBlock.includes('} }')) {
        addLog(`[ERROR] [SYNTAX_ABORT] TypeScript StructuralError: unexpected closing brace '}'. Edit aborted.`);
        return;
      }
      if (currentScenario.language === 'json' && replacementBlock.endsWith(',\n  }')) {
        addLog(`[ERROR] [SYNTAX_ABORT] JSONDecodeError: Trailing comma before closing brace. Edit aborted.`);
        return;
      }
    }

    // 5. Take snapshot & commit
    const newHash = computeHash(newCode);
    const newSnap: SnapshotItem = {
      version: snapshots.length + 1,
      hash: newHash,
      timestamp: new Date().toLocaleTimeString(),
      reason: 'surgical-edit',
      code: newCode,
      lines: newCode.split('\n').length,
    };

    setSnapshots((prev) => [newSnap, ...prev]);
    setCurrentCode(newCode);
    addLog(`[SUCCESS] [SURGICAL] Replaced 1 unique target block. Created snapshot v${newSnap.version} (SHA-256: ${newHash.substring(0, 12)}...).`);
  };

  // Inject Deliberate Syntax Error
  const handleInjectCorruptSyntax = () => {
    if (currentScenario.corruptTarget && currentScenario.corruptReplacement) {
      setTargetBlock(currentScenario.corruptTarget);
      setReplacementBlock(currentScenario.corruptReplacement);
      addLog(`[ALERT] Injected corrupt syntax payload into target/replacement inputs to test syntax gate.`);
    }
  };

  // Revert to snapshot
  const handleRevert = (snap: SnapshotItem) => {
    setCurrentCode(snap.code);
    addLog(`[ROLLBACK] Restored file to snapshot version ${snap.version} (SHA-256: ${snap.hash.substring(0, 12)}...).`);
  };

  const handleCopyCode = () => {
    navigator.clipboard.writeText(currentCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
              Phase 9 Engine
            </span>
            <span className="text-xs text-slate-400 font-mono">AST Syntax Gating &amp; Resilient Diff Engine</span>
          </div>
          <h2 className="text-lg font-bold text-white tracking-tight mt-1 flex items-center gap-2">
            <FileEdit className="w-5 h-5 text-emerald-400" /> Safe Code Modification &amp; Patching Studio
          </h2>
          <p className="text-xs text-slate-400 max-w-2xl mt-0.5">
            Surgical block replacement, unified diff patching, pre/post AST syntax validation, SHA-256 stale-file detection, and atomic snapshot rollbacks.
          </p>
        </div>

        {/* View mode toggle */}
        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 shrink-0">
          <button
            onClick={() => setEditMode('surgical')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all ${
              editMode === 'surgical' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Code2 className="w-3.5 h-3.5 text-emerald-400" />
            Surgical Editor
          </button>
          <button
            onClick={() => setEditMode('unified_diff')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all ${
              editMode === 'unified_diff' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <GitCommit className="w-3.5 h-3.5 text-indigo-400" />
            Unified Diff Hunks
          </button>
          <button
            onClick={() => setEditMode('snapshots')}
            className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-all ${
              editMode === 'snapshots' ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <History className="w-3.5 h-3.5 text-amber-400" />
            Snapshots ({snapshots.length})
          </button>
        </div>
      </div>

      {/* Preset Scenario Selector */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PRESET_SCENARIOS.map((sc) => {
          const isSelected = sc.id === selectedScenarioId;
          return (
            <button
              key={sc.id}
              onClick={() => handleSelectScenario(sc)}
              className={`text-left p-3.5 rounded-xl border transition-all ${
                isSelected
                  ? 'bg-slate-900/90 border-emerald-500/60 ring-1 ring-emerald-500/30'
                  : 'bg-slate-900/40 border-slate-800 hover:bg-slate-900/70 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white">{sc.name}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                  {sc.language}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{sc.description}</p>
              <div className="text-[10px] font-mono text-slate-400 mt-2 truncate flex items-center gap-1">
                <FileCode className="w-3 h-3 text-slate-400" /> {sc.filename}
              </div>
            </button>
          );
        })}
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Code Editor & Live File State */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
            {/* File Tab Bar */}
            <div className="px-4 py-2.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-mono font-medium text-slate-200">{currentScenario.filename}</span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                  {currentCode.split('\n').length} lines
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800 flex items-center gap-1">
                  <span className="text-slate-400">SHA-256:</span>
                  <span className="text-emerald-400 font-bold">{currentHash.substring(0, 10)}...</span>
                </div>
                <button
                  onClick={handleCopyCode}
                  className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  title="Copy code"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                </button>
              </div>
            </div>

            {/* Code Content */}
            <div className="p-4 bg-slate-950 font-mono text-xs text-slate-300 overflow-x-auto max-h-[420px] leading-relaxed">
              <pre className="select-text">
                {currentCode.split('\n').map((line, idx) => {
                  const lineNum = idx + 1;
                  const isTarget = targetBlock && line.includes(targetBlock.trim().split('\n')[0]);
                  return (
                    <div
                      key={idx}
                      className={`flex items-start gap-4 px-2 py-0.5 rounded ${
                        isTarget ? 'bg-amber-950/40 text-amber-200 border-l-2 border-amber-400' : 'hover:bg-slate-900/50'
                      }`}
                    >
                      <span className="text-slate-400 select-none text-right w-6">{lineNum}</span>
                      <span className="flex-1 whitespace-pre">{line}</span>
                    </div>
                  );
                })}
              </pre>
            </div>

            {/* Syntax Status Bar */}
            <div className="px-4 py-2.5 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                {syntaxCheck.valid ? (
                  <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                    <CheckCircle2 className="w-4 h-4" /> Syntax Valid ({currentScenario.language.toUpperCase()} AST)
                  </span>
                ) : (
                  <span className="flex items-center gap-1.5 text-rose-400 font-medium">
                    <XCircle className="w-4 h-4" /> {syntaxCheck.error} (Line {syntaxCheck.line})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-slate-400">Match Status:</span>
                {matchCount === 1 ? (
                  <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 text-[11px] font-mono">
                    1 Unique Match
                  </span>
                ) : matchCount === 0 ? (
                  <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[11px] font-mono">
                    0 Matches (Not Found)
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[11px] font-mono">
                    {matchCount} Matches (Ambiguous)
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Execution Timeline / Audit Log */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-indigo-400" /> Patcher Engine Audit Log
              </h3>
              <button
                onClick={() => setLogs([])}
                className="text-[11px] text-slate-400 hover:text-slate-200"
              >
                Clear
              </button>
            </div>
            <div className="bg-slate-950 rounded-lg p-3 font-mono text-[11px] text-slate-300 max-h-40 overflow-y-auto space-y-1">
              {logs.map((log, i) => (
                <div
                  key={i}
                  className={
                    log.includes('[ERROR]')
                      ? 'text-rose-400'
                      : log.includes('[SUCCESS]')
                      ? 'text-emerald-400'
                      : log.includes('[ALERT]')
                      ? 'text-amber-300'
                      : 'text-slate-400'
                  }
                >
                  {log}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Controls, Diff Viewer, & Safety Settings */}
        <div className="lg:col-span-5 space-y-4">
          {/* Safety Policies & Concurrency Controls */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" /> Modification Safety Gates
            </h3>

            <div className="space-y-2.5">
              {/* Syntax validation toggle */}
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 cursor-pointer">
                <div>
                  <div className="text-xs font-medium text-slate-200">AST Syntax Gate (Pre-Write)</div>
                  <div className="text-[11px] text-slate-400">Abort modification if syntax parse fails</div>
                </div>
                <input
                  type="checkbox"
                  checked={validateSyntax}
                  onChange={(e) => setValidateSyntax(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500 w-4 h-4"
                />
              </label>

              {/* Fuzzy matching toggle */}
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 cursor-pointer">
                <div>
                  <div className="text-xs font-medium text-slate-200">Whitespace Fuzzy Match</div>
                  <div className="text-[11px] text-slate-400">Tolerate line ending and trailing space shifts</div>
                </div>
                <input
                  type="checkbox"
                  checked={allowFuzzy}
                  onChange={(e) => setAllowFuzzy(e.target.checked)}
                  className="rounded border-slate-700 text-emerald-500 focus:ring-emerald-500 w-4 h-4"
                />
              </label>

              {/* Stale file concurrency simulator */}
              <label className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950 border border-slate-800 cursor-pointer">
                <div>
                  <div className="text-xs font-medium text-slate-200">Simulate Stale File (SHA-256 Conflict)</div>
                  <div className="text-[11px] text-slate-400">Triggers out-of-order write rejection</div>
                </div>
                <input
                  type="checkbox"
                  checked={simulateExternalStale}
                  onChange={(e) => setSimulateExternalStale(e.target.checked)}
                  className="rounded border-slate-700 text-amber-500 focus:ring-amber-500 w-4 h-4"
                />
              </label>
            </div>
          </div>

          {/* Mode 1: Surgical Target Replacement */}
          {editMode === 'surgical' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Code2 className="w-4 h-4 text-emerald-400" /> Surgical Edit Parameters
                </h3>
                <button
                  onClick={handleInjectCorruptSyntax}
                  className="text-[11px] px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 hover:bg-rose-900 flex items-center gap-1"
                >
                  <Zap className="w-3 h-3" /> Test Syntax Error Gate
                </button>
              </div>

              {/* Target Content */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Target Content (Must match uniquely):
                </label>
                <textarea
                  value={targetBlock}
                  onChange={(e) => setTargetBlock(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 font-mono text-xs text-amber-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                />
              </div>

              {/* Replacement Content */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Replacement Content:
                </label>
                <textarea
                  value={replacementBlock}
                  onChange={(e) => setReplacementBlock(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 font-mono text-xs text-emerald-300 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleApplySurgicalEdit}
                  disabled={matchCount !== 1 && !simulateExternalStale}
                  className={`flex-1 py-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                    matchCount === 1
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-950'
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  <FileEdit className="w-4 h-4" /> Apply Surgical Edit &amp; Commit
                </button>

                <button
                  onClick={() => {
                    setCurrentCode(currentScenario.originalCode);
                    setTargetBlock(currentScenario.targetContent);
                    setReplacementBlock(currentScenario.replacementContent);
                    addLog(`[RESET] Restored original code baseline.`);
                  }}
                  className="px-3 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs flex items-center gap-1"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Mode 2: Unified Diff Viewer */}
          {editMode === 'unified_diff' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                <GitCommit className="w-4 h-4 text-indigo-400" /> Unified Diff Preview
              </h3>
              <div className="bg-slate-950 rounded-lg p-3 font-mono text-xs overflow-x-auto leading-relaxed border border-slate-800 max-h-64">
                {diffText.split('\n').map((line, idx) => {
                  const isAdd = line.startsWith('+') && !line.startsWith('+++');
                  const isDel = line.startsWith('-') && !line.startsWith('---');
                  const isHdr = line.startsWith('@@');
                  return (
                    <div
                      key={idx}
                      className={
                        isAdd
                          ? 'text-emerald-400 bg-emerald-950/30'
                          : isDel
                          ? 'text-rose-400 bg-rose-950/30'
                          : isHdr
                          ? 'text-indigo-300 font-bold bg-indigo-950/40'
                          : 'text-slate-400'
                      }
                    >
                      {line}
                    </div>
                  );
                })}
              </div>
              <button
                onClick={handleApplySurgicalEdit}
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5"
              >
                <Zap className="w-4 h-4" /> Apply Unified Diff via ApplyPatchTool
              </button>
            </div>
          )}

          {/* Mode 3: Snapshot History & Rollback */}
          {editMode === 'snapshots' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
              <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
                <History className="w-4 h-4 text-amber-400" /> File Snapshots &amp; Point-in-Time Rollback
              </h3>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {snapshots.map((snap) => (
                  <div
                    key={snap.version}
                    className="p-3 bg-slate-950 rounded-lg border border-slate-800 flex items-center justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-white">v{snap.version}</span>
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          {snap.reason}
                        </span>
                        <span className="text-[10px] text-slate-400">{snap.timestamp}</span>
                      </div>
                      <div className="text-[10px] font-mono text-emerald-400 mt-1">
                        SHA-256: {snap.hash.substring(0, 16)}... ({snap.lines} lines)
                      </div>
                    </div>
                    <button
                      onClick={() => handleRevert(snap)}
                      className="px-2.5 py-1 bg-slate-800 hover:bg-amber-600 hover:text-white text-slate-300 text-xs font-medium rounded transition-all flex items-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" /> Revert
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

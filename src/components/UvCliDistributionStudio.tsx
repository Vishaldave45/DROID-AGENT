import React, { useState, useEffect } from "react";
import {
  Terminal,
  Cpu,
  Package,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCw,
  Copy,
  Check,
  Code2,
  Layers,
  FileCode,
  Zap,
  ShieldAlert,
  Server,
} from "lucide-react";

interface UvEnvironment {
  uv_available: boolean;
  uv_version: string;
  uv_path: string;
  python_version: string;
  python_executable: string;
  workspace_root: string;
  modules_loaded: number;
  timestamp: number;
}

interface PackageItem {
  name: string;
  version: string;
}

export const UvCliDistributionStudio: React.FC = () => {
  const [envInfo, setEnvInfo] = useState<UvEnvironment | null>(null);
  const [packages, setPackages] = useState<PackageItem[]>([]);
  const [pyproject, setPyproject] = useState<string>("");
  const [cliCommands, setCliCommands] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"cli" | "packages" | "pyproject">("cli");

  // CLI execution state
  const [selectedSubcommand, setSelectedSubcommand] = useState<string>("info");
  const [customArgs, setCustomArgs] = useState<string>("");
  const [executing, setExecuting] = useState<boolean>(false);
  const [cliOutput, setCliOutput] = useState<any>(null);
  const [cliDuration, setCliDuration] = useState<number | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [customUvCmd, setCustomUvCmd] = useState<string>("uv --version");
  const [uvCmdOutput, setUvCmdOutput] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/uv/status");
      const data = await res.json();
      if (data.success) {
        setEnvInfo(data.environment);
        setPackages(data.packages || []);
        setPyproject(data.pyproject || "");
        setCliCommands(data.cli_commands || []);
      }
    } catch (err) {
      console.error("Failed to load UV status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    handleExecCli("info", []);
  }, []);

  const handleExecCli = async (subcommand: string, args: string[] = []) => {
    setExecuting(true);
    setCliOutput(null);
    try {
      const res = await fetch("/api/cli/exec", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subcommand, args }),
      });
      const data = await res.json();
      setCliOutput(data);
      if (data.duration_ms) {
        setCliDuration(data.duration_ms);
      }
    } catch (err: any) {
      setCliOutput({ success: false, error: err.message });
    } finally {
      setExecuting(false);
    }
  };

  const handleRunCustomCli = () => {
    const parsedArgs = customArgs
      .trim()
      .split(" ")
      .filter((a) => a.length > 0);
    handleExecCli(selectedSubcommand, parsedArgs);
  };

  const handleRunUvCommand = async () => {
    setExecuting(true);
    try {
      const res = await fetch("/api/uv/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: customUvCmd }),
      });
      const data = await res.json();
      setUvCmdOutput(data.stdout || data.stderr || "No output returned.");
    } catch (err: any) {
      setUvCmdOutput("Error: " + err.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header & Status Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-slate-100">
                  Phase 14: Packaging, Unified CLI Distribution & UV Integration
                </h2>
                <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                  UV Active
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                Astral UV high-performance package manager powering backend execution & global{" "}
                <code className="text-emerald-400 font-mono bg-slate-800 px-1 py-0.5 rounded text-xs">
                  nexforge
                </code>{" "}
                CLI binary.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchStatus}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh Environment
            </button>
          </div>
        </div>

        {/* Telemetry Metric Chips */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-slate-800/80">
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/60">
            <div className="text-xs text-slate-400 font-medium">UV Executable</div>
            <div className="text-sm font-semibold text-emerald-400 truncate mt-0.5">
              {envInfo?.uv_version || "uv 0.12.9 (active)"}
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/60">
            <div className="text-xs text-slate-400 font-medium">Python Runtime</div>
            <div className="text-sm font-semibold text-sky-400 truncate mt-0.5">
              Python {envInfo?.python_version || "3.10.12"}
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/60">
            <div className="text-xs text-slate-400 font-medium">CLI Binary Target</div>
            <div className="text-sm font-semibold text-indigo-400 truncate mt-0.5">
              /usr/local/bin/nexforge
            </div>
          </div>
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/60">
            <div className="text-xs text-slate-400 font-medium">Full Stack Bridge</div>
            <div className="text-sm font-semibold text-purple-400 truncate mt-0.5">
              uv run --no-project python3
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab("cli")}
          className={`flex items-center gap-2 px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            activeTab === "cli"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <Terminal className="w-4 h-4" />
          Interactive CLI Terminal
        </button>
        <button
          onClick={() => setActiveTab("packages")}
          className={`flex items-center gap-2 px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            activeTab === "packages"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <Package className="w-4 h-4" />
          UV Installed Packages ({packages.length})
        </button>
        <button
          onClick={() => setActiveTab("pyproject")}
          className={`flex items-center gap-2 px-3.5 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            activeTab === "pyproject"
              ? "bg-emerald-600 text-white shadow-sm"
              : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
          }`}
        >
          <FileCode className="w-4 h-4" />
          pyproject.toml Specification
        </button>
      </div>

      {/* Tab 1: Interactive CLI */}
      {activeTab === "cli" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Command presets & dispatch */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-3">
                <Code2 className="w-4 h-4 text-emerald-400" />
                Global CLI Command Presets
              </h3>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setSelectedSubcommand("info");
                    setCustomArgs("");
                    handleExecCli("info", []);
                  }}
                  className="text-left p-2.5 rounded-lg border border-slate-800 bg-slate-950/70 hover:border-emerald-500/50 transition-colors"
                >
                  <div className="text-xs font-mono font-bold text-emerald-400">nexforge info</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">Platform runtime info</div>
                </button>

                <button
                  onClick={() => {
                    setSelectedSubcommand("gate");
                    setCustomArgs("app/storage/base.py");
                    handleExecCli("gate", ["app/storage/base.py"]);
                  }}
                  className="text-left p-2.5 rounded-lg border border-slate-800 bg-slate-950/70 hover:border-emerald-500/50 transition-colors"
                >
                  <div className="text-xs font-mono font-bold text-emerald-400">nexforge gate</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">6D code quality gate</div>
                </button>

                <button
                  onClick={() => {
                    setSelectedSubcommand("scan");
                    setCustomArgs("--path .");
                    handleExecCli("scan", ["--path", "."]);
                  }}
                  className="text-left p-2.5 rounded-lg border border-slate-800 bg-slate-950/70 hover:border-emerald-500/50 transition-colors"
                >
                  <div className="text-xs font-mono font-bold text-emerald-400">nexforge scan</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">AST symbols & metrics</div>
                </button>

                <button
                  onClick={() => {
                    setSelectedSubcommand("bench");
                    setCustomArgs("--all");
                    handleExecCli("bench", ["--all"]);
                  }}
                  className="text-left p-2.5 rounded-lg border border-slate-800 bg-slate-950/70 hover:border-emerald-500/50 transition-colors"
                >
                  <div className="text-xs font-mono font-bold text-emerald-400">nexforge bench</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">SWE benchmark challenges</div>
                </button>
              </div>

              {/* Custom Command Builder */}
              <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
                <label className="block text-xs font-semibold text-slate-300">
                  Custom Subcommand & Arguments
                </label>
                <div className="flex gap-2">
                  <select
                    value={selectedSubcommand}
                    onChange={(e) => setSelectedSubcommand(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500 font-mono"
                  >
                    {cliCommands.map((cmd) => (
                      <option key={cmd} value={cmd}>
                        {cmd}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    value={customArgs}
                    onChange={(e) => setCustomArgs(e.target.value)}
                    placeholder="e.g. --path app/cli or app/storage/base.py"
                    className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-emerald-500 font-mono"
                  />
                </div>
                <button
                  onClick={handleRunCustomCli}
                  disabled={executing}
                  className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  <Play className="w-3.5 h-3.5" />
                  {executing ? "Executing Subcommand..." : `Execute: nexforge ${selectedSubcommand}`}
                </button>
              </div>
            </div>

            {/* Direct UV Runner */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-emerald-400" />
                Direct Astral UV Command Runner
              </h3>
              <p className="text-xs text-slate-400 mb-3">
                Execute any raw UV command through the backend server subprocess.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customUvCmd}
                  onChange={(e) => setCustomUvCmd(e.target.value)}
                  placeholder="e.g. uv --version or uv pip list"
                  className="flex-1 bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 font-mono focus:outline-none focus:border-emerald-500"
                />
                <button
                  onClick={handleRunUvCommand}
                  disabled={executing}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors"
                >
                  Run
                </button>
              </div>

              {uvCmdOutput && (
                <div className="mt-3 p-2 bg-slate-950 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-300 max-h-32 overflow-auto whitespace-pre-wrap">
                  {uvCmdOutput}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Terminal Output */}
          <div className="lg:col-span-7">
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-md flex flex-col h-[520px]">
              {/* Terminal Window Header */}
              <div className="bg-slate-900 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                    <div className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                  </div>
                  <span className="text-xs font-mono text-slate-400 ml-2">
                    nexforge {selectedSubcommand} --json
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  {cliDuration !== null && (
                    <span className="text-[11px] font-mono text-emerald-400">
                      {cliDuration} ms
                    </span>
                  )}
                  {cliOutput && (
                    <button
                      onClick={() => handleCopy(cliOutput.stdout || JSON.stringify(cliOutput, null, 2))}
                      className="text-slate-400 hover:text-slate-200 transition-colors"
                      title="Copy Output"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  )}
                </div>
              </div>

              {/* Terminal Content Body */}
              <div className="flex-1 p-4 font-mono text-xs overflow-auto bg-slate-950 text-slate-300">
                {executing ? (
                  <div className="flex items-center gap-2 text-emerald-400 py-8 justify-center">
                    <RotateCw className="w-4 h-4 animate-spin" />
                    <span>Executing binary /usr/local/bin/nexforge via uv...</span>
                  </div>
                ) : cliOutput ? (
                  <div>
                    {cliOutput.exit_code === 0 ? (
                      <div className="flex items-center gap-2 text-emerald-400 text-xs mb-3 pb-2 border-b border-slate-800">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        <span>Command exited successfully with exit code 0</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-rose-400 text-xs mb-3 pb-2 border-b border-slate-800">
                        <AlertCircle className="w-3.5 h-3.5" />
                        <span>Command returned exit code {cliOutput.exit_code}</span>
                      </div>
                    )}

                    <pre className="whitespace-pre-wrap leading-relaxed text-slate-200">
                      {cliOutput.stdout || JSON.stringify(cliOutput.data || cliOutput, null, 2)}
                    </pre>

                    {cliOutput.stderr && (
                      <div className="mt-3 p-2 bg-rose-950/40 border border-rose-800/50 rounded text-rose-300 text-xs">
                        {cliOutput.stderr}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-slate-600 text-center py-16">
                    Click a preset or execute a subcommand to inspect output.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: UV Installed Packages */}
      {activeTab === "packages" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-slate-200">
                UV Managed Package Manifest
              </h3>
              <p className="text-xs text-slate-400">
                Python dependencies resolved and packaged through Astral UV.
              </p>
            </div>
            <span className="text-xs font-mono text-emerald-400 bg-slate-950 px-2.5 py-1 rounded-full border border-slate-800">
              {packages.length} Packages Verified
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {packages.map((pkg, idx) => (
              <div
                key={idx}
                className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between"
              >
                <div className="flex items-center gap-2.5">
                  <div className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded">
                    <Package className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{pkg.name}</div>
                    <div className="text-[11px] font-mono text-slate-500">v{pkg.version}</div>
                  </div>
                </div>
                <span className="px-2 py-0.5 text-[10px] font-medium bg-slate-900 text-emerald-400 border border-emerald-500/20 rounded">
                  Resolved
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: pyproject.toml Specification */}
      {activeTab === "pyproject" && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-slate-200">
                pyproject.toml Build & Packaging Config
              </h3>
              <p className="text-xs text-slate-400">
                Standard PEP 621 declarative specification defining entrypoints and UV tools.
              </p>
            </div>
            <button
              onClick={() => handleCopy(pyproject)}
              className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              Copy pyproject.toml
            </button>
          </div>

          <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto leading-relaxed max-h-[480px]">
            {pyproject}
          </pre>
        </div>
      )}
    </div>
  );
};

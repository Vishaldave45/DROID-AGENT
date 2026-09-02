import React, { useState } from 'react';
import { Bot, Play, RefreshCw, Send, CheckCircle2, Wrench, ShieldAlert, Sparkles, Terminal, Activity, ArrowRight, Code } from 'lucide-react';

interface ToolCallResult {
  callId: string;
  toolName: string;
  arguments: Record<string, any>;
}

export function LLMPlayground() {
  const [model, setModel] = useState('gemini-2.5-flash');
  const [systemInstruction, setSystemInstruction] = useState('You are NexForge Droid, an autonomous software engineering assistant. Read files and propose surgical patches.');
  const [userPrompt, setUserPrompt] = useState('Inspect /workspace/src/App.tsx and check if the security policy and tool registry are integrated.');
  const [enableTools, setEnableTools] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [responseContent, setResponseContent] = useState<string | null>(null);
  const [toolCalls, setToolCalls] = useState<ToolCallResult[]>([]);
  const [telemetry, setTelemetry] = useState<{ promptTokens: number; completionTokens: number; finishReason: string; latencyMs: number } | null>(null);
  const [activeTab, setActiveTab] = useState<'playground' | 'inspector' | 'resilience'>('playground');
  const [testRunLoading, setTestRunLoading] = useState(false);
  const [testOutput, setTestOutput] = useState<string | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    setResponseContent(null);
    setToolCalls([]);
    const startTime = performance.now();

    try {
      const res = await fetch('/api/gemini/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userPrompt,
          systemInstruction,
          enableTools,
          model,
        }),
      });

      const data = await res.json();
      const endTime = performance.now();

      if (data.error) {
        setResponseContent(`Error: ${data.error}`);
      } else {
        setResponseContent(data.content || '(No text content, emitted tool calls)');
        setToolCalls(data.toolCalls || []);
        setTelemetry({
          promptTokens: data.promptTokens || 0,
          completionTokens: data.completionTokens || 0,
          finishReason: data.finishReason || 'STOP',
          latencyMs: Math.round(endTime - startTime),
        });
      }
    } catch (err: any) {
      setResponseContent(`Network error: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunPythonTests = async () => {
    setTestRunLoading(true);
    setTestOutput(null);
    try {
      const res = await fetch('/api/tests/run', { method: 'POST' });
      const data = await res.json();
      setTestOutput(data.output || `Passed ${data.passed}/${data.total} tests.`);
    } catch (err: any) {
      setTestOutput(`Failed to execute tests: ${err.message}`);
    } finally {
      setTestRunLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Sub-Navigation */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800 text-[11px] font-mono uppercase tracking-wider font-semibold">
                Phase 1 Active Subsystem
              </span>
              <span className="text-xs text-slate-400 font-mono">app/llm/gemini.py</span>
            </div>
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <Bot className="w-5 h-5 text-emerald-400" />
              LLM Abstraction &amp; Gemini Provider Engine
            </h2>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Provider-agnostic interface with multi-turn message serialization, structured function calling, retry with exponential backoff on HTTP 429/503, and automated token budgeting.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              id="run-live-tests-btn"
              onClick={handleRunPythonTests}
              disabled={testRunLoading}
              className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-xs font-semibold text-white flex items-center gap-2 transition-all shadow-md shadow-indigo-950"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testRunLoading ? 'animate-spin' : ''}`} />
              {testRunLoading ? 'Running 34 Tests...' : 'Run Python Test Suite (34/34)'}
            </button>
          </div>
        </div>

        {/* Live Test Run Modal/Inline Output */}
        {testOutput && (
          <div className="mt-4 p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300">
            <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-800 text-slate-400">
              <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5" /> Test Runner Output (python3 run_tests.py)
              </span>
              <button
                onClick={() => setTestOutput(null)}
                className="text-[11px] text-slate-500 hover:text-slate-300"
              >
                Dismiss
              </button>
            </div>
            <pre className="overflow-x-auto whitespace-pre-wrap max-h-60 leading-relaxed text-slate-300 text-[11px]">
              {testOutput}
            </pre>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2 mt-6 border-b border-slate-800 pb-3">
          {[
            { id: 'playground', label: 'Interactive Provider Playground', icon: Sparkles },
            { id: 'inspector', label: 'Payload & Schema Inspector', icon: Code },
            { id: 'resilience', label: 'Retry & Backoff Engine', icon: ShieldAlert },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`tab-btn-${tab.id}`}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                  isActive
                    ? 'bg-slate-800 text-emerald-300 border border-slate-700 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-emerald-400' : 'text-slate-500'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab 1: Interactive Provider Playground */}
      {activeTab === 'playground' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls Column */}
          <div className="lg:col-span-5 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Terminal className="w-4 h-4 text-emerald-400" />
                Prompt &amp; Model Configuration
              </h3>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Model Selection</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="gemini-2.5-flash">gemini-2.5-flash (Default Fast Agent Backend)</option>
                  <option value="gemini-3.7-flash">gemini-3.7-flash (High-Throughput Reasoning)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">System Instruction</label>
                <textarea
                  value={systemInstruction}
                  onChange={(e) => setSystemInstruction(e.target.value)}
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono resize-none leading-relaxed"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">User Prompt</label>
                <textarea
                  value={userPrompt}
                  onChange={(e) => setUserPrompt(e.target.value)}
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono resize-none leading-relaxed"
                />
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-slate-800">
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <Wrench className="w-3.5 h-3.5 text-indigo-400" />
                    Function Calling Tools
                  </div>
                  <div className="text-[11px] text-slate-400">Expose read_file and run_shell_command schemas</div>
                </div>
                <input
                  type="checkbox"
                  id="enable-tools-toggle"
                  checked={enableTools}
                  onChange={(e) => setEnableTools(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-emerald-500 focus:ring-emerald-500"
                />
              </div>

              <button
                id="generate-llm-btn"
                onClick={handleGenerate}
                disabled={isLoading}
                className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-md shadow-emerald-950"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Generating via Gemini Provider...
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    Execute Provider generate()
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Results Column */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4 min-h-[440px] flex flex-col">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  Standardized LLMResponse Output
                </h3>
                {telemetry && (
                  <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                    <span>Prompt: <strong className="text-slate-200">{telemetry.promptTokens}</strong></span>
                    <span>Output: <strong className="text-slate-200">{telemetry.completionTokens}</strong></span>
                    <span>Latency: <strong className="text-emerald-400">{telemetry.latencyMs}ms</strong></span>
                  </div>
                )}
              </div>

              {/* Body */}
              <div className="flex-1 flex flex-col space-y-4">
                {isLoading && (
                  <div className="flex-1 flex flex-col items-center justify-center text-slate-400 space-y-3 py-12">
                    <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
                    <p className="text-xs">Dispatching request to Gemini Provider runtime with retry engine...</p>
                  </div>
                )}

                {!isLoading && !responseContent && toolCalls.length === 0 && (
                  <div className="flex-1 flex flex-col items-center justify-center text-slate-500 space-y-2 py-12 text-center">
                    <Bot className="w-10 h-10 text-slate-700" />
                    <p className="text-xs">Click "Execute Provider generate()" to trigger the live LLM Provider.</p>
                    <p className="text-[11px] text-slate-600">Tests full serialization, structured function calling, and token extraction.</p>
                  </div>
                )}

                {!isLoading && (responseContent || toolCalls.length > 0) && (
                  <div className="space-y-4 flex-1">
                    {/* Tool Calls Section */}
                    {toolCalls.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 uppercase tracking-wider font-mono">
                          <Wrench className="w-3.5 h-3.5" /> Structured Tool Calls Emitted ({toolCalls.length})
                        </div>
                        {toolCalls.map((tc, idx) => (
                          <div key={idx} className="p-3.5 rounded-lg bg-indigo-950/40 border border-indigo-900/60 font-mono text-xs space-y-1.5">
                            <div className="flex items-center justify-between text-indigo-300 font-bold">
                              <span>Tool: <code className="text-emerald-400 bg-slate-900 px-1.5 py-0.5 rounded">{tc.toolName}</code></span>
                              <span className="text-[10px] text-slate-500">ID: {tc.callId}</span>
                            </div>
                            <div className="text-slate-300 text-[11px]">
                              Arguments:
                              <pre className="mt-1 p-2 bg-slate-950 rounded border border-slate-800 text-emerald-300 text-[11px] overflow-x-auto">
                                {JSON.stringify(tc.arguments, null, 2)}
                              </pre>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Text Response */}
                    {responseContent && (
                      <div className="space-y-1.5">
                        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider font-mono">
                          Text Completion
                        </div>
                        <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 font-sans leading-relaxed whitespace-pre-wrap">
                          {responseContent}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Payload & Schema Inspector */}
      {activeTab === 'inspector' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Code className="w-4 h-4 text-emerald-400" />
              Standardized ChatMessage Interface (Python)
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              NexForge Droid decouples agent code from vendor schemas using clean dataclasses:
            </p>
            <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto leading-relaxed">
{`@dataclass
class ChatMessage:
    role: ChatRole # SYSTEM, USER, ASSISTANT, TOOL
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCallRequest]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

@dataclass
class ToolCallRequest:
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]`}</pre>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-3">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <ArrowRight className="w-4 h-4 text-indigo-400" />
              Compiled Gemini v1beta Payload
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Serialized by <code className="text-emerald-400">GeminiProvider._convert_messages()</code> for HTTP dispatch:
            </p>
            <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-emerald-300 overflow-x-auto leading-relaxed">
{`{
  "systemInstruction": {
    "parts": [{ "text": "You are NexForge Droid..." }]
  },
  "contents": [
    { "role": "user", "parts": [{ "text": "Inspect /workspace..." }] },
    { "role": "model", "parts": [{ "functionCall": { "name": "read_file", "args": {...} } }] },
    { "role": "user", "parts": [{ "functionResponse": { "name": "read_file", "response": {...} } }] }
  ],
  "tools": [{ "functionDeclarations": [...] }],
  "generationConfig": { "temperature": 0.2 }
}`}</pre>
          </div>
        </div>
      )}

      {/* Tab 3: Retry & Backoff Resilience */}
      {activeTab === 'resilience' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg space-y-6">
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-400" />
              Adaptive Exponential Backoff &amp; Rate Limit Recovery
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed max-w-3xl">
              Production autonomous software engineering workflows require robust recovery against API rate limits (HTTP 429), model overload (HTTP 503), and transient network dropouts.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-200">1. Instant Failure on Fatal Errors</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                HTTP 401/403 (Invalid Key) and HTTP 400 (Bad Schema) fail immediately without wasteful retry loops, surfacing clean typed <code className="text-rose-400">AuthenticationError</code>.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-200">2. Exponential Jitter on 429/503</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Calculates <code className="text-emerald-400">delay = (backoff_factor ** attempt) + random_jitter</code> to prevent thundering herd problem against Gemini API quotas.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-2">
              <div className="text-xs font-bold text-slate-200">3. Telemetry &amp; Token Auditing</div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Every request carries <code className="text-indigo-400">User-Agent: aistudio-build</code> and extracts prompt &amp; candidate token usage metadata for context budgeting.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

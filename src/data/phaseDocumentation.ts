export interface PhaseDoc {
  id: string;
  number: number;
  title: string;
  category: string;
  status: "Completed" | "Active" | "Next Phase";
  summary: string;
  keyModules: string[];
  cliExamples: string[];
  apiEndpoints: string[];
  architectureDetails: string;
  verificationSteps: string[];
}

export const PHASES_DOCUMENTATION: PhaseDoc[] = [
  {
    id: "phase-1",
    number: 1,
    title: "Core Architecture, Types & Security Sandboxing",
    category: "Core Engine",
    status: "Completed",
    summary: "Foundational Pydantic type definitions, tool registration protocols, and path-traversal sandboxing.",
    keyModules: [
      "app/core/types.py",
      "app/tools/registry.py",
      "app/tools/security.py",
      "app/tools/filesystem.py"
    ],
    cliExamples: [
      "nexforge info",
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_tools.py"
    ],
    apiEndpoints: [
      "GET /api/tools/list",
      "POST /api/tools/execute"
    ],
    architectureDetails: "Enforces strict security gating using PathValidator to prevent directory traversal escapes. All tools expose JSON schemas compliant with Gemini Function Calling.",
    verificationSteps: [
      "Ensure path traversal beyond workspace throws SecurityPolicyError",
      "Validate forbidden system commands (rm -rf /, cat /etc/passwd) are blocked"
    ]
  },
  {
    id: "phase-2",
    number: 2,
    title: "Autonomous ReAct Agent Loop & Model Client",
    category: "Agent Core",
    status: "Completed",
    summary: "Iterative Reason + Act loop with tool dispatching, multi-turn reasoning, and mock scenario fallbacks.",
    keyModules: [
      "app/agent/core.py",
      "app/agent/client.py",
      "app/agent/mock_provider.py"
    ],
    cliExamples: [
      "nexforge run --requirement 'Fix calculate_total bug' --iterations 6",
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_agent.py"
    ],
    apiEndpoints: [
      "POST /api/agent/run"
    ],
    architectureDetails: "Dispatches LLM reasoning iterations, collects tool outputs, builds observation history, and evaluates completion conditions via finish_task.",
    verificationSteps: [
      "Execute automated mock test scenarios (patch_bug, refactor_math)",
      "Check token budget and iteration limits are strictly respected"
    ]
  },
  {
    id: "phase-3",
    number: 3,
    title: "Pydantic State & SQLite Task Checkpointing",
    category: "Persistence",
    status: "Completed",
    summary: "Durable SQLite task lifecycle tracking with point-in-time state checkpointing and rollback recovery.",
    keyModules: [
      "app/storage/models.py",
      "app/storage/db.py",
      "app/storage/checkpoint.py"
    ],
    cliExamples: [
      "uv run --no-project python3 ./nexforge-droid/run_storage.py --op list-tasks"
    ],
    apiEndpoints: [
      "GET /api/storage/tasks",
      "POST /api/storage/tasks",
      "POST /api/storage/tasks/:id/checkpoint",
      "POST /api/storage/checkpoints/:id/restore"
    ],
    architectureDetails: "Persists task models, tool execution traces, and filesystem snapshot diffs to SQLite in WAL mode with millisecond restoration capabilities.",
    verificationSteps: [
      "Create task, take snapshot checkpoint, execute destructive change, and restore checkpoint"
    ]
  },
  {
    id: "phase-4",
    number: 4,
    title: "Full-Stack React + Vite Web Cockpit",
    category: "Interface",
    status: "Completed",
    summary: "Production-grade developer control center built with React 19, Tailwind CSS, Lucide icons, and Motion.",
    keyModules: [
      "server.ts",
      "src/App.tsx",
      "src/components/AgentMonitor.tsx",
      "src/components/Navigation.tsx"
    ],
    cliExamples: [
      "npm run build",
      "npm run dev"
    ],
    apiEndpoints: [
      "GET /api/health"
    ],
    architectureDetails: "Unified single-port Express server providing Vite SSR/SPA middleware, high-density system status monitors, and real-time state synchronizers.",
    verificationSteps: [
      "Verify zero TypeScript build errors with tsc --noEmit",
      "Check responsiveness across desktop and tablet viewports"
    ]
  },
  {
    id: "phase-5",
    number: 5,
    title: "Repository Intelligence & File Tree Scanner",
    category: "Code Intelligence",
    status: "Completed",
    summary: "Automated codebase discovery, language classification, manifest parsing, and LOC metrics.",
    keyModules: [
      "app/context/scanner.py",
      "app/context/manifest.py"
    ],
    cliExamples: [
      "nexforge scan --path . --json",
      "nexforge scan --path app/context"
    ],
    apiEndpoints: [
      "GET /api/repo/scan",
      "GET /api/repo/stats"
    ],
    architectureDetails: "Fast non-blocking scanner filtering .git, __pycache__, and node_modules while identifying entry points and package manifests.",
    verificationSteps: [
      "Scan nexforge-droid directory and confirm file metric counts match filesystem"
    ]
  },
  {
    id: "phase-6",
    number: 6,
    title: "Code Graph & Symbol Dependency Indexing",
    category: "Code Intelligence",
    status: "Completed",
    summary: "AST syntax analysis indexing classes, functions, and cross-file import call graphs.",
    keyModules: [
      "app/context/indexer.py",
      "app/context/graph.py"
    ],
    cliExamples: [
      "uv run --no-project python3 ./nexforge-droid/run_intelligence.py --op search-symbols --query Diagnostic"
    ],
    apiEndpoints: [
      "GET /api/repo/graph",
      "GET /api/repo/symbols",
      "GET /api/repo/symbol-details"
    ],
    architectureDetails: "Constructs a directed dependency graph calculating in-degree, out-degree, and blast radius for refactoring safety.",
    verificationSteps: [
      "Index AST symbols and verify all top-level classes and functions are discovered"
    ]
  },
  {
    id: "phase-7",
    number: 7,
    title: "AST-Aware Patcher & Safe Code Modifier",
    category: "Code Modification",
    status: "Completed",
    summary: "Atomic patch validation preventing syntax corruption before writes with standard unified diffs.",
    keyModules: [
      "app/patcher/safe_modifier.py",
      "app/patcher/diff_engine.py"
    ],
    cliExamples: [
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_patcher.py"
    ],
    apiEndpoints: [
      "POST /api/patcher/validate",
      "POST /api/patcher/diff",
      "POST /api/patcher/apply"
    ],
    architectureDetails: "Performs speculative in-memory AST parsing. If modified source produces a SyntaxError or IndentationError, the write is aborted.",
    verificationSteps: [
      "Attempt malformed indentation patch and verify it is rejected before disk modification"
    ]
  },
  {
    id: "phase-8",
    number: 8,
    title: "Dynamic Diagnostics, Traceback Parsing & Fix Loop",
    category: "Diagnostics",
    status: "Completed",
    summary: "Automated test runner, traceback frame decomposition, root-cause hypothesis generation, and rollback loops.",
    keyModules: [
      "app/diagnostics/traceback_parser.py",
      "app/diagnostics/diagnostic_reasoner.py",
      "app/diagnostics/diagnostic_loop_controller.py"
    ],
    cliExamples: [
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_diagnostics.py"
    ],
    apiEndpoints: [
      "POST /api/diagnostics/parse",
      "POST /api/diagnostics/diagnose",
      "POST /api/diagnostics/loop"
    ],
    architectureDetails: "Parses Python traceback strings into structured frames, identifies fault type, generates targeted repair suggestions, and rolls back if test failures increase.",
    verificationSteps: [
      "Simulate failing unit test and verify loop terminates with regression safeguard if failures increase"
    ]
  },
  {
    id: "phase-9",
    number: 9,
    title: "DAG Task Planner & Hierarchical Decomposer",
    category: "Planning",
    status: "Completed",
    summary: "Decomposes complex multi-stage engineering goals into directed acyclic graphs (DAGs) with topological scheduling.",
    keyModules: [
      "app/planner/dag.py",
      "app/planner/decomposer.py"
    ],
    cliExamples: [
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_planner.py"
    ],
    apiEndpoints: [
      "POST /api/planner/generate",
      "POST /api/planner/replan"
    ],
    architectureDetails: "Detects cycles, resolves dependencies, identifies parallelizable nodes, and triggers dynamic replanning if a node fails.",
    verificationSteps: [
      "Validate topological ordering of multi-step migration tasks"
    ]
  },
  {
    id: "phase-10",
    number: 10,
    title: "Multi-File Changeset Orchestration & Staging",
    category: "Orchestration",
    status: "Completed",
    summary: "Atomic multi-file refactor coordination with staging areas, dry-run diffs, and human-in-the-loop approval gating.",
    keyModules: [
      "app/orchestrator/changeset.py",
      "app/orchestrator/approval_gate.py"
    ],
    cliExamples: [
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_orchestrator.py"
    ],
    apiEndpoints: [
      "POST /api/orchestrator/changeset/create",
      "POST /api/orchestrator/changeset/apply",
      "POST /api/orchestrator/approval/decide"
    ],
    architectureDetails: "Collects edits across disparate files, performs blast radius analysis, stages diffs, and prompts operator approval when risk thresholds are exceeded.",
    verificationSteps: [
      "Stage multi-file refactor, verify approval gate holds execution until approved"
    ]
  },
  {
    id: "phase-11",
    number: 11,
    title: "Real-time Streaming Telemetry & SSE Logs",
    category: "Telemetry",
    status: "Completed",
    summary: "Sub-millisecond Server-Sent Events (SSE) streaming thought tokens, tool events, and telemetry frames to the UI.",
    keyModules: [
      "server.ts (/api/agent/stream)",
      "src/components/StreamingTelemetryStudio.tsx"
    ],
    cliExamples: [
      "curl -N http://localhost:3000/api/agent/stream?scenario=refactor-sqlite"
    ],
    apiEndpoints: [
      "GET /api/agent/stream"
    ],
    architectureDetails: "Maintains a high-throughput event stream transmitting structured JSON events categorized as thoughts, tool executions, terminal outputs, and metrics.",
    verificationSteps: [
      "Connect SSE client and confirm sequential reception of streaming event frames"
    ]
  },
  {
    id: "phase-12",
    number: 12,
    title: "Interactive Time-Travel Debugger & Breakpoints",
    category: "Debugging",
    status: "Completed",
    summary: "Step-by-step agent execution control, live breakpoint pausing, state snapshot inspection, and execution replay.",
    keyModules: [
      "app/streaming/stream_controller.py",
      "src/components/InteractiveDebuggerStudio.tsx"
    ],
    cliExamples: [
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_streaming.py"
    ],
    apiEndpoints: [
      "GET /api/debugger/scenarios",
      "POST /api/debugger/step",
      "POST /api/debugger/continue",
      "POST /api/debugger/breakpoints",
      "POST /api/debugger/reset"
    ],
    architectureDetails: "Deterministic step sequencer allowing developers to inspect agent thoughts, variable environments, and tool inputs prior to execution.",
    verificationSteps: [
      "Set breakpoint on specific tool call, verify execution halts and can be stepped manually"
    ]
  },
  {
    id: "phase-13",
    number: 13,
    title: "SWE-bench Suite & Multi-Criteria Quality Gates",
    category: "Evaluation",
    status: "Completed",
    summary: "Standardized SWE-bench software engineering challenges with a 6-dimensional code quality gate.",
    keyModules: [
      "app/evaluation/swe_benchmark.py",
      "app/evaluation/quality_gate.py",
      "src/components/EvaluationBenchmarkStudio.tsx"
    ],
    cliExamples: [
      "nexforge bench --id SWE-001 --json",
      "nexforge gate app/storage/base.py --json"
    ],
    apiEndpoints: [
      "GET /api/evaluation/benchmarks",
      "POST /api/evaluation/run-benchmark",
      "POST /api/evaluation/quality-gate",
      "GET /api/evaluation/leaderboard"
    ],
    architectureDetails: "Runs real-world SWE challenges calculating Pass@1 rates and evaluates code across 6 dimensions: Test Suite, AST Integrity, Security, Lint, Complexity, and Contract.",
    verificationSteps: [
      "Execute quality gate on source file and verify 6-dimension scores are calculated and weighted"
    ]
  },
  {
    id: "phase-14",
    number: 14,
    title: "Packaging, Unified CLI Distribution & UV Integration",
    category: "Distribution",
    status: "Active",
    summary: "Transition the entire platform to UV for package management and execute commands via the global nexforge CLI.",
    keyModules: [
      "app/cli/main.py",
      "pyproject.toml",
      "/usr/local/bin/nexforge",
      "server.ts (uv run bridge)",
      "src/components/UvCliDistributionStudio.tsx"
    ],
    cliExamples: [
      "nexforge info --json",
      "nexforge gate app/storage/base.py --json",
      "nexforge scan --path . --json",
      "nexforge bench --all --json",
      "uv run --no-project python3 -m unittest discover -s nexforge-droid/tests"
    ],
    apiEndpoints: [
      "GET /api/uv/status",
      "POST /api/uv/run",
      "GET /api/cli/info",
      "POST /api/cli/exec"
    ],
    architectureDetails: "Full transition of backend Python orchestration to Astral's UV package manager. All server processes invoke Python via 'uv run --no-project python3', eliminating virtualenv latency.",
    verificationSteps: [
      "Run nexforge --help in shell and verify command dispatcher displays all 6 subcommands",
      "Check server.ts routes execute through UV and return structured responses"
    ]
  },
  {
    id: "phase-15",
    number: 15,
    title: "Multi-Agent Swarm Collaboration & Autonomous Peer Review",
    category: "Swarm Intelligence",
    status: "Completed",
    summary: "Multi-agent consensus engine coordinating Architect, Coder, Reviewer, Critic, and Synthesizer personas with automated peer reviews and quorum voting.",
    keyModules: [
      "app/agent/swarm.py",
      "tests/test_swarm_collaboration.py",
      "src/components/SwarmCollaborationStudio.tsx"
    ],
    cliExamples: [
      "nexforge run --swarm --objective 'Refactor database schema with backward compatibility'",
      "uv run --no-project python3 -m unittest nexforge-droid/tests/test_swarm_collaboration.py"
    ],
    apiEndpoints: [
      "GET /api/swarm/roles",
      "POST /api/swarm/collaborate",
      "POST /api/swarm/deliberate"
    ],
    architectureDetails: "Autonomous swarm consensus framework where specialized agent roles collaborate: Architect designs plan, Coder implements diffs, Reviewer checks security/contracts, Critic finds boundary bugs, and Synthesizer tabulates quorum consensus.",
    verificationSteps: [
      "Run multi-agent deliberation simulation and verify quorum voting determines consensus decision"
    ]
  },
  {
    id: "phase-16",
    number: 16,
    title: "Universal Model Context Protocol (MCP) Server & Gateway",
    category: "Integration",
    status: "Completed",
    summary: "JSON-RPC 2.0 compliant Model Context Protocol (MCP 2024-11-05) Server, Tool Dispatcher, Resource Provider, Prompt Template Engine, and External Tool Gateway bridging GitHub, Postgres, Sentry, and Brave Search.",
    keyModules: [
      "app/mcp/protocol.py",
      "app/mcp/server.py",
      "app/mcp/client.py",
      "app/mcp/gateway.py",
      "run_mcp.py",
      "src/components/MCPGatewayStudio.tsx"
    ],
    cliExamples: [
      "nexforge mcp status",
      "nexforge mcp tools",
      "nexforge mcp servers",
      "python3 run_mcp.py serve"
    ],
    apiEndpoints: [
      "GET /api/mcp/status",
      "GET /api/mcp/tools",
      "GET /api/mcp/servers",
      "GET /api/mcp/resources",
      "POST /api/mcp/call",
      "POST /api/mcp/jsonrpc"
    ],
    architectureDetails: "Dual-role Model Context Protocol hub enabling Claude Desktop, Cursor, and IDEs to drive NexForge tools via stdio, while federating external tool servers into the autonomous agent loop.",
    verificationSteps: [
      "Verify JSON-RPC 2.0 initialize handshake returns protocol 2024-11-05 and capabilities",
      "Run tools/list and confirm all 28 native tools have valid JSON Schema specifications",
      "Execute external tool call through gateway federation client"
    ]
  },
  {
    id: "phase-17",
    number: 17,
    title: "Autonomous Git Worktrees, Branching, PR Lifecycle & CI/CD Self-Healing Sandbox",
    category: "DevOps & CI/CD",
    status: "Completed",
    summary: "Isolated git worktree checkouts, branch governance, automatic pull request markdown synthesis with AST risk metrics, and simulated CI/CD test runner with closed-loop self-healing repair.",
    keyModules: [
      "app/git/worktree.py",
      "app/git/branch.py",
      "app/git/pr_generator.py",
      "app/git/ci_pipeline.py",
      "app/tools/pr_tools.py",
      "src/components/GitPRStudio.tsx"
    ],
    cliExamples: [
      "nexforge branch list",
      "nexforge branch create feat/auth-tokens",
      "nexforge pr --title 'feat: add session token validation'",
      "nexforge ci run",
      "nexforge ci heal",
      "uv run --no-project python3 ./nexforge-droid/run_tests.py"
    ],
    apiEndpoints: [
      "GET /api/git/branches",
      "POST /api/git/create-branch",
      "POST /api/git/switch-branch",
      "GET /api/git/worktrees",
      "POST /api/git/create-worktree",
      "POST /api/git/remove-worktree",
      "POST /api/git/generate-pr",
      "POST /api/git/run-ci",
      "POST /api/git/heal-ci"
    ],
    architectureDetails: "Safely sandboxes agent code modifications using isolated Git worktrees and branches. Automatically generates comprehensive Pull Request descriptions with diff breakdowns, conventional commit titles, and risk ratings. Orchestrates a 5-stage CI/CD pipeline (syntax, security, tests, quality gate, build) with closed-loop self-healing that automatically generates and applies fix patches when CI fails.",
    verificationSteps: [
      "Create an isolated git branch and detached worktree sandbox",
      "Synthesize complete Pull Request markdown from staged changes",
      "Simulate CI/CD pipeline failure and verify automated self-healing recovers pipeline to green",
      "Verify 145/145 unit tests passing across all 17 phases"
    ]
  },
  {
    id: "phase-18",
    number: 18,
    title: "Neural Symbolic Memory & Long-term Agent Persistence",
    category: "Memory & Persistence",
    status: "Completed",
    summary: "Hybrid vector-symbolic memory architecture combining episodic experience logs, semantic knowledge graphs, working memory consolidation, and long-term vector retrieval for autonomous agents across sessions.",
    keyModules: [
      "app/memory/vector_store.py",
      "app/memory/symbolic_kb.py",
      "app/memory/episodic.py",
      "app/memory/consolidation.py",
      "app/tools/memory_tools.py"
    ],
    cliExamples: [
      "nexforge memory search --query 'authentication bug'",
      "nexforge memory consolidate",
      "nexforge memory stats"
    ],
    apiEndpoints: [
      "GET /api/memory/search",
      "POST /api/memory/store",
      "POST /api/memory/consolidate",
      "GET /api/memory/stats"
    ],
    architectureDetails: "Combines vector embedding retrieval with symbolic knowledge graph triples to provide cross-session agent memory, automatically consolidating episodic interactions into durable semantic knowledge.",
    verificationSteps: [
      "Verify semantic similarity retrieval returns relevant episodic records",
      "Verify symbolic knowledge graph stores and queries relationship triples correctly",
      "Verify automated consolidation summarizes raw session logs into compressed persistent memory nodes"
    ]
  },
  {
    id: "phase-19",
    number: 19,
    title: "Autonomous Test Suite Synthesizer & Mutation Testing Engine",
    category: "Diagnostics",
    status: "Active",
    summary: "Introspects Python AST to generate robust unittest test suites covering nominal and boundary conditions, combined with a mutation testing engine injecting syntactic mutants (AOR, ROR, COR) to verify test suite quality and coverage.",
    keyModules: [
      "app/testing/synthesizer.py",
      "app/testing/mutation.py",
      "app/testing/coverage.py",
      "app/tools/testing_tools.py"
    ],
    cliExamples: [
      "nexforge test synthesize --module app.agent.core",
      "nexforge test mutate --module app.utils"
    ],
    apiEndpoints: [
      "POST /api/testing/synthesize",
      "POST /api/testing/mutate",
      "POST /api/testing/coverage"
    ],
    architectureDetails: "Automates test creation from AST structure and evaluates test suite robustness by injecting arithmetic, relational, and logical mutants, computing strict mutation scores.",
    verificationSteps: [
      "Synthesize unit tests for target python module",
      "Run mutation testing and verify mutation score calculation",
      "Analyze AST statement and branch coverage metrics"
    ]
  }
];

# NexForge Droid: Comprehensive Multi-Phase Architectural Documentation

NexForge Droid is an autonomous software engineering agent platform built with a high-performance Python core and a responsive TypeScript/Vite cockpit. This document provides complete architectural specifications, API signatures, execution paradigms, and verification procedures for all project phases.

---

## Phase 1: Core Architecture, Types & Security Sandboxing
- **Objective**: Establish foundational type models, a sandboxed tool execution engine, and strict security policy gating.
- **Key Modules**:
  - `app/core/types.py`: Pydantic models for `ToolDefinition`, `ToolCall`, `ToolResult`, and `AgentState`.
  - `app/tools/registry.py`: Dynamic tool registry mapping system capabilities to LLM-compatible JSON schemas.
  - `app/tools/security.py`: `PathValidator` ensuring filesystem isolation, disallowing root escapes, blocking destructive commands (`rm -rf`, system credential access).
- **Verification**: Run `uv run --no-project python3 -m unittest nexforge-droid/tests/test_tools.py` and `test_security.py`.

---

## Phase 2: Autonomous ReAct Agent Loop & Model Client
- **Objective**: Implement the ReAct (Reason + Act) autonomous decision loop with tool dispatching and model abstraction.
- **Key Modules**:
  - `app/agent/core.py`: Autonomous execution engine driving task decomposition, thought generation, tool invocation, and termination criteria.
  - `app/agent/client.py`: Multi-provider LLM interface supporting Gemini Pro/Flash and deterministic offline mock scenarios.
  - `app/agent/mock_provider.py`: Mock scenarios (`patch_bug`, `refactor_math`, `test_failure`) for high-speed continuous integration.
- **Verification**: Verified via `test_agent.py` and dynamic execution endpoint `/api/agent/run`.

---

## Phase 3: Pydantic State & SQLite Task Checkpointing
- **Objective**: Provide durable local task persistence and snapshot checkpointing with instant rollback.
- **Key Modules**:
  - `app/storage/models.py`: SQLAlchemy and Pydantic entities for `Task`, `Checkpoint`, `ExecutionStep`.
  - `app/storage/db.py`: SQLite session lifecycle manager with WAL mode for concurrency.
  - `app/storage/checkpoint.py`: Checkpoint creation, diff recording, and state restoration on agent regression.
- **Verification**: Verified via `test_storage.py` and `/api/storage/*` endpoints.

---

## Phase 4: Full-Stack React + Vite Web UI
- **Objective**: Build an enterprise-grade operator console with high density, clear visual hierarchy, and real-time observability.
- **Key Modules**:
  - `server.ts`: Express backend serving Vite SPA and bridging REST/SSE calls to Python via UV.
  - `src/App.tsx`: Navigation bar, tab routing, system status chips, and phase switcher.
  - `src/components/AgentMonitor.tsx`: Live task monitoring, tool execution feeds, and prompt inspector.

---

## Phase 5: Repository Intelligence & File Tree Scanner
- **Objective**: Perform structural codebase discovery, language classification, manifest parsing, and LOC metrics.
- **Key Modules**:
  - `app/context/scanner.py`: `RepositoryScanner` scanning file trees, filtering ignored patterns, and extracting structural summaries.
  - `app/context/manifest.py`: Detection of `pyproject.toml`, `package.json`, `setup.cfg`, `Cargo.toml`.
- **Verification**: Run `nexforge scan --json` or invoke `/api/repo/scan`.

---

## Phase 6: Code Graph & Symbol Dependency Indexing
- **Objective**: Parse AST syntax trees to index classes, functions, and cross-file imports into a directed dependency graph.
- **Key Modules**:
  - `app/context/indexer.py`: Python AST visitor extracting symbol signatures, docstrings, call graphs, and references.
  - `app/context/graph.py`: Directed graph representation calculating in-degree, out-degree, and dependency impact.
- **Verification**: Verified via `test_intelligence.py` and visual graph rendering in `CodeGraphStudio.tsx`.

---

## Phase 7: AST-Aware Patcher & Safe Code Modifier
- **Objective**: Prevent syntax corruption by validating AST correctness and running atomic diff previews before modifying source files.
- **Key Modules**:
  - `app/patcher/safe_modifier.py`: Validates syntax with `ast.parse()` prior to disk write; automatically aborts on syntax error.
  - `app/patcher/diff_engine.py`: Generates standard unified diffs and computes structural edit statistics.
- **Verification**: Verified via `test_patcher.py` and endpoint `/api/patcher/validate`.

---

## Phase 8: Dynamic Diagnostics, Traceback Parsing & Fix Loop
- **Objective**: Ingest unhandled Python exceptions and test tracebacks, extract root-cause hypotheses, and drive automated fix loops.
- **Key Modules**:
  - `app/diagnostics/traceback_parser.py`: Parses Python tracebacks into structured stack frames and assertion error details.
  - `app/diagnostics/diagnostic_reasoner.py`: Categorizes faults (IndexError, TypeError, AssertionError) and proposes remedies.
  - `app/diagnostics/diagnostic_loop_controller.py`: Executes iterative test-and-repair cycles with automatic regression rollback.
- **Verification**: Verified via `test_diagnostics.py` and `DiagnosticsStudio.tsx`.

---

## Phase 9: DAG Task Planner & Hierarchical Decomposer
- **Objective**: Decompose high-level engineering objectives into acyclic directed dependency graphs (DAG) with parallel execution plans.
- **Key Modules**:
  - `app/planner/dag.py`: Task DAG representation with topological sorting, cycle detection, and ready-node discovery.
  - `app/planner/decomposer.py`: Hierarchical decomposition of complex requirements into atomic verifiable sub-tasks.
- **Verification**: Verified via `test_planner.py` and `TaskPlannerStudio.tsx`.

---

## Phase 10: Multi-File Changeset Orchestration & Staging
- **Objective**: Coordinate multi-file refactoring operations with staging areas, atomic commits, and human-in-the-loop approval gates.
- **Key Modules**:
  - `app/orchestrator/changeset.py`: `Changeset` tracking multi-file modifications, diff previews, and atomic rollback.
  - `app/orchestrator/approval_gate.py`: Human approval gate enforcing review for risky or high-blast-radius operations.
- **Verification**: Verified via `test_orchestrator.py` and `MultiFileOrchestratorStudio.tsx`.

---

## Phase 11: Real-time Streaming Telemetry & SSE Logs
- **Objective**: Stream live agent thought patterns, tool inputs, stdout/stderr streams, and metrics to the frontend over Server-Sent Events (SSE).
- **Key Modules**:
  - `server.ts` `/api/agent/stream`: Express SSE endpoint streaming structured telemetry frames.
  - `src/components/StreamingTelemetryStudio.tsx`: Real-time log inspector with event filtering and auto-scroll controls.

---

## Phase 12: Interactive Time-Travel Debugger & Breakpoints
- **Objective**: Provide deterministic step-by-step debugging, pause/resume execution, set breakpoints on tool calls, and reverse state.
- **Key Modules**:
  - `app/streaming/stream_controller.py`: Step-by-step agent execution controller with breakpoint detection.
  - `src/components/InteractiveDebuggerStudio.tsx`: Time-travel controls (`Step Forward`, `Continue`, `Reset`, `Add Breakpoint`).

---

## Phase 13: SWE-bench Suite & Multi-Criteria Quality Gates
- **Objective**: Standardized evaluation benchmark suite based on SWE-bench and a 6-dimensional code quality gate.
- **Key Modules**:
  - `app/evaluation/swe_benchmark.py`: Benchmark suite running standardized software engineering challenges and calculating Pass@1 rates.
  - `app/evaluation/quality_gate.py`: 6D Quality Gate auditing:
    1. **Test Suite Verification** (unit test passes, zero regressions)
    2. **AST & Syntax Integrity** (clean AST compilation, syntax validity)
    3. **Security Analysis** (credential leaks, unsafe builtins, path escapes)
    4. **Lint & Style Compliance** (formatting, imports, naming rules)
    5. **Cyclomatic Complexity** (decision complexity threshold analysis)
    6. **Requirements Contract** (verifying requirement specifications)
- **Verification**: Verified via `test_evaluation.py` and `EvaluationBenchmarkStudio.tsx`.

---

## Phase 14: Packaging, Unified CLI Distribution & UV Integration
- **Objective**: Transition the entire platform to `uv` for lightning-fast environment execution and provide a unified `nexforge` CLI.
- **Key Modules**:
  - `app/cli/main.py`: CLI dispatcher supporting `info`, `bench`, `gate`, `scan`, `run`, and `test` commands with `--json` output.
  - `pyproject.toml`: Declarative build definition, dependencies, dev extras, and `[project.scripts]` mapping `nexforge`.
  - `/usr/local/bin/nexforge`: Global system executable for seamless terminal execution.
  - `server.ts`: Complete migration of all backend Python subprocess calls to `uv run --no-project python3`.
- **Verification**: Run `nexforge info --json` or `npm run uv:test`.

---

## Phase 15: Multi-Agent Swarm Collaboration & Autonomous Peer Review
- **Objective**: Coordinate multiple specialized agent personas (`Architect`, `Coder`, `Reviewer`, `Critic`, `Synthesizer`) through structured deliberation, consensus voting, and automated peer review.
- **Key Modules**:
  - `app/agent/swarm.py`: Multi-agent orchestration engine with role definitions, deliberation cycles, and consensus quorum gating.
  - `tests/test_swarm_collaboration.py`: Unit tests validating role delegation, critiques, vote tabulation, and quorum consensus.
  - `src/components/SwarmCollaborationStudio.tsx`: Interactive multi-agent debate visualizer and consensus control room.

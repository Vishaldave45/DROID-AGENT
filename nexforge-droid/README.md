# NexForge Droid — Autonomous Coding Agent Runtime

> **Educational & Research Implementation** inspired by publicly observable concepts of modern autonomous coding agents.

---

## 🏛️ System Overview

NexForge Droid is an autonomous software-engineering agent runtime designed to explore, understand, plan, execute, test, diagnose, self-correct, and verify code modifications within software repositories.

```
                      USER / TASK
                           │
                           ▼
                 ┌───────────────────┐
                 │   Droid Runtime   │
                 └─────────┬─────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     STATE (DB)      CONTEXT ENGINE     MEMORY
          │                │                │
          └────────────────┼────────────────┘
                           │
                           ▼
                   PLANNER & REASONER
                           │
                           ▼
                      TOOL ROUTER
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       FILESYSTEM     CODE SEARCH        GIT
            └──────────────┬──────────────┘
                           │
                           ▼
                  SANDBOX EXECUTION (VM/Docker)
                           │
                           ▼
                     TEST ENGINE
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
                PASS              FAIL
                  │                 │
                  ▼                 ▼
             EVALUATOR      FAILURE DIAGNOSTIC
                  │                 │
                  ▼                 ▼
              COMPLETION       REPAIR & RETRY
```

---

## 📦 Project Structure

```
nexforge-droid/
├── app/
│   ├── __init__.py
│   ├── main.py                  # API / CLI Service Entrypoint
│   ├── config.py                # Environment & Typed Settings
│   ├── agent/                   # Agent Lifecycle & Orchestration Abstractions
│   ├── context/                 # Context Engine & Engineering Graph Retrieval
│   ├── tools/                   # Tool Contracts & Registry
│   ├── execution/               # Command & Sandbox Execution Abstractions
│   ├── security/                # Policy Gateway & Permission System
│   ├── git/                     # Git Engine & Workspace VCS
│   ├── evaluation/              # Evaluation & Verification Engine
│   ├── storage/                 # Persistence & State Store Abstractions
│   ├── llm/                     # LLM Provider Abstractions
│   └── observability/           # Structured Logging & Tracing
├── tests/                       # Automated Test Suites
├── Dockerfile                   # Containerized Sandbox/Runtime
├── docker-compose.yml           # Multi-service local environment
├── pyproject.toml               # Package Dependencies & Metadata
└── .env.example                 # Environment Variable Schema
```

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
cp .env.example .env
```

### 2. Run Test Suite
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### 3. Run FastAPI Application
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

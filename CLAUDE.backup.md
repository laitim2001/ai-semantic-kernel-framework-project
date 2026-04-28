# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## AI Assistant Notes

- **Project Location**: Windows (`C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project`)
- **Server Startup**: Use `cmd /c` or direct terminal execution, NOT `start /D` or `start /B`
  - `start /B python -m uvicorn ...` — Background execution causes process tracking issues
  - `cmd /c "cd /d path && python -m uvicorn ..."` — Recommended

```bash
# Recommended Backend startup (Windows)
cmd /c "cd /d C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project\backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
```

---

## Core Vision & Design Philosophy

> **This section defines the project's fundamental direction. Every design decision, suggestion, and implementation MUST align with these principles.**

### Mission
Build enterprise AI agent teams that work like **human professional teams** — not just using existing frameworks, but designing **novel agentic capabilities** that don't exist yet.

### Agent Team Design Principles
The platform delivers agents that are:
1. **Professional** — domain expertise, not generic chatbots
2. **Planned** — structured approach to tasks, not ad-hoc
3. **Memory-equipped** — remember past interactions, decisions, context
4. **Autonomous** — self-organize, plan, execute, and retry
5. **Controllable** — human oversight at all times
6. **Transparent** — all processes and decisions are visible/auditable
7. **Security-compliant** — follows enterprise-specific regulations
8. **Multi-intelligent** — multiple specialized agents collaborating
9. **Knowledge-aware** — RAG/knowledge base for enterprise-specific knowledge
10. **Action-capable** — real tool execution, not just conversation

### Development Philosophy
- MAF, Claude SDK, AG-UI, Claude Code patterns are **building blocks and inspiration**, NOT design boundaries
- Many capabilities require **novel architecture** that doesn't exist in any single framework
- Current agentic frameworks are all very new — none fully addresses enterprise production needs
- **DO NOT** default to "MAF has feature X, let's use it" — instead ask "what effect is needed?" then **co-design** a solution
- Reference multiple sources (MAF internals, CC source patterns, Claude SDK, industry research) as **design inspiration**
- The hybrid orchestrator (code-enforced steps + LLM routing) is an **intentional novel design**, not a workaround
- **User provides ideas and vision; AI assistant (Claude) is executor and coordinator** — together we design what doesn't exist yet

---

## Project Overview

**IPA Platform** (Intelligent Process Automation) - Enterprise AI Agent orchestration platform

| Attribute | Value |
|-----------|-------|
| **Core Framework** | Microsoft Agent Framework + Claude Agent SDK + AG-UI Protocol |
| **Current Status** | Phase 44 Completed - Deep Integration & Optimization |
| **Completed** | 44 Phases, 152+ Sprints, ~2500+ Story Points |
| **Tech Stack** | FastAPI + React 18 + PostgreSQL + Redis |

---

## Development Commands

### Unified Dev Environment (Recommended)

```bash
# View all service status
python scripts/dev.py status

# Start services
python scripts/dev.py start              # Start all (Docker + Backend + Frontend)
python scripts/dev.py start backend      # Backend only
python scripts/dev.py start frontend     # Frontend only
python scripts/dev.py start docker       # Docker services only

# Stop/Restart
python scripts/dev.py stop [service]
python scripts/dev.py restart [service]

# Logs
python scripts/dev.py logs postgres
python scripts/dev.py logs docker -f
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI/Uvicorn |
| Frontend | 3005 | Vite Dev Server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| RabbitMQ | 5672/15672 | Message Queue / Management UI |

---

## Architecture Overview

```
Frontend (React 18 + TypeScript + Fetch API)
    ↓ HTTP (port 3005)
Backend (FastAPI, port 8000)
    ├─ api/v1/           # 39 API route modules
    ├─ integrations/     # 16 integration modules (see below)
    ├─ domain/           # Business logic (20 domain modules)
    └─ infrastructure/   # Database, Cache, Messaging
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Directory Structure

```
backend/src/
├── api/v1/              # 41 API route modules (~591 endpoints)
│   ├── agents, workflows, sessions, executions
│   ├── ag_ui, claude_sdk, hybrid, mcp
│   ├── orchestration, autonomous, routing
│   ├── patrol, correlation, rootcause, audit
│   ├── swarm, a2a                          # Phase 29+ A2A
│   └── auth, files, sandbox, checkpoints, etc.
├── integrations/        # 16 integration modules
│   ├── agent_framework/ # MAF Adapters (30+ builders)
│   ├── claude_sdk/      # Claude SDK (autonomous, hooks, hybrid, mcp, tools)
│   ├── ag_ui/           # AG-UI Protocol (SSE, Events, Handlers)
│   ├── hybrid/          # Hybrid MAF+SDK (context, intent, risk, switching)
│   ├── orchestration/   # Three-tier Intent Routing (Phase 28)
│   ├── swarm/           # Agent Swarm System (Phase 29)
│   ├── mcp/             # MCP servers (Azure, Filesystem, LDAP, Shell, SSH)
│   └── a2a, memory, patrol, correlation, rootcause, audit, learning, llm
├── domain/              # 20 domain modules (business logic)
├── infrastructure/      # Database, Cache, Messaging, Storage
└── core/                # Performance, Sandbox, Security utilities

frontend/src/
├── pages/               # Page components (agents, workflows, dashboard, DevUI, etc.)
├── components/          # UI components
│   ├── unified-chat/    # Main chat interface (27+ components)
│   │   └── agent-swarm/ # Agent Swarm visualization (15 components + 4 hooks, Phase 29)
│   ├── ag-ui/           # Agentic UI components (chat, hitl, advanced)
│   ├── DevUI/           # Developer tools (15 components)
│   ├── ui/              # Shadcn UI components
│   └── layout, shared, auth
├── hooks/               # Custom React hooks (17 hooks)
├── api/                 # API client (Fetch API, NOT Axios)
├── store/, stores/      # Zustand state management
├── types/               # TypeScript type definitions
└── utils/               # Utility functions
```

---

## Code Standards

All code standards are defined in `.claude/rules/` directory:

| Rule File | Scope |
|-----------|-------|
| `backend-python.md` | Python backend code |
| `frontend-react.md` | React/TypeScript frontend |
| `agent-framework.md` | Agent Framework integration layer |
| `git-workflow.md` | Git commits and branches |
| `code-quality.md` | Code quality tools (Black, ESLint, etc.) |
| `testing.md` | Testing standards |
| `azure-openai-api.md` | Azure OpenAI API usage |

### Quick Commands

```bash
# Backend quality check
cd backend && black . && isort . && flake8 . && mypy . && pytest

# Frontend quality check
cd frontend && npm run lint && npm run build
```

---

## Environment Setup

Copy `.env.example` to `.env`. Key variables:

```bash
# Database
DB_NAME=ipa_platform
DB_USER=ipa_user
DB_PASSWORD=ipa_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=             # Optional, for production

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional: Additional LLM providers (in backend/.env.example)
# ANTHROPIC_API_KEY=<key>
# OPENAI_API_KEY=<key>

# Optional: mem0 Memory System (in backend/.env.example)
# MEM0_ENABLED=false
# QDRANT_PATH=./qdrant_data
```

> **Note**: See `backend/.env.example` for full configuration including mem0 memory system settings.

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/02-architecture/technical-architecture.md` | System architecture |
| `docs/01-planning/prd/prd-main.md` | Product requirements |
| `docs/03-implementation/sprint-planning/README.md` | Sprint planning overview |
| `docs/api/ag-ui-api-reference.md` | AG-UI API Reference |
| `claudedocs/CLAUDE.md` | AI assistant execution docs index |

### V9 Codebase Analysis (2026-03-31, Latest & Most Accurate)

> **Important**: V9 supersedes all previous versions (V1-V8). Covers Phase 1-44 with 130 verification waves (9.2/10 quality score). Based on 1,028 source files (792 .py + 236 .ts/.tsx), 327,582 LOC.

**Master Index**: `docs/07-analysis/V9/00-index.md` — Start here for full navigation

| Directory | Key Files | Purpose |
|-----------|-----------|---------|
| `V9/01-architecture/` | 11 layer files (L01-L11) | **11-layer architecture deep analysis** — Frontend → API → AG-UI → Routing → Orchestration → MAF → Claude SDK → MCP → Integrations → Domain → Infrastructure |
| `V9/02-modules/` | 4 module files | Module-level analysis (4 groupings) |
| `V9/03-features/` | 2 category files | **70+ features verification** with maturity matrix |
| `V9/04-flows/` | 2 E2E files | **5 E2E user journey validations** (Chat, CRUD, Workflow, HITL, Swarm) |
| `V9/05-issues/` | issue-registry.md | **62 deduplicated issues** (8 CRITICAL, 16 HIGH, 22 MEDIUM, 16 LOW) |
| `V9/06-cross-cutting/` | 5 files | Enum registry, error handling, logging, auth, cross-cutting concerns |
| `V9/07-delta/` | 3 phase-delta files | Phase 30-44 change tracking (new files, endpoints, features per phase) |
| `V9/08-data-model/` | 2 files | ORM schema, data model analysis |
| `V9/09-api-reference/` | 1 catalog | **591 API endpoints** complete catalog |
| `V9/10-event-contracts/` | 1 spec | Event specifications and contracts |
| `V9/11-config-deploy/` | 1 file | Configuration and deployment analysis |
| `V9/12-testing/` | 1 file | Testing landscape (386 test files) |
| `V9/13-mock-real/` | 1 map | **Implementation maturity map** — mock vs real for all features |

#### V9 Usage Scenarios — What to Read When

| Scenario | Start Here | Then Read |
|----------|-----------|-----------|
| **Project Onboarding** — First time understanding the project | `V9/00-index.md` → `V9/00-stats.md` | `V9/01-architecture/` layer files top-down |
| **Bug Investigation** — Researching known issues | `V9/05-issues/issue-registry.md` | Corresponding layer file for the affected module |
| **Feature Planning** — Planning new Phase/Sprint | `V9/03-features/` + `V9/13-mock-real/` | `V9/07-delta/` to see recent phase changes |
| **Architecture Decision** — Cross-layer modifications | `V9/01-architecture/` relevant layers | `V9/04-flows/` for E2E impact analysis |
| **Security/Quality Audit** — Code review preparation | `V9/05-issues/` (8 CRITICAL issues) | `V9/06-cross-cutting/` for auth, logging, error handling |
| **API Development** — Adding/modifying endpoints | `V9/09-api-reference/` | `V9/08-data-model/` + `V9/02-modules/` |
| **Phase Delta Tracking** — What changed in Phase X | `V9/07-delta/` (Phase 30-34, 35-39, 40-44) | Combined with `git log` for complete history |
| **Testing & Deployment** — Writing tests or deploying | `V9/12-testing/` + `V9/11-config-deploy/` | `V9/06-cross-cutting/` for enum registry |

#### V9 Freshness Policy

- **Baseline**: Phase 1-44, snapshot date 2026-03-31
- **Verification Quality**: 130 waves, 9.2/10 score, ~6,860 verification points
- **Staleness**: V9 content may diverge as new Phases are developed. Numbers (file counts, endpoints, LOC) will become increasingly approximate after Phase 44
- **Update Strategy**: Consider a V10 refresh after every 5 Phases or major architectural changes. Use `git log --since="2026-03-31"` + V9 as baseline to understand delta
- **Trust Level**: Verified statistics (endpoints, enums, ORM columns) are high-confidence. Behavioral descriptions and flow narratives should be cross-checked against current source code

### V8 Codebase Analysis (2026-03-15, Archived)

> V8 reports are archived at `docs/07-analysis/Overview/full-codebase-analysis/`. V9 is the current authoritative analysis. V8 remains useful for historical comparison (Phase 1-34 baseline).

| Document | Purpose |
|----------|---------|
| `MAF-Claude-Hybrid-Architecture-V8.md` | V8 11-layer architecture (Phase 1-34 baseline) |
| `MAF-Features-Architecture-Mapping-V8.md` | V8 70+ features verification |
| `Architecture-Review-Board-Consensus-Report.md` | Architecture Review Board consensus |
| `phase4-validation/` | V8 cross-validation reports |
| `sdk-version-gap/` | MAF & Claude SDK version gap analysis + MAF RC4 Upgrade Master Plan |

---

## ClaudeDocs - AI Assistant Execution Docs

> **Important**: The `claudedocs/` directory contains dynamic execution documentation produced collaboratively by AI assistants and the development team, managed separately from the design docs in `docs/`.

### Directory Structure

```
claudedocs/
├── 1-planning/          # Overall planning (epics, architecture, features)
├── 2-sprints/           # Sprint execution docs
├── 3-progress/          # Progress tracking (daily, weekly, milestones)
├── 4-changes/           # Change records (bug-fixes, feature-changes)
├── 5-status/            # Status reports (phase-reports, testing)
├── 6-ai-assistant/      # AI assistant related (prompts, analysis)
├── 7-archive/           # Historical archive
├── CLAUDE.md            # Detailed directory index
└── README.md            # Quick navigation
```

### AI Assistant Situation Prompts (SITUATION)

Use the corresponding prompt template based on current work context:

| Situation | Document | When to Use |
|-----------|----------|-------------|
| **SITUATION-1** | `6-ai-assistant/prompts/SITUATION-1-PROJECT-ONBOARDING.md` | Project onboarding, first contact |
| **SITUATION-2** | `6-ai-assistant/prompts/SITUATION-2-FEATURE-DEV-PREP.md` | Feature development preparation |
| **SITUATION-3** | `6-ai-assistant/prompts/SITUATION-3-FEATURE-ENHANCEMENT.md` | Feature enhancement or fixes |
| **SITUATION-4** | `6-ai-assistant/prompts/SITUATION-4-NEW-FEATURE-DEV.md` | New feature development execution |
| **SITUATION-5** | `6-ai-assistant/prompts/SITUATION-5-SAVE-PROGRESS.md` | Save progress, end session |
| **SITUATION-6** | `6-ai-assistant/prompts/SITUATION-6-SERVICE-STARTUP.md` | Service startup, environment check |
| **SITUATION-7** | `6-ai-assistant/prompts/SITUATION-7-NEW-ENV-SETUP.md` | New development environment setup |

### Change Record Conventions

When fixing bugs or implementing feature changes, create corresponding docs in `claudedocs/4-changes/`:

| Type | Directory | Naming Format | Example |
|------|-----------|---------------|---------|
| Bug Fix | `4-changes/bug-fixes/` | `FIX-XXX-description.md` | `FIX-001-hitl-approval-wrong-id-type.md` |
| Feature Change | `4-changes/feature-changes/` | `CHANGE-XXX-description.md` | `CHANGE-001-hitl-inline-approval-card.md` |
| Refactoring | `4-changes/refactoring/` | `REFACTOR-XXX-description.md` | `REFACTOR-001-api-structure.md` |

### Daily Workflow

1. **Before starting work**: Check `claudedocs/3-progress/daily/` for latest logs
2. **Fixing bugs**: Create FIX doc in `claudedocs/4-changes/bug-fixes/`
3. **Feature changes**: Create CHANGE doc in `claudedocs/4-changes/feature-changes/`
4. **End of session**: Use SITUATION-5 to save progress

### Detailed Guide

- Full directory index: `claudedocs/CLAUDE.md`
- Quick navigation: `claudedocs/README.md`
- Naming conventions and format templates: see `claudedocs/CLAUDE.md`

---

## Developer Preferences

### Communication
- **Language**: Respond in Traditional Chinese (for user communication)
- **Documentation**: Use English for all CLAUDE.md files
- **Detail Level**: Provide detailed explanations with reasoning
- **Confirmation**: Ask before destructive operations

### Code Style
- **Comments**: English for code comments
- **Git Commit**: Commit only when feature is complete
- **Testing**: New features must include unit tests

### Behavior Rules
- **Proactive Assistance**: Actively participate in development
- **Ask Before Acting**: When uncertain, always ask first
- **Deep Error Analysis**: Analyze root cause thoroughly
- **Never Delete Tests**: Do not delete or skip tests to solve problems
- **Never Delete Docs**: Do not delete documentation without asking
- **Never Delete Checklist Items**: When updating checklists, only change `[ ]` to `[x]`. Never remove unchecked items — they represent pending work. Violation occurred in Phase 42 Sprint 147.
- **Check Existing Before Building**: Before creating new infrastructure (SSE, tools, memory), verify MAF/AG-UI/Claude SDK doesn't already provide it. Violation occurred in Phase 42 Sprint 145.

---

## CRITICAL: Sprint Execution Workflow

> **This rule is mandatory for all sprint work. Violation occurred in Phase 35-38 (Sprint 107-120) and must never be repeated.**

Every sprint MUST follow this workflow in order:

### Step 1: Create Plan File
Before writing ANY code, create `docs/03-implementation/sprint-planning/phase-XX/sprint-XXX-plan.md`:
- User Stories (作為/我希望/以便 format)
- Technical specifications
- File change list
- Acceptance criteria

### Step 2: Create Checklist File
Create `docs/03-implementation/sprint-planning/phase-XX/sprint-XXX-checklist.md`:
- Checkbox items (`- [ ]`) for every deliverable
- Verification criteria
- Links to plan file

### Step 3: Implement Code
Only after plan + checklist exist, begin coding.

### Step 4: Update Checklist
As work progresses, mark items `[x]` in the checklist.

### Step 5: Create Progress Doc
Create `docs/03-implementation/sprint-execution/sprint-XXX/progress.md` with execution details.

### Correct Flow
```
Phase README → Sprint Plan → Sprint Checklist → Code → Update Checklist → Progress Doc
```

### WRONG Flow (what happened in Phase 35-38)
```
Phase README → Code → Progress Doc  (SKIPPED plan + checklist)
```

Reference existing examples: `docs/03-implementation/sprint-planning/phase-29/sprint-100-plan.md` and `sprint-100-checklist.md`

---

## CRITICAL: Microsoft Agent Framework API Usage

> **This is the most important rule for this project.**

When developing in `backend/src/integrations/agent_framework/builders/`:

### MUST Do

1. **Import official classes from `agent_framework`**
2. **Create official Builder instance**: `self._builder = OfficialBuilder()`
3. **Call official Builder in build()**: `return self._builder.build()`

### DO NOT

- Create custom implementation without `agent_framework` imports
- Skip `from agent_framework import ...` statements
- Implement similar functionality without calling official API

### Verification

```bash
cd backend && python scripts/verify_official_api_usage.py
# All 5 checks must pass
```

See `.claude/rules/agent-framework.md` for detailed rules.

---

## Important Notes

1. **Agent Framework is Preview**: API may change. Reference docs in `reference/agent-framework/`

2. **Target Market**: Taiwan/Hong Kong. Technical terms in English, user-facing content in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

---

**Last Updated**: 2026-03-31
**Project Start**: 2025-11-14
**Status**: Phase 44 Completed (152+ Sprints completed)
**Total Story Points**: ~2500+ pts across 44 phases
**V9 Analysis**: `docs/07-analysis/V9/00-index.md` (1,028 files, 327,582 LOC, 9.2/10 quality)

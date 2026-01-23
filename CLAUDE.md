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

## Project Overview

**IPA Platform** (Intelligent Process Automation) - Enterprise AI Agent orchestration platform

| Attribute | Value |
|-----------|-------|
| **Core Framework** | Microsoft Agent Framework + Claude Agent SDK + AG-UI Protocol |
| **Current Status** | Phase 28 Completed - Three-tier Intent Routing |
| **Completed** | 28 Phases, 99 Sprints, 2189 Story Points |
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
    ├─ api/v1/           # 38 API route modules
    ├─ integrations/     # 15 integration modules (see below)
    ├─ domain/           # Business logic (20 domain modules)
    └─ infrastructure/   # Database, Cache, Messaging
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Directory Structure

```
backend/src/
├── api/v1/              # 38 API route modules
│   ├── agents, workflows, sessions, executions
│   ├── ag_ui, claude_sdk, hybrid, mcp
│   ├── orchestration, autonomous, routing
│   ├── patrol, correlation, rootcause, audit
│   └── auth, files, sandbox, checkpoints, etc.
├── integrations/        # 15 integration modules
│   ├── agent_framework/ # MAF Adapters (30+ builders)
│   ├── claude_sdk/      # Claude SDK (autonomous, hooks, hybrid, mcp, tools)
│   ├── ag_ui/           # AG-UI Protocol (SSE, Events, Handlers)
│   ├── hybrid/          # Hybrid MAF+SDK (context, intent, risk, switching)
│   ├── orchestration/   # Three-tier Intent Routing (Phase 28)
│   ├── mcp/             # MCP servers (Azure, Filesystem, LDAP, Shell, SSH)
│   └── memory, patrol, correlation, rootcause, audit, learning, llm
├── domain/              # 20 domain modules (business logic)
├── infrastructure/      # Database, Cache, Messaging, Storage
└── core/                # Performance, Sandbox, Security utilities

frontend/src/
├── pages/               # Page components (agents, workflows, dashboard, DevUI, etc.)
├── components/          # UI components
│   ├── unified-chat/    # Main chat interface (25+ components)
│   ├── ag-ui/           # Agentic UI components (chat, hitl, advanced)
│   ├── ui/              # Shadcn UI components
│   └── layout, shared, auth, DevUI
├── hooks/               # Custom React hooks (14+ hooks)
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

**Last Updated**: 2026-01-23
**Project Start**: 2025-11-14
**Status**: Phase 28 Completed (99 Sprints completed)
**Total Story Points**: 2189 pts across 28 phases

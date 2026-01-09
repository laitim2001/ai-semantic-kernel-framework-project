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
| **Current Phase** | Phase 20 - File Attachment Support (Sprints 75-76) |
| **Completed** | Phase 1-19 (74 Sprints, 1665 pts) |
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
Frontend (React 18 + TypeScript)
    ↓ HTTPS (port 3005)
Backend (FastAPI, port 8000)
    ├─ api/v1/           # 20+ API route modules
    ├─ integrations/     # MAF + Claude SDK + MCP
    ├─ domain/           # Business logic
    └─ infrastructure/   # Database, Cache, Messaging
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Directory Structure

```
backend/src/
├── api/v1/              # API routes (agents, workflows, sessions, ag-ui, claude_sdk)
├── integrations/        # Framework integrations
│   ├── agent_framework/ # MAF Adapters (GroupChat, Handoff, Concurrent, etc.)
│   ├── claude_sdk/      # Claude SDK (Client, Tools, Hooks, MCP)
│   └── ag_ui/           # AG-UI Protocol (SSE, Events, Handlers)
├── domain/              # Business logic (agents, workflows, sessions)
└── infrastructure/      # Database, Cache, Messaging

frontend/src/
├── pages/               # Page components
├── components/          # Reusable UI components
├── hooks/               # Custom React hooks
├── api/                 # API client
└── store/               # Zustand state management
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

Copy `.env.example` to `.env`:

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

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/02-architecture/technical-architecture.md` | System architecture |
| `docs/01-planning/prd/prd-main.md` | Product requirements |
| `docs/03-implementation/sprint-planning/README.md` | Sprint planning overview |
| `docs/03-implementation/sprint-planning/phase-20/README.md` | Current phase |
| `docs/api/ag-ui-api-reference.md` | AG-UI API Reference |

---

## Developer Preferences

### Communication
- **Language**: Respond in Traditional Chinese
- **Detail Level**: Provide detailed explanations with reasoning
- **Confirmation**: Ask before destructive operations

### Code Style
- **Comments**: Mixed mode - important explanations in Chinese, short comments in English
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

2. **Chinese Documentation**: Target market is Taiwan/Hong Kong. Technical terms in English, comments in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

---

**Last Updated**: 2026-01-09
**Project Start**: 2025-11-14
**Status**: Phase 20 In Progress (74 Sprints completed)
**Total Story Points**: 1699 pts across 20 phases

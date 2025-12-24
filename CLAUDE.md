# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**IPA Platform** (Intelligent Process Automation) is an enterprise-grade AI Agent orchestration platform built on **Microsoft Agent Framework**.

- **Core Framework**: Microsoft Agent Framework (Preview) - unifies Semantic Kernel + AutoGen
- **Target Users**: Mid-size enterprises (500-2000 employees)
- **Status**: **Phase 11 Complete** - Agent-Session Integration - UAT Verified (4/4 scenarios passed)
- **Architecture**: Full official Agent Framework API integration (>95% API coverage)
- **Stats**: 3500+ tests, 310+ API routes, 25+ production-ready adapters
- **Phases Completed**: Phase 1-11 (Sprints 1-47)

---

## Development Commands

### Local Development

```bash
# Start all services (PostgreSQL, Redis, RabbitMQ, n8n)
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Stop services
docker-compose down -v
```

### Backend (Python FastAPI)

```bash
cd backend/

# Run backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Code Quality
black .                              # Format
isort .                              # Sort imports
flake8 .                             # Lint
mypy .                               # Type check

# Testing
pytest                               # All tests
pytest tests/unit/                   # Unit tests only
pytest tests/unit/test_agent_service.py::test_function  # Single test
pytest -v --cov=src                  # With coverage
```

### Frontend (React/TypeScript)

```bash
cd frontend/

# Install dependencies
npm install

# Run dev server
npm run dev

# Build
npm run build
```

### Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U ipa_user -d ipa_platform

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

---

## Architecture

### System Overview

```
Frontend (React 18 + TypeScript)
    ↓ HTTPS (port 3000)
Backend (FastAPI, port 8000)
    ├─ 15 API Modules (agents, workflows, executions, ...)
    ├─ Domain Services (state machine, checkpoints, routing)
    └─ Infrastructure (database, cache, messaging)
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Backend Architecture

```
backend/src/
├── api/v1/              # 20+ API route modules
│   ├── agents/          # Agent CRUD and configuration
│   ├── workflows/       # Workflow management
│   ├── executions/      # Execution lifecycle
│   ├── sessions/        # 🆕 Phase 11: Session-based conversations
│   ├── groupchat/       # GroupChat orchestration (→ Adapter)
│   ├── handoff/         # Agent handoff (→ Adapter)
│   ├── concurrent/      # Concurrent execution (→ Adapter)
│   ├── nested/          # Nested workflows (→ Adapter)
│   ├── planning/        # Dynamic planning (→ Adapter)
│   ├── code_interpreter/ # 🆕 Phase 8: Code execution
│   └── ...
│
├── integrations/        # 🔑 Official API Integration Layer (Phase 4)
│   └── agent_framework/
│       ├── builders/    # Adapter implementations
│       │   ├── groupchat.py      # GroupChatBuilderAdapter
│       │   ├── handoff.py        # HandoffBuilderAdapter
│       │   ├── concurrent.py     # ConcurrentBuilderAdapter
│       │   ├── nested_workflow.py # NestedWorkflowAdapter
│       │   ├── planning.py       # PlanningAdapter
│       │   └── magentic.py       # MagenticBuilderAdapter
│       ├── multiturn/   # MultiTurnAdapter + CheckpointStorage
│       └── memory/      # Memory storage adapters
│
├── domain/              # Business logic
│   ├── agents/          # Agent service
│   ├── workflows/       # Workflow service + state machine
│   ├── executions/      # Execution state machine
│   ├── sessions/        # 🆕 Phase 11: Agent-Session integration
│   │   ├── models.py    # Session, Message, ToolCall models
│   │   ├── service.py   # SessionService
│   │   ├── events.py    # SessionEventPublisher
│   │   ├── executor.py  # AgentExecutor (LLM interaction)
│   │   ├── streaming.py # StreamingHandler (SSE)
│   │   └── tool_handler.py # ToolCallHandler
│   └── orchestration/   # ⚠️ Deprecated - use adapters
│
├── infrastructure/      # External integrations
│   ├── database/        # SQLAlchemy models, repositories
│   ├── cache/           # Redis + LLM caching
│   └── messaging/       # RabbitMQ integration
│
└── core/               # Cross-cutting concerns
    ├── config.py       # Settings management
    └── performance/    # Performance monitoring
```

### Key Adapters (Phase 4-11)

| Adapter | Purpose | Official API |
|---------|---------|--------------|
| `GroupChatBuilderAdapter` | Multi-agent chat | `GroupChatBuilder` |
| `HandoffBuilderAdapter` | Agent handoff | `HandoffBuilder` |
| `ConcurrentBuilderAdapter` | Parallel execution | `ConcurrentBuilder` |
| `NestedWorkflowAdapter` | Nested workflows | `WorkflowExecutor` |
| `PlanningAdapter` | Task planning | `MagenticBuilder` |
| `MultiTurnAdapter` | Conversation state | `CheckpointStorage` |
| `SessionAgentBridge` | Agent-Session integration | `AgentExecutor` |
| `CodeInterpreterAdapter` | Code execution | `Responses API` |

### Frontend Architecture

```
frontend/src/
├── pages/              # 7 main pages
│   ├── Dashboard.tsx
│   ├── Workflows.tsx
│   ├── Agents.tsx
│   ├── Executions.tsx
│   ├── Templates.tsx
│   ├── Analytics.tsx
│   └── Settings.tsx
│
├── components/         # Reusable UI components
├── api/               # API client
├── store/             # Zustand state management
├── hooks/             # Custom React hooks
└── types/             # TypeScript definitions
```

### Key Design Patterns

1. **Adapter Pattern** (Phase 4): All orchestration via official Agent Framework adapters
2. **Execution State Machine**: Workflows go through states (pending → running → waiting_approval → completed/failed)
3. **Checkpoint System**: Human-in-the-loop approvals with timeout and escalation
4. **LLM Cache**: Redis-based caching for repeated LLM calls
5. **Connector Pattern**: Pluggable external system integrations (ServiceNow, Dynamics 365)

---

## Code Standards

### Python
- **Formatter**: Black (line-length: 100)
- **Import Sorter**: isort (profile: black)
- **Type Checker**: mypy (strict mode)
- **Test Coverage**: >= 80%

### TypeScript
- **Formatter**: Prettier
- **Linter**: ESLint
- **UI Framework**: Shadcn UI + Tailwind CSS

### Git Commit Format
```
<type>(<scope>): <description>

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

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
REDIS_PASSWORD=redis_password

# Azure OpenAI (for Agent Framework)
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
| `claudedocs/AI-ASSISTANT-INSTRUCTIONS.md` | AI workflow instructions |

---

## AI Assistant System

This project includes AI-assisted development workflows in `claudedocs/`:

### Quick Reference
- **PROMPT-01**: Project onboarding
- **PROMPT-04**: Development execution
- **PROMPT-06**: Progress save (most used)
- **PROMPT-09**: Session end

### Usage
```bash
# Start development task
"@claudedocs/prompts/PROMPT-04-SPRINT-DEVELOPMENT.md add-user-profile-api"

# Save progress
"@claudedocs/prompts/PROMPT-06-PROGRESS-SAVE.md"
```

Full instructions: `claudedocs/AI-ASSISTANT-INSTRUCTIONS.md`

---

## Developer Preferences

### Communication
- **Language**: Respond in Traditional Chinese
- **Detail Level**: Provide detailed explanations including reasoning and alternatives
- **Confirmation**: Ask before destructive operations (delete, refactor, etc.)

### Code Style
- **Comments**: Mixed mode - important explanations in Chinese, short comments in English
- **Git Commit**: Commit only when feature is complete, avoid small scattered commits
- **Testing**: New features must include unit tests

### Behavior Rules
- ✅ **Proactive Assistance**: Actively participate in development, suggest improvements when found
- ✅ **Ask Before Acting**: When uncertain, always ask before executing
- ✅ **Deep Error Analysis**: Analyze root cause thoroughly, provide multiple solutions
- ❌ **Never Delete Tests**: Do not delete or skip tests to solve problems
- ❌ **Never Delete Docs**: Do not delete documentation files without asking first

### Developer Context
- **Skill Level**: Full Stack (proficient in both frontend and backend)
- **Dependencies**: May introduce new dependencies if they significantly improve efficiency

---

## CRITICAL: Microsoft Agent Framework API Usage

**This is the most important rule for this project.**

### MUST Use Official API

When developing in `backend/src/integrations/agent_framework/builders/`, you **MUST**:

1. **Import official classes from `agent_framework`**:
```python
from agent_framework import (
    ConcurrentBuilder,      # for concurrent.py
    GroupChatBuilder,       # for groupchat.py
    HandoffBuilder,         # for handoff.py
    MagenticBuilder,        # for magentic.py
    WorkflowExecutor,       # for workflow_executor.py
)
```

2. **Use official Builder instance in adapter class**:
```python
class XxxBuilderAdapter:
    def __init__(self, ...):
        self._builder = OfficialBuilder()  # MUST have this line
```

3. **Call official Builder in build() method**:
```python
def build(self) -> Workflow:
    return self._builder.participants(...).build()  # MUST call official API
```

### DO NOT

- ❌ Do NOT create your own implementation without using `agent_framework` imports
- ❌ Do NOT skip `from agent_framework import ...` statements
- ❌ Do NOT implement similar functionality without calling official API

### Verification

Before completing any adapter work, run:
```bash
cd backend
python scripts/verify_official_api_usage.py
```

All checks must pass (5/5).

### Reference

- Official source code: `reference/agent-framework/python/packages/core/agent_framework/`
- Workflow checklist: `docs/03-implementation/sprint-planning/phase-3/SPRINT-WORKFLOW-CHECKLIST.md`

---

## Important Notes

1. **Agent Framework is Preview**: API may change. Reference docs in `reference/agent-framework/`

2. **Chinese Documentation**: Target market is Taiwan/Hong Kong. Technical terms in English, comments in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

4. **No sprint-status.yaml**: This file was removed. Use `bmm-workflow-status.yaml` for workflow tracking.

---

**Last Updated**: 2025-12-24
**Project Start**: 2025-11-14
**Status**: Phase 11 Complete (47 Sprints) - Agent-Session Integration UAT Verified

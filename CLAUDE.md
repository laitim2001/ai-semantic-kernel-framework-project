# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**IPA Platform** (Intelligent Process Automation) is an enterprise-grade AI Agent orchestration platform built on **Microsoft Agent Framework**.

- **Core Framework**: Microsoft Agent Framework (Preview) - unifies Semantic Kernel + AutoGen
- **Target Users**: Mid-size enterprises (500-2000 employees)
- **Status**: **MVP Complete** - 285/285 story points across 6 Sprints
- **Stats**: 812 tests, 155 API routes, 15 domain modules

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
├── api/v1/              # 15 API route modules
│   ├── agents/          # Agent CRUD and configuration
│   ├── workflows/       # Workflow management
│   ├── executions/      # Execution lifecycle
│   ├── checkpoints/     # Human-in-the-loop approvals
│   ├── connectors/      # External system integrations
│   ├── triggers/        # Workflow trigger definitions
│   ├── routing/         # Intelligent task routing
│   ├── templates/       # Workflow templates
│   ├── prompts/         # Prompt management
│   ├── learning/        # Few-shot learning
│   ├── notifications/   # Teams/email notifications
│   ├── audit/           # Audit logging
│   ├── cache/           # LLM response caching
│   ├── devtools/        # Developer utilities
│   └── versioning/      # Version control
│
├── domain/              # Business logic services
│   ├── agents/          # Agent service
│   ├── workflows/       # Workflow service + state machine
│   ├── executions/      # Execution state machine
│   ├── checkpoints/     # Checkpoint storage
│   └── ...
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

1. **Execution State Machine**: Workflows go through states (pending → running → waiting_approval → completed/failed)
2. **Checkpoint System**: Human-in-the-loop approvals with timeout and escalation
3. **LLM Cache**: Redis-based caching for repeated LLM calls
4. **Connector Pattern**: Pluggable external system integrations (ServiceNow, Dynamics 365)

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
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
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

## Important Notes

1. **Agent Framework is Preview**: API may change. Reference docs in `reference/agent-framework/`

2. **Chinese Documentation**: Target market is Taiwan/Hong Kong. Technical terms in English, comments in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

4. **No sprint-status.yaml**: This file was removed. Use `bmm-workflow-status.yaml` for workflow tracking.

---

**Last Updated**: 2025-12-01
**Project Start**: 2025-11-14
**Status**: MVP Complete (285/285 points, 6 Sprints)

# Backend - FastAPI Application

> IPA Platform backend service, based on Python FastAPI framework

---

## Quick Reference

```bash
# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Code quality
black .                 # Format code
isort .                 # Sort imports
flake8 .                # Lint
mypy .                  # Type check

# Testing
pytest                  # All tests
pytest tests/unit/      # Unit tests only
pytest tests/e2e/       # E2E tests
pytest tests/performance/ # Performance tests
pytest -v --cov=src     # With coverage
```

---

## Architecture Overview

```
backend/
├── main.py                 # FastAPI entry point (47 registered routers)
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
│
├── src/                    # Source code (~630+ .py files)
│   ├── api/v1/             # 39 API route modules (~540 endpoints)
│   ├── domain/             # 20 business logic modules
│   ├── infrastructure/     # Database, Cache (messaging/storage stubs)
│   ├── integrations/       # 15 integration modules (216 .py files)
│   └── core/               # Performance, Sandbox, Security utilities
│
├── tests/                  # Test suite (~303 test files)
│   ├── unit/               # Unit tests (~241 files)
│   ├── integration/        # Integration tests (~24 files)
│   ├── e2e/                # End-to-end tests (~19 files)
│   ├── performance/        # Performance benchmarks (~10 files)
│   ├── security/           # Security tests (~5 files)
│   ├── load/               # Load tests (~2 files)
│   ├── mocks/              # Shared mock objects (~2 files)
│   └── conftest.py         # Pytest fixtures
│
└── scripts/                # Utility scripts
    ├── verify_official_api_usage.py
    └── verify_env.py
```

---

## Layer Responsibilities

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **API** | `src/api/` | HTTP routes, request/response handling |
| **Domain** | `src/domain/` | Business logic, state machines |
| **Infrastructure** | `src/infrastructure/` | Database, cache, messaging |
| **Integrations** | `src/integrations/` | 15 modules: MAF, Claude SDK, AG-UI, Hybrid, MCP, Swarm, etc. |
| **Core** | `src/core/` | Config + 3 subsystems (performance, sandbox, security) |

### Data Flow

```
HTTP Request
    ↓
API Layer (FastAPI Router)
    ↓
Domain Layer (Service)
    ↓
Infrastructure Layer (Repository/Cache)
    ↓
Database/External Service
```

### Core Subsystems (`src/core/`)

```
core/
├── config.py               # Application configuration
├── sandbox_config.py       # Sandbox configuration
├── performance/            # Performance optimization (8 files)
│   ├── benchmark.py, cache_optimizer.py, concurrent_optimizer.py
│   ├── db_optimizer.py, metric_collector.py, middleware.py
│   ├── optimizer.py, profiler.py
├── sandbox/                # Sandbox execution (7 files)
│   ├── adapter.py, config.py, ipc.py
│   ├── orchestrator.py, worker.py, worker_main.py
└── security/               # Security utilities (4 files)
    ├── audit_report.py, jwt.py, password.py
```

### Integration Modules (`src/integrations/`)

| Module | Files | Purpose |
|--------|-------|---------|
| `agent_framework/` | 50 | MAF Adapters (builders, memory, multiturn, tools) |
| `claude_sdk/` | 44 | Claude SDK (autonomous, hooks, hybrid, mcp, tools) |
| `hybrid/` | 25 | Hybrid MAF+SDK (context, intent, risk, switching) |
| `orchestration/` | 21 | Three-tier Intent Routing (Phase 28) |
| `ag_ui/` | 18 | AG-UI Protocol (SSE, events, features) |
| `mcp/` | 12 | MCP Servers (Azure, Filesystem, LDAP, Shell, SSH) |
| `patrol/` | 10 | Continuous monitoring (Phase 23) |
| `swarm/` | 6 | Agent Swarm System (Phase 29) |
| `llm/` | 6 | LLM client integration |
| `memory/` | 5 | mem0 memory system |
| `learning/` | 5 | Few-shot learning |
| `audit/` | 4 | Audit integration |
| `correlation/` | 4 | Multi-agent event correlation |
| `a2a/` | 3 | Agent-to-Agent protocol |
| `rootcause/` | 3 | Root cause analysis |

---

## Code Standards

### Python Style

- **Formatter**: Black (line-length: 100)
- **Import Sorter**: isort (profile: black)
- **Type Checker**: mypy (strict mode)
- **Linter**: flake8

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Files | snake_case | `agent_service.py` |
| Classes | PascalCase | `AgentService` |
| Functions | snake_case | `get_agent_by_id()` |
| Constants | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| Private | _prefix | `_internal_method()` |

### Import Order

```python
# 1. Standard library
import os
from typing import Dict, List, Optional

# 2. Third-party packages
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# 3. Local imports
from src.core.config import settings
from src.domain.agents.service import AgentService
```

---

## API Design Rules

### Route Naming

| Operation | HTTP Method | Route Pattern |
|-----------|-------------|---------------|
| List | GET | `/api/v1/{resources}` |
| Get | GET | `/api/v1/{resources}/{id}` |
| Create | POST | `/api/v1/{resources}` |
| Update | PUT | `/api/v1/{resources}/{id}` |
| Delete | DELETE | `/api/v1/{resources}/{id}` |
| Action | POST | `/api/v1/{resources}/{id}/{action}` |

### Response Format

```python
# Success response
{
    "data": {...},
    "message": "Success"
}

# Error response
{
    "error": "ERROR_CODE",
    "message": "Human readable message",
    "details": {...}
}

# List response
{
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
}
```

---

## Critical Rules

### Agent Framework Integration

When working in `src/integrations/agent_framework/`:
- **MUST** import from `agent_framework` package
- **MUST** use Adapter pattern
- **MUST** run `python scripts/verify_official_api_usage.py`

See: `src/integrations/agent_framework/CLAUDE.md`

### Orchestration Module (Phase 28)

When working in `src/integrations/orchestration/`:

**Three-tier Intent Routing System**:
```
Layer 1: PatternMatcher (< 10ms) - Rule-based, regex matching
Layer 2: SemanticRouter (< 100ms) - Vector similarity
Layer 3: LLMClassifier (< 2000ms) - Claude Haiku fallback
```

**Core Components**:
| Component | Location | Purpose |
|-----------|----------|---------|
| BusinessIntentRouter | `intent_router/router.py` | Three-tier routing coordinator |
| GuidedDialogEngine | `guided_dialog/engine.py` | Multi-turn dialog guidance |
| InputGateway | `input_gateway/gateway.py` | Multi-source input processing |
| RiskAssessor | `risk_assessor/assessor.py` | Risk assessment |
| HITLController | `hitl/controller.py` | Human-in-the-loop approval |
| Metrics | `metrics.py` | OpenTelemetry monitoring |

**Quick Usage**:
```python
from src.integrations.orchestration import (
    BusinessIntentRouter,
    create_mock_router,
    ITIntentCategory,
    RoutingDecision,
)

# Create router
router = create_mock_router()

# Route user input
decision = await router.route("ETL Pipeline failed")
print(decision.intent_category)  # ITIntentCategory.INCIDENT
print(decision.routing_layer)    # "pattern"
```

See: `docs/03-implementation/sprint-planning/phase-28/ARCHITECTURE.md`

### Agent Swarm System (Phase 29)

When working in `src/integrations/swarm/`:

**Core Components**:
| Component | Location | Purpose |
|-----------|----------|---------|
| SwarmManager | `manager.py` | Swarm lifecycle and coordination |
| WorkerAgent | `worker.py` | Individual worker execution |
| SwarmEvents | `events/` | SSE event streaming |

**API Routes**: `src/api/v1/swarm/`
- `routes.py` — Swarm status API (3 endpoints)
- `demo.py` — Swarm demo/test API with SSE (5 endpoints)

**Frontend**: `frontend/src/components/unified-chat/agent-swarm/` (17 components)

### Testing Requirements

- New features **MUST** include unit tests
- Test coverage **MUST** be >= 80%
- Never delete or skip tests to make CI pass

### Database Operations

- Use SQLAlchemy ORM, not raw SQL
- Always use transactions for multi-step operations
- Repository pattern for data access

---

## Development Workflow

### Adding a New API Endpoint

1. Create/update route in `src/api/v1/{module}/routes.py`
2. Add service method in `src/domain/{module}/service.py`
3. Add repository method if needed
4. Write unit tests in `tests/unit/`
5. Update API documentation

### Adding a New Adapter

1. Create adapter in `src/integrations/agent_framework/builders/`
2. Import official class from `agent_framework`
3. Follow Adapter pattern template
4. Run verification script
5. Add tests

---

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ipa_platform
DB_USER=ipa_user
DB_PASSWORD=ipa_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
AZURE_OPENAI_API_KEY=xxx
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Debugging Tips

### Common Issues

1. **Import errors**: Check virtual environment activation
2. **Database connection**: Verify PostgreSQL is running
3. **Redis errors**: Check Redis service status
4. **API 500 errors**: Check logs in terminal

### Logging

```python
from src.core.logging import get_logger

logger = get_logger(__name__)
logger.info("Operation completed")
logger.error("Error occurred", exc_info=True)
```

---

**Last Updated**: 2026-02-09

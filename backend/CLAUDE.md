# Backend - FastAPI Application

> IPA Platform 後端服務，基於 Python FastAPI 框架

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
pytest -v --cov=src     # With coverage
```

---

## Architecture Overview

```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project configuration
│
├── src/                    # Source code
│   ├── api/                # REST API routes (FastAPI routers)
│   ├── domain/             # Business logic services
│   ├── infrastructure/     # External integrations (DB, cache, messaging)
│   ├── integrations/       # Agent Framework adapters (CRITICAL)
│   └── core/               # Cross-cutting concerns
│
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest fixtures
│
└── scripts/                # Utility scripts
    └── verify_official_api_usage.py
```

---

## Layer Responsibilities

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| **API** | `src/api/` | HTTP routes, request/response handling |
| **Domain** | `src/domain/` | Business logic, state machines |
| **Infrastructure** | `src/infrastructure/` | Database, cache, messaging |
| **Integrations** | `src/integrations/` | Agent Framework adapters |
| **Core** | `src/core/` | Config, logging, shared utilities |

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

**Last Updated**: 2025-12-18

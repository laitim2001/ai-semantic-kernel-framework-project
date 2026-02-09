# API Layer

> FastAPI routing layer — 39 route modules, ~540 endpoints, 47 registered routers

---

## Directory Structure

```
api/v1/
├── __init__.py             # Router aggregation (47 routers registered)
├── dependencies.py         # Shared dependencies (auth, DB, etc.)
│
│  # Phase 1: Foundation (17 modules)
├── agents/                 # Agent CRUD and management
├── workflows/              # Workflow CRUD and validation
├── executions/             # Execution tracking and state management
├── checkpoints/            # Human-in-the-loop checkpoint management
├── templates/              # Workflow template marketplace
├── triggers/               # Webhook trigger management (n8n)
├── connectors/             # Cross-system connector management
├── routing/                # Cross-scenario routing and decision logic
├── notifications/          # Teams and notification integration
├── audit/                  # Audit logging + decision audit (2 route files)
├── cache/                  # LLM response caching management
├── prompts/                # Prompt template management
├── learning/               # Few-shot learning mechanism
├── devtools/               # Execution tracing and debugging tools
├── dashboard/              # Dashboard analytics
├── versioning/             # Template version management
├── performance/            # Performance monitoring and optimization
│
│  # Phase 2: Advanced Orchestration (5 modules)
├── concurrent/             # Concurrent execution (Fork-Join)
├── handoff/                # Agent handoff and collaboration
├── groupchat/              # GroupChat multi-turn conversations
├── planning/               # Dynamic planning and autonomous decisions
├── nested/                 # Nested workflows and advanced orchestration
│
│  # Phase 8-10: Code Interpreter + MCP + Sessions
├── code_interpreter/       # Code execution and interpretation
├── mcp/                    # MCP server management and tool discovery
├── sessions/               # Session mode, multi-turn, WebSocket
│
│  # Phase 12: Claude Agent SDK (7 route files)
├── claude_sdk/             # Claude SDK integration
│   ├── routes.py           # Core SDK (6 endpoints)
│   ├── autonomous_routes.py # Autonomous execution (7 endpoints)
│   ├── hooks_routes.py     # Hook lifecycle (6 endpoints)
│   ├── hybrid_routes.py    # Hybrid context (5 endpoints)
│   ├── intent_routes.py    # Intent classification (6 endpoints)
│   ├── mcp_routes.py       # MCP integration (6 endpoints)
│   └── tools_routes.py     # Tool management (4 endpoints)
│
│  # Phase 13-14: Hybrid MAF+Claude SDK (4 route files)
├── hybrid/                 # Hybrid bridge
│   ├── context_routes.py   # Context synchronization
│   ├── core_routes.py      # Core hybrid operations
│   ├── risk_routes.py      # Risk assessment
│   └── switch_routes.py    # Mode switching
│
│  # Phase 15: AG-UI Protocol
├── ag_ui/                  # Agentic UI SSE streaming (25 endpoints)
│
│  # Phase 18-22: Platform Features
├── auth/                   # Authentication and authorization
├── files/                  # File upload and attachment management
├── memory/                 # Memory system (semantic, episodic, procedural)
├── sandbox/                # Sandbox security and isolated execution
├── autonomous/             # Autonomous decision-making and planning
│
│  # Phase 23: Observability
├── a2a/                    # Agent-to-Agent communication protocol
├── patrol/                 # Patrol mode for continuous monitoring
├── correlation/            # Multi-agent event correlation analysis
├── rootcause/              # Root cause analysis for incidents
│
│  # Phase 28: Three-tier Intent Routing (4 route files)
├── orchestration/          # Intent routing system
│   ├── routes.py           # Policy management (9 endpoints)
│   ├── intent_routes.py    # Intent classification (18 endpoints)
│   ├── dialog_routes.py    # Guided dialog (4 endpoints)
│   └── approval_routes.py  # HITL approval (4 endpoints)
│
│  # Phase 29: Agent Swarm (2 route files)
└── swarm/                  # Agent swarm visualization
    ├── routes.py           # Swarm status API (3 endpoints)
    └── demo.py             # Swarm demo/test API with SSE (5 endpoints)
```

---

## Complete Route Module Inventory

### Phase 1: Foundation

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `agents/` | 6 | Agent CRUD and management |
| `workflows/` | 9 | Workflow CRUD and validation |
| `executions/` | 11 | Execution tracking and state management |
| `checkpoints/` | 10 | HITL checkpoint management |
| `templates/` | 11 | Workflow template marketplace |
| `triggers/` | 8 | Webhook trigger management |
| `connectors/` | 9 | Cross-system connector management |
| `routing/` | 14 | Cross-scenario routing |
| `notifications/` | 11 | Teams and notification integration |
| `audit/` | 15 | Audit logging + decision audit (2 route files) |
| `cache/` | 9 | LLM response caching |
| `prompts/` | 11 | Prompt template management |
| `learning/` | 13 | Few-shot learning mechanism |
| `devtools/` | 12 | Execution tracing and debugging |
| `dashboard/` | 2 | Dashboard analytics |
| `versioning/` | 14 | Template version management |
| `performance/` | 11 | Performance monitoring |

### Phase 2: Advanced Orchestration

| Module | Endpoints | Purpose | Adapter |
|--------|-----------|---------|---------|
| `concurrent/` | 13 | Fork-Join concurrent execution | ConcurrentBuilderAdapter |
| `handoff/` | 14 | Agent handoff and collaboration | HandoffBuilderAdapter |
| `groupchat/` | 42 | GroupChat multi-turn conversations | GroupChatBuilderAdapter |
| `planning/` | 46 | Dynamic planning and decisions | MagenticBuilder |
| `nested/` | 16 | Nested workflows | NestedWorkflowAdapter |

### Phase 8-10: Extended Features

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `code_interpreter/` | 11 | Code execution (Responses API) |
| `mcp/` | 13 | MCP server management and tool discovery |
| `sessions/` | 14 | Session mode, multi-turn, WebSocket |

### Phase 12: Claude Agent SDK

| Route File | Endpoints | Purpose |
|------------|-----------|---------|
| `claude_sdk/routes.py` | 6 | Core SDK integration |
| `claude_sdk/autonomous_routes.py` | 7 | Autonomous execution |
| `claude_sdk/hooks_routes.py` | 6 | Hook lifecycle management |
| `claude_sdk/hybrid_routes.py` | 5 | Hybrid context integration |
| `claude_sdk/intent_routes.py` | 6 | Intent classification |
| `claude_sdk/mcp_routes.py` | 6 | MCP integration |
| `claude_sdk/tools_routes.py` | 4 | Tool management |

### Phase 13-14: Hybrid MAF+Claude SDK

| Route File | Endpoints | Purpose |
|------------|-----------|---------|
| `hybrid/context_routes.py` | 5 | Context synchronization |
| `hybrid/core_routes.py` | 4 | Core hybrid operations |
| `hybrid/risk_routes.py` | 7 | Risk assessment |
| `hybrid/switch_routes.py` | 7 | Mode switching |

### Phase 15: AG-UI Protocol

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `ag_ui/` | 25 | SSE streaming, event handling |

### Phase 18-22: Platform Features

| Module | Endpoints | Phase | Purpose |
|--------|-----------|-------|---------|
| `auth/` | 4 | 18 | Authentication (JWT) |
| `files/` | 6 | 20 | File upload and attachment |
| `memory/` | 7 | 22 | Memory system (mem0) |
| `sandbox/` | 6 | 21 | Sandboxed execution |
| `autonomous/` | 4 | 22 | Autonomous decision-making |

### Phase 23: Observability

| Module | Endpoints | Purpose |
|--------|-----------|---------|
| `a2a/` | 14 | Agent-to-Agent protocol |
| `patrol/` | 9 | Continuous monitoring |
| `correlation/` | 7 | Multi-agent event correlation |
| `rootcause/` | 4 | Root cause analysis |

### Phase 28: Three-tier Intent Routing

| Route File | Endpoints | Purpose |
|------------|-----------|---------|
| `orchestration/routes.py` | 9 | Policy management |
| `orchestration/intent_routes.py` | 18 | Intent classification API |
| `orchestration/dialog_routes.py` | 4 | Guided dialog |
| `orchestration/approval_routes.py` | 4 | HITL approval |

### Phase 29: Agent Swarm

| Route File | Endpoints | Purpose |
|------------|-----------|---------|
| `swarm/routes.py` | 3 | Swarm status API |
| `swarm/demo.py` | 5 | Swarm demo/test API (SSE) |

---

## Route Design Standards

### RESTful Conventions

| Operation | Method | Route Pattern |
|-----------|--------|---------------|
| List | GET | `/api/v1/{resource}` |
| Get | GET | `/api/v1/{resource}/{id}` |
| Create | POST | `/api/v1/{resource}` |
| Update | PUT | `/api/v1/{resource}/{id}` |
| Delete | DELETE | `/api/v1/{resource}/{id}` |
| Action | POST | `/api/v1/{resource}/{id}/{action}` |

### Route File Template

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.domain.{module}.service import {Module}Service
from . import schemas

router = APIRouter(prefix="/{module}", tags=["{Module}"])

@router.get("/", response_model=list[schemas.{Module}Response])
async def list_{module}s(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = {Module}Service(db)
    return service.get_all(skip=skip, limit=limit)

@router.get("/{id}", response_model=schemas.{Module}Response)
async def get_{module}(id: str, db: Session = Depends(get_db)):
    service = {Module}Service(db)
    item = service.get_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="{Module} not found")
    return item

@router.post("/", response_model=schemas.{Module}Response, status_code=status.HTTP_201_CREATED)
async def create_{module}(data: schemas.{Module}Create, db: Session = Depends(get_db)):
    service = {Module}Service(db)
    return service.create(data)
```

### Schema Pattern

```python
from pydantic import BaseModel, Field

class {Module}Base(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class {Module}Create({Module}Base):
    pass

class {Module}Update(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)

class {Module}Response({Module}Base):
    id: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

---

## Response Format

```python
# Success (single)
{"id": "uuid", "name": "Item", "created_at": "2026-01-01T00:00:00Z"}

# Success (list with pagination)
{"data": [...], "total": 100, "page": 1, "page_size": 20, "total_pages": 5}

# Error
{"detail": "Error message"}
{"error": "VALIDATION_ERROR", "message": "Invalid input", "details": {"field": "name"}}
```

---

## Common Patterns

### Dependency Injection

```python
from fastapi import Depends

def get_agent_service(db: Session = Depends(get_db)) -> AgentService:
    return AgentService(db)

@router.get("/")
async def list_agents(service: AgentService = Depends(get_agent_service)):
    return service.get_all()
```

### Error Handling

```python
from fastapi import HTTPException, status

raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete active agent")
raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"error": "VALIDATION_ERROR"})
```

---

**Last Updated**: 2026-02-09

# API Layer

> FastAPI 路由層 - 處理 HTTP 請求和響應

---

## Directory Structure

```
api/
├── __init__.py
├── v1/                     # API v1 namespace
│   ├── __init__.py
│   ├── agents/             # Agent management
│   ├── workflows/          # Workflow management
│   ├── executions/         # Execution lifecycle
│   ├── checkpoints/        # Checkpoint/approval
│   ├── templates/          # Workflow templates
│   ├── triggers/           # Workflow triggers
│   ├── connectors/         # External connectors
│   ├── routing/            # Intelligent routing
│   ├── notifications/      # Notifications
│   ├── audit/              # Audit logs
│   ├── versioning/         # Version control
│   ├── cache/              # Cache management
│   ├── prompts/            # Prompt management
│   ├── learning/           # Learning system
│   ├── devtools/           # Developer tools
│   ├── dashboard/          # Dashboard analytics
│   ├── performance/        # Performance metrics
│   │
│   │  # Agent Framework Features (→ Adapters)
│   ├── groupchat/          # GroupChat API → GroupChatBuilderAdapter
│   ├── handoff/            # Handoff API → HandoffBuilderAdapter
│   ├── concurrent/         # Concurrent API → ConcurrentBuilderAdapter
│   ├── nested/             # Nested Workflow API → NestedWorkflowAdapter
│   ├── planning/           # Planning API → PlanningAdapter
│   │
│   │  # Phase 11: Agent-Session Integration
│   ├── sessions/           # 🆕 Session-based conversations
│   │   ├── routes.py       # Session CRUD, Chat, Messages, Approvals
│   │   └── schemas.py      # Session/Message/ToolCall schemas
│   ├── code_interpreter/   # 🆕 Phase 8: Code execution
│   │
│   │  # Phase 13: Hybrid MAF + Claude SDK Architecture
│   └── hybrid/             # 🆕 Hybrid context management
│       ├── context_routes.py   # Context bridge & sync API
│       └── schemas.py          # Hybrid context schemas
```

---

## Route Design Standards

### RESTful Conventions

| Operation | Method | Route | Description |
|-----------|--------|-------|-------------|
| List | GET | `/api/v1/{resource}` | Get all items |
| Get | GET | `/api/v1/{resource}/{id}` | Get single item |
| Create | POST | `/api/v1/{resource}` | Create new item |
| Update | PUT | `/api/v1/{resource}/{id}` | Update item |
| Delete | DELETE | `/api/v1/{resource}/{id}` | Delete item |
| Action | POST | `/api/v1/{resource}/{id}/{action}` | Execute action |

### Route File Structure

```python
# routes.py template
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.{module}.service import {Module}Service
from . import schemas

router = APIRouter(prefix="/{module}", tags=["{Module}"])


@router.get("/", response_model=list[schemas.{Module}Response])
async def list_{module}s(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all {module}s with pagination."""
    service = {Module}Service(db)
    return service.get_all(skip=skip, limit=limit)


@router.get("/{id}", response_model=schemas.{Module}Response)
async def get_{module}(id: str, db: Session = Depends(get_db)):
    """Get single {module} by ID."""
    service = {Module}Service(db)
    item = service.get_by_id(id)
    if not item:
        raise HTTPException(status_code=404, detail="{Module} not found")
    return item


@router.post("/", response_model=schemas.{Module}Response, status_code=status.HTTP_201_CREATED)
async def create_{module}(
    data: schemas.{Module}Create,
    db: Session = Depends(get_db)
):
    """Create new {module}."""
    service = {Module}Service(db)
    return service.create(data)


@router.put("/{id}", response_model=schemas.{Module}Response)
async def update_{module}(
    id: str,
    data: schemas.{Module}Update,
    db: Session = Depends(get_db)
):
    """Update existing {module}."""
    service = {Module}Service(db)
    return service.update(id, data)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{module}(id: str, db: Session = Depends(get_db)):
    """Delete {module}."""
    service = {Module}Service(db)
    service.delete(id)
```

---

## Schema Design

### Pydantic Schema Patterns

```python
# schemas.py template
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class {Module}Base(BaseModel):
    """Base schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class {Module}Create({Module}Base):
    """Schema for creating new {module}."""
    pass


class {Module}Update(BaseModel):
    """Schema for updating {module} (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class {Module}Response({Module}Base):
    """Schema for API response."""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode
```

---

## Response Format

### Success Response

```python
# Single item
{
    "id": "uuid",
    "name": "Item Name",
    "created_at": "2025-12-18T10:00:00Z"
}

# List with pagination
{
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
}
```

### Error Response

```python
# HTTPException format
{
    "detail": "Error message"
}

# Custom error format
{
    "error": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
        "field": "name",
        "issue": "Field is required"
    }
}
```

---

## Agent Framework API Routes

These routes connect to **Adapter Layer** (`src/integrations/agent_framework/`):

| Route Module | Adapter | Official API |
|--------------|---------|--------------|
| `/groupchat` | GroupChatBuilderAdapter | GroupChatBuilder |
| `/handoff` | HandoffBuilderAdapter | HandoffBuilder |
| `/concurrent` | ConcurrentBuilderAdapter | ConcurrentBuilder |
| `/nested` | NestedWorkflowAdapter | WorkflowExecutor |
| `/planning` | PlanningAdapter | MagenticBuilder |
| `/sessions` | SessionAgentBridge | AgentExecutor |
| `/code_interpreter` | CodeInterpreterAdapter | Responses API |

---

## Sessions API Routes (Phase 11)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/sessions` | Create new session |
| GET | `/sessions/{id}` | Get session by ID |
| DELETE | `/sessions/{id}` | Delete session |
| GET | `/sessions/{id}/messages` | List session messages |
| POST | `/sessions/{id}/chat` | Send chat message |
| POST | `/sessions/{id}/chat/stream` | Stream chat response (SSE) |
| GET | `/sessions/{id}/tool-calls` | List tool calls |
| POST | `/sessions/{id}/tool-calls/{id}/approve` | Approve tool call |
| POST | `/sessions/{id}/tool-calls/{id}/reject` | Reject tool call |

---

## Hybrid Context API Routes (Phase 13)

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/hybrid/context/{session_id}` | Get hybrid context |
| GET | `/hybrid/context/{session_id}/status` | Get sync status |
| POST | `/hybrid/context/sync` | Trigger manual sync |
| POST | `/hybrid/context/merge` | Merge MAF and Claude contexts |
| GET | `/hybrid/context` | List all cached contexts |

### Example: GroupChat Route

```python
# api/v1/groupchat/routes.py
from fastapi import APIRouter
from src.integrations.agent_framework.builders.groupchat import GroupChatBuilderAdapter

router = APIRouter(prefix="/groupchat", tags=["GroupChat"])

@router.post("/sessions")
async def create_groupchat_session(config: GroupChatConfig):
    """Create a new GroupChat session."""
    adapter = GroupChatBuilderAdapter()
    # Uses official GroupChatBuilder internally
    session = adapter.create_session(config)
    return session
```

---

## Common Patterns

### Dependency Injection

```python
from fastapi import Depends
from src.core.database import get_db
from src.domain.agents.service import AgentService

def get_agent_service(db: Session = Depends(get_db)) -> AgentService:
    return AgentService(db)

@router.get("/")
async def list_agents(service: AgentService = Depends(get_agent_service)):
    return service.get_all()
```

### Query Parameters

```python
@router.get("/")
async def list_items(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    sort_by: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", enum=["asc", "desc"]),
):
    ...
```

### Path Parameters Validation

```python
from uuid import UUID

@router.get("/{agent_id}")
async def get_agent(agent_id: UUID):
    """Agent ID is automatically validated as UUID."""
    ...
```

---

## Error Handling

```python
from fastapi import HTTPException, status

# Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Agent not found"
)

# Validation Error
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={"error": "VALIDATION_ERROR", "message": "Invalid config"}
)

# Business Logic Error
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Cannot delete agent with active workflows"
)
```

---

**Last Updated**: 2025-12-24

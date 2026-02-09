# Sessions API

> Phase 11: Agent-Session Integration API Layer

---

## Directory Structure

```
sessions/
├── __init__.py
├── routes.py           # Session CRUD + Messages + Tool Calls
├── schemas.py          # Pydantic request/response schemas
├── chat.py             # Chat endpoints (sync/stream)
└── websocket.py        # WebSocket handler
```

---

## API Endpoints

### Session Management

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/sessions` | Create new session |
| GET | `/sessions/{id}` | Get session by ID |
| PUT | `/sessions/{id}` | Update session |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/end` | End session gracefully |

### Chat Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/sessions/{id}/chat` | Send message (sync response) |
| POST | `/sessions/{id}/chat/stream` | Send message (SSE streaming) |

### Message History

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/sessions/{id}/messages` | List session messages |
| GET | `/sessions/{id}/messages/{msg_id}` | Get specific message |

### Tool Call Management

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/sessions/{id}/tool-calls` | List tool calls |
| GET | `/sessions/{id}/tool-calls/{tc_id}` | Get tool call details |
| POST | `/sessions/{id}/tool-calls/{tc_id}/approve` | Approve tool call |
| POST | `/sessions/{id}/tool-calls/{tc_id}/reject` | Reject tool call |

### WebSocket

| Route | Description |
|-------|-------------|
| `ws://.../sessions/{id}/ws` | Real-time session communication |

---

## Schemas

### Session Schemas

```python
class SessionCreate(BaseModel):
    name: Optional[str] = None
    agent_id: Optional[str] = None
    config: Optional[SessionConfig] = None

class SessionConfig(BaseModel):
    approval_mode: str = "auto"  # "auto" | "manual"
    max_turns: int = 100
    timeout_seconds: int = 3600

class SessionResponse(BaseModel):
    id: str
    name: Optional[str]
    status: str  # "created" | "active" | "suspended" | "ended"
    created_at: datetime
    updated_at: datetime
```

### Message Schemas

```python
class ChatRequest(BaseModel):
    message: str
    attachments: Optional[List[AttachmentCreate]] = None

class ChatResponse(BaseModel):
    message_id: str
    content: str
    role: str  # "user" | "assistant"
    tool_calls: Optional[List[ToolCallResponse]] = None

class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    total: int
```

### Tool Call Schemas

```python
class ToolCallResponse(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]
    status: str  # "pending" | "approved" | "rejected" | "completed" | "failed"
    result: Optional[Any] = None

class ToolApprovalRequest(BaseModel):
    comment: Optional[str] = None

class ToolRejectionRequest(BaseModel):
    reason: str
```

---

## Streaming (SSE)

### Event Types

```
event: message_start
data: {"message_id": "..."}

event: content_delta
data: {"delta": "Hello"}

event: tool_call
data: {"id": "...", "name": "calculator", "arguments": {...}}

event: tool_result
data: {"id": "...", "result": 42}

event: message_end
data: {"message_id": "...", "usage": {...}}

event: error
data: {"code": "...", "message": "..."}
```

---

## Integration

### Domain Layer

- Uses `SessionService` from `domain/sessions/service.py`
- Uses `AgentExecutor` from `domain/sessions/executor.py`
- Uses `StreamingHandler` from `domain/sessions/streaming.py`

### Error Handling

```python
from src.domain.sessions.error_handler import SessionError, SessionErrorCode

# Error codes map to HTTP status codes
SessionErrorCode.SESSION_NOT_FOUND → 404
SessionErrorCode.INVALID_STATE → 400
SessionErrorCode.TOOL_EXECUTION_FAILED → 500
```

---

## Phase 28-29 Integration Points

### Phase 28: Three-tier Intent Routing

Sessions integrate with the orchestration layer for intelligent message routing:

- User messages are routed through `BusinessIntentRouter` (Pattern → Semantic → LLM)
- Routing decisions determine which agent/workflow handles the session
- Risk assessment may trigger HITL approval before execution
- Related API: `api/v1/orchestration/` (35 endpoints)

### Phase 29: Agent Swarm

Sessions can spawn agent swarm executions for complex multi-agent tasks:

- Swarm workers operate within a session context
- Real-time swarm progress via SSE events (`/api/v1/swarm/demo/events/{id}`)
- Worker results are aggregated back into the session message history
- Related API: `api/v1/swarm/` (8 endpoints)

---

**Last Updated**: 2026-02-09

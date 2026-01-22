# Sessions Domain

> Phase 11: Agent-Session Integration Business Logic Layer

---

## Directory Structure

```
sessions/
├── __init__.py
├── models.py           # Domain models (Session, Message, ToolCall, etc.)
├── service.py          # SessionService (lifecycle management)
├── repository.py       # SessionRepository (data access)
├── cache.py            # SessionCache (Redis caching)
├── events.py           # SessionEventPublisher (15 event types)
├── executor.py         # AgentExecutor (LLM interaction)
├── streaming.py        # StreamingHandler (SSE support)
├── tool_handler.py     # ToolCallHandler (with approval workflow)
├── approval.py         # ToolApprovalManager (Redis-based)
├── bridge.py           # SessionAgentBridge (connects session to agent)
├── error_handler.py    # SessionErrorHandler (24 error codes)
├── recovery.py         # SessionRecoveryManager
├── metrics.py          # MetricsCollector (Prometheus-style)
│
├── features/           # Session features
│   ├── tags.py         # TagService (6 system presets)
│   ├── statistics.py   # StatisticsService (lazy calc + cache)
│   └── templates.py    # TemplateService (5 system templates)
│
├── files/              # File handling
│   ├── analyzer.py     # FileAnalyzer (Strategy Pattern)
│   └── generator.py    # FileGenerator (Factory Pattern)
│
└── history/            # History management
    ├── manager.py      # HistoryManager (pagination, filtering)
    ├── bookmarks.py    # BookmarkService
    └── search.py       # SearchService
```

---

## Core Components

### 1. Domain Models (`models.py`)

```python
class Session:
    id: str
    name: Optional[str]
    status: SessionStatus  # CREATED, ACTIVE, SUSPENDED, ENDED
    agent_id: Optional[str]
    config: SessionConfig
    created_at: datetime
    updated_at: datetime

class Message:
    id: str
    session_id: str
    role: MessageRole  # USER, ASSISTANT, SYSTEM, TOOL
    content: str
    attachments: List[Attachment]
    tool_calls: List[ToolCall]

class ToolCall:
    id: str
    message_id: str
    name: str
    arguments: Dict[str, Any]
    status: ToolCallStatus  # PENDING, APPROVED, REJECTED, COMPLETED, FAILED
    result: Optional[Any]
```

### 2. Session State Machine

```
                ┌──────────┐
                │ CREATED  │
                └────┬─────┘
                     │ activate()
                     ▼
                ┌──────────┐
         ┌──────│  ACTIVE  │──────┐
         │      └────┬─────┘      │
 suspend()│          │ end()      │ end()
         ▼          │            │
    ┌──────────┐    │            │
    │SUSPENDED │────┘            │
    └──────────┘                 │
         │ resume()              │
         └───────────────────────┼───►┌──────────┐
                                 └───►│  ENDED   │
                                      └──────────┘
```

### 3. AgentExecutor (`executor.py`)

- Handles LLM interaction via Azure OpenAI
- Supports both sync and streaming responses
- Uses `LLMServiceProtocol` for abstraction

```python
class AgentExecutor:
    async def execute(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None,
        stream: bool = False
    ) -> Union[Message, AsyncIterator[StreamEvent]]:
        ...
```

### 4. ToolCallHandler (`tool_handler.py`)

- Executes tool calls with approval workflow
- Supports `auto` and `manual` approval modes
- Redis-based approval state management

```python
class ToolCallHandler:
    async def handle_tool_call(
        self,
        tool_call: ToolCall,
        approval_mode: str = "auto"
    ) -> ToolCallResult:
        if approval_mode == "manual":
            await self._request_approval(tool_call)
        return await self._execute_tool(tool_call)
```

### 5. StreamingHandler (`streaming.py`)

- SSE (Server-Sent Events) support
- Event types: `message_start`, `content_delta`, `tool_call`, `message_end`, `error`
- Async generator pattern

### 6. SessionEventPublisher (`events.py`)

15 event types for real-time updates:

| Event | Description |
|-------|-------------|
| `session.created` | Session created |
| `session.activated` | Session activated |
| `session.suspended` | Session suspended |
| `session.ended` | Session ended |
| `message.created` | New message added |
| `message.updated` | Message updated |
| `tool_call.pending` | Tool call awaiting approval |
| `tool_call.approved` | Tool call approved |
| `tool_call.rejected` | Tool call rejected |
| `tool_call.completed` | Tool call completed |
| `tool_call.failed` | Tool call failed |
| `stream.started` | Streaming started |
| `stream.chunk` | Stream chunk received |
| `stream.ended` | Streaming ended |
| `error.occurred` | Error occurred |

---

## Error Handling (`error_handler.py`)

### Error Codes (24 total)

| Category | Codes |
|----------|-------|
| Session | `SESSION_NOT_FOUND`, `SESSION_ALREADY_EXISTS`, `INVALID_STATE`, `SESSION_EXPIRED` |
| Message | `MESSAGE_NOT_FOUND`, `INVALID_MESSAGE`, `MESSAGE_TOO_LONG` |
| Tool | `TOOL_NOT_FOUND`, `TOOL_EXECUTION_FAILED`, `TOOL_TIMEOUT`, `INVALID_TOOL_ARGS` |
| Approval | `APPROVAL_REQUIRED`, `APPROVAL_TIMEOUT`, `APPROVAL_REJECTED` |
| LLM | `LLM_ERROR`, `LLM_TIMEOUT`, `RATE_LIMITED`, `TOKEN_LIMIT` |
| System | `INTERNAL_ERROR`, `DATABASE_ERROR`, `CACHE_ERROR`, `VALIDATION_ERROR` |

### HTTP Mapping

```python
SessionErrorCode.SESSION_NOT_FOUND → 404
SessionErrorCode.INVALID_STATE → 400
SessionErrorCode.APPROVAL_REQUIRED → 202
SessionErrorCode.RATE_LIMITED → 429
SessionErrorCode.LLM_ERROR → 502
```

---

## Metrics (`metrics.py`)

Prometheus-style metrics collection:

```python
# Counter
session_created_total
message_count_total
tool_call_count_total

# Histogram
llm_response_time_seconds
tool_execution_time_seconds

# Gauge
active_sessions_count
pending_approvals_count
```

Decorators for automatic timing:

```python
@track_time("llm_response")
async def call_llm(...):
    ...

@track_tool_time
async def execute_tool(...):
    ...
```

---

## Recovery (`recovery.py`)

- Checkpoint-based session recovery
- Event buffer for replay
- Auto-recovery on connection restore

```python
class SessionRecoveryManager:
    async def create_checkpoint(self, session_id: str) -> Checkpoint:
        ...

    async def recover_from_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str
    ) -> Session:
        ...
```

---

## Integration Points

### API Layer
- Routes in `api/v1/sessions/routes.py`
- Schemas in `api/v1/sessions/schemas.py`

### Infrastructure
- Redis: `infrastructure/cache/redis_client.py`
- PostgreSQL: `infrastructure/database/models/session.py`

### Agent Framework
- Uses `integrations/agent_framework/` for LLM integration

---

## Testing

Tests located in:
- `tests/unit/domain/sessions/` - Unit tests
- `tests/integration/api/` - API integration tests
- `tests/e2e/` - End-to-end tests

Key test files:
- `test_session_service.py`
- `test_agent_executor.py`
- `test_tool_handler.py`
- `test_streaming.py`
- `test_error_handler.py`
- `test_recovery.py`
- `test_metrics.py`

---

**Last Updated**: 2026-01-23

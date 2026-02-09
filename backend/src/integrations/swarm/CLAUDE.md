# Swarm — Agent Swarm State Tracking

> Phase 29, Sprints 100-106 | 7 Python files, ~1,100 LOC | Multi-agent swarm tracking + SSE events

---

## Directory Structure

```
swarm/
├── __init__.py                 # 30+ exports (models, tracker, integration, events)
├── models.py                   # Data structures and enums (393 LOC)
├── tracker.py                  # SwarmTracker — State management (693 LOC)
├── swarm_integration.py        # ClaudeCoordinator integration (404 LOC)
└── events/                     # SSE event system (Sprint 101)
    ├── __init__.py
    ├── types.py                # 9 event payload dataclasses (443 LOC)
    └── emitter.py              # SwarmEventEmitter with throttling (634 LOC)
```

---

## Architecture

```
ClaudeCoordinator (from claude_sdk/orchestrator)
    ↓ callbacks
SwarmIntegration
    ├── SwarmTracker (state management)
    │   ├── create_swarm()
    │   ├── start_worker()
    │   ├── add_thinking() / add_tool_call() / add_message()
    │   └── complete_swarm()
    │
    └── SwarmEventEmitter (SSE output)
        ├── emit_swarm_created()
        ├── emit_worker_started() / _thinking() / _tool_call()
        ├── emit_worker_completed()
        └── emit_swarm_completed()
            ↓ AG-UI CustomEvent
        Frontend (AgentSwarmPanel)
```

---

## Key Enums

| Enum | Values |
|------|--------|
| **WorkerType** | RESEARCH, WRITER, DESIGNER, REVIEWER, COORDINATOR, ANALYST, CODER, TESTER, CUSTOM |
| **WorkerStatus** | PENDING, RUNNING, THINKING, TOOL_CALLING, COMPLETED, FAILED, CANCELLED |
| **SwarmMode** | SEQUENTIAL, PARALLEL, HIERARCHICAL |
| **SwarmStatus** | INITIALIZING, RUNNING, PAUSED, COMPLETED, FAILED |

---

## Key Classes

| Class | File | LOC | Purpose |
|-------|------|-----|---------|
| **SwarmTracker** | tracker.py | 693 | Thread-safe swarm state management (optional Redis) |
| **SwarmEventEmitter** | events/emitter.py | 634 | SSE event emission with throttling (100ms default) |
| **SwarmIntegration** | swarm_integration.py | 404 | Callback bridge to ClaudeCoordinator |

---

## Data Models

```python
@dataclass
class AgentSwarmStatus:
    swarm_id: str
    mode: SwarmMode
    status: SwarmStatus
    workers: List[WorkerExecution]
    created_at: datetime
    completed_at: Optional[datetime]

@dataclass
class WorkerExecution:
    worker_id: str
    name: str
    type: WorkerType
    role: str
    status: WorkerStatus
    messages: List[WorkerMessage]
    tool_calls: List[ToolCallInfo]
    thinking: Optional[ThinkingContent]
```

---

## SSE Events (9 types)

| Event Name | Payload | Trigger |
|------------|---------|---------|
| `swarm_created` | SwarmCreatedPayload | Swarm initialized |
| `swarm_status_update` | SwarmStatusUpdatePayload | Status changed |
| `swarm_completed` | SwarmCompletedPayload | All workers done |
| `worker_started` | WorkerStartedPayload | Worker begins |
| `worker_progress` | WorkerProgressPayload | Worker status update |
| `worker_thinking` | WorkerThinkingPayload | Extended Thinking content |
| `worker_tool_call` | WorkerToolCallPayload | Tool execution |
| `worker_message` | WorkerMessagePayload | Worker communication |
| `worker_completed` | WorkerCompletedPayload | Worker finished |

Events are emitted as AG-UI `CustomEvent` via `src.integrations.ag_ui.events`.

---

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/api/v1/swarm/{id}/status` | Get swarm state |
| GET | `/api/v1/swarm/{id}/workers` | List workers |
| GET | `/api/v1/swarm/{id}/workers/{wid}` | Worker detail |
| POST | `/api/v1/swarm/demo/start` | Start demo swarm |
| GET | `/api/v1/swarm/demo/{id}/stream` | SSE event stream |

---

## Frontend Components

See `frontend/src/components/unified-chat/agent-swarm/` (17 components):
- `AgentSwarmPanel.tsx` — Main swarm container
- `WorkerCard.tsx` / `WorkerCardList.tsx` — Worker visualization
- `WorkerDetailDrawer.tsx` — Worker detail panel
- `ExtendedThinkingPanel.tsx` — AI thinking display
- `ToolCallsPanel.tsx` / `ToolCallItem.tsx` — Tool execution tracking

---

**Last Updated**: 2026-02-09

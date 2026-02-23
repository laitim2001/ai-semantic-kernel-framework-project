# CHANGE-004: Swarm Test Page Real Execution Mode

## Summary

Added real execution mode to the Swarm Test Page, enabling true backend connection and SSE event streaming for Agent Swarm visualization testing.

## Date

2026-01-30

## Sprint / Phase

Phase 29: Agent Swarm Visualization - Sprint 107

## Type

Feature Enhancement

## Components Changed

### Backend

| File | Change Type | Description |
|------|-------------|-------------|
| `backend/src/api/v1/swarm/demo.py` | **New** | Swarm Demo API with SSE event streaming |
| `backend/src/api/v1/swarm/__init__.py` | Modified | Export demo_router |
| `backend/src/api/v1/__init__.py` | Modified | Register swarm_demo_router |

### Frontend

| File | Change Type | Description |
|------|-------------|-------------|
| `frontend/src/hooks/useSwarmReal.ts` | **New** | Real hook for backend SSE connection |
| `frontend/src/pages/SwarmTestPage.tsx` | Modified | Support Mock/Real mode switching |

## API Endpoints

### New Demo API (`/api/v1/swarm/demo`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/swarm/demo/start` | Start a demo swarm execution |
| GET | `/swarm/demo/status/{swarm_id}` | Get demo execution status |
| POST | `/swarm/demo/stop/{swarm_id}` | Stop a running demo |
| GET | `/swarm/demo/scenarios` | List available demo scenarios |
| GET | `/swarm/demo/events/{swarm_id}` | SSE event stream for real-time updates |

### Request/Response Schemas

```python
# DemoStartRequest
{
    "scenario": "security_audit" | "etl_pipeline" | "data_pipeline" | "custom",
    "mode": "parallel" | "sequential" | "hierarchical",
    "speed_multiplier": 0.5 - 5.0,
    "workers": [...] // Optional, for custom scenario
}

# DemoStartResponse
{
    "swarm_id": "demo-xxxxxxxx",
    "session_id": "session-xxxxxxxx",
    "status": "started",
    "message": "Demo swarm started with N workers",
    "sse_endpoint": "/api/v1/swarm/demo/events/{swarm_id}"
}
```

### SSE Events

| Event Type | Description |
|------------|-------------|
| `swarm_update` | Real-time swarm status snapshot |
| `swarm_complete` | Swarm execution completed |
| `error` | Error notification |

## Demo Scenarios

| Scenario ID | Name | Workers | Duration |
|-------------|------|---------|----------|
| `security_audit` | 安全審計 | 4 | ~18 seconds |
| `etl_pipeline` | ETL Pipeline 診斷 | 3 | ~13 seconds |
| `data_pipeline` | 資料管道監控 | 2 | ~9 seconds |

## Frontend Changes

### Mode Switch Component

- Added Mock/Real mode toggle
- Visual indicators for connection status
- Mode-specific control panels

### useSwarmReal Hook

```typescript
interface UseSwarmRealReturn {
  // State
  swarmStatus: UIAgentSwarmStatus | null;
  selectedWorkerId: string | null;
  selectedWorkerDetail: WorkerDetail | null;
  isDrawerOpen: boolean;
  mockMessages: MockMessage[];

  // Connection State
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;

  // Available Scenarios
  scenarios: DemoScenario[];

  // Demo Actions
  startDemo: (request: DemoStartRequest) => Promise<void>;
  stopDemo: () => Promise<void>;
  loadScenarios: () => Promise<void>;

  // UI Actions
  selectWorker: (workerId: string | null) => void;
  openDrawer: () => void;
  closeDrawer: () => void;

  // Reset
  reset: () => void;
}
```

## Testing Instructions

### Prerequisites

1. Start backend service: `python scripts/dev.py start backend`
2. Start frontend service: `python scripts/dev.py start frontend`

### Test Real Mode

1. Navigate to `http://localhost:3005/swarm-test`
2. Click "Real" mode toggle
3. Select a demo scenario (e.g., "安全審計")
4. Adjust speed multiplier if needed (0.5x - 5x)
5. Click "啟動演示" button
6. Observe:
   - Connection status indicator turns green
   - Workers appear in the Orchestration Panel
   - Progress updates in real-time
   - Tool calls and thinking content updates
7. Click on a Worker card to see detailed information
8. Wait for completion or click "停止演示" to stop early

### Test Mock Mode (unchanged)

1. Click "Mock" mode toggle
2. Use existing mock controls as before

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                 │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │  SwarmTestPage  │    │   useSwarmReal  │                     │
│  │   (Mode Switch) │◄──►│   (SSE Client)  │                     │
│  └─────────────────┘    └────────┬────────┘                     │
│                                  │                               │
└──────────────────────────────────┼──────────────────────────────┘
                                   │ EventSource
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                          Backend                                  │
│  ┌─────────────────┐    ┌─────────────────┐                      │
│  │   Demo API      │    │  SSE Endpoint   │                      │
│  │  /swarm/demo/*  │───►│  /events/{id}   │                      │
│  └────────┬────────┘    └────────┬────────┘                      │
│           │                      │                                │
│           ▼                      ▼                                │
│  ┌─────────────────┐    ┌─────────────────┐                      │
│  │ SwarmIntegration│◄──►│  SwarmTracker   │                      │
│  │  (Simulation)   │    │  (State Store)  │                      │
│  └─────────────────┘    └─────────────────┘                      │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

## Known Limitations

1. Demo execution is simulated, not actual agent execution
2. SSE connection may timeout after extended idle periods
3. Speed multiplier affects all workers uniformly
4. Worker detail updates are based on state polling, not push

## Related Changes

- Sprint 100-106: Initial Swarm API and UI components
- CHANGE-003: Three-tier Router Real Implementation

## Rollback Instructions

1. Remove `backend/src/api/v1/swarm/demo.py`
2. Revert `backend/src/api/v1/swarm/__init__.py` to previous version
3. Revert `backend/src/api/v1/__init__.py` to remove demo_router
4. Remove `frontend/src/hooks/useSwarmReal.ts`
5. Revert `frontend/src/pages/SwarmTestPage.tsx` to mock-only version

## Reviewers

- [@claude-code] - Implementation
- [Pending] - Code Review

# Post-Merge Verification

After merging `poc/agent-team` into `main`, use this checklist to verify everything works.

---

## Will Everything Work the Same as PoC?

**Short answer**: Yes, IF the pre-merge fixes are applied and services are running.

**Detailed answer**:

| Aspect | Status | Notes |
|--------|--------|-------|
| PoC backend code | Identical | Same code, same branch, just merged |
| PoC frontend code | Identical | Same code |
| Backend port | **Different** | PoC used 8042/8044, main uses 8000 |
| Vite proxy | **Must fix** | Pre-merge fix changes 8044 → 8000 |
| Redis | Same | localhost:6379 (hardcoded in PoC) |
| Qdrant | Same | localhost:6333 (if running) |
| Azure OpenAI | Same | Uses same env vars |
| Frontend route | Same | `/agent-team-test` |

**Key difference**: You run the backend on port **8000** (not 8044):
```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## Verification Checklist

### Phase 1: Static Checks (no services needed)

- [ ] **Git state clean**
  ```bash
  git status  # no uncommitted changes
  git log -1  # merge commit visible
  ```

- [ ] **PoC files exist**
  ```bash
  ls backend/src/integrations/poc/
  # Expected: 9 files (agent_work_loop.py, approval_gate.py, etc.)
  ```

- [ ] **Routes registered**
  ```bash
  grep "poc_team_router" backend/src/api/v1/__init__.py
  # Expected: import + include_router lines
  ```

- [ ] **Frontend route exists**
  ```bash
  grep "agent-team-test" frontend/src/App.tsx
  # Expected: Route path="/agent-team-test"
  ```

- [ ] **Vite proxy correct**
  ```bash
  grep "target" frontend/vite.config.ts
  # Expected: 'http://localhost:8000'
  ```

- [ ] **Dependencies complete**
  ```bash
  grep "qdrant-client" backend/requirements.txt
  # Expected: qdrant-client entry exists
  ```

### Phase 2: Backend Startup

- [ ] **Install dependencies**
  ```bash
  cd backend
  pip install -r requirements.txt
  ```

- [ ] **Start backend**
  ```bash
  python -m uvicorn main:app --host 0.0.0.0 --port 8000
  # Expected: "Application startup complete"
  # Expected: No import errors
  ```

- [ ] **Check PoC endpoints registered**
  ```
  Open: http://localhost:8000/docs
  Search for: /poc/agent-team/
  Expected: test-subagent, test-team, test-hybrid, test-orchestrator
            + streaming versions + approval + memory endpoints
  ```

### Phase 3: Frontend Startup

- [ ] **Install dependencies**
  ```bash
  cd frontend
  npm install
  ```

- [ ] **Start frontend**
  ```bash
  npm run dev
  # Expected: Local: http://localhost:3005/
  ```

- [ ] **Agent Team Test Page loads**
  ```
  Open: http://localhost:3005/agent-team-test
  Expected: Test page with 4 mode buttons (Subagent, Team, Hybrid, Orchestrator)
  ```

### Phase 4: Functional Tests (requires Azure OpenAI + Redis)

**Prerequisites**:
- Redis running on localhost:6379
- Azure OpenAI credentials in `.env`
- (Optional) Qdrant running on localhost:6333

- [ ] **Mode A: Subagent** — Click "Test Subagent"
  ```
  Expected: 3 agents run in parallel, each checks one system
  Expected: Agent responses appear in results panel
  ```

- [ ] **Mode B: Agent Team** — Click "Test Team"
  ```
  Expected: TeamLead decomposes task → agents claim tasks → synthesis
  Expected: SSE events stream in real-time
  Expected: SharedTaskList shows task progress
  ```

- [ ] **Mode C: Hybrid** — Click "Test Hybrid"
  ```
  Expected: Orchestrator decides subagent vs team → executes chosen mode
  ```

- [ ] **Mode D: Orchestrator** — Click "Test Orchestrator"
  ```
  Expected: 6-step pipeline executes:
    Step 1: Read Memory
    Step 2: Search Knowledge
    Step 3: Analyze Intent
    Step 4: LLM Route Decision
    Step 5: Save Checkpoint
    Step 6: Memory Extraction
  ```

- [ ] **HITL Approval** (if HIGH risk task detected)
  ```
  Expected: Approval card appears
  Expected: Approve/Reject buttons work
  ```

- [ ] **SSE Streaming** — Test any streaming endpoint
  ```
  Expected: Real-time events appear in the UI
  Expected: Agent thinking/tool calls visible
  ```

### Phase 5: No Regression on Main Features

- [ ] **Main chat page still works**: http://localhost:3005/
- [ ] **Agent dashboard still loads**: http://localhost:3005/agents
- [ ] **Other pages unaffected**: Spot-check 2-3 other pages

---

## Troubleshooting

### Backend won't start — ImportError
```
Cause: Missing dependency
Fix: pip install -r requirements.txt
Check: pip list | grep qdrant
```

### Frontend API calls fail — 502/CORS
```
Cause: Vite proxy pointing to wrong port
Fix: Check frontend/vite.config.ts target is 'http://localhost:8000'
Fix: Ensure backend is running on port 8000
```

### Agent Team test fails — no LLM response
```
Cause: Azure OpenAI credentials not set
Fix: Check .env has AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY,
     AZURE_OPENAI_DEPLOYMENT_NAME
```

### Orchestrator Step 2 fails — Knowledge search
```
Cause: Qdrant not running or no data indexed
Impact: Non-blocking — step returns "Knowledge search failed" and continues
Fix: Start qdrant on localhost:6333 and index data
```

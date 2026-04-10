# Pre-Merge Fixes

These fixes must be applied to `poc/agent-team` branch BEFORE merging to `main`.

## Fix 1: Vite Proxy Port (CRITICAL)

**Problem**: PoC testing used port 8044, but main project backend runs on port 8000.

**File**: `frontend/vite.config.ts` line 30

**Current (PoC)**:
```typescript
target: 'http://localhost:8044',
```

**Should be**:
```typescript
target: 'http://localhost:8000',
```

**Impact if not fixed**: Frontend cannot reach backend after merge — all API calls fail.

**Command (run in PoC worktree)**:
```bash
cd /c/Users/Chris/Downloads/ai-semantic-kernel-poc-team
# Edit frontend/vite.config.ts: change 8044 to 8000
git add frontend/vite.config.ts
git commit -m "fix: restore vite proxy to port 8000 for main branch compatibility"
```

## Fix 2: Add qdrant-client to requirements.txt (HIGH)

**Problem**: `agent_team_poc.py` line 918 imports `qdrant_client`, but it's not listed in `backend/requirements.txt`.

**File**: `backend/requirements.txt`

**Add**:
```
qdrant-client>=1.7.0          # Vector search for knowledge base
```

**Impact if not fixed**: `pip install -r requirements.txt` won't install qdrant-client, causing ImportError at runtime when orchestrator mode's Step 2 (Knowledge Search) runs.

**Note**: The orchestrator handles this gracefully (try/except returns "Knowledge search failed"), so it's not a hard crash — but Step 2 will always fail.

**Command (run in PoC worktree)**:
```bash
cd /c/Users/Chris/Downloads/ai-semantic-kernel-poc-team
# Edit backend/requirements.txt: add qdrant-client
git add backend/requirements.txt
git commit -m "fix: add qdrant-client to requirements.txt"
```

## Optional: Redis URL Hardcoding (LOW — not blocking)

**Problem**: `agent_team_poc.py` hardcodes `redis://:{password}@localhost:6379/0` in 13 places instead of using a config service.

**Impact**: Works fine on localhost dev. Would need refactoring for different Redis hosts (production).

**Recommendation**: Fix in a future sprint, not before merge. The PoC is a test/demo module.

## Verification After Fixes

After applying fixes, in the PoC worktree:
```bash
git log -3 --oneline
# Should show your fix commits at the top

grep -n "8044" frontend/vite.config.ts
# Should return nothing (port changed to 8000)

grep -n "qdrant-client" backend/requirements.txt
# Should show the new entry
```

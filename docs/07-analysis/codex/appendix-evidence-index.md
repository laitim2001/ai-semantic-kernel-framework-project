# Evidence Index (Codex)

> Version: 0.1
> Date: 2026-02-11

---

## Metrics Evidence

1. File count baselines
- `rg --files backend/src | Measure-Object`
- `rg --files frontend/src | Measure-Object`
- `rg --files backend/tests | Measure-Object`
- `rg --files frontend/e2e | Measure-Object`

2. LOC baselines
- PowerShell line aggregation over `backend/src/**/*.py`
- PowerShell line aggregation over `frontend/src/**/*.{ts,tsx}`

3. API shape
- Route files count: `rg --files backend/src/api -g "*route*.py" -g "*routes*.py"`
- Endpoint decorators: `rg -n "@.*\.(get|post|put|patch|delete|options|head)\(" backend/src/api`
- Router includes: `rg -n "include_router\(" backend/src`

4. Frontend topology
- Pages/components/hooks/stores counts under `frontend/src`

## Risk Evidence

1. Proxy mismatch
- `frontend/vite.config.ts`
- `backend/main.py`

2. CORS mismatch
- `backend/src/core/config.py`
- `frontend/vite.config.ts`

3. Context synchronizer lock gap
- `backend/src/integrations/hybrid/context/sync/synchronizer.py`
- `backend/src/integrations/claude_sdk/hybrid/synchronizer.py`

4. Missing ReactFlow dependency
- `frontend/package.json`

5. InMemory and Mock surface
- `rg -n "class\s+\w*InMemory\w*" backend/src`
- `rg -n "class\s+\w*Mock\w*" backend/src`

6. Large file concentration
- backend and frontend >800 LOC scans

---

## Document Links

1. `docs/07-analysis/codex/00-analysis-charter.md`
2. `docs/07-analysis/codex/01-inventory-baseline.md`
3. `docs/07-analysis/codex/02-v7-output-spec.md`
4. `docs/07-analysis/codex/03-architecture-deep-analysis.md`
5. `docs/07-analysis/codex/04-features-mapping-deep-analysis.md`

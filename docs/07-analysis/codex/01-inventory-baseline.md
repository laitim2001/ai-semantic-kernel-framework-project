# Inventory Baseline (Codex)

> Version: 1.0
> Baseline date: 2026-02-11
> Generated from local repository scan
> Scope: `backend/src`, `frontend/src`, `backend/tests`, `frontend/e2e`

---

## 1. Global Scale

| Metric | Value |
|---|---:|
| Backend source files (`backend/src`) | 625 |
| Frontend source files (`frontend/src`) | 203 |
| Backend test files (`backend/tests`) | 305 |
| Frontend E2E files (`frontend/e2e`) | 13 |

## 2. LOC Baseline (Measured)

| Segment | LOC |
|---|---:|
| Backend Python LOC (`backend/src/**/*.py`) | 190,724 |
| Frontend TS/TSX LOC (`frontend/src/**/*.ts,tsx`) | 43,012 |
| Frontend all-file LOC (`frontend/src/**/*`) | 43,090 |

## 3. Backend Topology Baseline

### 3.1 File counts by top module

| Module | .py files | LOC |
|---|---:|---:|
| `backend/src/api` | 138 | 36,301 |
| `backend/src/core` | 23 | 7,143 |
| `backend/src/domain` | 112 | 39,407 |
| `backend/src/infrastructure` | 22 | 2,812 |
| `backend/src/integrations` | 315 | 105,060 |

### 3.2 API shape

| API metric | Value |
|---|---:|
| API files under `backend/src/api` | 140 |
| Route files matching `*route*.py`/`*routes*.py` | 52 |
| HTTP decorators (`@router.get/post/put/patch/delete/...`) | 542 |
| `include_router(...)` references (all backend/src) | 61 |
| `APIRouter(...)` occurrences (api layer) | 62 |

## 4. Frontend Topology Baseline

| Frontend metric | Value |
|---|---:|
| Page files (`frontend/src/pages`) | 39 |
| Component files (`frontend/src/components`) | 127 |
| Hook files (`frontend/src/hooks`) | 17 |
| Store files (`frontend/src/store`) | 1 |
| Stores files (`frontend/src/stores`) | 3 |

## 5. Key Code Signals (Risk/Complexity Indicators)

| Signal | Value |
|---|---:|
| Backend files >800 LOC | 25 |
| Frontend files >800 LOC | 7 |
| `console.log(...)` in frontend src | 54 |
| Backend lines matching `pass` or `...` | 360 |
| `class *InMemory*` count (backend/src) | 9 classes in 8 files |
| `class *Mock*` count (backend/src) | 19 classes in 16 files |
| Auth-related usages in API (`Depends(get_current_user...)` etc.) | 38 |
| API files with auth patterns (`backend/src/api/v1`) | 8 files |

## 6. Integration Layer Baseline (`backend/src/integrations`)

| Submodule | .py files | LOC |
|---|---:|---:|
| `agent_framework` | 53 | 30,687 |
| `hybrid` | 60 | 17,872 |
| `claude_sdk` | 47 | 12,506 |
| `mcp` | 43 | 10,528 |
| `orchestration` | 39 | 13,330 |
| `ag_ui` | 23 | 8,062 |
| `swarm` | 7 | 2,332 |
| `memory` | 5 | 1,508 |
| `a2a` | 4 | 745 |
| `audit` | 4 | 972 |
| `correlation` | 4 | 993 |
| `rootcause` | 3 | 652 |
| `learning` | 5 | 1,236 |
| `patrol` | 11 | 2,142 |
| `llm` | 6 | 1,461 |

## 7. Notable Configuration Findings (for deep-dive verification)

1. `frontend/vite.config.ts` uses proxy target `http://localhost:8010` while `backend/main.py` runs on port `8000`.
2. `backend/src/core/config.py` default CORS includes `http://localhost:3000` and `http://localhost:8000`; frontend dev server is on `3005`.
3. `frontend/package.json` has no `reactflow` dependency.
4. `backend/main.py` runs `uvicorn` with `reload=True`.

## 8. Evidence Notes

This baseline is command-derived and will be reused by:

1. `03-architecture-deep-analysis.md`
2. `04-features-mapping-deep-analysis.md`
3. `05-risks-gaps-remediation.md`

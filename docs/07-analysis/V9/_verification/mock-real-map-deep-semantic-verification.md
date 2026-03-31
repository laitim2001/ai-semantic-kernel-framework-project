# V9 Mock-Real Map — Deep Semantic Verification Report

> **Date**: 2026-03-31
> **Scope**: 50-point deep semantic verification of `mock-real-map.md` against actual source code
> **Method**: Targeted source code reads + grep verification across all 939+ source files
> **Prior report**: `mock-real-map-verification.md` (same date, initial pass)
> **This report**: Deeper verification focusing on semantic accuracy of descriptions, not just existence

---

## Verification Summary

| Category | Points | Pass | Fail | Warn | Notes |
|----------|--------|------|------|------|-------|
| P1-P10: REAL modules | 10 | 8 | 0 | 2 | n8n placeholder, correlation fallback |
| P11-P20: MOCK modules | 10 | 10 | 0 | 0 | All confirmed |
| P21-P30: PARTIAL modules | 10 | 8 | 1 | 1 | SmartFallback names wrong; checkpoints line ref |
| P31-P40: InMemory details | 10 | 9 | 0 | 1 | deprecated label unverifiable |
| P41-P50: Upgrade path + priority | 10 | 9 | 1 | 0 | SmartFallback strategy chain |
| **TOTAL** | **50** | **44** | **2** | **4** | |
| **Accuracy** | | **88%** | **4%** | **8%** | |

---

## Errors Found (Requiring Correction in `mock-real-map.md`)

### Error 1: SmartFallback Strategy Names (Section 3.3 Row A)

- **Doc says**: `RETRY > SIMPLIFY > SKIP > HUMAN_ESCALATION`
- **Actual enum** (`claude_sdk/autonomous/fallback.py:29-37`):
  ```python
  class FallbackStrategy(str, Enum):
      RETRY = "retry"
      ALTERNATIVE = "alternative"
      SKIP = "skip"
      ESCALATE = "escalate"
      ROLLBACK = "rollback"
      ABORT = "abort"
  ```
- **Errors**: `SIMPLIFY` does not exist (should be `ALTERNATIVE`); `HUMAN_ESCALATION` does not exist (should be `ESCALATE`); `ROLLBACK` and `ABORT` are omitted.
- **Fix**: Replace `RETRY > SIMPLIFY > SKIP > HUMAN_ESCALATION` with `RETRY > ALTERNATIVE > SKIP > ESCALATE > ROLLBACK > ABORT`
- **Note**: The prior verification report (P10, P47) also repeats this error.

### Error 2: domain/orchestration mock coverage incomplete (Section 1.2)

- **Doc says**: `nested/sub_executor.py:264` mock execution + `nested/recursive_handler.py:334` mock execution
- **Actual**: Three additional mock return paths exist in `nested/workflow_manager.py`:
  - Line 566: `"Fallback: return mock result"` (execute_by_reference)
  - Line 599: `"No execution service, returning mock result"` (execute_parallel)
  - Line 637: `"No execution service, returning mock result"` (execute_conditional)
- **Impact**: The mock scope of `domain/orchestration` is wider than documented.
- **Fix**: Add `workflow_manager.py:566,599,637 — mock result fallback for reference/parallel/conditional execution` to the Notes column.

---

## Warnings (Minor Inaccuracies)

### ⚠️ W1: domain/checkpoints line reference (Section 1.2)

- **Doc says**: `service.py:526 — proper HumanApprovalExecutor`
- **Actual**: Line 526 is inside a docstring (`HumanApprovalExecutor or None if not configured`). The actual `CheckpointService` class is at line 150; `HumanApprovalExecutor` instantiation is at line 185.
- **Suggestion**: Change to `service.py:150,185 — CheckpointService with HumanApprovalExecutor`

### ⚠️ W2: n8n/ labeled "REAL" with placeholder reasoning (Section 1.1)

- **Doc says**: REAL — `orchestrator.py:617` placeholder reasoning function
- **Actual**: Source at line 617 says `"""Default reasoning function (placeholder)."""` and the docstring explicitly states "In production, this should be replaced with the actual IPA orchestration router". This is more accurately described as "REAL + PLACEHOLDER" rather than pure "REAL".
- **Suggestion**: Change status to `REAL + PLACEHOLDER` or add note about the placeholder nature.

### ⚠️ W3: correlation/ fallback characterization (Section 1.1)

- **Doc says (per-module table)**: "No mock patterns; operational graceful fallback in `analyzer.py:441`"
- **Actual**: The spectrum diagram correctly places it in "REAL only", and the per-module table note mentions the graceful fallback. This is acceptable but the "No mock/fallback patterns found" in the main Evidence column contradicts the Notes column. Already flagged in prior report.

### ⚠️ W4: InMemoryConversationMemoryStore deprecated label (InMemory Risk Map)

- **Doc says**: `🟢 LOW — 已 deprecated, 影響範圍小`
- **Actual**: No `@deprecated` decorator or deprecation warning in source. The domain/CLAUDE.md marks `domain/orchestration/` as DEPRECATED but no runtime marker exists. Already flagged in prior report.

---

## P1-P10: REAL Modules — Detailed Verification

| # | Module | Doc Status | Verified | Evidence |
|---|--------|-----------|----------|----------|
| P1 | `integrations/correlation` | REAL | ✅ | `analyzer.py` has real correlation logic; `graph.py:361` has `analyze_clusters()`. No mock. |
| P2 | `integrations/a2a` | REAL | ✅ | `router.py:104` `process_queue()`, `discovery.py:24` `AgentDiscoveryService`. No mock/fallback. |
| P3 | `integrations/memory` | REAL | ✅ | `mem0_client.py` imports `from mem0 import Memory`, Qdrant config. `unified_memory.py:262` "Use mem0 as fallback" — operational, not mock. |
| P4 | `integrations/learning` | REAL | ✅ | `similarity.py:264` word-overlap is graceful degradation, not mock. |
| P5 | `integrations/n8n` | REAL | ⚠️ | `orchestrator.py:617` is explicitly a "placeholder" per source docstring. See W2. |
| P6 | `integrations/shared` | REAL | ✅ | No mock/fallback/InMemory patterns found. Protocol definitions only. |
| P7 | `integrations/contracts` | REAL | ✅ | No mock/fallback/InMemory patterns found. Interface contracts only. |
| P8 | `integrations/swarm` | REAL | ✅ | `worker_executor.py:249` fallback generate() and `task_decomposer.py:145` single-task fallback are operational graceful degradation. |
| P9 | `integrations/audit` | REAL | ✅ | `types.py:22` `FALLBACK_SELECTION` event type tracks fallback events. |
| P10 | `domain/sessions` | REAL | ✅ | `repository.py:88` `SQLAlchemySessionRepository` with `AsyncSession`. DB-backed. |

---

## P11-P20: MOCK Modules — Detailed Verification

| # | Module | Doc Status | Verified | Evidence |
|---|--------|-----------|----------|----------|
| P11 | `domain/agents` | MOCK | ✅ | `service.py:228` `[Mock Response]`; `builtin.py:417` `mock_weather`; `:471` `mock_results` |
| P12 | `domain/routing` | MOCK | ✅ | `scenario_router.py:355` "Mock execution for MVP" |
| P13 | `domain/sandbox` | SIMULATED | ✅ | `service.py:91` "Fast sandbox creation - simulated startup time < 200ms" |
| P14 | `domain/triggers` | MOCK | ✅ | `webhook.py:548` "Mock 執行 - 開發測試用" |
| P15 | `domain/orchestration` | MOCK+InMemory | ✅ | `sub_executor.py:264`, `recursive_handler.py:334` + **workflow_manager.py:566,599,637** (see Error 2) |
| P16 | `integrations/patrol` | MOCK FALLBACK | ✅ | `resource_usage.py:54` "psutil not installed, using mock data" |
| P17 | `integrations/llm` (dev) | MOCK FALLBACK | ✅ | `factory.py:234-239` dev mock with WARNING; `:226-231` production RuntimeError |
| P18 | `api/v1/orchestration` | MOCK FALLBACK | ✅ | `intent_routes.py:164` `create_mock_router`; `dialog_routes.py:161` `create_mock_dialog_engine` |
| P19 | `api/v1/cache` | MOCK FALLBACK | ✅ | `routes.py:79` "Failed to connect to Redis: Using mock service" |
| P20 | `integrations/knowledge` | FALLBACK | ✅ | `vector_store.py:73` in-memory; `embedder.py:51` hash-based pseudo-embedding |

---

## P21-P30: PARTIAL Modules — Detailed Verification

| # | Module | Doc Status | Verified | Evidence |
|---|--------|-----------|----------|----------|
| P21 | `integrations/agent_framework` | REAL+InMemory | ✅ | `checkpoint.py:653` InMemoryCheckpointStorage confirmed |
| P22 | `integrations/claude_sdk` | REAL+FALLBACK | ❌ | SmartFallback strategy names wrong (see Error 1) |
| P23 | `integrations/hybrid` | REAL+InMemory | ✅ | `switcher.py:183` InMemoryCheckpointStorage; `mediator.py:96` in-memory fallback |
| P24 | `integrations/orchestration` | REAL+MOCK+InMemory | ✅ | All three patterns confirmed |
| P25 | `integrations/ag_ui` | REAL+InMemory | ✅ | `thread/storage.py:276,341`; `sse_buffer.py:42,64`; `redis_storage.py` exists |
| P26 | `integrations/mcp` | REAL+InMemory | ✅ | `transport.py:321`; `audit.py:265` confirmed |
| P27 | `integrations/rootcause` | InMemory | ✅ | `case_repository.py:13` dual-mode (PostgreSQL + in-memory) |
| P28 | `integrations/incident` | REAL+InMemory | ✅ | `executor.py:24` InMemoryApprovalStorage import; rule-based fallbacks |
| P29 | `domain/checkpoints` | REAL | ⚠️ | Correct status but line ref `service.py:526` points to docstring (see W1) |
| P30 | `infrastructure/storage` | REAL (partial) | ✅ | Already corrected in doc (16 files listed, blob storage noted as not implemented) |

---

## P31-P40: InMemory Details — Detailed Verification

All 15 InMemory locations in Table B verified against source code with exact line numbers:

| # | Class | File:Line | Verified |
|---|-------|-----------|----------|
| 1 | InMemoryCheckpointStorage | `agent_framework/checkpoint.py:653` | ✅ |
| 2 | InMemoryThreadRepository | `ag_ui/thread/storage.py:276` | ✅ |
| 3 | InMemoryCache | `ag_ui/thread/storage.py:341` | ✅ |
| 4 | InMemoryApprovalStorage | `orchestration/hitl/controller.py:647` | ✅ |
| 5 | InMemoryDialogSessionStorage | `orchestration/guided_dialog/context_manager.py:690` | ✅ |
| 6 | InMemoryCheckpointStorage | `hybrid/switching/switcher.py:183` | ✅ |
| 7 | InMemoryTransport | `mcp/core/transport.py:321` | ✅ |
| 8 | InMemoryAuditStorage | `mcp/security/audit.py:265` | ✅ |
| 9 | InMemoryConversationMemoryStore | `domain/orchestration/memory/in_memory.py:29` | ⚠️ (deprecated label unverifiable) |
| 10 | InMemoryBackend | `infrastructure/storage/backends/memory.py:24` | ✅ |
| 11 | InMemoryStorageBackend | `infrastructure/storage/memory_backend.py:17` | ✅ |
| 12 | InMemoryLock | `infrastructure/distributed_lock/redis_lock.py:154` | ✅ |
| 13 | (inline dict) | `ag_ui/sse_buffer.py:42,64` | ✅ |
| 14 | AutonomousTaskStore | `api/v1/autonomous/routes.py:87` | ✅ (`_tasks: Dict[str, Dict]` at :91) |
| 15 | RootCauseStore | `api/v1/rootcause/routes.py:118` | ✅ (`_analyses: Dict[str, Dict]` at :122) |

Dict vs Redis fallback distinction:
- Items 1-9, 13: Pure `Dict[str, ...]` with no Redis fallback path in same module
- Item 10-11: `InMemoryBackend`/`InMemoryStorageBackend` used as fallback by `StorageFactory` when Redis/Postgres unavailable
- Item 12: `InMemoryLock` used as fallback when Redis unavailable — confirmed at `redis_lock.py:242`
- Items 14-15: Pure `Dict` in API layer — no fallback path, always in-memory

---

## P41-P50: Mock→Real Upgrade Path / Priority — Verification

| # | Claim | Verified | Notes |
|---|-------|----------|-------|
| P41 | HIGH risk InMemory → migrate to Redis/PostgreSQL | ✅ | Reasonable priority. 9 HIGH items identified correctly. |
| P42 | MEDIUM risk → next sprint migration | ✅ | 4 MEDIUM items are cache/lock/switching — lower business impact. |
| P43 | LOW risk → acceptable (test/deprecated) | ✅ | InMemoryTransport (test) and SSE buffer (transient) are correctly LOW. |
| P44 | LLM fallback chain: Azure → Claude SDK → MockLLMService(dev) / RuntimeError(prod) | ✅ | Spectrum diagram accurately depicts this chain. |
| P45 | Knowledge/RAG fallback: Qdrant → in-memory hash | ✅ | `vector_store.py:73` and `embedder.py:51` confirm the chain. |
| P46 | Patrol fallback: psutil → fabricated metrics | ✅ | `resource_usage.py:54` confirms. |
| P47 | SmartFallback chain: RETRY > SIMPLIFY > SKIP > HUMAN_ESCALATION | ❌ | Wrong enum names (see Error 1). Actual: RETRY > ALTERNATIVE > SKIP > ESCALATE > ROLLBACK > ABORT |
| P48 | Storage factory chain: Redis > Postgres > InMemory (dev) / RuntimeError (prod) | ✅ | `_resolve_backend_type` and `_handle_fallback` confirm. |
| P49 | Intent router: USE_REAL_ROUTER toggle with mock import from tests.mocks | ✅ | `intent_routes.py:54,164` confirm. |
| P50 | Frontend swarm: user toggle between useSwarmMock / useSwarmReal, default mock | ✅ | `SwarmTestPage.tsx:157` `useState<TestMode>('mock')` confirms default. |

---

## Corrections to Prior Verification Report

The initial `mock-real-map-verification.md` has these issues:

1. **P10 (line 61)**: States "RETRY > SIMPLIFY > SKIP > HUMAN_ESCALATION strategy chain" — this repeats the doc's error. Actual enum values differ (see Error 1 above).
2. **P47 (line 217)**: Same error repeated.
3. **P30/P50 (lines 140-141, 227-229)**: Flags `infrastructure/storage (file)` as "STUB — Empty directory" error, but the doc has already been corrected to "REAL (partial)" with 16 files listed. The verification report is stale on this point.

---

## Final Assessment

**44/50 points pass (88%)** — 2 confirmed errors, 4 warnings

The `mock-real-map.md` is a high-quality document with strong source-level evidence. The two errors are:
1. **SmartFallback enum names** — uses fictional names instead of actual source enum values
2. **domain/orchestration mock coverage** — omits 3 mock paths in `workflow_manager.py`

All 15 InMemory locations, all fallback patterns, all silent/explicit fallback paths, the frontend mock/real toggle, and the factory decision trees are verified accurate against source code.

# Sprint 51.2 — Progress

**Sprint**: 51.2 — Cat 3 Memory Layer (Level 0 → Level 3)
**Branch**: `feature/phase-51-sprint-2-cat3-memory-layer`（branched from 51.1 closeout `7595e60`）
**Period**: 2026-04-30
**Status**: ✅ DONE — Phase 51 完成 3/3

---

## Daily Log

### Day 0 — Plan + Checklist + Phase 51 README sync (estimate 4h / actual ~1h ≈ 25%)

- 起草 `sprint-51-2-plan.md`（9 章節 / 5 user stories / 雙軸 9-cell scope / MemoryHint 5 欄位擴展 / 13 acceptance）
- 起草 `sprint-51-2-checklist.md`（Day 0-5 ~50 tasks 含 DoD + verify cmd）
- Phase 51 README sync — 51.2 標 PLANNING + 範疇成熟度表加 Post-51.2 預期
- 環境確認：Day 0.3 grep 確認 `0007_memory_layers.py` migration + ORM 已存在於 49.3，Day 1.7 alembic migration N/A
- Commit `eb17d64` (3 files / +694 / -17)

### Day 1 — MemoryHint 擴展 + MemoryLayer ABC 微調 + 17.md sync (plan 6h / actual ~1.5h ≈ 25%)

- 開 feature branch `feature/phase-51-sprint-2-cat3-memory-layer`
- `_contracts/memory.py` MemoryHint 擴 5 欄位（time_scale / confidence / last_verified_at / verify_before_use / source_tool_call_id）
- `memory/_abc.py` write() ttl→time_scale + confidence；read() 加 time_scales 軸；新增 MemoryTimeScale enum helper
- 17.md §1.1 + §2.1 sync
- 預期 ≤ 3 callers blast radius — 實際 0 constructor callers in src/tests
- Commit `4ab5ef8` (3 files / +100 / -21)；mypy 56 src clean / 73 unit tests + 1 platform-skip pass

### Day 2 — 5 Layer concrete impl + 31 unit tests (plan 7h / actual ~2h ≈ 29%)

- `memory/layers/__init__.py` re-exports
- `user_layer.py` 核心（PG memory_user；4 spec 欄位存 metadata JSONB；24h TTL for short_term）
- `tenant_layer.py`（PG memory_tenant；long_term only；short_term raise）
- `system_layer.py`（read-only；SystemReadOnlyError）
- `role_layer.py`（簡化版；write/evict raise NotImplementedError）
- `session_layer.py` **改 in-memory dict** vs plan Redis（49.x cache 仍 stub；CARRY-029 promote 到 Redis when ready）
- 5 test files / 31 tests（超 plan 26）
- Commit `f7d0614` (12 files / +1483 / 0 deletions)；mypy 62 src / 31 layer tests + 104 wider sanity pass

### Day 3 — Retrieval + ConflictResolver + Extraction + 20 unit tests (plan 6h / actual ~1.5h ≈ 25%)

- `retrieval.py` `MemoryRetrieval` 跨層 search；asyncio.gather 並行；session_id slot 路由；relevance×confidence 排序；layer exception non-fatal
- `conflict_resolver.py` 4 條規則（high-conf / fresh-verified / layer-specificity / HITL fallback `RequiresHumanReviewError`）
- `extraction.py` `MemoryExtractor` 手動觸發；ChatRequest + ChatClient ABC（中性，0 LLM SDK leak）；tolerant JSON parser；clamp confidence [0,1]
- 中途修正：ChatClient.chat 簽名是 `chat(request: ChatRequest, ...)` 不是 `chat(messages=, tools=)`
- 3 test files / 20 tests（超 plan 17：8 retrieval + 8 conflict + 4 extraction）
- Commit `948fcd5` (6 files / +843 / 0 deletions)；mypy 65 src clean / 51 memory tests + 124 wider sanity pass

### Day 4 — memory_tools placeholder→real + register_builtin_tools wire + 8 integration tests + 17.md §3.1/§4.1 sync (plan 5h / actual ~1.5h ≈ 30%)

- `tools/memory_tools.py` 重寫：MEMORY_SEARCH_SPEC schema 加 time_scales；MEMORY_WRITE_SPEC 加 time_scale + confidence；移 placeholder tag；新增 `make_memory_search_handler` / `make_memory_write_handler` 工廠；保留 `memory_placeholder_handler` 作 dev fallback
- `tools/__init__.py register_builtin_tools` 接 optional `memory_retrieval` + `memory_layers`；real wired 時用 factory + isinstance 驗證；無 wired 時 placeholder
- Plan 偏差：plan 寫 wire 在 `business_domain/_register_all.py` → 改 `tools/__init__.py` 對應 51.1 builtin pattern
- 8 integration tests（超 plan 6）
- Bug fix：刪除 `tests/unit/agent_harness/memory/__init__.py` + `tests/integration/memory/__init__.py`（pytest 套件名衝突，convention path-based discovery）
- 17.md §3.1 memory rows 移 placeholder mark / §4.1 MemoryAccessed event payload 擴
- Commit `2ad3fa2` (6 files / +679 / -86)；mypy 65 src clean / 132 wider sanity pass

### Day 5 — Tenant Isolation + Lead-then-Verify e2e + Extraction worker integration + retro + closeout (plan 4h / actual ~1.5h ≈ 38%)

- `tests/integration/memory/test_tenant_isolation.py` ~5 tests — multi-tenant red-team（cross-tenant search 0 leak / write isolated / session composite key / user retrieval filter / extraction no pollution）
- `tests/integration/memory/test_extraction_worker.py` ~3 tests — 5-message session extraction / no SDK leak / tenant-user provenance
- `tests/e2e/test_lead_then_verify_workflow.py` ~2 tests — stale hint verify-then-rewrite flow + consistent path
- Phase 51 README ✅ DONE marker；範疇成熟度 Cat 3 Level 0 → Level 3
- 寫 progress.md + retrospective.md
- Commit Day 5 closeout（待）

---

## Test Totals

| Stage | Active Pass | Platform Skip |
|-------|-------------|---------------|
| 51.1 closeout (baseline) | 315 | 1 |
| 51.2 Day 1 (extend MemoryHint) | 73 unit/agent_harness | 1 |
| 51.2 Day 2 (5 layers) | 104 unit/agent_harness | 1 |
| 51.2 Day 3 (retrieval+resolver+extraction) | 124 unit/agent_harness | 1 |
| 51.2 Day 4 (real handlers) | 132 unit + integration/memory | 1 |
| **51.2 Day 5 closeout** | **142** unit + integration/memory + e2e/lead-then-verify | **1** |

51.2 net delta vs Day 1 baseline (73): **+69 tests** (10 Day 5 NEW + 8 Day 4 + 20 Day 3 + 31 Day 2)

---

## Estimate Accuracy

| Day | Plan | Actual | % | Theme |
|-----|------|--------|---|-------|
| 0 | 4h | ~1h | 25% | Plan + checklist + Phase README sync |
| 1 | 6h | ~1.5h | 25% | MemoryHint extension + ABC + 17.md sync |
| 2 | 7h | ~2h | 29% | 5-layer concrete impl + 31 unit tests |
| 3 | 6h | ~1.5h | 25% | Retrieval + ConflictResolver + Extraction + 20 tests |
| 4 | 5h | ~1.5h | 30% | memory_tools real + register wire + 8 integration tests |
| 5 | 4h | ~1.5h | 38% | Tenant isolation + lead-then-verify + retro + closeout |
| **Total** | **32h** | **~9h** | **28%** | — |

V2 7-sprint cumulative avg: ~21-25%; 51.2 28% slightly above (Day 5 retro work + Day 4 mock-pattern setup added cycles vs estimate).

---

**Maintainer**: User + AI assistant
**Created**: 2026-04-30 (Sprint 51.2 Day 5 closeout)

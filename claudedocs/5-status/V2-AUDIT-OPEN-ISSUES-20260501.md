# V2 Audit Open Issues — 2026-05-01

**Audit window**: W1+W2 (2026-04-29) + W3 (2026-05-01)
**Coverage**: Sprint 49.1 → 51.2 (10/22 V2 sprints)
**Tracking**: GitHub issues + this index doc + monthly review

---

## P0 Open Issues (4)

All blocking Phase 53.x; **must close before Phase 53.1 worker fork** (修補成本翻倍 mitigation).

| # | Issue | Effort | Status |
|---|-------|--------|--------|
| [#11](https://github.com/laitim2001/ai-semantic-kernel-framework-project/issues/11) | chat router multi-tenant 隔離 (W3-2 Critical 1) | 1-2 days | 🔴 Open |
| [#12](https://github.com/laitim2001/ai-semantic-kernel-framework-project/issues/12) | TraceContext propagation at chat handler (W3-2 Critical 2) | half day | 🔴 Open |
| [#13](https://github.com/laitim2001/ai-semantic-kernel-framework-project/issues/13) | audit_log hash chain verifier (W1-3) | 2-3 days | 🔴 Open |
| [#14](https://github.com/laitim2001/ai-semantic-kernel-framework-project/issues/14) | JWT replace X-Tenant-Id header (W1-2) | 1-2 days | 🔴 Open |

**Total effort**: 5-8 days → recommended single 7-day cleanup sprint per `V2-AUDIT-CLEANUP-SPRINT-TEMPLATE.md`.

**Labels**: `audit-carryover` + `priority/P0`

---

## P1 Status (8)

| # | Item | Status | Resolution |
|---|------|--------|------------|
| W1-2 #3 | delete `backend/src/middleware/tenant.py` stub | ✅ Fixed | PR [#10](https://github.com/laitim2001/ai-semantic-kernel-framework-project/pull/10) commit `ab0d727d` |
| W2-1 #5 | CI lint scope expansion | ✅ Fixed | PR [#10](https://github.com/laitim2001/ai-semantic-kernel-framework-project/pull/10) commit `d3070e12` |
| W2-1 #4 | `adapters/azure_openai/tests/test_integration.py` | ⏳ Pending | Cleanup sprint Day 6.4 |
| W2-2 #6 | `requirements.txt` Celery cleanup + temporalio TODO | ⏳ Pending | Cleanup sprint Day 6.1 |
| W2-2 #7 | unify `runtime/workers/` ↔ `platform_layer/workers/` | ⏳ Pending | Cleanup sprint Day 6.2 |
| W2-2 #8 | AgentLoopWorker docstring stub warning | ⏳ Pending | Cleanup sprint Day 6.3 |
| W3-1 | mutable `LoopState` → frozen + reducer | ⏳ Phase 53.1 | Carryover (CARRY-007) transparently noted |
| W3-1 | `ToolCallExecuted/Failed` event owner drift | ⏳ Phase 51.x | Carryover (CARRY-009) transparently noted |

---

## Process Fixes (W3 #1-#5)

| # | Fix | Status | Location |
|---|-----|--------|----------|
| 1 | Sprint plan template 加 Audit Carryover 段落 | ✅ Done | `phase-52-context-prompt/sprint-52-2-plan.md` §10 |
| 2 | Retrospective template 加 Audit Debt 段落 | ✅ Done | `phase-52-context-prompt/sprint-52-2-checklist.md` Day 4.9 |
| 3 | GitHub issue per P0/P1 | ✅ Done | This doc + issues #11-14 |
| 4 | 每月 Audit Status Review | ⏳ Scheduled | Manual review (next: 2026-06-01) |
| 5 | Audit re-verify 每 2-3 sprint | ⏳ Scheduled | W4 audit post-cleanup + 52.2 close |

---

## Audit Deliverables (13 reports)

### Week 1 (2026-04-29)
- `V2-AUDIT-BASELINE-20260429.md` — 起點 baseline (54 交付項 + 24 高風險)
- `V2-AUDIT-W1-CONTRACTS.md` — `_contracts/` 跨 sprint 一致性 ✅
- `V2-AUDIT-W1-RLS.md` — RLS + tenant_id 0-leak ✅
- `V2-AUDIT-W1-AUDIT-HASH.md` — Audit hash chain ⚠️ (P0 #3 source)
- `V2-AUDIT-W1-ORM-LOCK.md` — ORM TenantScopedMixin + StateVersion ✅
- `V2-AUDIT-WEEK1-SUMMARY.md`

### Week 2 (2026-04-29)
- `V2-AUDIT-W2-ADAPTER.md` — Adapter + LLM Neutrality ✅
- `V2-AUDIT-W2-WORKER.md` — Worker queue + agent_loop_worker ⚠️
- `V2-AUDIT-WEEK2-SUMMARY.md`

### Week 3 (2026-05-01)
- `V2-AUDIT-W3-0-CARRYOVER.md` — Process drift ❌ (7/8 P1 dropped)
- `V2-AUDIT-W3-1-PHASE50-1.md` — Cat 1 Loop + AP-1 lint ✅
- `V2-AUDIT-W3-2-PHASE50-2.md` — Phase 50.2 主流量 🟡 (P0 #1+#2 source)
- `V2-AUDIT-WEEK3-SUMMARY.md` — 雙層問題決策報告

### Cleanup Template
- `V2-AUDIT-CLEANUP-SPRINT-TEMPLATE.md` — Sprint plan + checklist template (593 行)

---

## W4 Audit Trigger

**Pre-conditions** (all must hold):
1. All 4 P0 issues (#11-14) closed
2. 4 pending P1 resolved (cleanup sprint Day 6)
3. Sprint 52.2 closed with retrospective filed
4. Cleanup sprint closed with retrospective filed (per template Day 7)

**W4 scope**:
- Re-verify W1-2 (RLS + JWT) post-fix
- Re-verify W1-3 (audit hash) post-verifier
- Re-verify W3-2 (Phase 50.2 main flow) post-fix
- Audit Sprint 52.2 (PromptBuilder)
- Audit Sprint 51.0/51.1/51.2 (Tools + Memory) — first time covered
- Audit cleanup sprint itself (process discipline check)

**Estimated W4 duration**: 4-6 hours (similar to W3)

---

## Index Maintenance

This doc is the single source of truth for V2 audit follow-up status. Update when:
- Issue closes → mark P0 status `✅ Fixed (issue #N)`
- New audit week completes → add new row + update W4 trigger conditions
- Process fix matures → flip ⏳ to ✅

**Last updated**: 2026-05-01 (audit session)

# Sprint 49.3 Progress

**Sprint**: 49.3 — RLS + Audit Append-Only + Memory + Qdrant Tenant 隔離
**Branch**: `feature/phase-49-sprint-3-rls-audit-memory`
**Started**: 2026-04-29
**Closed**: 2026-04-29
**Plan**: [`sprint-49-3-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-3-plan.md)
**Story Points**: 26 (planned) → all completed

---

## Day-by-Day estimate vs actual

| Day | Plan | Actual | Ratio | Notes |
|-----|------|--------|-------|-------|
| Day 1 — Audit log + append-only + hash chain + state_snapshots TRUNCATE 補 | 5h | ~50 min | 17% | TRUNCATE state_snapshots 需 CASCADE 才到 trigger（FK + trigger 雙擋變多一層 defense） |
| Day 2 — api_keys + rate_limits + 5 memory tables | 6h | ~45 min | 12.5% | Role.display_name (NOT NULL) 而非 plan 的 name；test 修 1 次 |
| Day 3 — Governance 3 tables | 5h | ~30 min | 10% | 3 表全 junction-via-session（plan 說 TenantScopedMixin → 09.md 權威修正） |
| Day 4 — RLS 13 tables + middleware + RLS tests | 7h | ~55 min | 13% | 關鍵：ipa_v2 SUPERUSER+BYPASSRLS 繞 RLS — 需建 rls_app_role NOLOGIN 真驗 |
| Day 5 — Qdrant abstraction + 紅隊 + closeout | 5h | ~50 min | 17% | AV-3 需 SAVEPOINT；event-loop closed 需 middleware test 加 dispose autouse fixture |
| **Total** | **28h** | **~3.7h** | **13%** | 對齊 49.2 ~15% 比例（plan 估算偏保守）|

---

## Daily highlights

### Day 1 (2026-04-29)
- Migrations 0005 + ROW + STATEMENT TRUNCATE triggers on audit_log + state_snapshots
- audit_helper.py: SENTINEL_HASH + canonical SHA-256 + tenant-scoped chain
- 6 audit tests + 49.2 deferred test_state_snapshot_truncate_blocked 啟用通過
- 32 PASS / 0 SKIPPED（49.2 26 + 49.3 6；49.2 留的 1 skip 消除）

### Day 2 (2026-04-29)
- 0006 api_keys + rate_limits（對齐 09.md：key_prefix / permissions / rate_limit_tier）
- 0007 5 memory layers（memory_system 全局、memory_tenant + memory_user TenantScopedMixin、memory_role + memory_session_summary junction）
- 11 tests pass（plan 寫 10 → 多加 rate_limit UNIQUE test）
- 43 PASS

### Day 3 (2026-04-29)
- 0008 governance 3 表（approvals / risk_assessments / guardrail_events）全 junction-via-session
- 6 governance tests 含 cross-tenant via JOIN sessions
- 49 PASS

### Day 4 (2026-04-29)
- 0009 RLS：13 tables × 2 policies = 26 total
- platform_layer/middleware first launch：TenantContextMiddleware + get_db_session_with_tenant
- 4 middleware tests + 6 RLS enforcement tests
- 關鍵發現 + 設計：ipa_v2 是 SUPERUSER + BYPASSRLS（繞 FORCE RLS），測試需建 `rls_app_role` NOLOGIN + SET LOCAL ROLE 切換
- pg_partman 🚧 → 49.4（postgres:16-alpine image 不支援）
- 59 PASS

### Day 5 (2026-04-29)
- Qdrant namespace abstraction（不接 client；51.2 接）+ 3 tests
- 紅隊 6 攻擊向量（AV-1 至 AV-6）全擋
- 全套 alembic cycle from base 跑通
- closeout：3 個 README + progress + retrospective + Phase 49 README + checklist 全 [x]
- **73 PASS** / 0 SKIPPED / ~3.2s

---

## Surprises / 對齐 09.md 修正記錄

1. **audit_log 不 partition**：plan 過度設計 `+ 3 monthly partitions`，09.md L658 為單表設計 → 移除
2. **api_keys 欄位名**：plan `last_4` / `scopes` → 09.md `key_prefix` / `permissions`
3. **rate_limits 無 api_key_id**：09.md per-tenant-per-resource-per-window 模型
4. **Governance 3 表 + memory_role / memory_session_summary 全 junction-via-session**：plan 寫 TenantScopedMixin 全錯，09.md 權威無 tenant_id 欄位
5. **RLS 13 表（不是 14）**：plan 把 approvals/risk/guardrail 算入，但這 3 表是 junction → 不掛 RLS
6. **TRUNCATE state_snapshots**：sessions FK 反向參照先擋；測試需 `CASCADE` 才到 trigger（變相 FK + trigger 雙擋）
7. **ipa_v2 SUPERUSER + BYPASSRLS**：繞所有 RLS 包括 FORCE → RLS 驗證測試必須 SET LOCAL ROLE 切非 bypass role
8. **pg_partman extension 不在 image**：postgres:16-alpine 不含；🚧 → 49.4
9. **Event loop closed**：middleware tests 用 FastAPI/httpx 共享 engine singleton；需 autouse fixture 在每 test 後 dispose_engine（同 49.2 retro pattern 擴展到 middleware tests）

---

## Cumulative branch state

```
feature/phase-49-sprint-3-rls-audit-memory
├── 7561358 docs(sprint-49-3): plan + checklist
├── 6613642 feat(infrastructure-db): Day 1 audit log append-only + hash chain
├── 66f3881 feat(infrastructure-db): Day 2 api_keys + rate_limits + 5 memory layers
├── 1d35253 feat(infrastructure-db): Day 3 governance — approvals + risk + guardrail
├── 2413e41 feat(platform-layer): Day 4 RLS 13 tables + tenant_context middleware
└── (closeout commit, this) Day 5 closeout
```

---

## Quality gates passed (all green)

- pytest: **73/73 PASS** (49.2 26 + 49.3 47; 0 SKIPPED)
- mypy --strict: 0 issues on all 49.3 source files
- black + isort + flake8: clean
- LLM SDK leak grep on agent_harness/ + infrastructure/ + platform_layer/: 0
- alembic downgrade base → upgrade head from zero: ✅
- Multi-tenant rule check: 鐵律 1/2/3 all ✅

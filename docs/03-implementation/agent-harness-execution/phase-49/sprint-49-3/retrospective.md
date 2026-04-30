# Sprint 49.3 Retrospective

**Sprint**: 49.3 — RLS + Audit Append-Only + Memory + Qdrant Tenant 隔離
**Branch**: `feature/phase-49-sprint-3-rls-audit-memory`
**Started**: 2026-04-29
**Closed**: 2026-04-29
**Plan**: [`sprint-49-3-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-3-plan.md)
**Story Points**: 26 (planned) → all completed

---

## Outcome summary

Sprint 49.3 delivered the **complete multi-tenant security baseline** that all subsequent business sprints depend on:

| Deliverable | Status |
|-------------|--------|
| audit_log append-only + hash chain + ROW + STATEMENT triggers | ✅ |
| state_snapshots STATEMENT TRUNCATE trigger（49.2 deferred 補裝）| ✅ |
| api_keys + rate_limits | ✅ |
| 5-layer memory schema (system / tenant / role / user / session_summary) | ✅ |
| Governance 3 表 (approvals / risk_assessments / guardrail_events) | ✅ |
| RLS policies on 13 tenant-scoped tables (26 policies) | ✅ |
| TenantContextMiddleware + get_db_session_with_tenant dep | ✅ |
| QdrantNamespaceStrategy（per-tenant collection + payload filter）| ✅ |
| 紅隊 6 攻擊向量驗證 0 leak | ✅ |
| 73 PASS / 0 SKIPPED / 0 LLM SDK leak | ✅ |
| 49.2 retro action items 清算（state_snapshots TRUNCATE）| ✅ |

---

## Estimates vs Actual

| Day | Plan | Actual | Ratio |
|-----|------|--------|-------|
| Day 1 — Audit log + append-only + hash chain | 5h | ~50 min | 17% |
| Day 2 — api_keys + rate_limits + 5 memory layers | 6h | ~45 min | 12.5% |
| Day 3 — Governance 3 tables | 5h | ~30 min | 10% |
| Day 4 — RLS + middleware + RLS tests | 7h | ~55 min | 13% |
| Day 5 — Qdrant + 紅隊 + closeout | 5h | ~50 min | 17% |
| **Total** | **28h** | **~3.7h** | **13%** |

對齊 49.2 (15%) — 計畫估算保守是 V2 sprint workflow 的**特色**而非 bug；保留 buffer 應對 schema 對齐意外。

---

## What went well

### 1. AC-10 紅隊 6 攻擊向量全綠
紅隊套件成為本 sprint 最關鍵的驗收測試。AV-1（forged tenant）/ AV-2（missing SET LOCAL）/ AV-3（SQL injection）/ AV-4（UPDATE audit）/ AV-5a/b（TRUNCATE audit + state）/ AV-6（Qdrant 跨 namespace）全擋。

### 2. RLS 真驗測試（rls_app_role）
ipa_v2 是 SUPERUSER + BYPASSRLS 是預期之外但**極關鍵的發現**。若沒發現，測試會 false-positive（看似通過 RLS，實際被 bypass）。設計 `rls_app_role` + `SET LOCAL ROLE` 切換是真實驗 RLS 的唯一可行模式。同時提示生產環境部署必須用非-BYPASSRLS app role。

### 3. 雙擋 defense-in-depth 多次自然湧現
- TRUNCATE state_snapshots：sessions FK 反向參照（先擋）+ STATEMENT trigger（CASCADE 後再擋）
- audit_log：ROW UPDATE/DELETE trigger + STATEMENT TRUNCATE trigger
- Qdrant：collection name 隔離 + payload filter
這種多層保護不是 over-engineering 是 09.md / 14.md 設計權威要求；落地後反而幫助測試覆蓋率。

### 4. 09.md 權威同步成本可控
本 sprint 6 處 plan 過度設計（partition / 欄位名 / TenantScopedMixin / RLS 14 vs 13）全部對齐 09.md 修正，每處在 commit message + checklist 明文記錄。回顧時可清楚追溯為何 plan 與 schema 有差異 + 為何選 09.md 為權威。

### 5. 49.2 retro action items 全清
49.2 retro 列 7 項，本 sprint 處理：
- ✅ state_snapshots STATEMENT TRUNCATE trigger（隨 0005 一起裝）
- 🚧 pg_partman rolling +6 months → 49.4（image 不支援）
- 🚧 tool_calls.message_id FK → 49.4+（仍待 PG 18 partial-partition FK）
- 🚧 CI .ini ASCII-only lint → 49.4 lint rules
- ⏸ session.py coverage 43% → 49.3+ FastAPI integration test（本 sprint 不接 endpoint，留下個業務 sprint）
- ⏸ branch protection rule（用戶 admin UI；carryover）
- ⏸ npm audit 2 moderate vulnerabilities（carryover）

---

## What surprised us / what to improve

### 1. ⚠️ ipa_v2 SUPERUSER + BYPASSRLS
**Severity**: 設計核心發現；若未察覺 RLS 測試全部 false-positive

dev container 的 ipa_v2 role 是 SUPERUSER + BYPASSRLS（`SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='ipa_v2'` 兩者都 t）。SUPERUSER 繞所有 RLS 包括 FORCE。為真實驗 RLS，測試在 transaction 內建 `rls_app_role` NOLOGIN + GRANT CRUD + `SET LOCAL ROLE` 切換。

**Action item**: 49.4 deployment guide 必須明示生產 app role 不可有 BYPASSRLS / SUPERUSER。

### 2. ⚠️ pg_partman 不在 postgres:16-alpine
**Severity**: 49.2 carryover + 49.3 carryover 均推遲

`SELECT name FROM pg_available_extensions WHERE name LIKE 'pg_partman%'` 回零行。需 image 換 `postgres:16` full + 自訂 Dockerfile + docker-compose env 改動，超出 49.3 scope。

**Action item**: 49.4 lint+infra 階段同步 image 升級 + pg_partman extension setup（含 messages / message_events / audit_log 三 partitioned table 的 create_parent setup）。

### 3. ⚠️ Plan 過度設計：09.md 權威需先讀
**Severity**: 6 處 schema 偏差需修；commit message 需詳記

Plan 預先猜測欄位名 / mixin 使用，多處與 09.md 不符。每 Day 開工前需先 `Grep CREATE TABLE` + `Read` 對應 09.md 段落驗證 plan，再開始實作。

**Action item**: 49.4 + 後續 sprint plan 起草時務必逐行對齐 09.md / 14.md 等權威；plan 中欄位描述不可寫「可能」「大致」必須 100% 對應源頭。

### 4. ⚠️ TRUNCATE FK 反向參照
**Severity**: AV-5b test design 1 次重做

TRUNCATE state_snapshots 會被 sessions FK 反向參照先擋（FeatureNotSupportedError），STATEMENT trigger 不會 fire。測試需 `TRUNCATE state_snapshots CASCADE` 才能驗 trigger。

意外結果：FK + trigger 雙擋成為 defense-in-depth；test docstring 已說明。

### 5. ⚠️ memory_role / memory_session_summary / approvals / risk_assessments / guardrail_events 全 junction
**Severity**: 設計層級偏離；plan 5 處連續錯誤需修

Plan 把這 5 表全標 TenantScopedMixin。09.md 權威：除 memory_tenant + memory_user 外，其他 5 表均為 junction-via-FK（role / session）。這是 09.md 設計選擇 — junction tables 透過 FK chain 解 tenant，避免 redundant column。

**修正**：5 表全純 junction（無 tenant_id 欄）；RLS 也跳過（13 不是 14 表）；cross-tenant test 改用 JOIN sessions 過濾。

### 6. ⚠️ Test 跨 file event-loop closed
**Severity**: 全套 pytest run 1 fail（單獨 run 7/7 pass）

`test_tenant_context.py` 用 FastAPI/httpx 共享 engine singleton；conftest's db_session fixture 已 dispose engine 但 middleware tests 不走該 fixture。下一個 file (test_red_team_isolation) 第一個 test 在 cleanup 階段拿到 closed loop 的 connection 報錯。

**修正**: middleware test file 加 autouse fixture `_dispose_engine_after_each_test`。

**Action item**: 任何用 FastAPI/httpx + 共享 engine 的測試 file 必須加類似 autouse dispose；49.4 起的 endpoint integration tests 套用此 pattern。

### 7. ⚠️ AV-3 SQL injection cast 需 SAVEPOINT
**Severity**: AV-3 test design 1 次重做

`set_config(...)` + 後續 SELECT 觸發 ::uuid cast 失敗 → DBAPIError → transaction aborted；rollback 摧毀 rls_app_role（也是同一 tx 創建的）→ 下個 iteration「role does not exist」。

**修正**: 用 `db_session.begin_nested()` SAVEPOINT，每個 bogus 值在獨立 savepoint 內測試 + rollback；外層 tx + role 不受影響。

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

7 commits（含 closeout）。Branch sits 31+ commits ahead of `main` because it carries forward all 49.1 + 49.2 work.

---

## Sprint 49.4 prerequisites unblocked

- ✅ All 13 ORM models registered + 26 RLS policies in place
- ✅ `TenantContextMiddleware` + `get_db_session_with_tenant` ready for endpoint integration
- ✅ Governance 3 tables ready for HITL Frontend (Phase 53.4)
- ✅ Memory 5 tables ready for Phase 51.2 retrieval / extraction
- ✅ QdrantNamespaceStrategy ready for Phase 51.2 client integration
- ✅ Audit hash chain ready for governance / compliance integration
- ✅ Real PostgreSQL CI service in place

Sprint 49.4 plan + checklist creation: **NEXT** (rolling planning per `.claude/rules/sprint-workflow.md`).

---

## Action items for Sprint 49.4+ (carry forward)

1. **pg_partman setup**: install extension（image 升級 → `postgres:16` full + Dockerfile）+ create_parent for messages / message_events / audit_log（p_premake=6）
2. **App role for production**: deployment guide 明示 `app_role NOLOGIN + GRANT CRUD + no BYPASSRLS / no SUPERUSER`；連線字串改用此 role
3. **CI lint**: `.ini` ASCII-only + cross-category-import check + LLM SDK leak script（rule 1-3 from 17.md §8.1-8.3）
4. **`tool_calls.message_id` FK**: revisit either via composite (id, created_at) or wait for PG 18 partial-partition FK
5. **session.py + middleware coverage**: integration test when first FastAPI endpoint lands (50.2)
6. **Branch protection rule**: 用戶 GitHub UI（carry from 49.1）
7. **49.1+49.2+49.3 merge to main**: 用戶決定直 push 或開 PR
8. **npm audit 2 moderate vulnerabilities**: 後續 sprint
9. **Worker queue 選型 PoC**: Celery vs Temporal（49.4 deliverable per roadmap）

---

## Approvals & sign-off

- [x] All checklist items closed (or explicitly deferred with `🚧` annotation)
- [x] All linters pass (black / isort / flake8 / mypy strict on all 49.3 source files)
- [x] 73 PASS + 0 SKIPPED (47 new in 49.3 + 26 inherited from 49.2)
- [x] Migration cycle from zero proven (downgrade base → upgrade head)
- [x] Real PostgreSQL via docker compose throughout
- [x] LLM SDK leak grep: 0 imports
- [x] CI workflow inherits 49.2 setup (no new CI required for 49.3)
- [x] Phase 49 README updated (3/4 sprint complete = 75%)

**Sprint 49.3 status**: ✅ DONE

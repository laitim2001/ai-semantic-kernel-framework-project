# Phase 49 — Foundation

**Phase 進度**：Sprint 49.3 ✅ DONE — **3 / 4 sprint complete**（75%）
**啟動日期**：2026-04-28
**目標完成**：2026-05-26（4 sprint × 1 週）

---

## Phase 49 目標

> 建立 V2 完整骨架（不寫業務邏輯）：CI / DB / RLS / Workers / Adapters / OTel + Lint。
> 所有後續 18 個 sprint 都依賴本 Phase 完成。

詳細路線圖見 [`../06-phase-roadmap.md` §Phase 49](../06-phase-roadmap.md#phase-49-foundation4-sprint-原-3)。

---

## Sprint 進度總覽

| Sprint | 狀態 | 主題 | 完成日期 | Branch / Commits |
|--------|------|------|---------|------------------|
| **49.1** | ✅ DONE | V1 封存 + V2 目錄骨架 + CI Pipeline | 2026-04-29 | `feature/phase-49-sprint-1-v2-foundation`（13 commits）|
| **49.2** | ✅ DONE | DB Schema + Async ORM 核心 | 2026-04-29 | `feature/phase-49-sprint-2-db-orm`（7 commits）|
| **49.3** | ✅ DONE | RLS + Audit Append-Only + Memory + Qdrant 隔離 | 2026-04-29 | `feature/phase-49-sprint-3-rls-audit-memory`（7 commits）|
| 49.4 | 📋 待啟動 | Adapters + Worker Queue 選型 + OTel + Lint Rules | TBD | TBD |

---

## Sprint 文件導航

```
phase-49-foundation/
├── README.md                          ← (this file) Phase 49 入口
├── sprint-49-1-plan.md                ✅ DONE
├── sprint-49-1-checklist.md           ✅ DONE
├── sprint-49-2-plan.md                ✅ DONE
├── sprint-49-2-checklist.md           ✅ DONE
├── sprint-49-3-plan.md                📋 待 Sprint 49.2 收尾後建立（rolling planning）
├── sprint-49-3-checklist.md           📋 同上
├── sprint-49-4-plan.md                📋 待 49.3 收尾後建立
└── sprint-49-4-checklist.md           📋 同上
```

執行紀錄在：
```
docs/03-implementation/agent-harness-execution/phase-49/
├── sprint-49-1/
│   ├── progress.md
│   ├── retrospective.md
│   └── artifacts/
└── sprint-49-2/
    ├── progress.md
    └── retrospective.md
```

---

## Phase 49 累計交付（3/4 sprint）

### Sprint 49.1 ✅
- V1 (Phase 1-48) → `archived/v1-phase1-48/`（READ-ONLY；tag `v1-final-phase48`）
- V2 backend 5 層骨架 + 11+1 ABC 全部可 import
- `_contracts/` single-source 跨範疇型別包
- `ChatClient` ABC（`adapters/_base/`）
- `HITLManager` ABC（中央化）
- V2 frontend 骨架（React 18 + Vite 5 + Zustand + ESLint flat）
- `docker-compose.dev.yml`（postgres / redis / rabbitmq / qdrant）
- GitHub Actions CI（backend-ci.yml + frontend-ci.yml + PR template）

### Sprint 49.2 ✅
- Alembic 系統 + 4 migrations（identity / sessions partition / tools / state）
- 13 ORM models + 1 mixin（TenantScopedMixin 強制鐵律 1）
- `engine.py` + `session.py` + `exceptions.py` 含 `StateConflictError`
- StateVersion 雙因子（counter + content_hash）樂觀鎖
- state_snapshots append-only trigger
- 3 個月 partition Day 1（messages + message_events × 2026-04/05/06）
- 29 unit tests + real docker compose PostgreSQL（AP-10 對策）
- CI 升級：spin up postgres service + alembic step + 嚴格 flake8
- 49.1 retro action items 清算（02/03/04/05/06.md `platform/` → `platform_layer/` 22 處）

### Sprint 49.3 ✅
- Audit log append-only + hash chain（ROW UPDATE/DELETE + STATEMENT TRUNCATE）
- 5 layer memory schema（system / tenant / role / user / session_summary）
- API auth + quotas（api_keys + rate_limits）
- Governance（approvals + risk_assessments + guardrail_events）
- RLS policies on 13 tenant-scoped tables（26 policies；ENABLE + FORCE）
- platform_layer/middleware first launch：TenantContextMiddleware + get_db_session_with_tenant
- QdrantNamespaceStrategy（per-tenant collection + payload filter；client integration → 51.2）
- 紅隊 6 攻擊向量驗證 0 leak（AC-10 acceptance suite）
- 73 unit + security tests，0 SKIPPED
- 49.2 retro carryover：state_snapshots STATEMENT TRUNCATE trigger 補裝
- 🚧 pg_partman → 49.4（postgres:16-alpine 不支援 extension）

---

## Phase 49 結束驗收（依 06-phase-roadmap.md）

完成 49.4 後應達到：
- ✅ 整體基礎設施 100% 就緒
- ✅ CI / Lint / OTel 全部上線
- ✅ 11 範疇 + 範疇 12 成熟度全部 Level 0（合理 — 還沒實作；50.1 起進 Level 1+）
- ✅ 接下來可開始實作範疇

---

## 下一步

**用戶下次 session 開始時**：
1. 用 `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md` onboarding
2. 指示「啟動 Sprint 49.3 — RLS + Audit + Memory + Qdrant」
3. AI 助手依 rolling planning 建 49.3 plan + checklist 等用戶 approve 才 code

**注意**：本 Phase 49 README 在 Sprint 49.2 Day 5.6 closeout 時補建（per 49.2 回顧的 option B 決策；不影響 49.1+49.2 已完成的工作）。

---

**Last Updated**：2026-04-29 (Sprint 49.2 closeout)
**Maintainer**：用戶 + AI 助手共同維護

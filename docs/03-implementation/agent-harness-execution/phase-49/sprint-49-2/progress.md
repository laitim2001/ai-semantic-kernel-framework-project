# Sprint 49.2 — Progress Log

**Sprint**: 49.2 — DB Schema + Async ORM 核心
**Plan**: [`../../../agent-harness-planning/phase-49-foundation/sprint-49-2-plan.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-2-plan.md)
**Checklist**: [`../../../agent-harness-planning/phase-49-foundation/sprint-49-2-checklist.md`](../../../agent-harness-planning/phase-49-foundation/sprint-49-2-checklist.md)
**Branch**: `feature/phase-49-sprint-2-db-orm`（從 49.1 branch carry forward）
**Started**: 2026-04-29
**Story Points**: 22

---

## Day 1 — Alembic 基底 + Identity migration + ORM (2026-04-29)

**Plan estimate**: 5h
**Actual**: ~50 min（持續 49.1 的 ~24% 比率）
**Commits planned for end of day**: 1

### Tasks completed

| Task | Status | Notes |
|------|--------|-------|
| 1.1 Pre-flight check | ✅ | Branch carry-forward from 49.1 (main 落後 16 commits)；docker postgres healthy；deps 4 件全 ok |
| 1.2 Alembic 基底 (alembic.ini + env.py + script.py.mako + 2 __init__) | ✅ | env.py 用 SQLAlchemy 2.0 async pattern + NullPool |
| 1.3 Base + TenantScopedMixin + exceptions | ✅ | TenantScopedMixin 用 declared_attr ensure subclass 各有獨立 column |
| 1.4 engine.py + session.py + Settings 4 fields + .env.example | ✅ | Real PG 16.10 ping pass; pool=10/overflow=20/recycle=300/echo=False |
| 1.5 identity.py 5 ORM models | ✅ | Base.metadata 註冊 5 表；列對齐 09.md L114-191 |
| 1.6 Migration 0001 + alembic up/down/up cycle | ✅ | up→6 表、down→1 表(metadata only)、re-up→6 表（idempotent）|
| 1.7 test_engine_connect.py 3 tests | ✅ | pytest 3/3 PASS in 0.48s（real docker compose PG，AP-10 對策）|

### Commits

```
b414e7c docs(sprint-49-2): plan + checklist for Phase 49 Sprint 2
<TBD>   feat(infrastructure-db, sprint-49-2): Day 1 alembic + identity migration + ORM models
```

### Notes / Surprises

1. **Bash CWD persistence trap**: 早期 `cd backend && python ...` 後 shell 留在 backend/，導致後續 `mkdir -p backend/...` 在錯位置建空 dir `backend/backend/`。即時 grep + 清理 + 改用絕對路徑或 subshell `(cd ... && cmd)` pattern 避免。
2. **Windows cp950 encoding bite**: Day 1.6 `alembic upgrade head` 第一次跑因 alembic.ini 含 em-dash `—`（U+2014, UTF-8 0xE2 0x80 0x94）crash，因為 alembic 用 `encoding="locale"` 在 Windows 解 UTF-8。修為 ASCII hyphen 即解。**Action item**：CI 加 lint 檢查 `.ini` 檔純 ASCII，or 設 PYTHONUTF8=1 環境變數。
3. **TenantScopedMixin pattern**: 用 `@declared_attr @classmethod` 確保每個 subclass 都拿到獨立的 `tenant_id` Column 實例 + 正確 FK 解析。ORM 註冊驗證列名出現在 5 表中正確（`users.tenant_id`、`roles.tenant_id`、tenants/user_roles/role_permissions 不帶）。
4. **Plan 修正**：原 plan 說「Role/UserRole/RolePermission 全帶 tenant_id」是誤判；09.md 權威 schema 只有 `roles` 帶 tenant_id。User_roles + role_permissions 是 junction，依 FK chain 推斷 tenant。已依 09.md 修正執行。

### Day 1 acceptance bridge

- [x] AC-1 partial: `alembic upgrade head` + `alembic downgrade base` 跑通 0001（剩 0002-0004 待 Day 2-4）
- [x] AC-2 partial: 5 ORM models 註冊 Base.metadata；CRUD 測試 Day 2 起寫
- [ ] AC-3 (StateVersion race) → Day 4
- [ ] AC-4 (append-only trigger) → Day 4
- [ ] AC-5 (partition routing) → Day 2

---

## Day 2 — TBD (Sessions partition + ORM + CRUD test)

_planned 2026-04-29 後續 / 用戶下次 session_

---

## Day 3 — TBD (Tools migration + ORM + CRUD test)

---

## Day 4 — TBD (State + append-only + StateVersion race test)

---

## Day 5 — TBD (Settings + 文件 platform_layer 同步 + 整合驗收 + closeout)

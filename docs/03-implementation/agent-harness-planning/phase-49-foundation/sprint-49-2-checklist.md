# Sprint 49.2 — Checklist

**Sprint**: 49.2 — DB Schema + Async ORM 核心
**Plan**: [sprint-49-2-plan.md](./sprint-49-2-plan.md)
**建立日期**：2026-04-29
**狀態**：📋 計劃中（待用戶 approve）
**Story Points**：22
**5 Days × 5h average = 25h**

---

## 使用說明

- 每個任務勾選 `- [ ]` → `- [x]` **不可刪除未勾選項**（per CLAUDE.md sacred rule）
- 阻塞時加 `🚧 阻塞：<reason>` 在該項下方
- 每天結束前更新 progress.md 對應條目
- 每個 commit message 必須對應一個 task ID（如 `feat(infrastructure-db, sprint-49-2): 1.2 ...`）

---

## Day 1 — Alembic 基底 + Identity migration + ORM（估 5h）

### 1.1 Pre-flight check（10 min）— ✅ DONE 2026-04-29
- [x] **確認 working tree 狀態**
  - 結果：working tree 乾淨（discussion-log 為用戶 IDE，不阻塞）；untracked = 49.2 plan/checklist
- [x] **建立 49.2 feature branch**
  - 結果：`feature/phase-49-sprint-2-db-orm` 從 49.1 branch carry forward 建立（main 落後 49.1 16 commits，唯一可行路徑）
  - 補：plan+checklist 作為 branch 第一個 commit `b414e7c docs(sprint-49-2): plan + checklist`
- [x] **確認 docker compose postgres up**
  - 結果：`ipa_v2_postgres` healthy（port 5432）；qdrant unhealthy（49.2 不用，49.3 修復）；redis/rabbitmq healthy
- [x] **驗證 Python venv 已裝核心 deps**（自加 — 49.1 retro lessons）
  - 結果：sqlalchemy 2.0.48 / asyncpg 0.31.0 / alembic 1.18.4 / pydantic_settings 2.13.1 全部就位

### 1.2 Alembic 基底（45 min）— ✅ DONE
- [x] **建立 `backend/alembic.ini`**
- [x] **建立 `backend/src/infrastructure/db/migrations/env.py`**
- [x] **建立 `backend/src/infrastructure/db/migrations/script.py.mako`**
- [x] **建立 `migrations/__init__.py` + `versions/__init__.py`**
- 結果：alembic CLI 在 `cd backend && alembic --help` 通過

### 1.3 DeclarativeBase + TenantScopedMixin（30 min）— ✅ DONE
- [x] **建立 `backend/src/infrastructure/db/base.py`**（Base + TenantScopedMixin via declared_attr）
- [x] **建立 `backend/src/infrastructure/db/exceptions.py`**（DBException / StateConflictError / MigrationError）
- 結果：imports OK；Base.metadata.tables 初為空（預期，Day 1.5 後填）

### 1.4 Async Engine + Session Factory（45 min）— ✅ DONE
- [x] **建立 `backend/src/infrastructure/db/engine.py`**（get_engine / get_session_factory / dispose_engine 三 helper）
- [x] **建立 `backend/src/infrastructure/db/session.py`**（get_db_session async generator）
- [x] **更新 `backend/src/infrastructure/db/__init__.py`**（re-export 9 個 public symbol）
- [x] **擴充 `backend/src/core/config/__init__.py`**（db_pool_size=10 / db_pool_max_overflow=20 / db_pool_recycle_sec=300 / db_echo=False）
- [x] **更新 `.env.example`**（root，補 DB_POOL_* + DB_ECHO 4 行）
- 結果：Real PostgreSQL 16.10 ping 通；pool config 4 fields 顯示正確

### 1.5 Identity ORM models（45 min）— ✅ DONE
- [x] **建立 `backend/src/infrastructure/db/models/__init__.py`**
- [x] **建立 `backend/src/infrastructure/db/models/identity.py`**
  - 5 個 ORM：Tenant（無 mixin）/ User（mixin）/ Role（mixin）/ UserRole（無 mixin）/ RolePermission（無 mixin）
  - **Plan 修正執行**：09.md 只 roles 帶 tenant_id；user_roles + role_permissions 為 junction，無 tenant_id（依 FK chain）
- [x] **更新 `models/__init__.py` re-export 5 個 model**
- 結果：Base.metadata 註冊 5 表，columns 對齐 09-db-schema-design.md L114-191

### 1.6 Migration 0001（45 min）— ✅ DONE
- [x] **建立 `migrations/versions/0001_initial_identity.py`**（手寫 op.create_table；含 partial index + 4 UniqueConstraint）
- [x] **跑 migration up + verify**：6 表存在（5 業務 + alembic_version）
- [x] **跑 migration down + verify**：1 表（only alembic_version）
- [x] **重新 upgrade verify idempotent**：6 表恢復
- 🟡 **Surprise：Windows cp950 encoding error**（alembic.ini em-dash 字符）
  - 修：em-dash → ASCII hyphen
  - Action：CI 加 .ini ASCII-only lint，或 PYTHONUTF8=1（→ Day 5 / 49.4）

### 1.7 連線 smoke test（20 min）— ✅ DONE
- [x] **建立 `backend/tests/unit/infrastructure/db/test_engine_connect.py`**（3 tests）
- [x] **跑 test**：3/3 PASS in 0.48s
  - test_engine_can_ping_postgres
  - test_engine_reports_pg_version（驗 PG 16+ real DB）
  - test_session_factory_yields_async_session
- [ ] **Day 1 commit**（待執行）
- [x] **建立 progress.md Day 1 條目**（已建）

---

## Day 2 — Sessions partition + ORM + CRUD test（估 5h）— ✅ DONE

### 2.1 Sessions ORM models（60 min）— ✅ DONE
- [x] **建立 `models/sessions.py`**（Session + Message + MessageEvent）
- [x] **更新 `models/__init__.py` re-export**
- 結果：8 表註冊（5 identity + sessions + messages + message_events）；composite PK + postgresql_partition_by 配置正確

### 2.2 Migration 0002 — partition 設計（90 min）— ✅ DONE
- [x] **建立 `migrations/versions/0002_sessions_partitioned.py`**
  - 含 3 個月 partition（**2026-04 為當月，加碼避 NOW() 撞牆**）+ 全部 indexes
- [x] **跑 migration up + verify partition**：`\dt+ messages*` 顯示 4 entry（parent + 3 partitions）
- [x] **跑 migration down + verify**：表全消失
- 🟡 **Surprise**：原計畫只 2 partition（05, 06）但 NOW()=2026-04-29 落不進。修：補 2026-04 partition

### 2.3 conftest.py 與 db_session fixture（45 min）— ✅ DONE
- [x] **建立 `backend/tests/conftest.py`** 含 db_session fixture + seed_tenant + seed_user helpers
- 🟡 **Surprise**：pytest-asyncio per-test event loop + module-level engine singleton 衝突 → `RuntimeError: Event loop is closed`。修：fixture teardown 加 `await dispose_engine()` 強制 next test 重建 engine

### 2.4 CRUD tests for Sessions（60 min）— ✅ DONE
- [x] **`test_models_crud.py` 5 tests**（2 identity + 3 sessions）全 PASS

### 2.5 Partition routing test（45 min）— ✅ DONE
- [x] **`test_partition_routing.py` 4 tests**（3 messages parametrize + 1 message_events）全 PASS via `tableoid::regclass`

### 2.6 Day 2 收尾（20 min）— ✅ DONE
- [x] **跑全 test**：12/12 PASS in 0.5s
- [x] **mypy strict**：13 source files 0 errors
- [x] **black + isort + flake8**：clean（修了 sessions.py em-dash + test files 過長 + unused User import）
- [ ] **Day 2 commit**（待執行）
- [x] **更新 progress.md Day 2 條目**

---

## Day 3 — Tools migration + ORM + CRUD test（估 4h）— ✅ DONE

### 3.1 Tools ORM models（60 min）— ✅ DONE
- [x] **建立 `models/tools.py`**（ToolRegistry global / ToolCall per-tenant / ToolResult no tenant via FK chain）
- [x] **更新 `models/__init__.py` re-export**
- 結果：11 ORM 註冊（5 identity + 3 sessions + 3 tools）
- 🟡 **Plan 修正 from 09.md**：ToolResult 不帶 tenant_id（09.md L25 list 沒列；junction style）

### 3.2 Migration 0003（45 min）— ✅ DONE
- [x] **建立 `migrations/versions/0003_tools.py`**（含 partial index `status='active'`）
- [x] **跑 migration up + down**：兩方向通過
- 🟡 **Surprise**：tool_calls.message_id 在 09.md L335 寫 FK 但 messages PK 為 (id, created_at) composite → 取消 FK 約束（不支援 partial-key FK in PG 16）；message_id 改純 UUID column。記錄於 model + migration docstring

### 3.3 CRUD tests for Tools（90 min）— ✅ DONE
- [x] **擴充 `test_models_crud.py` 3 個新 tests**：tools_registry_global / tool_call_with_session / tool_result_link_to_call

### 3.4 Day 3 收尾（25 min）— ✅ DONE
- [x] **跑全 test**：15/15 PASS in 0.7s
- [x] **mypy strict / black / isort / flake8**：clean（再次自動 reformat 2 files）
- [x] **LLM SDK leak grep**：0 imports
- [ ] **Day 3 commit**（待執行）
- [x] **更新 progress.md Day 3 條目**

---

## Day 4 — State migration + append-only + StateVersion race test（估 6h）

### 4.1 State ORM models（45 min）
- [ ] **建立 `models/state.py`**
  - DoD：2 個 ORM：StateSnapshot（繼承 TenantScopedMixin）/ LoopState（繼承）
  - 對齐 09-db-schema-design.md L508-555
  - StateSnapshot 含 `version: int`、`parent_version: int | None`、`state_hash: str`、`reason: str`、`UNIQUE(session_id, version)`
- [ ] **更新 `models/__init__.py` re-export**

### 4.2 `append_snapshot()` helper + StateConflictError 處理（90 min）
- [ ] **擴充 `models/state.py` 加 `append_snapshot()` async function**
  - DoD：實作 plan 第 4 節 pseudocode；驗 parent_version + parent_hash + INSERT 失敗轉 StateConflictError
- [ ] **加 `compute_state_hash(state_data: dict) -> str` helper**
  - DoD：SHA-256 of `json.dumps(state_data, sort_keys=True)`

### 4.3 Migration 0004（60 min）
- [ ] **建立 `migrations/versions/0004_state.py`**
  - DoD：手寫 SQL：
    1. `CREATE TABLE state_snapshots ...`（含 UNIQUE(session_id, version)）
    2. `CREATE TABLE loop_states ...`
    3. `CREATE OR REPLACE FUNCTION prevent_state_snapshot_modification()`
    4. `CREATE TRIGGER state_snapshots_no_update_delete`
  - 對齐 09-db-schema-design.md L508-555
- [ ] **跑 migration up + down**
  - DoD：兩方向均成功；trigger 在 up 後存在於 `\df`

### 4.4 Append-only trigger 測試（45 min）
- [ ] **建立 `tests/unit/infrastructure/db/test_state_append_only.py`**
  - DoD：3 個 test：
    1. `test_state_snapshot_can_insert`：normal append 成功
    2. `test_state_snapshot_cannot_update`：UPDATE raise IntegrityError matching "append-only"
    3. `test_state_snapshot_cannot_delete`：DELETE 同樣 raise

### 4.5 StateVersion 雙因子 Race condition 測試（120 min）
- [ ] **建立 `tests/unit/infrastructure/db/test_state_race.py`**
  - DoD：1 個 test `test_concurrent_snapshot_insert_one_wins`：
    - 用 `asyncio.Barrier(2)` 嚴格同步兩 worker
    - 兩 worker 同時用 parent_version=5 + 同一 expected_parent_hash
    - 期望：1 成功 1 失敗（StateConflictError）
  - 額外：跑 100 次（`pytest -k race --count=100`）confirm 不 flaky
- [ ] **加 `parent_hash` 不符測試**
  - DoD：1 個 test `test_parent_hash_mismatch_raises`：parent_version 對但 parent_hash 不符 → StateConflictError

### 4.6 Day 4 收尾（30 min）
- [ ] **跑全 test**
  - DoD：`pytest backend/tests/unit/infrastructure/db/ -v` 全 PASS（≥ 14 tests）
- [ ] **mypy strict 通過**
  - DoD：`mypy backend/src/infrastructure/db --strict` 0 errors
- [ ] **Day 4 commit**
  - DoD：`feat(infrastructure-db, sprint-49-2): Day 4 state snapshots + append-only + StateVersion race test`
- [ ] **更新 progress.md Day 4 條目**

---

## Day 5 — Settings 收尾 + V2 文件 platform 同步 + 整合驗收 + closeout（估 5h）

### 5.1 Settings 與 .env.example 完整化（30 min）
- [ ] **檢查 Settings 所有 db_* 欄位**
  - DoD：`Settings()` 以 `.env` 載入 + 用 default 不報錯
- [ ] **`.env.example` 與 `.env.example` 同步**
  - DoD：`grep DB_ backend/.env.example` 顯示 5 條（DATABASE_URL + 4 DB_POOL_*）

### 5.2 49.1 retro action items 清算（45 min）
- [ ] **`02-architecture-design.md` platform → platform_layer**
  - DoD：`grep -n 'platform/' docs/03-implementation/agent-harness-planning/02-architecture-design.md` 0 matches（除非引述歷史 V1，否則改完）
- [ ] **`06-phase-roadmap.md` platform → platform_layer**
  - DoD：同上
- [ ] **掃其他規劃文件**
  - DoD：`grep -rn 'platform/' docs/03-implementation/agent-harness-planning/` 只剩歷史性引用（標記 OK）
  - Command：`grep -rn 'platform/' docs/03-implementation/agent-harness-planning/`
- [ ] **`.gitignore` Python 構建產物 pattern audit**
  - DoD：`grep -E '__pycache__|\.egg-info|\.pytest_cache|\.mypy_cache|\.coverage' .gitignore` 全部存在

### 5.3 整合驗收：完整 migration cycle（45 min）
- [ ] **Drop + recreate database**
  - Command：`docker compose -f docker-compose.dev.yml exec postgres psql -U ipa_v2 -c "DROP DATABASE IF EXISTS ipa_v2_test"; ... CREATE DATABASE ipa_v2_test;`
- [ ] **`alembic upgrade head` 從零跑通**
  - DoD：4 migration 全成功；`\dt` 顯示 13 張表（含 partition）
- [ ] **`alembic downgrade base` 全 rollback**
  - DoD：所有表 + trigger + function 全消失
- [ ] **再 upgrade head**
  - DoD：成功（idempotency 驗證）

### 5.4 整合驗收：跑全 test suite（30 min）
- [ ] **跑全 unit + integration tests**
  - Command：`pytest backend/ -v --cov=src/infrastructure/db --cov-report=term-missing`
  - DoD：全 PASS；`infrastructure/db/` coverage ≥ 80%
- [ ] **跑 mypy strict 全 backend/src**
  - Command：`mypy backend/src --strict`
  - DoD：0 errors
- [ ] **跑 black + isort + flake8**
  - DoD：全 clean
- [ ] **LLM SDK leak grep（49.1 既有規則延續）**
  - Command：`grep -rE "^import openai|^from openai|^import anthropic|^from anthropic" backend/src/agent_harness/ backend/src/infrastructure/`
  - DoD：0 matches

### 5.5 CI workflow update（30 min）
- [ ] **`.github/workflows/backend-ci.yml` 加 alembic + postgres service**
  - DoD：CI job 在 lint/mypy/pytest 之前 spin up postgres + run alembic upgrade head
- [ ] **Push 並驗 CI green**
  - DoD：CI 在 push 後變 green（如未 merge 則待用戶決定 PR / 直 push）

### 5.6 文件 + retrospective + closeout（90 min）
- [ ] **更新 `infrastructure/db/README.md`**
  - DoD：49.2 status: implemented；列出 13 表 + alembic 用法
- [ ] **建立 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-2/progress.md`**（如未隨日更新則此處統整）
  - DoD：5 day estimate vs actual 對照表 + notes
- [ ] **建立 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-2/retrospective.md`**
  - DoD：5 必述（outcome / estimates vs actual / went-well / surprises / Action items for 49.3）+ sign-off block
- [ ] **更新 checklist 整體狀態 → ✅ DONE**
- [ ] **Day 5 commit + push**
  - Commits（建議分 2）：
    1. `chore(infrastructure-db, sprint-49-2): Day 5.1-5.5 settings + platform_layer doc sync + CI alembic`
    2. `docs(sprint-49-2): Day 5.6 progress + retrospective + closeout`
- [ ] **Push branch**
  - DoD：`git push origin feature/phase-49-sprint-2-db-orm` 成功
- [ ] **報告用戶 Sprint 49.2 ✅ DONE**

---

## Sprint 49.2 結束狀態

完成此 checklist 後，Sprint 49.2 應達到：

- ✅ 4 個 Alembic migration（0001-0004）up/down 跑通
- ✅ 13 張 ORM models 全部可 CRUD（real PostgreSQL）
- ✅ StateVersion 雙因子 race condition test 通過（100 次無 flaky）
- ✅ state_snapshots append-only trigger 驗證通過
- ✅ Messages / message_events partition routing 驗證通過
- ✅ pytest fixture `db_session` 用 docker compose real PostgreSQL
- ✅ mypy strict 0 errors / lint clean / LLM SDK 零 leak
- ✅ V2 規劃文件 02 + 06 platform → platform_layer 同步
- ✅ CI 自動跑 alembic + pytest（postgres service in workflow）
- ✅ Sprint 49.2 commit ≥ 5（每日至少 1）+ pushed
- ✅ progress.md + retrospective.md 完整

---

## 🚧 延後項清單（per CLAUDE.md sacred rule，不可刪）

下列項**故意不在 49.2 做**，已歸於後續 sprint：

- 🚧 **audit_log + append-only + hash chain** → Sprint 49.3
- 🚧 **api_keys / rate_limits** → Sprint 49.3
- 🚧 **5 層 memory 表（system/tenant/role/user/session_summary）** → Sprint 49.3
- 🚧 **approvals / risk_assessments / guardrail_events** → Sprint 49.3 / 53.4
- 🚧 **RLS policies 全表套用 + per-request `SET LOCAL app.tenant_id` middleware** → Sprint 49.3
- 🚧 **Qdrant tenant-aware namespace** → Sprint 49.3
- 🚧 **verification_results** → Sprint 54.1（範疇 10）
- 🚧 **subagent_runs / subagent_messages** → Sprint 54.2（範疇 11）
- 🚧 **worker_tasks / outbox** → Sprint 49.4
- 🚧 **cost_ledger / llm_invocations** → Sprint 49.4
- 🚧 **pg_partman 自動分區** → Sprint 49.3
- 🚧 **indexes optimization (0014)** → Sprint 49.3 / 49.4
- 🚧 **Encryption at rest（PII 欄位）** → Sprint 49.3 / 14.md security 落地時

---

## Rolling Planning 紀律自檢

完成此 checklist 才允許開始 code：
- ☐ 沒預寫 Sprint 49.3 / 49.4 plan + checklist
- ☐ 沒在本 checklist 寫具體 49.3 / 49.4 task（只列 🚧 與「目標 sprint」）
- ☐ 本 checklist + sprint-49-2-plan.md 已被用戶 review + approve

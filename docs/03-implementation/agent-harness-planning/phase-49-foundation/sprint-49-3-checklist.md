# Sprint 49.3 — Checklist

**Plan**：[`sprint-49-3-plan.md`](./sprint-49-3-plan.md)
**狀態**：📋 計劃中（待用戶 approve 才開 branch + 進 Day 1）
**Branch**：`feature/phase-49-sprint-3-rls-audit-memory`（待建）
**開始日**：TBD（用戶 approve 後）
**目標完成**：開工後 5 工作天內

> **Sacred Rule**：未勾選 `[ ]` 永不刪除；無法在本 sprint 內完成的，標 `🚧 延後到 49.X` + 理由保留。

---

## Day 1 — Audit log 完整鏈（估 5h）

### 1.1 設計 + ORM model（30 min）
- [x] **設計 `audit_log` schema（含 BIGSERIAL id + tenant_id NOT NULL + operation + resource_type + resource_id + access_allowed + payload JSONB + prev_hash + row_hash + timestamp_ms + 月度 PARTITION BY RANGE(created_at)）**
  - DoD：schema 對齐 09-db-schema-design.md L678-720；月度 partition 含 2026-04/05/06
  - Output：`backend/src/infrastructure/db/models/audit.py` (AuditLog ORM)

### 1.2 Alembic migration 0005（90 min）
- [x] **寫 `0005_audit_log_append_only` migration**
  - **Scope 修正（對齐 09.md）**：09-db-schema-design.md L658 audit_log 為單表非 partition；plan 中「+3 monthly partitions」是過度設計，已刪除。實際交付：1 audit_log 主表（BIGSERIAL pk + TenantScopedMixin）+ ROW UPDATE/DELETE trigger + STATEMENT TRUNCATE trigger
  - **同時補裝**：state_snapshots 的 STATEMENT TRUNCATE trigger（49.2 deferred）
  - DoD：upgrade() 與 downgrade() 對等；alembic upgrade head 成功 ✅
  - Command：`cd backend && alembic upgrade head`

### 1.3 結構驗證（20 min）
- [x] **pg_trigger 查詢確認 4 trigger 全裝（actual function names: prevent_audit_modification + prevent_state_snapshot_modification）**
  - DoD：4 triggers 確認：audit_log_no_update_delete (ROW)、audit_log_no_truncate (STATEMENT)、state_snapshots_no_update_delete (ROW)、state_snapshots_no_truncate (STATEMENT) ✅
  - Command：`SELECT tgname, tgrelid::regclass, tgtype FROM pg_trigger WHERE tgname LIKE '%audit%' OR tgname LIKE '%state_snapshots%'`

### 1.4 audit_helper.py（45 min）
- [x] **寫 `compute_audit_hash(*, previous_log_hash, operation_data, tenant_id, timestamp_ms) -> str`（SHA-256, canonical JSON sort_keys + tight separators）**
- [x] **寫 async `append_audit(session, *, tenant_id, operation, resource_type, operation_data, user_id=None, session_id=None, ...) -> AuditLog`**
  - 內部：select latest current_log_hash by tenant → SENTINEL_HASH 若無前序 → compute new hash → insert
  - **欄位名對齐 09.md**：`previous_log_hash` / `current_log_hash` / `operation_data` / `operation_result`（plan 用的 `prev_hash` / `payload` 已修正）
  - DoD：mypy strict pass ✅
  - Output：`backend/src/infrastructure/db/audit_helper.py`

### 1.5 test_audit_append_only.py（90 min）
- [x] **test_audit_can_insert**：baseline INSERT + SENTINEL_HASH + 獨立重算 hash 一致 ✅
- [x] **test_audit_cannot_update**：UPDATE raise `audit_log is append-only` ✅
- [x] **test_audit_cannot_delete**：DELETE raise 同上 ✅
- [x] **test_audit_cannot_truncate**：`TRUNCATE audit_log` raise 同上 ✅
- [x] **test_state_snapshots_cannot_truncate**：49.2 carryover；用 `TRUNCATE state_snapshots CASCADE` 繞過 FK check 後 trigger raise `state_snapshots is append-only` ✅
- [x] **test_audit_hash_chain_integrity**：3 rows append → SENTINEL bootstrap + chain[N].previous == chain[N-1].current + 獨立重算一致 ✅
  - **Scope 修正**：plan 中 `test_audit_partition_routing` 隨 partition 設計刪除一同移除；改為 hash chain integrity 更實質
  - DoD：6 tests 全綠 ✅
  - 順手解：49.2 留的 `test_state_snapshot_truncate_blocked` skip 已在本 sprint 補裝後啟用通過 ✅
  - 全套回歸：32/32 PASS（49.2 26 + 49.3 6；無 SKIPPED）
  - Command：`pytest backend/tests/unit/infrastructure/db/ -q`

### 1.6 commit Day 1（10 min）
- [ ] **commit `feat(infrastructure-db, sprint-49-3): Day 1 audit log append-only + hash chain + state_snapshots TRUNCATE 補`**

---

## Day 2 — api_keys + rate_limits + 5 memory tables（估 6h）

### 2.1 api_keys + rate_limits 設計 + ORM（30 min）
- [x] **api_keys 欄位（對齐 09.md L869-896）**：id / tenant_id / name(128) / key_prefix(16) / key_hash(128 bcrypt) / permissions JSONB / rate_limit_tier / status / expires_at / last_used_at / created_by FK users / created_at / revoked_at
- [x] **rate_limits 欄位（對齐 09.md L902-919）**：id / tenant_id / resource_type / window_type / quota / used / window_start / window_end + UNIQUE(tenant, resource, window_type, window_start)
  - **Scope 修正**：plan 寫的 `last_4` / `scopes` / `api_key_id` 已對齐 09.md 改為 `key_prefix` / `permissions` / 無 api_key_id（rate_limits 是 per-tenant per-resource per-window，與 api_key 無 FK）
  - **檔案位置改動**：plan 寫「擴充 identity.py」，實作為新檔 `models/api_keys.py`（職責分明：API auth+quota vs identity/RBAC；精神對齐 ✅）
  - DoD：兩 ORM 都用 TenantScopedMixin ✅

### 2.2 0006 migration（45 min）
- [x] **寫 `0006_api_keys_rate_limits` migration**（含 ix_api_keys_tenant_id + idx_api_keys_active partial WHERE status='active' + idx_api_keys_prefix + ix_rate_limits_tenant_id + idx_rate_limits_lookup DESC + UNIQUE constraint）
  - DoD：alembic upgrade + downgrade 對稱 ✅

### 2.3 5 memory tables 設計 + ORM（60 min）
- [x] **memory_system**（全局；無 tenant_id；id / key UNIQUE / category / content / metadata / version / timestamps）✅
- [x] **memory_tenant**（TenantScopedMixin；key / category / content / vector_id / metadata + UNIQUE(tenant,key) + idx_memory_tenant_category）✅
- [x] **memory_role**（**junction via role_id only**；無直接 tenant_id；同 user_roles 模式 — 09.md L432-447 不含 tenant_id；plan 中「TenantScopedMixin + role_id」修正為純 junction）✅
- [x] **memory_user**（TenantScopedMixin + user_id FK；category / content / vector_id / source / source_session_id / confidence Numeric(3,2) / expires_at / metadata + 4 indexes 含 partial expires）✅
- [x] **memory_session_summary**（**junction via session_id UNIQUE**；無直接 tenant_id；09.md L485-498 不含 tenant_id；plan 中「TenantScopedMixin」修正為純 junction）✅
  - **Scope 修正**：plan 寫「4 個 memory 用 TenantScopedMixin」，09.md 權威：只 memory_tenant + memory_user 用（2 個）；memory_role / memory_session_summary 是 junction-style（同 user_roles / role_permissions / tool_results 49.2 模式）
  - DoD：5 ORM classes；2 帶 TenantScopedMixin、2 junction、1 全局 ✅
  - Output：`backend/src/infrastructure/db/models/memory.py`

### 2.4 0007 migration（60 min）
- [x] **寫 `0007_memory_layers` migration**（5 表 + 11 indexes：mem_tenant 4 / mem_role 3 / mem_user 5 / mem_session_summary 2 / mem_system 2）
  - DoD：alembic upgrade + downgrade ✅

### 2.5 結構驗證（15 min）
- [x] **psql 驗 7 表全建 + index 數量**：api_keys 4 / rate_limits 4 / memory_system 2 / memory_tenant 4 / memory_role 3 / memory_user 5 / memory_session_summary 2 ✅

### 2.6 測試（90 min）
- [x] **test_api_keys_crud.py（5 tests）**：
  - test_api_key_create_active ✅
  - test_api_key_lookup_by_hash ✅
  - test_api_key_revoke ✅
  - test_api_key_expire_lookup ✅
  - test_rate_limit_create_unique（UNIQUE 違反 IntegrityError）✅
- [x] **test_memory_models_crud.py（6 tests）**：
  - test_memory_system_global ✅
  - test_memory_tenant_scoped ✅
  - test_memory_role_via_role（修：Role 用 display_name 而非 name）✅
  - test_memory_user_with_provenance ✅
  - test_memory_session_summary_unique ✅
  - test_memory_user_cross_tenant_via_filter（app-layer 過濾驗證；RLS 驗證留 Day 4）✅
  - DoD：11 tests 全綠（plan 寫「10 tests」實作 11 個更完整）
  - 全套回歸：43/43 PASS（49.2 26 + 49.3 17，0 SKIPPED）

### 2.7 commit Day 2（10 min）
- [ ] **commit `feat(infrastructure-db, sprint-49-3): Day 2 api_keys + rate_limits + 5 memory layers`**

---

## Day 3 — Governance 3 tables（估 5h）

### 3.1 approvals 設計（30 min）
- [x] **欄位（對齐 09.md L566-601）**：id / session_id FK / action_type / action_summary / action_payload JSONB / risk_level / risk_score Numeric(3,2) / risk_reasoning / required_approver_role / approver_user_id FK users / status (pending/approved/rejected/expired) / decision_reason / teams_notification_sent / teams_message_id / created_at / expires_at / decided_at
  - **Scope 修正**：plan 寫的 `tenant_id` / `requestor_user_id` / `approval_type` / `reason` 對齐 09.md → **junction via session_id**（無直接 tenant_id；同 memory_session_summary 模式）；`approver_user_id` (不是 actor_user_id)；`action_type` (不是 approval_type)
  - DoD：純 junction，無 TenantScopedMixin ✅

### 3.2 risk_assessments 設計（30 min）
- [x] **欄位（對齐 09.md L605-622）**：id / session_id FK / tool_call_id FK NULL / risk_level / risk_score Numeric(3,2) NOT NULL / triggered_rules JSONB / reasoning / requires_approval BOOL / created_at
  - **Scope 修正**：09.md 用 `risk_level` + `risk_score Numeric(3,2)` 不是 plan 寫的 `score INT 0-100 + severity enum`；無 `recommendation` / `blocked`；改用 `requires_approval` + `tool_call_id` FK（plan 沒提）
  - DoD：純 junction via session_id；無 TenantScopedMixin ✅

### 3.3 guardrail_events 設計 + ORM（30 min）
- [x] **欄位（對齐 09.md L628-648）**：id / session_id FK NULL / layer / check_type / passed BOOL / severity / detected_pattern / action_taken / metadata / created_at
  - **Scope 修正**：09.md 用 `layer + check_type + passed + severity + detected_pattern + action_taken` 不是 plan 寫的 `detector_type + severity + action_taken enum(logged/blocked/sanitized)`；action_taken 真實值為 `allow / block / tripwire_fired`；session_id 可為 NULL（pre-session input layer）
  - DoD：純 junction；無 TenantScopedMixin ✅
  - Output：`backend/src/infrastructure/db/models/governance.py` 含 3 classes ✅

### 3.4 0008 migration + upgrade（60 min）
- [x] **寫 `0008_governance` migration**（3 表 + 7 indexes：approvals 3 + risk_assessments 1 + guardrail_events 3 = 7 functional + 3 pkey = 10 total）
  - DoD：alembic upgrade + downgrade ✅
  - 結構驗證：approvals 4 / risk_assessments 2 / guardrail_events 4 indexes ✅

### 3.5 test_governance_models_crud.py（90 min）
- [x] **test_approval_state_machine_pending_to_approved**：actor user + decided_at 填寫 ✅
- [x] **test_approval_state_machine_pending_to_rejected**：decision_reason 寫入 ✅
- [x] **test_approval_pending_query_uses_partial_index**：partial idx 只含 status='pending' ✅
- [x] **test_risk_assessment_create_with_score**：Numeric(3,2) + triggered_rules JSONB + requires_approval ✅
- [x] **test_guardrail_event_three_action_types**：allow / block / tripwire_fired 3 案例 + partial passed=FALSE 索引 ✅
- [x] **test_governance_cross_tenant_via_session_chain**：JOIN sessions 過濾 tenant_id（governance 無直接 tenant_id 故必須 JOIN；RLS 在 Day 4 補強）✅
  - DoD：6 tests 全綠
  - 全套回歸：49/49 PASS（49.2 26 + 49.3 23，0 SKIPPED）

### 3.6 commit Day 3（10 min）
- [ ] **commit `feat(infrastructure-db, sprint-49-3): Day 3 governance — approvals + risk + guardrail events`**

---

## Day 4 — RLS + middleware + pg_partman（估 7h）

### 4.1 14 表 RLS policy 清單（30 min）
- [ ] **列出 14 張 session-scoped 表**：users / roles / sessions / messages / message_events / tool_calls / state_snapshots / loop_states / api_keys / rate_limits / approvals / risk_assessments / guardrail_events / audit_log
  - 同時列出 6 張全局表（不掛 RLS）：tenants / tools_registry / user_roles / role_permissions / tool_results / memory_system

### 4.2 0009 migration（120 min）
- [ ] **寫 `0009_rls_policies_pg_partman` migration**
  - 14 表 × `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
  - 14 表 × `CREATE POLICY tenant_isolation_<table> USING (tenant_id = current_setting('app.tenant_id', true)::uuid)`
  - 14 表 × `CREATE POLICY tenant_insert_<table> FOR INSERT WITH CHECK (tenant_id = ...)`
  - **pg_partman**：CREATE EXTENSION + 3 個 create_parent（messages / message_events / audit_log，p_premake=6）
  - DoD：upgrade + downgrade 對等；upgrade 能跑通

### 4.3 結構驗證（30 min）
- [ ] **\dt + check policies**：`SELECT * FROM pg_policies WHERE schemaname = 'public'` → 28 行（14×2）
- [ ] **pg_partman setup verify**：`SELECT * FROM partman.part_config`

🚧 **延後條件**：若 pg_partman extension 在 `postgres:16-alpine` 不可裝，將 4.2 中 pg_partman 部分拆 0009b 並標 `🚧 延後到 49.4 lint+infra 階段`，理由：image 換 `postgres:16` full 需 docker compose env 改動，本 sprint 範圍外。

### 4.4 tenant_context middleware（60 min）
- [ ] **新建 `backend/src/platform_layer/middleware/__init__.py`**
- [ ] **`backend/src/platform_layer/middleware/tenant_context.py`**：
  - `TenantContextMiddleware(BaseHTTPMiddleware)` extract `X-Tenant-Id` header → set `request.state.tenant_id`
  - `get_db_session_with_tenant(request)` async generator：取 request.state.tenant_id → SET LOCAL → yield session
  - DoD：mypy strict pass

### 4.5 test_tenant_context.py（45 min）
- [ ] **test_missing_header_returns_401**
- [ ] **test_invalid_uuid_returns_400**
- [ ] **test_valid_uuid_sets_request_state**
- [ ] **test_get_db_session_with_tenant_sets_local**：integration test 驗 SET LOCAL 確實寫入
  - DoD：4 tests 全綠

### 4.6 test_rls_enforcement.py（90 min）
- [ ] **test_rls_select_blocked_without_set_local**：query messages → 0 rows（NULL setting 不匹配）
- [ ] **test_rls_select_scoped_to_tenant**：SET LOCAL tenant_a → 只看到 tenant_a messages
- [ ] **test_rls_insert_with_check_blocks_wrong_tenant**：SET LOCAL tenant_a + INSERT (tenant_id=tenant_b) → raise
- [ ] **test_rls_update_blocked_cross_tenant**：SET LOCAL tenant_a + UPDATE messages WHERE id=<tenant_b's>...→ 0 rows affected
- [ ] **test_rls_delete_blocked_cross_tenant**：同上
  - 在 audit_log / approvals / memory_user 三表至少各覆蓋 1 案例（防漏）
  - DoD：5+ tests 全綠

### 4.7 commit Day 4（10 min）
- [ ] **commit `feat(platform-layer, sprint-49-3): Day 4 RLS 14 表 + tenant context middleware + pg_partman`**

---

## Day 5 — Qdrant abstraction + 紅隊 + closeout（估 5h）

### 5.1 Qdrant namespace abstraction（45 min）
- [ ] **新建 `backend/src/infrastructure/vector/__init__.py`**
- [ ] **`backend/src/infrastructure/vector/qdrant_namespace.py`**：
  - `QdrantNamespaceStrategy.collection_name(tenant_id, layer)` static
  - `QdrantNamespaceStrategy.payload_filter(tenant_id)` static
  - 不接 Qdrant client（推 51.2）
  - DoD：mypy strict pass

### 5.2 test_qdrant_namespace.py（30 min）
- [ ] **test_collection_name_tenant_unique**：兩 tenant 名稱不同
- [ ] **test_collection_name_layer_separated**：同 tenant 不同 layer 名不同
- [ ] **test_payload_filter_contains_tenant_id**
  - DoD：3 tests 全綠

### 5.3 紅隊測試套件（90 min）
- [ ] **新建 `backend/tests/security/test_red_team_isolation.py`**：
  - **AV-1**：偽造 X-Tenant-Id 為 tenant_b（middleware 接受合法 UUID 但 RLS 擋）→ 跨 tenant query 0 rows
  - **AV-2**：移除 SET LOCAL（直連 session 不過 dependency）→ query 0 rows
  - **AV-3**：嘗試 SQL injection 入 set_config('app.tenant_id', '...; SELECT * FROM ...')→ ::uuid cast 擋
  - **AV-4**：UPDATE audit_log → trigger raise
  - **AV-5**：TRUNCATE audit_log + state_snapshots → trigger raise
  - **AV-6**：兩 tenant 用 QdrantNamespaceStrategy 拿 collection name → 名稱前綴 prefix 不重疊；payload filter 含 tenant_id must
  - DoD：6 tests 全綠

### 5.4 全套驗收（30 min）
- [ ] **alembic downgrade base + alembic upgrade head 從零跑通**
- [ ] **`pytest backend/tests/unit/infrastructure/db/ backend/tests/unit/platform_layer/ backend/tests/unit/infrastructure/vector/ backend/tests/security/`** 全綠
- [ ] **\dt 確認最終表數量**：49.2 的 13 表 + 49.3 新增（audit_log + 3 partitions + api_keys + rate_limits + 5 memory + 3 governance）= 13 + 13 = 26 表 + 6 全局已存在 = 26 base + 6 partitions + 觸發器 functions
  - DoD：表 / function / policy 數量符合 plan §AC-1

### 5.5 Lint + 規範驗證（20 min）
- [ ] **mypy strict 全 backend/src/infrastructure/db/ + backend/src/infrastructure/vector/ + backend/src/platform_layer/middleware/**
- [ ] **flake8 + isort + black --check**
- [ ] **LLM SDK leak grep on new files**：`grep -rn "import openai\|import anthropic\|from openai\|from anthropic" backend/src/infrastructure/ backend/src/platform_layer/` → 0 結果
- [ ] **跨範疇 import check（手動）**：infrastructure 不 import agent_harness（單向依賴）

### 5.6 文件 closeout（55 min）
- [ ] **更新 `backend/src/infrastructure/db/README.md`**（補 49.3 deliverables 段）
- [ ] **新建 `backend/src/platform_layer/middleware/README.md`**（簡述 tenant_context middleware）
- [ ] **新建 `backend/src/infrastructure/vector/README.md`**（簡述 qdrant_namespace + 51.2 接 client 計畫）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-3/progress.md`**（5 days estimate vs actual + 意外項）
- [ ] **建 `docs/03-implementation/agent-harness-execution/phase-49/sprint-49-3/retrospective.md`**（5 必述 + sign-off）
- [ ] **更新 `docs/03-implementation/agent-harness-planning/phase-49-foundation/README.md`**（49.3 ✅ DONE，3/4 = 75%）
- [ ] **將本 checklist 全項目 [x]（或標 🚧 + 理由）**

### 5.7 commit Day 5 closeout（10 min）
- [ ] **commit `docs(sprint-49-3): Day 5 closeout — Sprint 49.3 DONE`**

---

## Sprint 49.3 Done 條件（all must ✅）

- [ ] AC-1 5 個 migrations 正反向 cycle 跑通
- [ ] AC-2 audit append-only DB 層三擋（UPDATE/DELETE/TRUNCATE）
- [ ] AC-3 hash chain 串連完整
- [ ] AC-4 14 表 RLS 跨 tenant 0 leak
- [ ] AC-5 5 層 memory CRUD + tenant 隔離
- [ ] AC-6 governance 3 表 workflow stub
- [ ] AC-7 tenant_context middleware + dependency
- [ ] AC-8 Qdrant namespace abstraction
- [ ] AC-9 49.2 carried-over 兩件清掉（state_snapshots TRUNCATE + pg_partman）（後者若 image 不支援，標 🚧 → 49.4）
- [ ] AC-10 紅隊 6 攻擊向量 0 leak
- [ ] AC-11 CI 通過：alembic + pytest + mypy + lint + LLM leak grep

---

## Sprint 49.3 closeout sign-off（Day 5 完成時填）

- [ ] 全 checklist 項 `[x]` 或標 🚧 + 理由
- [ ] All linters pass
- [ ] X PASS + Y SKIPPED（X / Y 待 closeout 填）
- [ ] Migration cycle from base proven
- [ ] Real PostgreSQL via docker compose throughout
- [ ] LLM SDK leak grep: 0 imports
- [ ] CI workflow updated（若 0009 RLS migration 需新 verify step）
- [ ] Phase 49 README 更新（3/4 sprint complete）

**Sprint 49.3 status**：📋 計劃中 → 待用戶 approve → 開工

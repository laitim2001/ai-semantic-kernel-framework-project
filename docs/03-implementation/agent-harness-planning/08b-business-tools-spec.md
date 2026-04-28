# 08b — 業務領域工具規格（IPA Business Tools）

**建立日期**：2026-04-28
**版本**：V2.0
**狀態**：Phase 55 主要實作目標

> **本檔職責**：定義 IPA 平台的 5 個業務領域工具，避免混入 `01-eleven-categories-spec.md` 通用 harness spec。**範疇 2（Tools）只定義通用工具規範**；業務工具在此檔規範。

---

## 為什麼拆出此檔

V2 review（2026-04-28）發現範疇 2 把 IPA 業務領域工具（patrol / correlation / rootcause / audit / incident）寫進**通用** harness spec：

| 問題 | 影響 |
|------|------|
| 通用 harness 鎖入特定業務 | 未來新業務（finance / hr）就要再改範疇 2 spec |
| 違反「11 範疇是通用 harness」的 framing | 範疇 2 應該是工具**機制**，非工具**清單** |
| 跨團隊 review 時聚焦混亂 | 業務 stakeholder 看到 spec 中夾 patrol / correlation 會混淆 |

**解法**：通用機制 → 範疇 2；業務工具 → 本檔。

---

## 業務工具註冊原則

所有業務工具**必須**透過範疇 2 `ToolRegistry` 註冊，**不可繞過**。註冊位置：

```
backend/src/business_domain/{domain}/tools.py
  ↓
透過 register_{domain}_tools(registry: ToolRegistry) 在 startup 呼叫
  ↓
範疇 2 ToolRegistry 統一管理
```

業務工具**必須**遵守範疇 2 ToolSpec 規範（包括 ToolAnnotations / concurrency_policy / version / hitl_policy）。

---

## 5 個業務領域工具集

### Domain 1：Patrol（巡檢）

**職責**：對 server / 服務做健康檢查、收集指標、回報異常。

| 工具名稱 | annotations | concurrency | hitl_policy | 風險 |
|---------|------------|------------|------------|------|
| `patrol_check_servers(scope)` | read_only=True, idempotent=True | READ_ONLY_PARALLEL | auto | LOW |
| `patrol_get_results(patrol_id)` | read_only=True, idempotent=True | READ_ONLY_PARALLEL | auto | LOW |
| `patrol_schedule(cron, scope)` | destructive=True | SEQUENTIAL | ask_once | MEDIUM |
| `patrol_cancel(patrol_id)` | destructive=True | SEQUENTIAL | ask_once | MEDIUM |

**Storage**：`patrols` / `patrol_results` 表（schema 見 09.md）

### Domain 2：Correlation（事件關聯）

**職責**：分析 alert / log 之間的關聯，找出 root cause 候選。

| 工具名稱 | annotations | concurrency | hitl_policy | 風險 |
|---------|------------|------------|------------|------|
| `correlation_analyze(alerts)` | read_only=True | READ_ONLY_PARALLEL | auto | LOW |
| `correlation_find_root_cause(incident_id)` | read_only=True | SEQUENTIAL | auto | LOW |
| `correlation_get_related(alert_id, depth)` | read_only=True, idempotent=True | READ_ONLY_PARALLEL | auto | LOW |

### Domain 3：Root Cause（根本原因）

**職責**：對 incident 做深度診斷，提出修復建議。

| 工具名稱 | annotations | concurrency | hitl_policy | 風險 |
|---------|------------|------------|------------|------|
| `rootcause_diagnose(incident_id)` | read_only=True | SEQUENTIAL | auto | LOW |
| `rootcause_suggest_fix(incident_id)` | read_only=True | SEQUENTIAL | auto | LOW |
| `rootcause_apply_fix(fix_id)` | destructive=True | SEQUENTIAL | **always_ask** | **HIGH** |

> `rootcause_apply_fix` 是**最高風險**工具，必須 `always_ask` + `risk_level=HIGH`，多 reviewer 審批。

### Domain 4：Audit（審計）

**職責**：合規查核、生成審計報告、追蹤異常。

| 工具名稱 | annotations | concurrency | hitl_policy | 風險 |
|---------|------------|------------|------------|------|
| `audit_query_logs(time_range, filters)` | read_only=True | READ_ONLY_PARALLEL | auto | LOW |
| `audit_generate_report(template, params)` | read_only=True, open_world=True | SEQUENTIAL | auto | MEDIUM |
| `audit_flag_anomaly(record_id, reason)` | destructive=True | SEQUENTIAL | ask_once | MEDIUM |

### Domain 5：Incident（事件管理）

**職責**：建立 / 更新 / 關閉事件單、跨系統溝通。

| 工具名稱 | annotations | concurrency | hitl_policy | 風險 |
|---------|------------|------------|------------|------|
| `incident_create(title, severity, ...)` | destructive=True | SEQUENTIAL | ask_once | MEDIUM |
| `incident_update_status(id, status)` | destructive=True | SEQUENTIAL | ask_once | MEDIUM |
| `incident_close(id, resolution)` | destructive=True | SEQUENTIAL | always_ask | HIGH |
| `incident_get(id)` | read_only=True | READ_ONLY_PARALLEL | auto | LOW |
| `incident_list(filters)` | read_only=True | READ_ONLY_PARALLEL | auto | LOW |

---

## 業務工具的 ToolSpec 範例

```python
# backend/src/business_domain/rootcause/tools.py
from agent_harness._contracts import (
    ToolSpec, ToolAnnotations, ConcurrencyPolicy, HITLPolicy,
)
from agent_harness.tools import ToolRegistry

def register_rootcause_tools(registry: ToolRegistry) -> None:
    registry.register(ToolSpec(
        name="rootcause_apply_fix",
        description="Apply a suggested fix to an incident. Highly destructive.",
        input_schema={
            "type": "object",
            "properties": {
                "fix_id": {"type": "string"},
                "dry_run": {"type": "boolean", "default": False},
            },
            "required": ["fix_id"],
        },
        output_schema={"type": "object", "properties": {"applied": {"type": "boolean"}}},
        result_content_types=["text", "json"],

        annotations=ToolAnnotations(
            read_only=False,
            destructive=True,
            idempotent=False,        # apply 同 fix 二次有副作用
            open_world=False,
        ),
        concurrency_policy=ConcurrencyPolicy.SEQUENTIAL,
        version="1.0",

        handler=_apply_fix_handler,

        permissions=PermissionSpec(roles=["sre_lead", "ops_manager"], tenant_scoped=True),
        hitl_policy=HITLPolicy(
            mode="always_ask",
            risk_threshold="HIGH",
            sla_seconds=14_400,        # 4h
            fallback_on_timeout="reject",
        ),

        is_mutating=True,
        sandbox_level=SandboxLevel.NONE,  # 直接呼叫業務 service

        audit=AuditSpec(
            log_request=True,
            log_response=True,
            sensitive_fields=["fix_payload.credentials"],
        ),
    ))
```

---

## 業務工具與通用範疇的整合

### 與範疇 2（Tools）

| 角色 | 通用範疇 2 | 業務工具（本檔） |
|------|----------|---------------|
| ToolSpec 規範 | Owner | Caller（必須遵守） |
| ToolRegistry | Owner | 透過 registry 註冊 |
| Sandbox / Permission / Audit | 機制提供 | 配置使用 |
| 工具清單 | 通用 6 大類 | 5 業務 domain |

### 與 §HITL 中央化

業務工具的 `hitl_policy` 觸發時，呼叫**統一的 `HITLManager`**（見範疇 12 後 §HITL 中央化），不自建 HITL 邏輯。

### 與範疇 9（Guardrails）

業務工具的 destructive 操作必經範疇 9 `tool_guardrail` 檢查；guardrail 結果為 escalate 時觸發 HITL（已是統一路徑）。

### 與範疇 12（Observability）

業務工具 handler 接 `trace_context: TraceContext`，OTel span category = `TOOL_EXEC`。

---

## Phase 55 接入時序

```
Phase 55.1 - 業務 Backend
  ├─ 5 個 business_domain/ 模組 service 層
  ├─ business_domain/{domain}/tools.py 註冊到 ToolRegistry
  └─ Mock backend 接入 PoC（Phase 51.0 即建）

Phase 55.2 - 業務 Frontend
  ├─ pages/agents/（含 React Flow 畫 agent 拓撲）
  ├─ pages/workflows/（業務工具呼叫鏈視覺化）
  └─ pages/incidents/（incident 列表 / 詳情）

Phase 55.3 - 缺漏前端 6 頁
  ├─ memory inspector / audit viewer / tools admin
  └─ admin / dashboard / DevUI
```

---

## 驗收標準

### 結構驗收
- [ ] 5 個 business_domain 模組各自獨立目錄
- [ ] 每個 domain 的 tools.py 透過 `register_{domain}_tools` 註冊
- [ ] 全 24 個業務工具 ToolSpec 完整（含 annotations / concurrency / hitl_policy）
- [ ] 高風險工具（rootcause_apply_fix / incident_close）`always_ask`

### 整合驗收
- [ ] 業務工具的 audit log 進入統一 audit 表（範疇 9）
- [ ] 業務工具的 trace 進入統一 OTel collector（範疇 12）
- [ ] 業務工具 HITL 進入統一 approvals 表（§HITL 中央化）

### 安全驗收
- [ ] Tenant A agent 無法呼叫 Tenant B 的業務工具（Permission spec 強制）
- [ ] 高風險工具 multi-reviewer 機制
- [ ] PII / 敏感欄位（如 credentials）audit redact

### SLO 量化驗收
- [ ] Read-only 業務工具 p95 < 1s
- [ ] Mutating 業務工具 p95 < 3s（不含 HITL wait）
- [ ] HITL 平均 wait < 30 min（reviewer SLA）

---

## 參考文件

- [01-eleven-categories-spec.md](./01-eleven-categories-spec.md) — 範疇 2 通用 ToolSpec / §HITL 中央化
- [09-db-schema-design.md](./09-db-schema-design.md) — 業務 domain 表 schema
- [17-cross-category-interfaces.md](./17-cross-category-interfaces.md) — ToolSpec single-source

---

**最後更新**：2026-04-28
**主要實作 Phase**：Phase 55.1（backend）+ Phase 55.2（frontend）

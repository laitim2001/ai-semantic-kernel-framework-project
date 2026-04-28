# V2 企業 SaaS Readiness 規劃

**建立日期**：2026-04-23
**版本**：V2.0
**對應**：Phase 51-55 規劃 + Phase 56+ 完成

---

## SaaS Readiness 成熟度

V2 不打算第一輪做完整商業 SaaS，但**架構必須留接口**。

```
Stage 0: 內部試用（Phase 49-55 完成）
  - 單一公司部署
  - 1-3 tenant
  - 手動 onboarding
  ↓
Stage 1: Multi-tenant 內部 SaaS（Phase 56-58）
  - 同公司內多 BU
  - 5-20 tenant
  - 半自動 onboarding
  - SLA monitoring
  ↓
Stage 2: 外部商業 SaaS（Phase 60+）
  - 跨公司客戶
  - SOC 2 / ISO 27001 認證
  - 自助 onboarding
  - Billing 整合
  - 24x7 support
```

本文件**規劃 Stage 1 為主目標**（V2 範圍），Stage 2 為長期。

---

## Tenant Lifecycle Management

### Tenant Provisioning（建立流程）

```
┌─────────────────────────────────────────────┐
│ Step 1: Admin 建立 Tenant 請求               │
│ - 填寫公司資訊                              │
│ - 選擇 plan（基本 / 進階 / 企業）            │
│ - 設定初始 quota                            │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│ Step 2: 系統自動 provisioning                │
│ 2.1 建立 tenants record                     │
│ 2.2 建立 tenant default roles               │
│ 2.3 建立 default policies (HITL / risk)     │
│ 2.4 建立 Qdrant namespace                   │
│ 2.5 建立 system memory（Layer 1）seeded     │
│ 2.6 建立 first admin user                   │
│ 2.7 建立 API key（hashed）                   │
│ 2.8 觸發 welcome email                      │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│ Step 3: Tenant Onboarding（自動 / 半自動）   │
│ 3.1 上傳 tenant memory（公司 playbook）     │
│ 3.2 設定企業工具 credentials（D365 等）      │
│ 3.3 配置 SSO / SAML（如 Entra ID）          │
│ 3.4 邀請其他 user                           │
│ 3.5 跑 tenant health check                  │
└─────────────────────────────────────────────┘
```

### Tenant State Machine

```
[requested] → [provisioning] → [active] → [suspended] → [archived]
                    ↓                          ↑              ↓
               [provision_failed]          [reactivated]  [deleted]
```

### Tenant 配置範本

```yaml
# config/tenant_plans.yml
plans:
  basic:
    quota:
      tokens_per_day: 100_000
      cost_usd_per_day: 5
      sessions_per_user_concurrent: 3
      api_keys_max: 1
    features:
      verification: false
      thinking: false
      subagents: false
      mcp_servers: ["filesystem"]
    
  standard:
    quota:
      tokens_per_day: 1_000_000
      cost_usd_per_day: 50
      sessions_per_user_concurrent: 10
      api_keys_max: 3
    features:
      verification: true
      thinking: false
      subagents: true
      mcp_servers: ["filesystem", "shell", "ldap"]
    
  enterprise:
    quota:
      tokens_per_day: 10_000_000
      cost_usd_per_day: 500
      sessions_per_user_concurrent: 50
      api_keys_max: 10
    features:
      verification: true
      thinking: true
      subagents: true
      mcp_servers: "*"
      custom_tools: true
      dedicated_support: true
```

---

## SLA 與監控

### SLA 承諾（內部 SaaS Stage 1，**2026-04-28 review 修訂**）

> **Review 修訂**：
> - 99% / 99.5% → 99.5% / 99.9%（業界 SaaS 至少 99.9%；99% = 每月 down 7.2 小時，企業客戶不買單）
> - **HITL approval time 從 SLA 移除**（那是 customer-side 行為，不該由 platform 承擔），改為 HITL queue notification latency
> - Loop latency「簡單」明確定義
> - DR RPO/RTO 修正為 WAL streaming-based

| 指標 | Standard | Enterprise | 定義 / 量測方式 |
|------|---------|-----------|---------------|
| Availability | **99.5%** | **99.9%** | 月度 uptime（per region），不含 scheduled maintenance |
| API p99 latency | < 2s | < 1s | 排除 LLM call 的純 API（auth / CRUD） |
| Loop latency（簡單）| < 10s | < 5s | **定義「簡單」**：≤ 3 turns + ≤ 2 tool_calls + 0 subagent + < 4K input tokens |
| Loop latency（中等）| < 60s | < 30s | 4-10 turns + 多工具 + 0-1 subagent |
| Loop latency（複雜）| < 5min | < 3min | 10+ turns 或多 subagent |
| **HITL queue notification latency** | < 5 min | < 1 min | reviewer 收到 Teams / email 通知時間（**不含 reviewer 決策時間**）|
| Support response | < 4 hours | < 1 hour | Sev1 incident 回應 |
| Backup RPO（PostgreSQL） | < 5 min | **< 1 min** | **WAL streaming replication + PITR**（hourly backup 不夠精細） |
| Backup RPO（Qdrant） | 4 hr | 1 hr | Vector DB snapshot 頻率（24hr 對 memory-driven agent 太慢，調整為 1-4hr） |
| Backup RPO（Redis HITL state） | 5 min | 1 min | 若 Redis 存 session/HITL state，必須 backup（不能假設純 cache） |
| RTO（Postgres failure） | 1 hr | **15 min** | Automated failover + read replica promotion（4hr 太慢，業界標準 < 1hr） |
| RTO（Region failure） | 4 hr | **1 hr** | Cross-region DR drill 必達 |

### SLA 監控

```python
# observability/sla_monitor.py
class SLAMonitor:
    async def check_uptime_per_tenant(self): ...
    async def check_latency_p99_per_tenant(self): ...
    async def check_quota_usage_per_tenant(self): ...
    
    async def generate_monthly_report(self, tenant_id: UUID) -> SLAReport:
        """每月寄送 SLA 報告給 tenant admin"""
```

### SLA 補償機制（如未達標，**2026-04-28 review 修訂**：補中間階梯）

```yaml
# config/sla_credits.yml
sla_violations:
  - threshold: availability < 99.9%   # Enterprise 標準
    credit: 5% monthly fee
  - threshold: availability < 99.5%
    credit: 10% monthly fee
  - threshold: availability < 99%     # ⭐ 補中間層
    credit: 15% monthly fee
  - threshold: availability < 95%
    credit: 25% monthly fee
  - threshold: availability < 90%
    credit: 100% monthly fee（terminate option）
```

---

## Billing 整合（為 Stage 2 預留）

### 計費模型

V2 規劃支援 3 種計費模式：

#### 模式 1：訂閱制（Subscription）
```
basic:    $X/user/month
standard: $Y/user/month
enterprise: $Z/user/month + custom
```

#### 模式 2：用量制（Usage-based）
```
基於：
- LLM tokens（input + output 分價）
- Tool calls
- Storage GB-hour
- Active sessions
```

#### 模式 3：混合（推薦）
```
- Base subscription（含基本 quota）
- 超量收費（per token / call / GB）
- Cap 上限（避免 surprise bill）
```

### Cost Ledger 整合

```python
# 每次 LLM call / Tool call 自動寫 cost_ledger
async def execute_with_cost_tracking(...):
    result = await ...
    
    await cost_ledger.record(
        tenant_id=ctx.tenant_id,
        cost_type="llm",
        sub_type=f"{provider}_{model}_input",
        quantity=usage.prompt_tokens,
        unit="tokens",
        unit_cost_usd=PRICING[model]["input"],
        total_cost_usd=usage.prompt_tokens * PRICING[model]["input"] / 1000,
        session_id=ctx.session_id,
    )
    return result
```

### Billing 月結流程（Stage 2）

```python
# 每月 1 號跑
async def monthly_billing_run():
    for tenant in active_tenants:
        usage = await aggregate_cost_ledger(
            tenant_id=tenant.id,
            month=last_month,
        )
        
        invoice = generate_invoice(
            tenant=tenant,
            usage=usage,
            plan=tenant.plan,
        )
        
        if tenant.payment_method:
            charge_result = await stripe.charge(invoice)
            ...
        
        send_invoice_email(tenant, invoice)
```

---

## Disaster Recovery（DR）

### DR 場景與恢復策略

| 場景 | 影響 | RTO | RPO | 策略 |
|------|-----|-----|-----|------|
| 單 worker failure | 該 task 重試 | < 30s | 0 | Auto-retry |
| 單 backend instance failure | Load balancer 切走 | < 1min | 0 | Multi-instance |
| Postgres replica failure | Failover to standby | < 5min | < 1min | HA setup |
| Postgres primary failure | Manual failover | < 30min | < 1hr | Standby + WAL |
| Redis failure | 重建 cache，sessions 從 DB 恢復 | < 5min | 部分 session 中斷 | DB-backed state |
| Region failure | DR site activation | < 4hr | < 1hr | Cross-region replication |
| 整體 service compromise | Restore from backup | < 24hr | < 24hr | Backup strategy |
| Tenant data corruption | Point-in-time recovery | < 4hr | < 1hr | PITR + audit log replay |

### Backup 策略（重申）

```yaml
backup:
  postgresql:
    incremental: hourly
    full: daily
    retention: 30 days
    cross_region_replication: true
    encryption: AES-256
    
  qdrant:
    full: daily
    retention: 30 days
    
  audit_log:
    real_time_replication: enabled
    retention: 7 years（合規）
    archive_after: 90 days → cold storage
    
  configuration:
    git_committed: true
    encrypted_secrets_in_keyvault: true
```

### DR Drill（演練）

每季度執行：
1. 從 backup 還原到隔離環境
2. 驗證資料完整性（hash chain check）
3. 跑 smoke test
4. 量測 RPO / RTO 達成
5. 更新 runbook

---

## Tenant Onboarding 自動化

### Onboarding Wizard（Frontend）

```
Step 1: 公司資訊
  ↓
Step 2: 選擇 plan + quota
  ↓
Step 3: 上傳 tenant memory
  - CLAUDE.md 等價檔案
  - 公司 playbook（PDF / DOCX）
  - 可選：上傳企業工具 credentials
  ↓
Step 4: SSO 設定
  - Entra ID tenant ID
  - 或 LDAP
  - Test connection
  ↓
Step 5: 邀請首批 users
  - Email list
  - 預設 role
  ↓
Step 6: Health check + 啟用
  - 自動跑測試 session
  - 確認所有元件 ready
  - Tenant 進入 active 狀態
```

### Onboarding API

```python
POST /api/v1/admin/tenants
{
  "company_name": "ACME Corp",
  "plan": "standard",
  "admin_email": "admin@acme.com",
  "memory_files": [...],
  "sso_config": {...},
  "initial_users": [...]
}
→ 201 Created
{
  "tenant_id": "...",
  "status": "provisioning",
  "estimated_ready_in_seconds": 60
}

GET /api/v1/admin/tenants/{id}/onboarding-status
→ {
  "status": "active",
  "completed_steps": [...],
  "pending_steps": [...],
  "health_check": {...}
}
```

---

## Customer Support Integration

### Support Tier

| Tier | 涵蓋 | 響應時間 |
|------|-----|--------|
| Self-service | 文件 + FAQ + 社群 | N/A |
| Standard | Email | < 4 hours |
| Premium | Email + Teams | < 1 hour |
| Enterprise | Dedicated CSM + 24x7 | < 15 min（critical）|

### Support Tooling

- **In-app help**：Right panel 含 FAQ + 文件搜索
- **Feedback widget**：每頁可回報問題
- **Session debugging**：Admin 可查看 user 的 session（經 audit）
- **Bug report 自動化**：附上 session ID + state snapshot

### Support 知識庫

V2 必須維護：
- 用戶手冊（per role）
- API 文件（OpenAPI 自動生成）
- 故障排除（common issues）
- Best practices guides
- Video tutorials（短）

---

## Feature Flags

### Feature Flag 系統

```python
# core/feature_flags.py
class FeatureFlags:
    async def is_enabled(
        self,
        flag_name: str,
        tenant_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> bool: ...
```

### 預期 Feature Flags

```yaml
features:
  # Provider features
  thinking_enabled:
    default: true
    overrides:
      tenant: { basic: false }  # basic plan 不開 extended thinking

  verification_enabled:
    default: true
    overrides:
      tenant: { basic: false }

  # Experimental
  new_loop_engine_v2:
    default: false
    overrides:
      tenant: { internal_alpha: true }

  # Cost control
  llm_caching_enabled:
    default: true

  # Compliance
  pii_masking:
    default: true
    overrides:
      tenant: { healthcare_*: strict }
```

### Tenant 等級切換

```python
# Tenant admin 可在 UI 切換部分 features
# System admin 可全局切換
# 變更走 audit log
```

---

## Multi-tenancy Scaling 策略（**2026-04-28 review 修訂**）

> **Review 修訂**：
> - Stage 1 上限 50 → 200-500 tenant（良好設計的 RLS + 索引可撐）
> - **Stage 2 (Schema-per-tenant) 標記為反模式並建議砍**（500 schema × 每次 alter table 是 migration 噩夢）
> - Stage 1 直接跳 Stage 3（DB-per-tenant for enterprise）+ Citus（horizontal sharding）
> - 補 Qdrant scaling 路線

### Scaling 階段

#### Stage 1: Shared Schema, Shared DB（Phase 49-55，**修訂上限**）

```
所有 tenant 在同一 PostgreSQL DB
透過 RLS 隔離（見 14.md §RLS Bypass 防護）
透過 Connection pooler transaction-mode 強制 SET LOCAL
適合：200-500 tenant（原文件估 50 偏低）
要件：每個 tenant_id 必有索引、查詢 < 100ms p99
```

#### ⛔ Stage 2: Schema-per-tenant（**反模式 — 建議砍**）

```
原規劃：每個 tenant 一個 PostgreSQL schema
適合：50-500 tenant（紙上談兵）

⛔ 為何反模式（業界共識）：
1. Migration 噩夢：500 schema × 每次 alter table = migration 跑 500 次
2. Connection pooling 變複雜：pgbouncer 必須 schema-aware
3. Backup 工具不友善：pg_dump per-schema 備份效率低
4. 客戶數成長時無法 reshard
5. RLS 已能提供等價隔離（且更便宜）

✅ 替代方案：直接從 Stage 1 → Stage 3，跳過此階段
```

#### Stage 2 (修訂)：Citus Horizontal Sharding（Phase 56-58，500-2000 tenant）

```
PostgreSQL Citus extension：透明 sharding
分片鍵：tenant_id（co-located shards）
適合：500-2000 tenant
優點：應用程式碼幾乎不變、自動 reshard、單一 DB endpoint
缺點：licensing cost、cross-shard query 限制
```

#### Stage 3: DB-per-tenant（**提前**至 Phase 56+，僅企業大客戶 / 高合規）
```
每個 tenant 獨立 DB instance
適合：金融 / 政府 / 高合規場景
優點：完全隔離、獨立 scaling、合規友善（資料居留 / BYOK）
缺點：成本高（per-tenant infra）
與 Citus 並用：大部分 tenant 在 Citus，少數 enterprise 用 dedicated
```

### Qdrant（Vector DB）Scaling 路線（**2026-04-28 review 補充**）

> **Review 發現**：原文件無 Vector DB scaling 路線。

| 階段 | 設定 | 適合 | Phase |
|------|------|------|-------|
| **Stage A** | 單 Qdrant cluster，per-tenant namespace（collection prefix） | < 200 tenant，總向量 < 100M | 49.3 起 |
| **Stage B** | 多 Qdrant cluster，按 tenant size sharding | 200-1000 tenant | 56-58 |
| **Stage C** | Cluster federation + replica per region | 1000+ tenant 跨 region | 60+ |

**注意**：Qdrant snapshot 頻率必須 ≤ 1hr（見 SLA 表 RPO 修訂），否則 memory-driven agent 體驗中斷。

---

## Compliance Reporting

### 客戶可請求的報告

```
GET /api/v1/compliance/{tenant_id}/reports?type=audit_log&period=last_month
→ 下載 audit log（CSV / JSON）

GET /api/v1/compliance/{tenant_id}/reports?type=data_inventory
→ 該 tenant 所有資料清單（GDPR 用）

GET /api/v1/compliance/{tenant_id}/reports?type=access_log
→ 誰在何時存取了什麼

GET /api/v1/compliance/{tenant_id}/reports?type=sla_metrics&period=YYYY-MM
→ SLA 達成率報告
```

---

## Public API & Integration

### V2 對外 API（Stage 1 後）

```
POST /api/v1/sessions          # 啟動 session
POST /api/v1/sessions/{id}/messages  # 送訊息
GET  /api/v1/sessions/{id}/events    # SSE event stream
POST /api/v1/sessions/{id}/resume    # HITL 後 resume

POST /api/v1/tools/register    # 客戶註冊自定 tool（透過 webhook）
GET  /api/v1/tools             # 列工具

POST /api/v1/webhooks/configure  # 配置 callback
```

### Webhook 規格

```json
{
  "event_type": "session.completed",
  "tenant_id": "...",
  "session_id": "...",
  "data": {...},
  "timestamp": "2026-XX-XX",
  "signature": "..."  // HMAC-SHA256
}
```

### Rate Limit

```
Per API key:
  - 100 requests/min（standard）
  - 1000 requests/min（enterprise）

Per tenant:
  - 全 token 配額（plan-based）
```

---

## Status Page

公開 status page 顯示：
- 系統狀態（operational / degraded / down）
- 各 component 健康度
- 過去 incidents
- Scheduled maintenance

工具：Statuspage.io / 自建（簡單版）

---

## 結語

SaaS Readiness 不是一蹴可及。本文件規劃：

| Phase | SaaS Readiness 成果 |
|-------|--------------------|
| Phase 49 | Multi-tenant DB 基礎 + RLS |
| Phase 51 | Tenant memory 隔離 |
| Phase 52 | Per-tenant quota |
| Phase 53 | Audit + 合規基礎 |
| Phase 55 | Tenant onboarding API |
| Phase 56+ | SLA monitoring + DR + Billing |
| Phase 60+ | 認證 + 完整 SaaS |

**Phase 49-55 範圍內**，達到 **Stage 1（內部 SaaS）** 即可。
**Stage 2（商業 SaaS）** 是長期路線。

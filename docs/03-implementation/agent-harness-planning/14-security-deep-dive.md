# V2 安全合規深度規劃

**建立日期**：2026-04-23
**版本**：V2.0
**對應**：Phase 49 起貫穿全程，Phase 53 重點實作

---

## 安全模型總覽

V2 採用 **Zero-Trust + Defense in Depth + Compliance-Ready** 三原則。

```
                  ┌──────────────────────────────┐
                  │ Compliance & Audit Layer     │ ← 合規層（不可篡改）
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │ Application Security Layer    │ ← 範疇 9 + Tripwire
                  │ (Guardrails / RBAC / Tools)   │
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │ Data Security Layer          │ ← Encryption / RLS / DLP
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │ Network Security Layer        │ ← TLS / WAF / Egress
                  └──────────────┬───────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │ Infrastructure Security      │ ← Container / Host / Sandbox
                  └──────────────────────────────┘
```

---

## 資料分類（Data Classification）

### 4 級分類

| 分類 | 範例 | 處理規則 |
|------|------|---------|
| **Public** | Marketing material | 一般處理 |
| **Internal** | 一般業務資料 | 員工可存取 |
| **Confidential** | 客戶資料、財務 | RBAC + audit + encryption |
| **Restricted** | PII、健康資料、合約 | RBAC + RLS + encryption + DLP + 審批 |

### 自動分類機制

```python
# governance/data_classification/classifier.py
class DataClassifier:
    async def classify(self, data: str) -> DataClassification:
        """
        基於：
        - PII 檢測（正則 + ML）
        - 關鍵字檢測（信用卡、SSN、健保 ID）
        - 上下文線索（資料源 metadata）
        """
```

### 跨範疇強制

- 範疇 2 Tools：執行前自動分類 input；輸出自動分類
- 範疇 3 Memory：寫入時必須帶 classification
- 範疇 9 Guardrails：高分類資料觸發更嚴 HITL
- 範疇 7 State：不同分類有不同 retention policy

---

## Encryption 策略

### Encryption at Rest

| 資源 | 加密方式 | 金鑰管理 |
|------|---------|---------|
| PostgreSQL | TDE（Transparent Data Encryption） | Azure Managed Identity → Key Vault |
| Object Storage | Server-side encryption | Azure Storage encryption |
| Redis | TLS + auth（不存敏感資料） | password rotated 90 天 |
| Qdrant | Filesystem encryption | Host level |
| Backup | AES-256 加密 | 獨立 KMS key |

### 欄位級加密（敏感欄位）

```python
# 對特定欄位額外加密
class EncryptedColumn(TypeDecorator):
    """SQLAlchemy 自定 type，存讀時自動加解密"""
    
# 應用：
class User(Base):
    email: Mapped[str] = mapped_column(EncryptedColumn(...))
    phone: Mapped[str | None] = mapped_column(EncryptedColumn(...))

class Memory(Base):
    content: Mapped[str] = mapped_column(EncryptedColumn(...))  # 可能含 PII
```

### Encryption in Transit

- 所有外部流量：**TLS 1.3 強制**
- 內部 service 間：mTLS（K8s service mesh，Phase 56+）
- DB 連線：SSL required
- LLM API：HTTPS only

---

## Authentication & Authorization

### Identity 提供者

| 來源 | 用途 |
|------|-----|
| **Microsoft Entra ID（Azure AD）** | 主要認證（OIDC / SAML） |
| Internal LDAP | Fallback / on-prem |
| Service principals | 服務間認證 |
| API keys | 外部系統呼叫（含 hashed） |

### Token 流程（OIDC）

```
1. User → Frontend → Entra ID
2. Entra ID → Frontend (JWT access_token + refresh_token)
3. Frontend → Backend API (Bearer token)
4. Backend 驗證 token：
   - 簽名（JWKS）
   - 未過期
   - audience 正確
   - tenant 在 allow-list
5. 提取 user_id / tenant_id / roles
6. 注入 ExecutionContext
```

### RBAC 模型

```
Tenant → Users → Roles → Permissions
                          ↓
                    resource_type:resource_pattern:action
```

範例：
```yaml
roles:
  - code: data_analyst
    permissions:
      - resource_type: tool
        pattern: "salesforce_query"
        action: execute
      - resource_type: tool
        pattern: "salesforce_update"
        action: execute
        constraints:
          hitl_required: true
      - resource_type: memory
        pattern: "tenant:*"
        action: read
      - resource_type: memory
        pattern: "user:self:*"
        action: write

  - code: finance_manager
    inherits: [data_analyst]
    permissions:
      - resource_type: tool
        pattern: "erp_*"
        action: execute
      - resource_type: approval
        pattern: "*"
        action: approve
```

### Permission Check 流程

```python
# 範疇 9 Guardrails
async def check_tool_call(tc: ToolCall, ctx: ExecutionContext):
    # 1. RBAC check
    if not await rbac.has_permission(
        user=ctx.user_id,
        resource_type="tool",
        resource_pattern=tc.tool_name,
        action="execute"
    ):
        return ToolGuardrailResult.denied("permission_denied")
    
    # 2. Tenant policy check
    policy = await tenant_policy.get(ctx.tenant_id)
    if tc.tool_name in policy.disallowed_tools:
        return ToolGuardrailResult.denied("tenant_policy")
    
    # 3. Risk + HITL check
    risk = await risk_assessor.assess(tc, ctx)
    if risk.requires_approval:
        return ToolGuardrailResult.requires_hitl(risk)
    
    return ToolGuardrailResult.passed()
```

---

## Threat Modeling（STRIDE）

### 對 V2 的威脅分析

| 威脅類別 | 攻擊向量 | 緩解 |
|---------|--------|------|
| **Spoofing** | 偽造 user / tenant | OIDC + token 簽名驗證 |
| **Tampering** | 修改 audit log | append-only triggers + hash chain |
| **Tampering** | 修改 LLM 訊息 | server-side state，client 不持有 |
| **Repudiation** | 否認操作 | Audit log + 不可篡改 |
| **Information Disclosure** | 跨 tenant 洩漏 | RLS + encrypted columns |
| **Information Disclosure** | LLM 洩漏 prompt 給 user | Output guardrail（PII detection） |
| **Information Disclosure** | Prompt injection 抽取 system prompt | Input guardrail + monitoring |
| **DoS** | 無限 loop / token 耗盡 | max_turns + token_budget + rate limit |
| **DoS** | 同時開大量 session | Per-tenant concurrency limit |
| **Elevation of Privilege** | Tool 越權 | RBAC + tenant policy |
| **Elevation of Privilege** | Subagent 越權 | Subagent 繼承父權限，不放大 |

### Prompt Injection 防禦（OWASP LLM01）

```python
# guardrails/input_guardrail/prompt_injection.py
INJECTION_PATTERNS = [
    r"ignore (previous|above|all) (instructions|context)",
    r"system prompt",
    r"reveal (your|the) (system|instructions)",
    r"forget (all|your) (instructions|rules)",
    # ... 更多模式
]

class PromptInjectionDetector:
    async def detect(self, user_input: str) -> InjectionResult:
        # 1. 模式匹配
        # 2. ML 分類器（fine-tuned BERT-small）
        # 3. LLM-based 二次驗證（高風險樣本）
        ...
```

### Information Disclosure 防禦

```python
# guardrails/output_guardrail/pii_filter.py
class PIIFilter:
    async def scan(self, output: str) -> ScanResult:
        """
        偵測：
        - 信用卡號（Luhn check）
        - SSN / 國民身分證號
        - 電子郵件 / 電話
        - IBAN / 銀行帳號
        - API key / token pattern
        """
```

---

## OWASP LLM Top 10 控制矩陣（**2026-04-28 review 新增**）

> **Review 發現**：原文件對 OWASP LLM Top 10 防禦覆蓋不全（評分 6.5/10）。本節補完整對照矩陣。

### 完整控制矩陣

| OWASP | 風險 | V2 控制 | 範疇 / 位置 | Phase |
|-------|------|---------|-----------|-------|
| **LLM01** Prompt Injection | 直接 + 間接（從 KB / Tool 回傳污染） | Pattern + ML + LLM 二驗 + **間接注入隔離**（見下方） | 範疇 9 input_guardrail + tool_guardrail | 53.3 |
| **LLM02** Insecure Output | XSS / SSRF via output | PII filter + **markdown sanitizer + HTML escape**（output_guardrail） | 範疇 9 output_guardrail | 53.3 |
| **LLM03** Training Data Poisoning（含 RAG / Memory） | Memory / KB 寫入污染影響 RAG | **provenance tracking** + write source tagging + content scanner | 範疇 3 memory + 範疇 9 | 51.2 |
| **LLM04** Model DoS | Token / concurrency / wallet attack | Token budget + concurrency cap + **Wallet Attack Detector**（見 11.md §成本守門） | 範疇 8 + 11.md | 53.2 + 53.3 |
| **LLM05** Supply Chain | Model / embedding 來源未驗證 | **Model registry + signed images + Trivy scan + adapter checksum verify** | 13.md devops | 49.4 |
| **LLM06** Sensitive Info Disclosure | PII / 直接 + 間接洩漏（log/error/embedding） | PII filter + **error message sanitizer + audit redact + embedding inversion test** | 範疇 9 + 14.md DLP | 53.3 |
| **LLM07** Insecure Plugin/Tool | RBAC + tool output schema | RBAC + **tool output JSON schema validation**（範疇 6 對接） | 範疇 2 + 6 + 9 | 51.1 |
| **LLM08** Excessive Agency | Tool chaining 越權 | HITL + **action whitelist per agent / per role** + capability matrix | §HITL + 範疇 9 CapabilityMatrix | 53.3 + 53.4 |
| **LLM09** Overreliance | UI 過度信任 LLM | **UI confidence indicator** + verification result 顯示 + verification metadata | 16.md frontend | 55.3 |
| **LLM10** Model Theft | 攻擊者 prompt 抽取 / 推理還原 | **Rate limit per tenant** + watermarking（per-tenant invisible token in system prompt）+ exfiltration detection | 14.md + 範疇 9 | 53.3 + 56+ |

### 間接 Prompt Injection 防禦（LLM01 補強）

> 直接 prompt injection（用戶輸入嘗試攻擊）已在原 §Prompt Injection 防禦處理；**間接注入**（從 KB 文件 / Tool 回傳的污染內容混入 LLM context）原文件未提，是 V2 最大攻擊面。

```python
# guardrails/input_guardrail/indirect_injection.py
class IndirectInjectionDetector:
    """檢查所有「進入 LLM context 但非用戶直接輸入」的內容。"""

    UNTRUSTED_SOURCES = {"kb_search", "web_fetch", "memory_search", "tool_result"}

    async def scan_observation(
        self,
        content: str,
        source: str,
        trace_context: TraceContext,
    ) -> IndirectInjectionResult:
        """
        檢查：
        1. Pattern 偵測（同 LLM01）
        2. Hidden instructions（HTML comments / unicode invisible）
        3. Role-switching attempts（"You are now ..."）
        4. Privilege escalation（"override permissions"）
        5. Data exfiltration（"send to attacker.com"）
        """
        if source not in self.UNTRUSTED_SOURCES:
            return IndirectInjectionResult(safe=True)
        # ... 5 種偵測
```

### Defense in Depth 應用

```
User Input → [Direct Injection Detector] → Loop
                                              ↓
KB / Tool Result → [Indirect Injection Detector] → Observation Masker → 回注 messages
                                                                              ↓
LLM Output → [PII Filter] + [Toxicity Check] + [LLM-as-judge second pass] → User
```

**規則**：任何「非用戶直接輸入」的內容進入 LLM context 必經 IndirectInjectionDetector。違反 lint rule（Phase 53.3）。

### 驗收測試（11.md §安全測試對接）

- [ ] OWASP LLM01：用 garak / PyRIT 200+ payload，pass rate ≥ 95%
- [ ] OWASP LLM03：memory poisoning 測試案例 ≥ 10
- [ ] OWASP LLM06：間接洩漏（log / audit / error / embedding inversion）≥ 5
- [ ] OWASP LLM08：tool chaining 越權測試 ≥ 5

---

## BYOK / Customer-Managed Keys（**2026-04-28 review 新增**）

> **Review 發現**：大型 enterprise 客戶必問「能否用我們自己的金鑰？」。原文件未提。本節補。

### Key Hierarchy

```
Tier 1: 平台 Master Key（V2 own，KMS 管理，輪換 12 月）
   ↓ encrypts
Tier 2: Tenant DEK（Data Encryption Key，per tenant，輪換 24 月）
   ↓ encrypts
Tier 3: Field-level keys（per sensitive column，per tenant）

OR （BYOK 啟用時）

Tier 1: 客戶 KMS Master Key（客戶 own，平台無法 export）
   ↓ encrypts
Tier 2: Tenant DEK（V2 cached，定期向客戶 KMS unwrap）
   ↓ encrypts
Tier 3: Field-level keys
```

### BYOK 模式選項

| 模式 | 說明 | 客戶適用 |
|------|------|--------|
| **Platform-Managed**（預設） | V2 自管金鑰 | 中小型客戶 |
| **CMK (Customer-Managed Key)** | 客戶提供 Azure Key Vault / AWS KMS reference，V2 透過 IAM 取用 | 中大型客戶 |
| **HYOK (Hold Your Own Key)** | 客戶 HSM 保管，每次解密都向客戶 endpoint 請求 | 金融 / 政府 |
| **Bring Your Own Encryption** | 客戶 SDK 加密後送 V2，V2 永遠看不到明文 | 極高敏感 |

### CMK 接入 API

```python
# tenant onboarding
@dataclass
class TenantKeyConfig:
    mode: Literal["platform_managed", "cmk", "hyok", "byoe"]
    cmk_key_id: str | None              # Azure Key Vault key URI / AWS KMS ARN
    cmk_iam_role: str | None            # 客戶提供的 cross-account role
    rotation_policy: KeyRotationPolicy

class TenantKeyManager:
    async def get_dek(self, tenant_id: UUID, trace_context: TraceContext) -> bytes:
        """取得 tenant DEK；BYOK 模式向客戶 KMS unwrap。"""
        config = await self.get_key_config(tenant_id)
        if config.mode == "platform_managed":
            return await self.platform_kms.decrypt(...)
        elif config.mode == "cmk":
            return await self.customer_kms_unwrap(config.cmk_key_id, ...)
        elif config.mode == "hyok":
            return await self.customer_hsm_request(config.cmk_iam_role, ...)
        elif config.mode == "byoe":
            raise NotImplementedError("BYOE: data already encrypted by customer SDK")
```

### Key 輪換政策

| Key Tier | 輪換週期 | 輪換方式 |
|---------|--------|---------|
| Platform Master Key | 12 個月 | KMS 自動輪換 + envelope re-encryption batch |
| Tenant DEK (CMK) | 客戶定義（通常 24 月） | 客戶觸發，V2 background re-wrap |
| Field-level keys | 24 個月 | per-column re-encrypt batch（dual-write 期間） |
| Backup encryption keys | 與 prod **物理隔離**（防 ransomware 同時加密 backup） | 獨立 KMS instance |

### 驗收標準

- [ ] CMK / HYOK 模式至少 PoC（Phase 56+ 完整實作）
- [ ] Key rotation 演練（季度）
- [ ] Backup 加密 key 與 prod key 在不同 KMS instance / region

---

## RLS Bypass 防護（**2026-04-28 review 新增**）

> **Review 發現**：multi-tenant 最常見漏洞是 RLS bypass。PostgreSQL `BYPASSRLS` 角色 / connection pooler 沒 SET ROLE 都會 bypass。本節補強防護。

### 風險場景

| 場景 | 風險 |
|------|------|
| Migration role 有 `BYPASSRLS` | DDL 操作意外讀到全 tenant 資料 |
| Connection pooler（PgBouncer / pgcat）共用 connection | 沒 `SET LOCAL` 會把 tenant A 的 query 跑在 tenant B context |
| Application 用 superuser 連線 | superuser 自動 bypass RLS |
| pg_dump / pg_restore | 預設 bypass |
| SECURITY DEFINER function | function owner 角色 bypass |

### 強制控制

```sql
-- 1. 所有 application 角色明確 NOBYPASSRLS
CREATE ROLE app_user NOBYPASSRLS;
GRANT USAGE ON SCHEMA public TO app_user;

-- 2. 拒絕 superuser 在 application connection
-- Per-tenant connection user，無 superuser 權限
CREATE ROLE tenant_app_user NOBYPASSRLS LOGIN PASSWORD '...';

-- 3. 強制 SET LOCAL（per-request, in transaction）
-- backend/src/middleware/tenant.py
async def tenant_context_middleware(request, call_next):
    tenant_id = extract_tenant_id_from_jwt(request)
    async with db.transaction():
        await db.execute("SET LOCAL app.tenant_id = :tid", {"tid": str(tenant_id)})
        response = await call_next(request)
    return response

-- 4. RLS policy 使用 current_setting
CREATE POLICY tenant_isolation ON sessions
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### Tenant ID 注入測試

```python
# 防 JWT vs query string mismatch attack
async def test_tenant_id_consistency():
    """
    Attack: JWT 帶 tenant_A，query string 帶 tenant_B
    Expected: 拒絕（401 / 403）
    """
    response = await client.get(
        "/api/v1/incidents",
        headers={"Authorization": f"Bearer {token_for_tenant_a}"},
        params={"tenant_id": str(tenant_b_id)},
    )
    assert response.status_code in (401, 403)
```

### Connection Pooler 配置

```ini
# pgbouncer.ini
# Transaction-level pooling（強制每 transaction reset）
pool_mode = transaction
server_reset_query = DISCARD ALL    # 確保 SET LOCAL 不污染下個 transaction

# 拒絕 session-level pooling（會洩漏 SET LOCAL）
# pool_mode = session  ❌
```

### CI / 測試套件

```bash
# scripts/test/rls_bypass_check.sh
# 1. 用 NOBYPASSRLS user 嘗試跨 tenant query → 必須 0 row
# 2. 用 superuser 嘗試 → expected: PR review 拒絕（連線設定錯誤）
# 3. 跨 tenant_id JWT mismatch → 401/403

pytest tests/security/test_rls_bypass.py
```

### 驗收標準（Phase 49.3）

- [ ] All application connections use NOBYPASSRLS role
- [ ] Connection pooler 強制 transaction-level pooling
- [ ] Tenant ID 注入測試通過（JWT / query string / header 三方一致）
- [ ] Migration / pg_dump 使用獨立有 BYPASSRLS 的 role（含 audit + alert）
- [ ] 季度 red-team test：故意嘗試 RLS bypass，必須 100% 阻擋

---

## Sandbox 安全

### 沙盒分層

| 層級 | 用途 | 隔離強度 |
|------|------|--------|
| **none** | 純 read-only API（如 KB search） | 應用層 |
| **process** | Python 計算（無 fs 存取） | OS process + seccomp |
| **container** | 任意 Python / Shell | Docker container |
| **microvm** | 高風險未審工具（Phase 56+） | Firecracker |

### Container Sandbox 規格

```yaml
# 沙盒 container 配置
resources:
  cpu: 0.5
  memory: 512Mi
  ephemeral-storage: 100Mi

securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: [ALL]

network:
  egress: deny-all（除非白名單）

timeout: 30s（強制）
```

---

## Audit 與合規

### Audit Log 必記錄事件

```python
AUDIT_REQUIRED_EVENTS = [
    # 認證
    "user_login", "user_logout", "auth_failure",
    
    # 授權
    "permission_check", "permission_denied",
    
    # Session
    "session_started", "session_ended", "session_paused",
    
    # Tool
    "tool_executed", "tool_denied", "tool_failed",
    
    # HITL
    "approval_requested", "approval_granted", "approval_rejected",
    
    # Memory
    "memory_written", "memory_deleted",
    
    # Guardrail
    "tripwire_fired", "guardrail_violation",
    
    # Data
    "data_classified", "pii_detected", "data_exported",
    
    # Admin
    "tenant_created", "user_role_changed", "policy_updated",
]
```

### Audit Log 結構（**2026-04-28 review 修訂**：Merkle Tree + 外部錨定）

> **Review 發現**：原單點 hash chain 在高併發下 last_entry 競態會破壞順序；且內部 DBA 仍可整段重寫（缺外部錨定）。本次升級。

#### Per-Tenant Merkle Tree（取代單點 chain）

```python
# 每筆 audit entry（不再依賴 previous_log_hash 串連）
audit_entry = {
    "id": uuid4(),
    "timestamp_ms": now_ms(),
    "tenant_id": ...,
    "user_id": ...,
    "operation": "tool_executed",
    "resource_type": "tool",
    "resource_id": "salesforce_query",
    "operation_data": {...},
    "operation_result": "success",
    "leaf_hash": sha256(canonical_json(entry)),
    "trace_context": {...},                      # 範疇 12 propagation
}

# 每分鐘 build Merkle tree per tenant
async def build_merkle_tree(tenant_id: UUID, time_window: timedelta = timedelta(minutes=1)):
    leaves = await fetch_audit_leaves(tenant_id, time_window)
    tree = MerkleTree(leaves=[e.leaf_hash for e in leaves])
    root_hash = tree.root_hash

    await save_merkle_root({
        "tenant_id": tenant_id,
        "window_start": ...,
        "window_end": ...,
        "leaf_count": len(leaves),
        "root_hash": root_hash,
        "tree_metadata": tree.serialize(),         # 用於後續 inclusion proof
    })
```

**優點**：
- 避免高併發競態（leaves 可並行寫入，root 由 background batch 計算）
- 任一 leaf tampering 必破壞 root_hash（O(log n) 偵測）
- 支援 inclusion proof（給單一 entry 證明其在某 root 下）

#### 外部錨定（External Anchoring）

> 內部 DBA 即使能寫 root_hash 也無法竄改外部已錨定的 hash，**這是 SOC 2 audit 必要**。

```python
# 三層錨定（每層獨立、互不依賴）

# 層 1：Cloud Object Lock（最便宜）
# 每小時把 root hashes 寫入 S3 / Azure Blob 並開啟 Object Lock (WORM mode)
async def anchor_to_object_lock(roots: list[MerkleRoot]):
    payload = json.dumps([r.dict() for r in roots])
    await s3_client.put_object(
        Bucket="audit-anchors-prod",
        Key=f"roots/{date}/{hour}.json",
        Body=payload,
        ObjectLockMode="COMPLIANCE",                  # 即 root account 也不能刪
        ObjectLockRetainUntilDate=now() + 7 years,
    )

# 層 2：Public Notary（每日，金融客戶要）
# 把每日 super-root 推到外部公證服務（如 OpenTimestamps / Chainpoint）
async def anchor_to_public_notary(super_root: str):
    await opentimestamps_client.stamp(super_root)
    # 結果可在 Bitcoin blockchain 驗證

# 層 3：SIEM 即時 forward（防主機被入侵後刪 log）
# audit entry 寫入 DB 同時 fire-and-forget 到 SIEM
async def forward_to_siem(entry: AuditEntry):
    await asyncio.gather(
        db.insert_audit(entry),
        siem_client.send(entry),                      # syslog / Splunk HEC
        return_exceptions=True,
    )
```

#### 驗證流程（每日 + on-demand）

```python
# 每日批次
async def daily_audit_verification():
    for tenant_id in active_tenants:
        # 1. 重算 Merkle tree
        recomputed_root = await rebuild_merkle_tree(tenant_id, day=yesterday)
        stored_root = await get_stored_root(tenant_id, day=yesterday)
        assert recomputed_root == stored_root, "Tampering detected"

        # 2. 與外部錨定比對
        anchored = await fetch_object_lock_anchor(tenant_id, day=yesterday)
        assert stored_root == anchored.root_hash, "Anchor mismatch"

# On-demand inclusion proof（給合規 auditor）
async def prove_audit_entry_included(entry_id: UUID) -> InclusionProof:
    entry = await fetch_audit(entry_id)
    tree = await rebuild_merkle_tree(entry.tenant_id, window=entry.window)
    return tree.generate_proof(entry.leaf_hash)
```

#### 時間戳信任源（**2026-04-28 review 補強**）

> **Review 發現**：NTP 攻擊 / 時鐘漂移會破壞 hash chain 順序。本節補強。

- DB 時間戳一律用 `clock_timestamp()` 而非應用伺服器 NTP（避免漂移）
- 高敏感操作（incident_close / rootcause_apply_fix）額外用 **monotonic logical clock**（per-tenant counter）
- 每日 batch 驗證 NTP drift（與 cloud provider authoritative time 比對）

---

## 合規認證準備

### 目標認證

| 認證 | 適用範圍 | 預期時程 |
|------|--------|---------|
| **SOC 2 Type II** | 雲服務通用 | Phase 56+（生產 6 月後） |
| **ISO 27001** | 資安管理 | Phase 60+ |
| **GDPR** | 歐洲 client | Phase 53 起準備 |
| **HIPAA** | 醫療業 client | 未來考慮 |
| **PCI DSS** | 信用卡 | 不打算碰 |

### GDPR 必要能力（Phase 53 前準備）

| 能力 | 實作位置 |
|------|--------|
| **Right to Access**（請求個資副本） | API: `/api/v1/gdpr/my-data` |
| **Right to Erasure**（被遺忘權） | API: `/api/v1/gdpr/delete-me` + 跨表刪除 |
| **Right to Rectification** | User profile 編輯 |
| **Right to Portability** | JSON / CSV 匯出 |
| **Right to Restrict Processing** | Account suspension |
| **Data Processing Agreement** | 法律文件 + tenant 簽署 |
| **Privacy by Design** | 預設不收集多餘資料 |
| **Breach Notification**（72hr） | Incident response runbook |

### GDPR 刪除挑戰（重要）

```python
# 「被遺忘權」實作的複雜度：
async def gdpr_delete_user(user_id: UUID, tenant_id: UUID):
    """
    必須刪除：
    - users / user_roles / api_keys
    - sessions（cascade）→ messages / tool_calls / etc.
    - memory_user
    - cost_ledger（保留 anonymized 7 年 - 稅務）
    
    不能刪：
    - audit_log（合規要求保留 + append-only）
    
    解法：audit_log 中的 user_id 替換為 hashed pseudonym
          保留 audit 完整性，但無法回溯個人
    """
```

---

## DLP（Data Leakage Prevention）

### Egress 監控

```python
# 所有對外請求（包括 LLM API）經過 DLP
class EgressDLP:
    async def check(self, request: HttpRequest) -> DLPResult:
        # 1. 掃描 body 找 PII / 機密
        # 2. 檢查 destination 是否白名單
        # 3. 高風險請求阻擋 + alert
```

### LLM API 特殊保護

```python
# 防止把 Confidential / Restricted 資料送給 LLM
class LLMRequestSanitizer:
    async def sanitize(self, messages: list[Message]) -> list[Message]:
        """
        策略：
        - PII → 替換為 placeholder（如 [EMAIL], [PHONE]）
        - 內部代碼名稱 → 替換為 generic
        - 帳號資訊 → 完全移除
        """
```

---

## Vulnerability Management

### 掃描層

| 層級 | 工具 | 頻率 |
|------|-----|-----|
| Dependencies | Dependabot + safety + npm audit | 每 PR + 每日 |
| Container images | Trivy + Snyk | 每次 build |
| SAST（靜態） | Semgrep + Bandit | 每 PR |
| DAST（動態） | OWASP ZAP | 每週 staging |
| Penetration test | 第三方 | 每 6 個月 |
| Dependency 升級 | Renovate bot | 自動 PR |

---

## Incident Response

### 安全事件分類

| Severity | 範例 | 響應時間 |
|---------|------|--------|
| **Critical** | Data breach / RCE | < 15 分鐘 |
| **High** | Auth bypass / 跨 tenant 洩漏 | < 1 小時 |
| **Medium** | DoS / 個別 user 異常 | < 4 小時 |
| **Low** | 偵測到 prompt injection 嘗試 | < 24 小時 |

### Runbook 範本

```
## Runbook: Suspected Data Breach

### 偵測來源
- DLP egress alert
- Audit log 異常
- 用戶投訴

### 立即行動（前 15 分鐘）
1. 通知 security oncall
2. 建立 incident channel
3. 確認 scope（哪個 tenant / user / 多少資料）
4. 暫停可能受影響的 sessions
5. 保留 audit log + 系統 snapshot

### 初步分析（1 小時內）
6. Root cause assessment
7. 確認是否真實 breach（非誤報）
8. 評估資料外洩範圍

### Mitigation（4 小時內）
9. 修復或隔離受影響系統
10. Reset 所有可能受影響的 credentials
11. 通知受影響 client（GDPR 72hr 內）

### Post-mortem（48 小時內）
12. 完整事件報告
13. Action items + 責任人
14. 流程改進
```

---

## 安全測試清單（Phase 53 必跑）

```
☐ Authentication bypass testing
☐ Authorization (RBAC) testing
☐ Multi-tenant isolation（跨 tenant 攻擊嘗試）
☐ Prompt injection（LLM01）
☐ Output handling（LLM02）
☐ Tool abuse（LLM07）
☐ DoS / resource exhaustion（LLM04）
☐ Sandbox escape（容器 / process）
☐ Session hijacking
☐ CSRF（前端）
☐ XSS（前端）
☐ SQL injection（雖然用 ORM 仍須驗）
☐ Audit log tamper resistance
☐ Encryption at rest 驗證
☐ TLS configuration（SSL Labs A+）
```

---

## 安全 KPI

| KPI | 目標 |
|-----|------|
| 漏洞修復 SLA（critical） | < 24 小時 |
| 漏洞修復 SLA（high） | < 7 天 |
| Pen test 嚴重發現 | 0 critical, < 3 high |
| Audit log 完整性檢查 | 每日通過 |
| MTTR（Mean Time To Repair） | < 4 小時 |
| MTTD（Mean Time To Detect） | < 15 分鐘 |
| Security training 完成率 | 100% 開發者 |

---

## 結語

V2 安全要求遠超 V1。本文件覆蓋：
- ✅ 資料分類 + 加密
- ✅ Auth / RBAC
- ✅ Threat model（STRIDE + OWASP LLM）
- ✅ Sandbox 多層
- ✅ Audit + hash chain
- ✅ 合規（GDPR / SOC 2 預備）
- ✅ DLP
- ✅ Vuln management
- ✅ Incident response

**Phase 49**：基礎（auth / RLS / encryption）
**Phase 50-52**：應用層（Guardrails / DLP）
**Phase 53**：強化（重點 Phase）
**Phase 56+**：認證準備

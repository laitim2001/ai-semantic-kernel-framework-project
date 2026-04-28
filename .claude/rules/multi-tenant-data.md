# 多租戶資料隔離 + RBAC + GDPR 規則

**Purpose**: DB schema tenant_id / scope 強制隔離 + RLS + API 層 dependency 強制 + GDPR/PII 處理。

**Category**: Security / Data Architecture
**Created**: 2026-04-28
**Last Modified**: 2026-04-28
**Status**: Active

**Modification History**:
- 2026-04-28: Initial creation from 10-server-side-philosophy §原則 1 + 09-db-schema-design + 14-security-deep-dive

---

## 核心鐵律（三條，無例外）

### 規則 1：所有業務 Table 必有 `tenant_id` 欄位

任何表涉及業務資料（非全局系統資料），必須包含 `NOT NULL` 的 `tenant_id` 欄位。

```sql
-- ✅ 正確
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,        -- 鐵律
    user_id UUID NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    UNIQUE (tenant_id, id)
);

-- ❌ 禁止：無 tenant_id
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    content TEXT
);
```

### 規則 2：所有 Query 必須 by `tenant_id` 過濾

每個資料庫查詢（SELECT / INSERT / UPDATE / DELETE）都必須提供 `tenant_id` 過濾條件。

```python
# ✅ 正確
async def get_conversation(session_id: UUID, tenant_id: UUID) -> Conversation:
    stmt = select(Conversation).where(
        (Conversation.id == session_id) &
        (Conversation.tenant_id == tenant_id)
    )
    return await db.execute(stmt)

# ❌ 禁止
async def get_conversation(session_id: UUID) -> Conversation:
    stmt = select(Conversation).where(Conversation.id == session_id)
    return await db.execute(stmt)  # 洩漏風險
```

### 規則 3：所有 API Endpoint 必接 `current_tenant` Dependency

FastAPI dependency injection 強制注入 `current_tenant_id`。

```python
# ✅ 正確
@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    current_tenant: UUID = Depends(get_current_tenant),  # ← 強制
) -> ConversationResponse:
    db_result = await db.get_conversation(conversation_id, current_tenant)
    if not db_result:
        raise HTTPException(status_code=404)
    return db_result

# ❌ 禁止
@app.get("/api/v1/conversations/{conversation_id}")
async def get_conversation(conversation_id: UUID) -> ConversationResponse:
    return await db.get_conversation(conversation_id)
```

---

## Schema 範本

### 業務表（必有 tenant_id）

```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    title VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversations_tenant_user ON conversations(tenant_id, user_id);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    tenant_id UUID NOT NULL,           -- 冗餘但必須（加速查詢）
    user_id UUID,
    role VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    UNIQUE (conversation_id, id)
);

CREATE INDEX idx_messages_tenant ON messages(tenant_id);
CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at);
```

### 全局表（無 tenant_id；極少數）

```sql
-- 系統預設規則 / 工具定義（所有 tenant 共用）
CREATE TABLE tools_registry (
    id UUID PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description TEXT,
    input_schema JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

> 全局表清單必須在 PR 中明示 + 經 architect review。

---

## Memory 雙軸 Scope

Memory 除了 `tenant_id` 隔離，還有 5 層級（system / tenant / role / user / session）× 3 時間尺度（永久 / 季 / 天）：

```sql
CREATE TABLE memory_user (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,        -- 雙軸 1
    user_id UUID NOT NULL,          -- 雙軸 2
    category VARCHAR(64),
    content TEXT,
    expires_at TIMESTAMPTZ,         -- NULL = 永久；3m = 季；1d = 天
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_memory_tenant_user ON memory_user(tenant_id, user_id);
CREATE INDEX idx_memory_expires ON memory_user(expires_at) WHERE expires_at IS NOT NULL;
```

---

## Row-Level Security（RLS）

### PostgreSQL RLS Policy

```sql
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_conversations ON conversations
    USING (tenant_id = current_setting('app.tenant_id')::uuid);

CREATE POLICY tenant_all_conversations ON conversations
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### 應用層 Query Filter（Fallback）

若用 PgBouncer 等 connection pooler 無法 per-request SET，應用層強制：

```python
class ConversationQueryMixin:
    @classmethod
    def scoped_query(cls, session: Session, tenant_id: UUID):
        return session.query(cls).filter(cls.tenant_id == tenant_id)

conversations = await ConversationQueryMixin.scoped_query(db, current_tenant_id).all()
```

### 何時選哪種

| 條件 | 推薦 |
|------|------|
| 無 connection pooler / per-request connection | RLS policy（DB 層強制，最安全） |
| 用 PgBouncer / pgcat | 應用層 filter |
| Critical tables（payment / PII） | 雙重防護（同時用） |

---

## API 層強制 Dependency

```python
# middleware/tenant.py
class TenantContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tenant_id = extract_tenant_from_jwt(request.headers.get("Authorization"))
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        request.state.current_tenant_id = tenant_id

        # 設置 DB session local context（for RLS）
        async with db.session() as session:
            await session.execute(
                text("SET LOCAL app.tenant_id = :tid"),
                {"tid": str(tenant_id)}
            )
            response = await call_next(request)
        return response

# Dependency
async def get_current_tenant(request: Request) -> UUID:
    if not hasattr(request.state, "current_tenant_id"):
        raise HTTPException(status_code=401)
    return request.state.current_tenant_id
```

### 禁止模式

```python
# ❌ 從 query string 讀 tenant_id（可被偽造）
@app.get("/api/conversations")
async def list_conversations(tenant_id: UUID = Query(...)):
    ...  # 應從 JWT 讀

# ❌ 同時收 query 與 JWT 但不驗證一致性
@app.get("/api/conversations")
async def list_conversations(
    current_tenant: UUID = Depends(get_current_tenant),
    tenant_id: UUID = Query(...),
):
    if current_tenant != tenant_id:
        raise HTTPException(status_code=403, detail="Tenant mismatch")
```

---

## 跨租戶資料禁止規範

### ❌ 禁止行為列表

| 禁止 | 理由 | 正確做法 |
|-----|------|--------|
| `SELECT * FROM conversations WHERE id = $1` | 跨 tenant 讀 | `WHERE id = $1 AND tenant_id = $2` |
| `UPDATE messages SET ... WHERE id = $1` | 跨 tenant 寫 | `WHERE id = $1 AND tenant_id = $2` |
| `DELETE FROM memory WHERE user_id = $1` | 可能刪別 tenant 的 user | `WHERE user_id = $1 AND tenant_id = $2` |
| 「user A 能讀就讓 B 看」邏輯 | 違反 zero-trust | 明確檢查 tenant 匹配 + RBAC |

### ✅ 標準範式

```python
async def secure_query(condition_key: UUID, current_tenant_id: UUID, table: TableClass):
    stmt = select(table).where(
        (table.id == condition_key) &
        (table.tenant_id == current_tenant_id)
    )
    result = await db.execute(stmt)
    if not result:
        # 404 不區分「不存在」vs「非此 tenant」（避免資訊洩漏）
        raise HTTPException(status_code=404)
    return result
```

---

## PII / GDPR 處理

### PII 欄位標記 + 加密

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    email VARCHAR(256) NOT NULL,    -- pii=True，應用層加密
    phone VARCHAR(32),              -- pii=True
    display_name VARCHAR(256),      -- 非 PII
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

```python
class User(Base):
    email: Mapped[str] = mapped_column(EncryptedColumn(...))
    phone: Mapped[str | None] = mapped_column(EncryptedColumn(...))
```

### GDPR Right to Erasure 實作

```python
async def gdpr_delete_user(user_id: UUID, tenant_id: UUID):
    async with db.transaction():
        user = await db.get_user(user_id, tenant_id)
        if not user:
            raise ValueError("User not found")

        # 1. 刪除 PII
        await db.execute(
            delete(users).where(
                (users.c.id == user_id) & (users.c.tenant_id == tenant_id)
            )
        )

        # 2. 匿名化 audit log（保留完整性，但無法回溯）
        pseudonym = hashlib.sha256(str(user_id).encode()).hexdigest()[:16]
        await db.execute(
            update(audit_log)
            .where(audit_log.c.user_id == user_id)
            .values(user_id=pseudonym)
        )

        # 3. 記錄 GDPR 刪除事件
        await audit.log_gdpr_deletion(user_id, tenant_id)
```

### PII 脫敏

```python
class PIIRedactor:
    """log / output 中自動脫敏 PII。"""

    @staticmethod
    def redact(text: str) -> str:
        text = re.sub(r'(.)@(.)', r'\1***@\2***', text)            # email
        text = re.sub(r'\d{3}-\d{3}', '***-***', text)             # phone
        text = re.sub(r'\d{3}-\d{2}-\d{4}', '***-**-****', text)   # SSN
        return text

# 使用
logger.info(f"User action: {PIIRedactor.redact(user_input)}")
```

---

## 多租戶測試案例（每個業務 endpoint 必須）

### Case 1：跨租戶讀取被拒

```python
@pytest.mark.asyncio
async def test_cross_tenant_read_denied():
    tenant_a = await db.create_tenant("Tenant A")
    tenant_b = await db.create_tenant("Tenant B")

    conv_a = await db.create_conversation(
        tenant_id=tenant_a.id, user_id=user_a.id, content="Tenant A secret"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_conversation(
            conversation_id=conv_a.id,
            current_tenant=tenant_b.id,
        )
    assert exc_info.value.status_code == 404  # 隱藏真實存在
```

### Case 2：跨租戶寫入被拒

```python
@pytest.mark.asyncio
async def test_cross_tenant_write_denied():
    conv_b = await db.create_conversation(tenant_id=tenant_b.id, ...)

    with pytest.raises(HTTPException) as exc_info:
        await update_conversation(
            conversation_id=conv_b.id,
            current_tenant=tenant_a.id,
            new_content="Hijack!",
        )
    assert exc_info.value.status_code == 404

    conv_b_check = await get_conversation(conv_b.id, tenant_b.id)
    assert conv_b_check.content != "Hijack!"
```

### Case 3：RLS Policy 在 DB 層強制

```python
@pytest.mark.asyncio
async def test_rls_policy_enforced():
    async with db.session() as session:
        await session.execute(
            text("SET LOCAL app.tenant_id = :tid"),
            {"tid": str(tenant_a.id)}
        )
        result = await session.execute(select(conversations))
        rows = result.fetchall()
        assert len(rows) == 1  # 只看到 A
        assert rows[0].tenant_id == tenant_a.id
```

---

## Audit Log（必記每次跨租戶 access 嘗試）

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    user_id UUID,
    operation VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id VARCHAR(256),
    access_allowed BOOLEAN NOT NULL,
    attempted_tenant VARCHAR(256),       -- 跨 tenant 嘗試時記錄
    timestamp_ms BIGINT NOT NULL,
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);
```

---

## CI Lint（自動檢查）

```bash
# scripts/check_tenant_isolation.sh
#!/bin/bash
echo "Checking for missing tenant_id in queries..."

# 找 query 沒帶 tenant_id 的（簡化版；實際需 AST 解析）
grep -rn "select(\|update(\|delete(" backend/src --include="*.py" \
  | grep -v "tenant_id" \
  | grep -v "^#" \
  | grep -v "tools_registry\|tenants" \
  | head -20

if [ $? -eq 0 ]; then
    echo "❌ Possible queries without tenant_id filter"
    exit 1
fi
echo "✅ All queries appear filtered"
```

```bash
# scripts/check_endpoint_dependency.sh
#!/bin/bash
# 找 FastAPI endpoint 沒有 current_tenant dependency
grep -rln "@app\.\(get\|post\|put\|delete\|patch\)" backend/src/api \
  | xargs grep -L "current_tenant" \
  | head -10

if [ $? -eq 0 ]; then
    echo "❌ Endpoints without current_tenant dependency"
    exit 1
fi
```

---

## 引用

- **09-db-schema-design.md** — DB Schema 完整規劃
- **14-security-deep-dive.md** §多租戶 / RLS / GDPR
- **10-server-side-philosophy.md** §原則 1 Server-Side First
- **02-architecture-design.md** §多租戶隔離

---

**多租戶隔離失敗 = 合規災難 + 安全漏洞。所有開發必須遵守本規則。**

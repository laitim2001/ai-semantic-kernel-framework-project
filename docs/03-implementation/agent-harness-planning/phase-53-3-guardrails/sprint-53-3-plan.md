# Sprint 53.3 — Guardrails 核心 (Cat 9)

**Phase**: phase-53-3-guardrails
**Sprint**: 53.3
**Duration**: 5 days (Day 0-4 standard layout)
**Status**: TODO → IN PROGRESS → DONE
**Created**: 2026-05-03
**Owner**: User-spawned session 2026-05-03+
**Branch**: feature/sprint-53-3-guardrails (off main `149de254`)

---

## Sprint Goal

實作 V2 範疇 9 (Guardrails & Safety) **核心**：把 `01-eleven-categories-spec.md` §範疇 9 規格落地為**生產級實作** — `GuardrailEngine` + 3 層 Guardrails（input / output / tool）concrete impl + `Tripwire` ABC + plug-in registry（per `17.md §6` 邊界，**non-範疇 8**）+ `CapabilityMatrix`（capability → tool 對應）+ **WORM append-only audit log + hash chain**（不可篡改強驗證）+ AgentLoop 3 層 check 整合（loop start input check / 每 tool call tool check / loop end output check + tripwire 立即終止）。同時 bundle 2 個 Cat 8 carryover：AD-Cat8-1 fakeredis + RedisBudgetStore integration test、AD-Cat8-3 ToolResult.error_class 欄位。**這是 V2 第 15 sprint（64% → 68%）**，phase 53 第 3 sprint。

> **Scope 控制注意**：53.3 為 **Cat 9 核心** — 3 階段審批（trust establishment / permission check / explicit confirmation）的後 2 階段（HITL 完整化）排程到 **53.4 Governance Frontend + V1 HITL/Risk 遷移**。本 sprint 只實作 trust baseline + permission check stub（per US-4 CapabilityMatrix），不做 Teams / UI 整合。

---

## Background

### Cat 9 history

- **Sprint 49.1 (Phase 49 Foundation)** 落地 ABC stub：
  - `backend/src/agent_harness/guardrails/_abc.py`：`GuardrailType` enum (INPUT / OUTPUT / TOOL)、`GuardrailAction` enum (PASS / BLOCK / SANITIZE / ESCALATE / REROLL)、`GuardrailResult` dataclass、`Guardrail` ABC (check) + `Tripwire` ABC (trigger_check / register_pattern)
  - `backend/src/agent_harness/guardrails/__init__.py`：empty re-export stub
  - `backend/src/agent_harness/guardrails/README.md`：明確標 "Implementation Phase: 53.3-53.4"
- **多個檔案 reference guardrails**（loop / tools / verification 等已預期 Cat 9 整合點），但**沒有**concrete impl

### 53.3 為何啟動 phase 53.3

per `06-phase-roadmap.md` §Phase 53：
- 53.1 — State Mgmt (Cat 7) ✅ COMPLETE 2026-05-02 (PR #39 → main aaa3dd75)
- 53.2 — Error Handling (Cat 8) ✅ COMPLETE 2026-05-03 (PR #48 → main a77878ad)
- 53.2.5 — CI carryover (archived ci.yml) ✅ COMPLETE 2026-05-03 (PR #50/#51/#52 → main 149de254)
- 53.3 — Guardrails 核心 (Cat 9) ← **本 sprint**
- 53.4 — Governance Frontend + V1 HITL/Risk 遷移 + 三階段審批完整化

Guardrails 是 Cat 10 / Cat 11 / Phase 55 的前置：
- Verification (Cat 10) self-correction loop 與 Output guardrail 不同責任邊界（per 17.md §6）— Cat 10 修「答錯」、Cat 9 防「不安全」
- Subagent (Cat 11) dispatcher 在 spawn child agent 前需 input guardrail check
- Phase 55 business domain canary 必須有 Cat 9 三層全綠才能上線（敏感業務 API 必須 tool guardrail 守門）
- Cat 8 ErrorTerminator 已就緒（53.2 落地）— Cat 9 Tripwire 邊界明確（per 17.md §6 §第 6 部分），不混用

### Sprint 53.2 carryover bundling (53.x 早期)

per Sprint 53.2 retrospective Q5（`docs/03-implementation/agent-harness-execution/phase-53-2/sprint-53-2-error-handling/retrospective.md` §Audit Debt）：

- **AD-Cat8-1** RedisBudgetStore 0% coverage；需 fakeredis dep + integration test → 53.x or 54.x
  - `_redis_store.py` 在 53.2 因 CI 無 Redis 而 0% covered；本 sprint 加 fakeredis dev dep + integration test 驗 MULTI/EXEC pipeline 行為
- **AD-Cat8-3** ToolResult.error_class 欄位
  - 53.2 soft-failure 路徑 synthesizes Exception(str)；loses original type；本 sprint 加欄位讓 ErrorPolicy.classify 真知道原 exception type
- **Carry deferred**：AD-Cat8-2（RetryPolicyMatrix end-to-end retry-with-backoff loop）larger refactor → 54.x bundle；AD-CI-4/5（sprint plan template + paths-filter strategy）→ 53.4 with sprint workflow rule update；AI-22（chaos test enforce_admins）→ separate chaos sprint

### Branch protection 已生效（since Sprint 52.6 + Solo-dev policy 53.2 結構性變更）

- `enforce_admins=true` block admin bypass
- `required_approving_review_count=0`（**永久**，2026-05-03 Sprint 53.2 起；solo-dev policy；無第二 reviewer 不需 review approval）
- 4 active CI checks（Lint + Type Check / Test (PG16) / V2 Lints / Backend CI 子作業）
- 53.3 PR 走**正常 normal merge**（user approve → 我 merge；OR direct merge if author = solo dev）；**不**走 temp-relax bootstrap（已淘汰）

詳見：
- `01-eleven-categories-spec.md` §範疇 9 Guardrails & Safety
- `17-cross-category-interfaces.md` §1.1 GuardrailResult / Tripwire single-source + §6 Tripwire 邊界（範疇 8 vs 9）
- `agent_harness/guardrails/README.md`（Sprint 49.1 stub readme）
- Sprint 53.2 retrospective AD-Cat8-1 / AD-Cat8-3
- `06-phase-roadmap.md` §Sprint 53.3 Deliverables
- `feedback_branch_protection_solo_dev_policy.md`

---

## User Stories

### US-1：作為 V2 開發者，我希望 `GuardrailEngine` 能組合多個 `Guardrail` 並按 type (input/output/tool) 跑 check chain，以便上層 Loop 在 3 個切點呼叫對應 chain 而不需知道內部 detector 細節

- **驗收**：
  - `GuardrailEngine.check_input(content, ctx) -> GuardrailResult`
  - `GuardrailEngine.check_output(content, ctx) -> GuardrailResult`
  - `GuardrailEngine.check_tool_call(tc, ctx) -> GuardrailResult`
  - 內部 chain：依 registered Guardrail `guardrail_type` 過濾，按 priority order 跑；first non-PASS result 短路返回（fail-fast）
  - `register(guardrail: Guardrail, *, priority: int = 100)` 註冊；priority 0=最高
  - 並行 batch 執行模式（`batch_check_tool_calls(tcs)` for parallel tool guardrails）— per spec p95 < 50ms per tool
  - YAML config 載入支援（`backend/config/guardrails.yaml`）— per-type guardrail list + ordering
  - Unit tests ≥ 90% coverage
  - **`GuardrailTriggered` event** emit per `17.md §3 Loop events`
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/engine.py` (new)
  - `backend/src/agent_harness/_contracts/events.py`（補 `GuardrailTriggered` event）
  - `backend/config/guardrails.yaml` (new)
  - test files
- **GitHub Issue**：#53（Day 0 建立）

### US-2：作為 platform owner，我希望 `PIIDetector` + `JailbreakDetector` 兩個 input guardrail concrete impl（defense in depth：regex/pattern + LLM-as-judge fallback），以便 input 階段擋下 PII leak 與 prompt injection

- **驗收**：
  - `PIIDetector(Guardrail)`：guardrail_type=INPUT；regex 偵測（email / phone / SSN / credit card）+ optional LLM-as-judge second-pass（high-risk content）
  - `JailbreakDetector(Guardrail)`：guardrail_type=INPUT；pattern list（"ignore previous instructions" / "system prompt" / "jailbreak" / "DAN"）+ embedding similarity（optional, behind feature flag）
  - 偵測命中 → return `GuardrailAction.BLOCK` with `risk_level=HIGH`
  - 模糊命中 → return `GuardrailAction.ESCALATE`（→ HITL via §HITL stub）
  - SLO p95 < 100ms（per spec）；regex-only path < 10ms
  - red-team test set：**PII detection accuracy > 95%** + **jailbreak detection accuracy > 90%**（pre-curated 30+ case fixtures each）
  - Unit tests cover positive + negative + false-positive 邊界
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/input/pii_detector.py` (new)
  - `backend/src/agent_harness/guardrails/input/jailbreak_detector.py` (new)
  - `backend/tests/fixtures/guardrails/pii_redteam.yaml` (new — 30+ cases)
  - `backend/tests/fixtures/guardrails/jailbreak_redteam.yaml` (new — 30+ cases)
  - test files
- **GitHub Issue**：#54

### US-3：作為合規負責人，我希望 `ToxicityDetector` + `SensitiveInfoDetector` 兩個 output guardrail concrete impl，以便 output 階段擋下毒性內容 + 敏感資訊外洩

- **驗收**：
  - `ToxicityDetector(Guardrail)`：guardrail_type=OUTPUT；regex/pattern + LLM-as-judge（必要時）；categories: hate / harassment / violence / sexual
  - `SensitiveInfoDetector(Guardrail)`：guardrail_type=OUTPUT；偵測 system prompt leak / internal IDs / tenant cross-leak（基於 tenant_id 上下文）
  - 命中 → 依 risk 返回 `BLOCK` (high) / `SANITIZE` (medium, return sanitized_content) / `REROLL` (low, ask LLM retry)
  - SLO p95 < 200ms（含 LLM-as-judge）；regex-only < 50ms
  - Multi-tenant 隔離 test：tenant A output 含 tenant B internal ID → BLOCK
  - Unit tests + tenant cross-leak test
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/output/toxicity_detector.py` (new)
  - `backend/src/agent_harness/guardrails/output/sensitive_info_detector.py` (new)
  - `backend/tests/fixtures/guardrails/toxicity_cases.yaml` (new — 20+ cases)
  - `backend/tests/fixtures/guardrails/sensitive_leak_cases.yaml` (new — 15+ cases)
  - test files
- **GitHub Issue**：#55

### US-4：作為 tool platform owner，我希望 `CapabilityMatrix` 把 capability 對應到 tool list + per-tool permission rule，以便 `ToolGuardrail` 能在每個 tool call 前獨立 gating（CC ~40 capability 對應）

- **驗收**：
  - `CapabilityMatrix(Mapping[Capability, list[ToolName]])` + `permission_rules: dict[ToolName, PermissionRule]`
  - `Capability` enum：READ_KB / WRITE_KB / EXECUTE_QUERY / MODIFY_TICKET / SEND_NOTIFICATION / etc（≥ 8 capabilities）
  - `PermissionRule(role_required, tenant_scope, max_calls_per_session, requires_approval)`
  - YAML config 載入（`backend/config/capability_matrix.yaml`）— per-tenant override
  - `ToolGuardrail(Guardrail)`：guardrail_type=TOOL；check_tool_call 查 matrix → permission 檢查 → return GuardrailResult
  - 三階段審批 stage 1 + 2：trust baseline（session start 建立用戶角色 + tenant policy）+ permission check（每 tool 自動 check）；stage 3 explicit confirmation defer 53.4
  - SLO p95 < 50ms（per spec, per tool call）
  - Multi-tenant 隔離 test：tenant A 角色 write tools 不能 affect tenant B
  - Unit tests + integration with ToolGuardrail
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/tool/capability_matrix.py` (new)
  - `backend/src/agent_harness/guardrails/tool/tool_guardrail.py` (new)
  - `backend/config/capability_matrix.yaml` (new)
  - test files
- **GitHub Issue**：#56

### US-5：作為 security owner，我希望 `Tripwire` ABC + plug-in registry（已 stub），以便 PII leak / jailbreak / data exfil 嫌疑檢測命中時 loop 立即中斷（NOT retry，per 17.md §6 邊界）

- **驗收**：
  - `DefaultTripwire(Tripwire)` impl：register_pattern(name, detector_callable) + trigger_check(content, ctx)
  - 內建 patterns：`pii_leak_detected`、`prompt_injection_detected`、`unauthorized_tool_access`、`unsafe_output_detected`（4 個 stub patterns；rate_limit/budget defer Cat 8 already）
  - Tripwire 觸發 → emit `TripwireTriggered` event → AgentLoop 立即 break + checkpoint state
  - SLO < 50ms（per spec）
  - **Cat 8 vs Cat 9 邊界守住**：grep `ErrorTerminator` 在 `guardrails/` = 0 hits；grep `Tripwire` 在 `error_handling/` = 0 hits
  - Unit tests cover：register / trigger / no-match / multiple-patterns / async-safety
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/tripwire.py` (new)
  - `backend/src/agent_harness/_contracts/events.py`（補 `TripwireTriggered` event；前已 stub 名為 `GuardrailTriggered`，本 sprint 補 `TripwireTriggered` 區分）
  - test files
- **GitHub Issue**：#57

### US-6：作為 audit / compliance owner，我希望 **WORM (Write-Once-Read-Many) append-only audit log + hash chain**（per spec §驗收），以便 guardrail decisions / tripwire trips / tool denials 不可篡改

- **驗收**：
  - `WORMAuditLog` impl：append_only writes；entries 含 `prev_hash` + `entry_hash` (SHA-256 of prev_hash + content)
  - DB schema：`audit_log_v2` table（id / tenant_id / timestamp / event_type / content / prev_hash / entry_hash）— Alembic migration
  - `verify_chain(tenant_id, from_id, to_id) -> ChainVerificationResult` 驗證連續 hash 鏈未斷裂
  - 寫入失敗 → ErrorTerminator FATAL（audit log 不可失敗）
  - Append latency p95 < 20ms
  - Unit tests + integration test：寫 100 entries → verify chain → 篡改 entry 50 → verify fail at entry 50
- **影響檔案**：
  - `backend/src/agent_harness/guardrails/audit/worm_log.py` (new)
  - `backend/src/agent_harness/guardrails/audit/chain_verifier.py` (new)
  - `backend/alembic/versions/<timestamp>_add_audit_log_v2.py` (new migration)
  - `backend/src/infrastructure/db/models/audit_log_v2.py` (new ORM model)
  - test files
- **GitHub Issue**：#58

### US-7：作為 AgentLoop owner，我希望 3 層 guardrail check 在 loop 主流量真實 wire（input check at start / tool check before each tool call / output check at end + tripwire 立即終止 + WORM audit 紀錄），以便 Loop 真實使用 Cat 9 整套機制（反 AP-4 Potemkin）

- **驗收**：
  - `AgentLoop.run()` 加 5 個 opt-in deps（同 Cat 7 / Cat 8 pattern）：
    - `guardrail_engine: GuardrailEngine | None = None`
    - `tripwire: Tripwire | None = None`
    - `audit_log: WORMAuditLog | None = None`
    - `capability_matrix: CapabilityMatrix | None = None`
    - 既有 deps（reducer/checkpointer/error_*）保留
  - **Loop start**：`guardrail_engine.check_input(user_input, ctx)` + `tripwire.trigger_check(input)` → 命中 → emit `GuardrailTriggered/TripwireTriggered` + audit_log.append + Loop break
  - **Per tool call**：`guardrail_engine.check_tool_call(tc, ctx)` + `tripwire.trigger_check(tc)` → BLOCK → 回注 LLM as `ToolResult(is_error=True, content="Tool blocked: ...")`；ESCALATE → HITL stub；TRIPWIRE → break
  - **Loop end**：`guardrail_engine.check_output(final_response, ctx)` → BLOCK/SANITIZE/REROLL 處理；REROLL → 重 LLM call (max 1 次, defer Cat 10 self-correction loop)；TRIPWIRE → break
  - 整合 test 6 scenarios：
    - input PII detected → BLOCK + audit logged
    - input jailbreak → BLOCK + tripwire triggered
    - tool unauthorized → BLOCK + LLM 回注 error
    - output toxicity high → BLOCK + audit logged
    - output sensitive info → SANITIZE + content replaced
    - output reroll → 1 retry then accept
  - **不退步** Cat 1/7/8 既有 tests（51.x + 53.1 + 53.2 baseline）
  - Opt-in pattern：所有 Cat 9 deps 傳 None → fallback 至 raw behavior（53.2 行為保留）
- **影響檔案**：
  - `backend/src/agent_harness/orchestrator_loop/loop.py`
  - `backend/src/agent_harness/orchestrator_loop/_abc.py`（新 deps）
  - 可能 `backend/src/api/v1/chat/router.py`（DI: guardrail_engine + tripwire + audit_log + capability_matrix）
  - `backend/tests/integration/agent_harness/orchestrator_loop/test_loop_guardrails.py` (new)
- **GitHub Issue**：#59

### US-8：作為 53.2 carryover owner，我希望 AD-Cat8-1 RedisBudgetStore integration test 實作（fakeredis dev dep + MULTI/EXEC pipeline 驗證），以便 Cat 8 _redis_store.py 從 0% coverage 升至 ≥ 80%

- **驗收**：
  - `fakeredis>=2.20` 加入 `backend/pyproject.toml [project.optional-dependencies] dev`
  - `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py` (new)
  - 測試：increment 原子性 (concurrent INCR + EXPIRE) / get / TTL 正確 / multi-tenant key isolation / pipeline rollback on error
  - `_redis_store.py` coverage ≥ 80%（53.2 baseline 0%）
  - 不退步 53.2 既有 budget tests
  - 關閉 GitHub issue（53.2 retrospective AD-Cat8-1 對應 ticket）
- **影響檔案**：
  - `backend/pyproject.toml`（fakeredis dev dep）
  - `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py` (new)
- **GitHub Issue**：#60（Day 0 建立 — AD-Cat8-1 ticket）

### US-9：作為 53.2 carryover owner，我希望 AD-Cat8-3 `ToolResult.error_class` 欄位實作，以便 soft-failure 路徑保留原 exception type 給 ErrorPolicy.classify 用（非 synthesize Exception(str)）

- **驗收**：
  - `ToolResult` dataclass 加 `error_class: str | None = None`（fully-qualified class name e.g. `aiohttp.ClientConnectionError`）
  - `ToolExecutor.execute()` 異常路徑：`error_class=f"{type(exc).__module__}.{type(exc).__name__}"`
  - `DefaultErrorPolicy.classify()` 增強：先 try `error_class` lookup，再 fallback 既有 MRO walk
  - 不破壞既有 ToolResult 序列化（新增欄位 default None）
  - Unit test：register custom Exception class → soft-failure ToolResult → classify 正確命中 category
  - 不退步 51.x + 53.2 既有 tests
  - 關閉 GitHub issue（53.2 retrospective AD-Cat8-3 對應 ticket）
- **影響檔案**：
  - `backend/src/agent_harness/_contracts/tools.py`（補 ToolResult.error_class）
  - `backend/src/agent_harness/tools/executor.py`（異常路徑寫 error_class）
  - `backend/src/agent_harness/error_handling/policy.py`（classify 增強）
  - test files
- **GitHub Issue**：#61（Day 0 建立 — AD-Cat8-3 ticket）

---

## Technical Specifications

### US-1 — GuardrailEngine framework

**設計**：

```python
# backend/src/agent_harness/guardrails/engine.py
import asyncio
from dataclasses import dataclass, field
from typing import Any
from agent_harness._contracts import TraceContext
from agent_harness.guardrails._abc import (
    Guardrail, GuardrailAction, GuardrailResult, GuardrailType,
)


@dataclass
class _RegisteredGuardrail:
    guardrail: Guardrail
    priority: int


class GuardrailEngine:
    """Composes multiple Guardrails per type; runs chain with fail-fast."""

    def __init__(self) -> None:
        self._registry: dict[GuardrailType, list[_RegisteredGuardrail]] = {
            GuardrailType.INPUT: [],
            GuardrailType.OUTPUT: [],
            GuardrailType.TOOL: [],
        }

    def register(self, guardrail: Guardrail, *, priority: int = 100) -> None:
        self._registry[guardrail.guardrail_type].append(
            _RegisteredGuardrail(guardrail=guardrail, priority=priority)
        )
        self._registry[guardrail.guardrail_type].sort(key=lambda r: r.priority)

    async def _run_chain(
        self,
        gtype: GuardrailType,
        content: Any,
        *,
        trace_context: TraceContext | None = None,
    ) -> GuardrailResult:
        for entry in self._registry[gtype]:
            result = await entry.guardrail.check(
                content=content, trace_context=trace_context
            )
            if result.action != GuardrailAction.PASS:
                return result  # fail-fast
        return GuardrailResult(action=GuardrailAction.PASS)

    async def check_input(self, content, *, trace_context=None) -> GuardrailResult:
        return await self._run_chain(GuardrailType.INPUT, content, trace_context=trace_context)

    async def check_output(self, content, *, trace_context=None) -> GuardrailResult:
        return await self._run_chain(GuardrailType.OUTPUT, content, trace_context=trace_context)

    async def check_tool_call(self, tc, *, trace_context=None) -> GuardrailResult:
        return await self._run_chain(GuardrailType.TOOL, tc, trace_context=trace_context)

    async def batch_check_tool_calls(self, tcs, *, trace_context=None) -> list[GuardrailResult]:
        """Parallel for many tool calls per turn."""
        return await asyncio.gather(*(
            self.check_tool_call(tc, trace_context=trace_context) for tc in tcs
        ))
```

**`GuardrailTriggered` event** (per 17.md §3 §247)：

```python
# backend/src/agent_harness/_contracts/events.py
@dataclass(frozen=True)
class GuardrailTriggered:
    """範疇 9 emit；Cat 1 Loop 接收。"""
    guardrail_type: str  # "input" / "output" / "tool"
    guardrail_name: str
    action: str  # GuardrailAction value
    reason: str | None
    risk_level: str  # LOW / MEDIUM / HIGH / CRITICAL
```

**驗證**：
- Unit tests：register / priority order / fail-fast / 3 types isolation / batch parallel
- Coverage ≥ 90%

**Effort**: 0.5 day（Day 1 上半）

### US-2 — Input guardrails (PII + Jailbreak)

**設計**：

```python
# backend/src/agent_harness/guardrails/input/pii_detector.py
import re
from agent_harness.guardrails._abc import Guardrail, GuardrailType, GuardrailAction, GuardrailResult


class PIIDetector(Guardrail):
    guardrail_type = GuardrailType.INPUT

    PATTERNS = {
        "email": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
        "phone": re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{4,9}"),
        "ssn": re.compile(r"\d{3}-\d{2}-\d{4}"),
        "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    }

    def __init__(self, *, llm_judge_threshold: int = 2) -> None:
        self._llm_threshold = llm_judge_threshold

    async def check(self, *, content, trace_context=None) -> GuardrailResult:
        text = self._extract_text(content)
        hits = {name: p.findall(text) for name, p in self.PATTERNS.items()}
        total_hits = sum(len(h) for h in hits.values())
        if total_hits == 0:
            return GuardrailResult(action=GuardrailAction.PASS)
        if total_hits >= self._llm_threshold:
            return GuardrailResult(
                action=GuardrailAction.BLOCK,
                reason=f"PII detected: {[k for k, v in hits.items() if v]}",
                risk_level="HIGH",
            )
        return GuardrailResult(
            action=GuardrailAction.ESCALATE,
            reason=f"PII suspected: {hits}",
            risk_level="MEDIUM",
        )

    def _extract_text(self, content) -> str: ...


# backend/src/agent_harness/guardrails/input/jailbreak_detector.py
class JailbreakDetector(Guardrail):
    guardrail_type = GuardrailType.INPUT

    PATTERNS = [
        re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+prompt", re.IGNORECASE),
        re.compile(r"\bjailbreak\b", re.IGNORECASE),
        re.compile(r"\bDAN\s+mode\b", re.IGNORECASE),
        re.compile(r"developer\s+mode", re.IGNORECASE),
    ]

    async def check(self, *, content, trace_context=None) -> GuardrailResult:
        text = str(content)
        for p in self.PATTERNS:
            if p.search(text):
                return GuardrailResult(
                    action=GuardrailAction.BLOCK,
                    reason=f"Jailbreak pattern: {p.pattern}",
                    risk_level="HIGH",
                )
        return GuardrailResult(action=GuardrailAction.PASS)
```

**Red-team fixture** (`tests/fixtures/guardrails/pii_redteam.yaml`)：

```yaml
positives:
  - id: pii_001
    content: "My email is john@example.com"
    expected_action: ESCALATE
    expected_risk: MEDIUM
  - id: pii_002
    content: "Email: john@example.com phone: +1-555-1234"
    expected_action: BLOCK
    expected_risk: HIGH
  # ... 30+ cases
negatives:
  - id: pii_neg_001
    content: "How does email work?"
    expected_action: PASS
  # ...
```

**驗證**：
- Unit tests pass on red-team fixtures: PII accuracy ≥ 95%, Jailbreak ≥ 90%
- SLO regex-only path < 10ms（pytest-benchmark）

**Effort**: 1 day（Day 1 下半 + Day 2 上半 share）

### US-3 — Output guardrails (Toxicity + SensitiveInfo)

**設計**：

```python
# backend/src/agent_harness/guardrails/output/toxicity_detector.py
class ToxicityDetector(Guardrail):
    guardrail_type = GuardrailType.OUTPUT
    PATTERNS = {
        "hate": [...],
        "harassment": [...],
        "violence": [...],
        "sexual": [...],
    }

    async def check(self, *, content, trace_context=None) -> GuardrailResult:
        text = str(content)
        hits = self._regex_scan(text)
        if not hits:
            return GuardrailResult(action=GuardrailAction.PASS)
        max_severity = max(h["severity"] for h in hits)
        if max_severity == "HIGH":
            return GuardrailResult(action=GuardrailAction.BLOCK, risk_level="HIGH", ...)
        if max_severity == "MEDIUM":
            return GuardrailResult(
                action=GuardrailAction.SANITIZE,
                sanitized_content=self._redact(text, hits),
                risk_level="MEDIUM",
            )
        return GuardrailResult(action=GuardrailAction.REROLL, risk_level="LOW")


# backend/src/agent_harness/guardrails/output/sensitive_info_detector.py
class SensitiveInfoDetector(Guardrail):
    guardrail_type = GuardrailType.OUTPUT

    SYSTEM_PROMPT_LEAK_PATTERNS = [
        re.compile(r"You are an? (\w+) (?:agent|assistant)", re.IGNORECASE),
        re.compile(r"<system>.*</system>", re.DOTALL),
    ]

    async def check(self, *, content, trace_context=None) -> GuardrailResult:
        text = str(content)
        # System prompt leak
        for p in self.SYSTEM_PROMPT_LEAK_PATTERNS:
            if p.search(text):
                return GuardrailResult(action=GuardrailAction.BLOCK, reason="system prompt leak", risk_level="CRITICAL")
        # Tenant cross-leak
        if hasattr(trace_context, "tenant_id"):
            other_tenants_ids = await self._fetch_other_tenant_ids(trace_context.tenant_id)
            for tid in other_tenants_ids:
                if str(tid) in text:
                    return GuardrailResult(action=GuardrailAction.BLOCK, reason=f"cross-tenant leak: {tid}", risk_level="CRITICAL")
        return GuardrailResult(action=GuardrailAction.PASS)
```

**驗證**：
- Multi-tenant cross-leak test：tenant A output 含 tenant B UUID → BLOCK
- 20+ toxicity cases / 15+ sensitive info cases red-team set
- SLO p95 < 200ms（含 LLM-as-judge fallback；regex-only path < 50ms）

**Effort**: 1 day（Day 2 下半 + Day 3 上半 share）

### US-4 — CapabilityMatrix + ToolGuardrail

**設計**：

```python
# backend/src/agent_harness/guardrails/tool/capability_matrix.py
from enum import Enum
from dataclasses import dataclass


class Capability(Enum):
    READ_KB = "read_kb"
    WRITE_KB = "write_kb"
    EXECUTE_QUERY = "execute_query"
    MODIFY_TICKET = "modify_ticket"
    SEND_NOTIFICATION = "send_notification"
    READ_PII = "read_pii"
    EXECUTE_SHELL = "execute_shell"  # high-risk
    CALL_EXTERNAL_API = "call_external_api"


@dataclass(frozen=True)
class PermissionRule:
    role_required: str  # "user" / "admin" / "ops"
    tenant_scope: str  # "any" / "own_only"
    max_calls_per_session: int
    requires_approval: bool


class CapabilityMatrix:
    def __init__(
        self,
        capability_to_tools: dict[Capability, list[str]],
        permission_rules: dict[str, PermissionRule],
    ) -> None:
        self._capability_to_tools = capability_to_tools
        self._permission_rules = permission_rules
        self._tool_to_capability = self._build_inverse()

    def get_capability(self, tool_name: str) -> Capability | None:
        return self._tool_to_capability.get(tool_name)

    def get_rule(self, tool_name: str) -> PermissionRule | None:
        return self._permission_rules.get(tool_name)

    @classmethod
    def from_yaml(cls, path: str) -> "CapabilityMatrix": ...


# backend/src/agent_harness/guardrails/tool/tool_guardrail.py
class ToolGuardrail(Guardrail):
    guardrail_type = GuardrailType.TOOL

    def __init__(self, matrix: CapabilityMatrix) -> None:
        self._matrix = matrix

    async def check(self, *, content, trace_context=None) -> GuardrailResult:
        tc = content  # ToolCall
        rule = self._matrix.get_rule(tc.tool_name)
        if not rule:
            return GuardrailResult(action=GuardrailAction.BLOCK, reason=f"unknown tool: {tc.tool_name}", risk_level="HIGH")
        # Stage 2: permission check
        user_role = self._extract_user_role(trace_context)
        if rule.role_required != "any" and user_role != rule.role_required:
            return GuardrailResult(action=GuardrailAction.BLOCK, reason=f"role required: {rule.role_required}", risk_level="HIGH")
        # tenant scope check
        # max calls check (counter via state.transient or external)
        # approval gate stub (defer 53.4 explicit confirmation)
        if rule.requires_approval:
            return GuardrailResult(action=GuardrailAction.ESCALATE, reason="requires approval", risk_level="MEDIUM")
        return GuardrailResult(action=GuardrailAction.PASS)
```

**YAML config**:

```yaml
# backend/config/capability_matrix.yaml
capabilities:
  read_kb: [search_kb, get_doc]
  write_kb: [create_doc, update_doc, delete_doc]
  execute_query: [salesforce_query, sap_query]
  modify_ticket: [update_jira, close_jira]
  execute_shell: [run_command]  # high-risk

permission_rules:
  search_kb:
    role_required: any
    tenant_scope: own_only
    max_calls_per_session: 100
    requires_approval: false
  delete_doc:
    role_required: admin
    tenant_scope: own_only
    max_calls_per_session: 10
    requires_approval: true
  run_command:
    role_required: ops
    tenant_scope: own_only
    max_calls_per_session: 5
    requires_approval: true
```

**驗證**：
- Multi-tenant test：tenant_a admin 角色不能 affect tenant_b
- SLO p95 < 50ms（per spec）
- Stage 1 + 2 working；Stage 3 (explicit confirmation) defer 53.4

**Effort**: 0.75 day（Day 3 share）

### US-5 — Tripwire concrete impl

**設計**：

```python
# backend/src/agent_harness/guardrails/tripwire.py
from typing import Callable, Any, Awaitable
from agent_harness.guardrails._abc import Tripwire as TripwireABC


DetectorFn = Callable[[Any], Awaitable[bool]]


class DefaultTripwire(TripwireABC):
    def __init__(self) -> None:
        self._patterns: dict[str, DetectorFn] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self._patterns["pii_leak_detected"] = self._detect_pii_leak
        self._patterns["prompt_injection_detected"] = self._detect_prompt_injection
        self._patterns["unauthorized_tool_access"] = self._detect_unauth_tool
        self._patterns["unsafe_output_detected"] = self._detect_unsafe_output

    def register_pattern(self, *, name: str, detector: DetectorFn) -> None:
        self._patterns[name] = detector

    async def trigger_check(self, *, content, trace_context=None) -> bool:
        for name, fn in self._patterns.items():
            if await fn(content):
                # log which pattern via trace
                return True
        return False

    async def _detect_pii_leak(self, content) -> bool: ...
    async def _detect_prompt_injection(self, content) -> bool: ...
    async def _detect_unauth_tool(self, content) -> bool: ...
    async def _detect_unsafe_output(self, content) -> bool: ...


class TripwireTriggered:  # event in _contracts/events.py
    pattern_name: str
    detail: str | None
```

**Cat 8 vs Cat 9 邊界守門**（同 53.2 §AC §跨切面紀律）：
- grep `ErrorTerminator` 在 `backend/src/agent_harness/guardrails/` = 0 hits
- grep `Tripwire` 在 `backend/src/agent_harness/error_handling/` = 0 hits（53.2 已守住）

**驗證**：
- Unit tests cover：register / trigger / no-match / multiple-patterns / async-safety
- SLO < 50ms（per spec）

**Effort**: 0.75 day（Day 3 下半 share）

### US-6 — WORM audit log + hash chain

**設計**：

```python
# backend/src/infrastructure/db/models/audit_log_v2.py
class AuditLogV2(Base):
    __tablename__ = "audit_log_v2"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"))
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    event_type: Mapped[str]
    content: Mapped[dict] = mapped_column(JSONB)
    prev_hash: Mapped[str | None]  # NULL for tenant's first entry
    entry_hash: Mapped[str]  # SHA-256 of (prev_hash + canonical_json(content))


# backend/src/agent_harness/guardrails/audit/worm_log.py
import hashlib
import json


class WORMAuditLog:
    """Write-Once-Read-Many append-only audit log with hash chain."""

    def __init__(self, db_session_factory) -> None:
        self._sf = db_session_factory

    async def append(
        self,
        *,
        tenant_id: UUID,
        event_type: str,
        content: dict,
    ) -> AuditLogV2:
        async with self._sf() as session:
            prev = await session.execute(
                select(AuditLogV2)
                .where(AuditLogV2.tenant_id == tenant_id)
                .order_by(AuditLogV2.id.desc())
                .limit(1)
            )
            prev_row = prev.scalar_one_or_none()
            prev_hash = prev_row.entry_hash if prev_row else None
            canonical = json.dumps(content, sort_keys=True, separators=(",", ":"))
            entry_hash = hashlib.sha256(
                ((prev_hash or "") + canonical).encode("utf-8")
            ).hexdigest()
            entry = AuditLogV2(
                tenant_id=tenant_id, event_type=event_type,
                content=content, prev_hash=prev_hash, entry_hash=entry_hash,
            )
            session.add(entry)
            await session.commit()
            return entry


# backend/src/agent_harness/guardrails/audit/chain_verifier.py
@dataclass(frozen=True)
class ChainVerificationResult:
    valid: bool
    broken_at_id: int | None
    total_entries: int


async def verify_chain(
    session_factory, tenant_id: UUID, *, from_id=None, to_id=None
) -> ChainVerificationResult: ...
```

**Alembic migration**:

```python
# backend/alembic/versions/<timestamp>_add_audit_log_v2.py
def upgrade():
    op.create_table(
        "audit_log_v2",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("tenant_id", sa.UUID, sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("content", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("prev_hash", sa.String(64)),
        sa.Column("entry_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_index("idx_audit_v2_tenant_ts", "audit_log_v2", ["tenant_id", "timestamp"])
```

**驗證**：
- Append → verify chain → tamper one entry → verify fail at exact id
- Append latency p95 < 20ms（pytest-benchmark）
- Multi-tenant 隔離：tenant A 篡改不影響 tenant B 鏈

**Effort**: 1 day（Day 3 下半 + Day 4 上半 share）

### US-7 — AgentLoop 3 layer integration

**設計**：

```python
# backend/src/agent_harness/orchestrator_loop/loop.py
class AgentLoop:
    def __init__(
        self,
        chat_client, tool_executor, prompt_builder, verifier,
        reducer, checkpointer,
        # Cat 8 deps (existing)
        error_policy=None, retry_policy=None, circuit_breaker=None,
        error_budget=None, error_terminator=None,
        # Cat 9 deps (new, opt-in)
        guardrail_engine: "GuardrailEngine | None" = None,
        tripwire: "Tripwire | None" = None,
        audit_log: "WORMAuditLog | None" = None,
        capability_matrix: "CapabilityMatrix | None" = None,
        ...
    ): ...

    async def run(self, *, messages, tools, ..., trace_context=None):
        # ===== Loop start: input check =====
        if self._guardrail_engine:
            input_result = await self._guardrail_engine.check_input(messages[-1], trace_context=trace_context)
            if input_result.action != GuardrailAction.PASS:
                await self._emit_guardrail_triggered(input_result, "input")
                if self._audit_log:
                    await self._audit_log.append(
                        tenant_id=trace_context.tenant_id,
                        event_type="guardrail.input.block",
                        content={"reason": input_result.reason, ...},
                    )
                return self._build_blocked_response(input_result)
        if self._tripwire:
            if await self._tripwire.trigger_check(content=messages[-1], trace_context=trace_context):
                await self._emit_tripwire_triggered("input")
                return self._build_tripwire_response()

        # ===== Main loop =====
        while True:
            response = await self._chat_with_retry(...)
            if response.stop_reason == StopReason.TOOL_USE:
                for tc in response.tool_calls:
                    # ===== Per tool call: tool check =====
                    if self._guardrail_engine:
                        tool_result = await self._guardrail_engine.check_tool_call(tc, trace_context=trace_context)
                        if tool_result.action == GuardrailAction.BLOCK:
                            await self._audit_log_append("tool.block", {"tool": tc.tool_name, "reason": tool_result.reason})
                            error_msg = ToolResult(tool_call_id=tc.id, is_error=True, content=f"Tool blocked: {tool_result.reason}")
                            messages.append(...error_msg)
                            continue
                        elif tool_result.action == GuardrailAction.ESCALATE:
                            # HITL stub (defer 53.4 full)
                            ...
                    if self._tripwire and await self._tripwire.trigger_check(content=tc, trace_context=trace_context):
                        await self._emit_tripwire_triggered("tool")
                        return self._build_tripwire_response()
                    # Cat 8 tool execution path (53.2 baseline)
                    state, result = await self._execute_tool_with_error_handling(tc, state, trace_context)
                    ...
                continue
            # END_TURN
            break

        # ===== Loop end: output check =====
        if self._guardrail_engine:
            output_result = await self._guardrail_engine.check_output(response.content, trace_context=trace_context)
            if output_result.action == GuardrailAction.BLOCK:
                await self._audit_log_append("output.block", ...)
                return self._build_blocked_response(output_result)
            if output_result.action == GuardrailAction.SANITIZE:
                response = response.with_content(output_result.sanitized_content)
            if output_result.action == GuardrailAction.REROLL:
                # 1 retry (defer Cat 10 full self-correction)
                response = await self._reroll_once(...)
        if self._tripwire and await self._tripwire.trigger_check(content=response.content, trace_context=trace_context):
            await self._emit_tripwire_triggered("output")
            return self._build_tripwire_response()
        return response
```

**驗證**：
- Cat 1/7/8 既有 tests **不退步**（51.x + 53.1 + 53.2 baseline）
- 整合 test 6 scenarios（per US-7 acceptance）
- Opt-in pattern：所有 Cat 9 deps 傳 None → fallback 至 53.2 行為

**Effort**: 1.25 day（Day 4 大半）

### US-8 — fakeredis + RedisBudgetStore integration test

**設計**：

```toml
# backend/pyproject.toml
[project.optional-dependencies]
dev = [
    # ... existing
    "fakeredis>=2.20",
]
```

```python
# backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py
import pytest
from fakeredis.aioredis import FakeRedis
from agent_harness.error_handling._redis_store import RedisBudgetStore


@pytest.fixture
async def fake_redis():
    return FakeRedis(decode_responses=False)


@pytest.fixture
async def redis_store(fake_redis):
    return RedisBudgetStore(client=fake_redis)


@pytest.mark.asyncio
async def test_increment_atomicity_concurrent(redis_store):
    # 100 concurrent INCR
    await asyncio.gather(*(redis_store.increment("k1", ttl_seconds=60) for _ in range(100)))
    val = await redis_store.get("k1")
    assert val == 100


@pytest.mark.asyncio
async def test_ttl_correct(redis_store, fake_redis):
    await redis_store.increment("k1", ttl_seconds=60)
    ttl = await fake_redis.ttl(b"k1")
    assert 55 < ttl <= 60


@pytest.mark.asyncio
async def test_multi_tenant_isolation(redis_store):
    await redis_store.increment("tenant_a:budget", ttl_seconds=86400)
    await redis_store.increment("tenant_b:budget", ttl_seconds=86400)
    assert await redis_store.get("tenant_a:budget") == 1
    assert await redis_store.get("tenant_b:budget") == 1
```

**驗證**：
- `_redis_store.py` coverage ≥ 80%
- 53.2 既有 budget tests（11 個）不退步
- pytest 跑時不需要真 Redis（fakeredis dev dep）

**Effort**: 0.5 day（Day 0 上半 + 部分 Day 4 carryover bundle）

### US-9 — ToolResult.error_class field

**設計**：

```python
# backend/src/agent_harness/_contracts/tools.py
@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    is_error: bool = False
    content: Any = None
    error_class: str | None = None  # NEW: fully-qualified class name
    metadata: dict = field(default_factory=dict)


# backend/src/agent_harness/tools/executor.py
class ToolExecutor:
    async def execute(self, tc: ToolCall, ...) -> ToolResult:
        try:
            ...
        except Exception as exc:
            return ToolResult(
                tool_call_id=tc.id,
                is_error=True,
                content=str(exc),
                error_class=f"{type(exc).__module__}.{type(exc).__name__}",  # NEW
            )


# backend/src/agent_harness/error_handling/policy.py
class DefaultErrorPolicy(ErrorPolicy):
    def classify(self, error, context, *, trace_context=None) -> ErrorClass:
        # NEW: try error_class lookup first if available via context
        if hasattr(context, "error_class") and context.error_class:
            cls_str = context.error_class
            if cls_str in self._registry_by_str:
                return self._registry_by_str[cls_str]
        # Fallback: existing MRO walk
        for exc_type in type(error).__mro__:
            if exc_type in self._registry:
                return self._registry[exc_type]
        return ErrorClass.UNEXPECTED
```

**驗證**：
- Unit test：register custom Exception class → soft-failure ToolResult → classify 正確命中 category
- 不破壞 ToolResult 序列化（新增欄位 default None）
- 51.x + 53.2 既有 tests 不退步

**Effort**: 0.25 day（Day 1 上半 share）

---

## File Change List

### US-1 (GuardrailEngine)
- ➕ `backend/src/agent_harness/guardrails/engine.py` (new)
- ✏️ `backend/src/agent_harness/_contracts/events.py`（補 `GuardrailTriggered` event）
- ➕ `backend/config/guardrails.yaml` (new)
- ✏️ `backend/src/agent_harness/guardrails/__init__.py`（re-export）
- ➕ `backend/tests/unit/agent_harness/guardrails/test_engine.py` (new)

### US-2 (Input guardrails)
- ➕ `backend/src/agent_harness/guardrails/input/__init__.py` (new)
- ➕ `backend/src/agent_harness/guardrails/input/pii_detector.py` (new)
- ➕ `backend/src/agent_harness/guardrails/input/jailbreak_detector.py` (new)
- ➕ `backend/tests/fixtures/guardrails/pii_redteam.yaml` (new — 30+ cases)
- ➕ `backend/tests/fixtures/guardrails/jailbreak_redteam.yaml` (new — 30+ cases)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_input_pii.py` (new)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_input_jailbreak.py` (new)

### US-3 (Output guardrails)
- ➕ `backend/src/agent_harness/guardrails/output/__init__.py` (new)
- ➕ `backend/src/agent_harness/guardrails/output/toxicity_detector.py` (new)
- ➕ `backend/src/agent_harness/guardrails/output/sensitive_info_detector.py` (new)
- ➕ `backend/tests/fixtures/guardrails/toxicity_cases.yaml` (new — 20+ cases)
- ➕ `backend/tests/fixtures/guardrails/sensitive_leak_cases.yaml` (new — 15+ cases)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_output_toxicity.py` (new)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_output_sensitive_info.py` (new)

### US-4 (CapabilityMatrix + ToolGuardrail)
- ➕ `backend/src/agent_harness/guardrails/tool/__init__.py` (new)
- ➕ `backend/src/agent_harness/guardrails/tool/capability_matrix.py` (new)
- ➕ `backend/src/agent_harness/guardrails/tool/tool_guardrail.py` (new)
- ➕ `backend/config/capability_matrix.yaml` (new)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_capability_matrix.py` (new)
- ➕ `backend/tests/unit/agent_harness/guardrails/test_tool_guardrail.py` (new)

### US-5 (Tripwire)
- ➕ `backend/src/agent_harness/guardrails/tripwire.py` (new)
- ✏️ `backend/src/agent_harness/_contracts/events.py`（補 `TripwireTriggered` event）
- ➕ `backend/tests/unit/agent_harness/guardrails/test_tripwire.py` (new)

### US-6 (WORM audit log)
- ➕ `backend/src/agent_harness/guardrails/audit/__init__.py` (new)
- ➕ `backend/src/agent_harness/guardrails/audit/worm_log.py` (new)
- ➕ `backend/src/agent_harness/guardrails/audit/chain_verifier.py` (new)
- ➕ `backend/src/infrastructure/db/models/audit_log_v2.py` (new ORM model)
- ➕ `backend/alembic/versions/<timestamp>_add_audit_log_v2.py` (new migration)
- ➕ `backend/tests/integration/agent_harness/guardrails/test_worm_log.py` (new)
- ➕ `backend/tests/integration/agent_harness/guardrails/test_chain_verifier.py` (new)

### US-7 (AgentLoop integration)
- ✏️ `backend/src/agent_harness/orchestrator_loop/loop.py`
- 可能 ✏️ `backend/src/agent_harness/orchestrator_loop/_abc.py`（新 deps）
- 可能 ✏️ `backend/src/api/v1/chat/router.py`（DI: guardrail_engine + tripwire + audit_log + capability_matrix）
- ➕ `backend/tests/integration/agent_harness/orchestrator_loop/test_loop_guardrails.py` (new)
- ✏️ `backend/src/agent_harness/guardrails/__init__.py`（final re-export 全 concrete classes）

### US-8 (fakeredis carryover)
- ✏️ `backend/pyproject.toml`（fakeredis>=2.20 dev dep）
- ➕ `backend/tests/integration/agent_harness/error_handling/test_redis_budget_store.py` (new)

### US-9 (ToolResult.error_class carryover)
- ✏️ `backend/src/agent_harness/_contracts/tools.py`（補 `error_class: str | None = None`）
- ✏️ `backend/src/agent_harness/tools/executor.py`（異常路徑寫 error_class）
- ✏️ `backend/src/agent_harness/error_handling/policy.py`（classify 增強）
- ✏️ `backend/tests/unit/agent_harness/tools/test_executor.py`（補 error_class case）
- ✏️ `backend/tests/unit/agent_harness/error_handling/test_policy.py`（補 by-string lookup case）

---

## Acceptance Criteria

### Sprint-level（必過）

- [ ] 9 user stories 全 ✅（US-1 ~ US-9）
- [ ] `cd backend && python -m pytest --tb=no -q` exit 0：
  - **理想**：≥ 760 PASS / 0 xfail / 4 skipped / 0 failed（680 baseline + ≥ 80 new Cat 9 + carryover tests）
  - **可接受**：≥ 740 PASS / ≤ 1 xfail (carryover with new issue) / 4 skipped / 0 failed
- [ ] `cd backend && mypy --strict src` 220+ files clean（Cat 9 新增 ~14 files；不退步）
- [ ] `python scripts/lint/check_llm_sdk_leak.py --root backend/src` LLM SDK leak = 0
- [ ] 6 個 V2 lint scripts 全綠（含 cross-category-import / promptbuilder-usage / ap1 / 其他）
- [ ] 4 個 active CI required checks 在 53.3 PR 全綠（Lint + Type Check / Test (PG16) / V2 Lints / Backend CI）
- [ ] 8 GitHub issues #53-61 全 close
- [ ] Cat 9 coverage ≥ 80%（per code-quality.md target）

### 跨切面紀律

- [ ] **Normal merge**：53.3 PR 走正常 review flow（user approve → 我 merge OR direct merge solo-dev policy）；**不**用 admin override；**不**用 temp-relax bootstrap
- [ ] **No silent xfail**：未解的 test 必須有對應新 GitHub issue + retrospective Audit Debt 記錄
- [ ] **No new Potemkin**：GuardrailEngine / Tripwire / WORMAuditLog / CapabilityMatrix / 各 detector 必須在主流量（AgentLoop）真實使用 — US-7 是反 AP-4 守門
- [ ] **Cat 8 vs Cat 9 邊界守住**（雙向）：
  - grep `Tripwire` 在 `error_handling/` = 0 hits（53.2 已守住）
  - grep `ErrorTerminator` 在 `guardrails/` = 0 hits（本 sprint 守住）

### 主流量整合驗收（per W3 process fix #6）

- [ ] **GuardrailEngine.check_input 真在 AgentLoop 用嗎？** Grep `guardrail_engine\.check_input` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **GuardrailEngine.check_output 真在 AgentLoop 用嗎？** Grep `guardrail_engine\.check_output` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **GuardrailEngine.check_tool_call 真在 AgentLoop 用嗎？** Grep `guardrail_engine\.check_tool_call` 在 `orchestrator_loop/` ≥ 1 處
- [ ] **Tripwire 真在 AgentLoop 用嗎？** Grep `tripwire\.trigger_check` 在 `orchestrator_loop/` ≥ 3 處（input/tool/output）
- [ ] **WORMAuditLog 真在 AgentLoop 用嗎？** Grep `audit_log\.append` 在 `orchestrator_loop/` ≥ 2 處
- [ ] **ToolGuardrail 真在 主流量用嗎？** Grep `ToolGuardrail` register 在 DI 點 ≥ 1 處
- [ ] **3 layer 真整合嗎？** Integration test：input PII / tool unauth / output toxicity 6 個 scenario 全過
- [ ] **Cat 9 coverage 真達標嗎？** `pytest --cov=src/agent_harness/guardrails` ≥ 80%
- [ ] **WORM hash chain 真不可篡改嗎？** Integration test：篡改 entry 50 → verify_chain fail at exact id

---

## Deliverables（見 checklist 詳細）

| Day | 工作 |
|-----|------|
| 0 | Setup: branch + plan + checklist + GitHub issues #53-61 + Cat 9 baseline reproduce + Cat 8 carryover (US-9 ToolResult quick) + fakeredis dep add (US-8 setup) |
| 1 | **US-1 GuardrailEngine + GuardrailTriggered event + US-2 Input guardrails (PII + Jailbreak) 上半 + US-9 ToolResult.error_class** + commit + push 驗 backend-ci 綠 |
| 2 | **US-2 完成 + US-3 Output guardrails (Toxicity + SensitiveInfo)** + multi-tenant test + push 驗 |
| 3 | **US-4 CapabilityMatrix + ToolGuardrail + US-5 Tripwire + US-6 WORM (上半)** + alembic migration + push 驗 |
| 4 | **US-6 完成 + US-7 AgentLoop 3 layer integration + US-8 fakeredis RedisBudgetStore test + retrospective + Sprint Closeout + PR open（normal merge）** |

Day 0 預計 2026-05-04 啟動；Day 1-4 預計 5 days。

---

## Dependencies & Risks

### 依賴

- main HEAD `149de254` (Sprint 53.2.5 closeout merged) ✅
- Branch protection `enforce_admins=true` + `required_approving_review_count=0` 已生效（Sprint 53.2 solo-dev policy 永久）✅
- `gh` CLI authenticated ✅
- 4 active CI required checks 在 PR-level 全綠 baseline（53.2.5 closeout 確認）✅
- Cat 1 (Loop) / Cat 2 (Tools) / Cat 6 (Output Parser) / Cat 7 (State) / Cat 8 (Error) Phase 50-53.2 落地（為 US-7 整合提供既有 dependencies）
- Cat 8 ErrorTerminator 已 production-ready（53.2 落地）— Cat 9 Tripwire 邊界明確（per 17.md §6）
- PostgreSQL 12+ JSONB support（US-6 audit_log_v2 schema）
- fakeredis>=2.20 可用（US-8 dev dep）

### 風險

| Risk | Mitigation |
|------|------------|
| **Cat 9 6 個新 module + AgentLoop 整合 + 2 carryover 1 個 sprint 太緊** | Day-by-day hard checkpoint；US-1 0.5d、US-2 1d、US-3 1d、US-4 0.75d、US-5 0.75d、US-6 1d、US-7 1.25d，US-8/9 共 0.75d，total ~7d；若超 → 砍 US-8 fakeredis（次低優）→ 砍 US-3 SensitiveInfoDetector LLM-as-judge fallback（保留 regex-only）|
| **PII / jailbreak detection accuracy 達不到 95% / 90%** | Day 1 起跑 red-team fixture 30+ case；如 < target → 加 LLM-as-judge fallback（feature flag opt-in）→ 開新 issue defer fine-tune 到 53.4 |
| **WORM hash chain 引入 race condition** | DB UNIQUE constraint on entry_hash + transactional append（SELECT prev FOR UPDATE）；test 含 concurrent append（asyncio.gather × 10）+ verify chain 仍連續 |
| **AgentLoop 3 layer integration 退步 51.x + 53.1 + 53.2 baseline** | Day 4 push 後立即跑既有 integration test suite；如有退步 → rollback + opt-in pattern（同 53.1 / 53.2 reducer pattern）|
| **Cat 8 vs Cat 9 邊界混淆**（ErrorTerminator vs Tripwire 雙向）| 設計階段 grep `Tripwire` 在 `error_handling/` = 0 / `ErrorTerminator` 在 `guardrails/` = 0；CI lint 加守門（可考慮新 lint script `check_cat8_cat9_boundary.py`）|
| **`alembic upgrade head` 在 Linux CI 失敗** | Day 3 push 立即跑 backend-ci.yml；如失敗 → revert migration + 改用 raw SQL DDL in fixture |
| **Output check REROLL 邏輯與 Cat 10 self-correction 衝突** | 本 sprint REROLL 限 max 1 retry；Cat 10 self-correction loop 完整實作 defer 54.1；in retrospective 紀錄為 design 邊界 |
| **Multi-tenant cross-leak detection false positive** | Day 2 / 3 跑 30+ tenant cross-leak fixture；FP > 5% → 改用 strict ID matching（避免 substring match）|
| **Sprint scope 太寬** | 砍 scope hierarchy：US-8 fakeredis carryover → US-3 SensitiveInfo LLM-as-judge → US-2 jailbreak embedding similarity → US-6 advanced chain verification → core US-1/4/5/7 不可砍 |
| **paths-filter blocker on docs-only PR**（per AD-CI-5） | 53.3 PR 含 src + docs 變更；不會觸發 paths-filter blocker；但 retrospective 若有 docs-only follow-up PR 必須 touch backend-ci.yml header（per 53.2.5 workaround）|

---

## Audit Carryover Section（per W3 process fix #1）

本 sprint 處理：
- **AD-Cat8-1 fakeredis + RedisBudgetStore integration test**（53.2 retrospective Q5）→ US-8
- **AD-Cat8-3 ToolResult.error_class field**（53.2 retrospective Q5）→ US-9

**不在 53.3 scope（明確排除）**：
- AD-Cat8-2 RetryPolicyMatrix end-to-end retry-with-backoff loop → 54.x（larger refactor）
- AD-CI-4 sprint plan §Risks template 加 paths-filter risk class → 53.4 with sprint-workflow.md update
- AD-CI-5 required_status_checks 對 docs-only PR 長期 strategy → 53.4 or infrastructure track
- AI-22 dummy red PR enforce_admins chaos test → separate chaos sprint
- AD-Cat7-1 Full sole-mutator refactor → Phase 54.x with verifier integration
- AD-Cat7-3 state_snapshots retention policy → Phase 54.x
- AD-Cat7-4 AgentLoopImpl.resume() full impl → Phase 54.x
- #29 V2 frontend E2E setup → 53.4+ frontend track
- #30 sandbox image CI build → infrastructure track
- #31 V2 backend Dockerfile + Deploy workflow → infrastructure track
- §HITL 中央化完整實作 → Phase 53.4
- 三階段審批 stage 3 explicit confirmation（Teams / UI）→ Phase 53.4
- Cat 10 Verification Self-correction loop 完整 → Phase 54.1

### 後續 audit 預期

W4 audit（Sprint 53.3 完成後）：驗證
- GuardrailEngine 在主流量真用（3 切點 grep evidence）
- Tripwire 在主流量真用（grep `tripwire.trigger_check` 在 `orchestrator_loop/` ≥ 3 處）
- WORMAuditLog 在主流量真用（grep `audit_log.append` 在 `orchestrator_loop/` ≥ 2 處）
- 3 layer guardrails 真實作（input PII detect / tool unauth block / output toxicity sanitize integration test 證據）
- Cat 8 vs Cat 9 邊界守住（雙向 grep evidence）
- Cat 9 coverage ≥ 80% 真達
- WORM hash chain 真不可篡改（tamper test 證據）
- PII / jailbreak detection accuracy red-team 結果

---

## §10 Process 修補落地檢核

per 52.5 §10 + 52.6 §10 + 53.1 §10 + 53.2 §10：

- [x] Plan template 加 Audit Carryover 段落（本 plan §Audit Carryover Section）
- [ ] Retrospective 加 Audit Debt 段落（Day 4 retrospective.md）
- [ ] GitHub issue per US（#53-61 Day 0 建立）
- [ ] **per W3 process fix #6**：Sprint Retrospective「主流量整合驗收」必答題（Day 4）
- [ ] **per 53.2 §AD-Cat8-1**：US-8 (fakeredis) Day 0 setup + Day 4 完成
- [ ] **per 53.2 §AD-Cat8-3**：US-9 (ToolResult.error_class) Day 1 完成（small task）
- [ ] **53.x 無新 closeout bookkeeping branch 待 bundle**（53.2 已 bundle 進 main）
- [ ] **52.5 §AD-2 + 52.6 + 53.1 + 53.2 closeout**：Sprint 53.3 PR 走 normal merge（**zero temp-relax**；branch protection enforce_admins=true + review_count=0 自動強制；solo-dev policy 永久）

---

## Retrospective 必答（per W3-2 + 52.6 + 53.1 + 53.2 教訓）

Sprint 結束時，retrospective 必須回答（**6 必答條**）：

1. **Q1 What went well**：每個 US 真清了嗎？列每 US 對應 commit + verification 結果（含 4 active CI required checks 在 main HEAD 的 run id + status）
2. **Q2 What didn't go well**：跨切面紀律守住了嗎？admin-merge count（本 sprint 應 = 0；temp-relax count = 0；branch protection enforce）/ Cat 9 coverage 數字 / Cat 8 vs Cat 9 邊界 grep evidence（雙向：`Tripwire` 在 `error_handling/` = 0 + `ErrorTerminator` 在 `guardrails/` = 0）
3. **Q3 What we learned**：generalizable lessons — 例如 PII detection accuracy 80% 時 false-positive 模式 / WORM hash chain 在 PG12 vs PG16 差異 / 3 layer guardrail engine 與 Cat 8 retry chain 互動模式
4. **Q4 Audit Debt deferred**：本 sprint 期間發現的新 audit-worthy 問題列出（明確標 ID + target sprint）— 例如 LLM-as-judge fallback 不在本 sprint 落地 / explicit confirmation stage 3 defer 53.4 / output reroll vs Cat 10 self-correction 邊界 / red-team fixture 規模擴大策略
5. **Q5 Next steps**：rolling planning 下；不寫具體未來 sprint 任務，只寫 carryover 候選（例如本 sprint 衍生 AD-Cat9-1 LLM-as-judge fallback / AD-Cat9-2 PII red-team fixture 200+ case 擴充 / AD-Cat9-3 explicit confirmation stage 3 → 53.4）
6. **Q6 主流量整合驗收 + Cat 9 vs Cat 8 邊界守住**（合成題，scope-specific）：
   - GuardrailEngine.check_input 真用？check_output 真用？check_tool_call 真用？grep evidence
   - Tripwire 在主流量 3 切點真用？grep evidence
   - WORMAuditLog 真寫？2 切點 grep evidence
   - 3 layer integration 6 scenario test 全過？
   - Cat 9 vs Cat 8 邊界 grep ＝ 0（雙向）？
   - Cat 9 coverage 真 ≥ 80%？
   - PII detection accuracy ≥ 95%？Jailbreak ≥ 90%？red-team result evidence
   - WORM hash chain tamper test 真 fail at exact id？

---

## Sprint Closeout

- [ ] Day 4 retrospective.md 寫好（含 6 必答 + Audit Debt + scope 變動明示）
- [ ] All 9 GitHub issues #53-61 closed
- [ ] PR 開到 main，title: `feat(guardrails, sprint-53-3): Cat 9 Guardrails 核心 — GuardrailEngine + 3 layer detectors + Tripwire + CapabilityMatrix + WORM audit log + AgentLoop 3 layer integration + Cat 8 carryover (fakeredis + ToolResult.error_class)`
- [ ] PR body 含每 US verification 證據 + workflow run id + Cat 9 coverage 數字 + Cat 8 vs Cat 9 邊界 grep 證據（雙向）+ red-team accuracy 結果 + WORM tamper test 證據
- [ ] **PR 用正常 merge**（NOT admin override，NOT temp-relax bootstrap）— branch protection enforce_admins=true + review_count=0 自動強制；solo-dev policy 永久
- [ ] V2 milestone 更新：15/22 sprints (68%)
- [ ] Memory update：phase 53.3 完成 + Cat 9 Level 4 達成 + AD-Cat8-1 closure status + AD-Cat8-3 closure status

---

**權威排序**：`agent-harness-planning/` 19 docs > 本 plan > V1 文件 / 既有代碼。本 plan 對齊 `01-eleven-categories-spec.md` §範疇 9 + `17-cross-category-interfaces.md` §1.1 / §6 (Tripwire 邊界 vs Cat 8) + `06-phase-roadmap.md` §Sprint 53.3 + Sprint 49.1 stub + Sprint 53.2 retrospective AD-Cat8-1 / AD-Cat8-3。

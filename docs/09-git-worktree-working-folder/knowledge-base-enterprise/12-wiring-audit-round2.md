# 12 - Wiring Audit Round 2（Pipeline Steps / Intent Router / Tool Handlers / Expert Registry / Context）

**執行日期**：2026-04-20
**執行方式**：root-cause-analyst subagent 獨立調查，Grep + Read 實證每個 finding
**Scope**：首輪 audit（Doc 10）未覆蓋嘅 layers
**總 findings**：19 個新 gap，其中 **6 個 🔴 HIGH** 嚴重度

**Scope coverage**：
- ✅ Pipeline Steps 3-8（intent / risk / hitl / llm_route / postprocess）
- ✅ Intent Router 三層一致性（pattern_matcher / semantic_router / llm_classifier）
- ✅ Tool Handler 集體 audit（dispatch_handlers.py 所有 8 個 handler）
- ✅ Expert Registry tool 綁定（domain_tools / tool_validator / bridge）
- ✅ PipelineContext read/write 對稱性 + checkpoint serialization

---

## 零、Executive Summary

### 最關鍵發現：全新「Fake Dispatcher」pattern（比 M-01 更隱蔽）

**首輪 Doc 10 發現的 M-01（search_memory）係「silent stub」—— import 本身 fail**。
**Round 2 發現的 TH-01/02/03 係更深層的「Fake Dispatcher」—— import 成功、class 成功 instantiate、但 business method 從未被 call，只 fabricate 假 response**。

這個 pattern 特別危險：
- Runtime 完全無 error、無 warning
- Connection test 會 pass
- Only production end-to-end test 先會顯露
- **Silent fail 比 crash 更有害** — LLM agent 見到「success」回應繼續推理，錯誤 grounding cascading

### 新發現總覽

| 嚴重度 | 數量 | Pattern |
|-------|------|---------|
| 🔴 HIGH | 6 | Fake dispatcher × 3、Dual engine × 1、Registry binding × 1、Serialization × 1 |
| 🟡 MEDIUM | 7 | Config drift、threshold 漂移、命名誤導、silent fallback |
| 🟢 LOW | 6 | Dead write、enum 硬編碼、docstring 不符 |

### 合計（首輪 + Round 2 + Panel）

| 來源 | Gap 數 | CRITICAL/HIGH |
|------|-------|--------------|
| Doc 10 首輪 | 13（K-01~K-06, M-01~M-02, A-01~A-05） | 6 |
| Doc 11 Panel 新發現 | 4（E-01, HITL-01, C-01, C-02, + CI-01/02, WORM-01, PII-01） | 3+ |
| **Doc 12 Round 2（本文）** | **19（P-01~P-07, IR-01, TH-01~TH-05, ER-01~ER-03, CTX-01~CTX-03）** | **6** |
| **總合** | **~36** | **15** |

---

## 一、Pipeline Steps 3-8 Findings

### P-01 🟡 MEDIUM — AZURE deployment name 三處硬編碼

**證據**：
```
step3_intent.py:265  os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-5.4-mini")
step3_intent.py:336  （同上，router 主路徑）
step6_llm_route.py:206  （同上，重複）
```
**問題**：三處各自 `os.getenv`，違反 single-source-of-truth；若未來切換 model 需同時改三處
**修復**：抽至 `core/config.py Settings.azure_deployment_name`
**估時**：0.5 天

### P-02 🟢 LOW — COMPLETENESS_THRESHOLD magic number

**證據**：`step3_intent.py:148` `COMPLETENESS_THRESHOLD = 0.50` 寫死在函數內
**問題**：非由 `RouterConfig` 傳入，與 `intent_router.router` 的 completeness 設定無連結
**修復**：改由 config 傳入
**估時**：0.3 天

### P-03 🟡 MEDIUM — SemanticRouter threshold 漂移

**證據**：
```
step3_intent.py:363            threshold=0.50  # "low inner threshold"
semantic_router/router.py:99   default threshold=0.85  # constructor default
```
**問題**：依賴註釋而非代碼保證 RouterConfig 真做二次 filter；若 RouterConfig 未套用，實際就是 0.50 silent downgrade（召回太多 irrelevant 結果）
**修復**：驗證 RouterConfig filter 實際觸發 + 加 integration test
**估時**：0.5 天

### P-04 🟢 LOW — Step 4 custom_factors 是 dead metadata

**證據**：
```
step4_risk.py:173-175  custom_factors["memory_available"] = ...
step4_risk.py:174      custom_factors["knowledge_available"] = ...
# Grep risk_assessor/ 內無 reader
```
**問題**：write-only field（延續首輪 C-01 pattern）
**修復**：刪除或補 downstream reader
**估時**：0.2 天

### P-05 🟡 MEDIUM — Step 4/5 intent whitelist 硬編碼

**證據**：
```
step4_risk.py          non_actionable = {"query", "unknown", "request"}
step5_hitl.py:92       actionable_intents = {"change", "incident"}
```
**問題**：兩處字面量各自定義；若 `ITIntentCategory` enum 擴展，silent drift
**修復**：集中派生自 `ITIntentCategory`
**估時**：0.3 天

### P-06 🟢 LOW — Step 6 "team" route silent fallback

**證據**：
```
step6_llm_route.py:26        # team route 被註釋排除
step6_llm_route.py:191-195   VALID_ROUTES = {"direct_answer", "subagent"}
# 但 prompt 仍提 team
```
**問題**：LLM 回 "team" 時 `_extract_route` 會 fall to DEFAULT_ROUTE 但無 log
**修復**：加 explicit log 或重寫 prompt
**估時**：0.2 天

### P-07 🟢 LOW — Step 8 consolidation ImportError 被 swallow

**證據**：`step8_postprocess.py:198-199` `except ImportError: pass`
**問題**：無 log，若 `memory/consolidation.py` rename 會 silent disable consolidation 永久
**修復**：加 logger.warning + OTel metric
**估時**：0.1 天

---

## 二、Intent Router 三層一致性 Findings

### IR-01 🟡 MEDIUM — LLMClassifier 三個不同 default confidence

**證據**：
```
llm_classifier/classifier.py:110   confidence=0.0  # exception path
llm_classifier/classifier.py:189   confidence=0.0  # exception path
llm_classifier/classifier.py:256   "confidence": 0.5  # 錯誤路徑
```
**問題**：caller 無法用 confidence threshold 區分 success/error
**修復**：統一錯誤路徑為單一 sentinel value（建議 -1 or 0.0）+ 加 `error: str` 欄位
**估時**：0.3 天

---

## 三、Tool Handler 集體 Findings — 🚨 Fake Dispatcher Pattern

### TH-01 🔴 HIGH — handle_dispatch_workflow 永未 execute

**證據**：`dispatch_handlers.py:171-176`
```python
# WorkflowExecutorAdapter() 被 instantiate 但從未被 call
# 註釋 line 168 "Here we prepare the dispatch and record result"
# 實際只 return {"message": f"Workflow '{type}' queued for execution"}
```
**問題**：agent call `dispatch_workflow` tool 完全無實際 workflow execution，只返回文字假象
**修復**：實際 call `adapter.execute(...)` 或明確 raise NotImplementedError
**估時**：1 天

### TH-02 🔴 HIGH — handle_dispatch_swarm 只 notify 冇 dispatch

**證據**：`dispatch_handlers.py:249-254`
```python
# 只 call SwarmIntegration.on_coordination_started 嘅 lifecycle event
# 但實際 worker 冇被 dispatch
```
**問題**：Swarm agent 永遠冇真正 execute
**修復**：實際 call `swarm_manager.dispatch(...)`
**估時**：1 天

### TH-03 🔴 HIGH — handle_dispatch_to_claude 完全冇 call Coordinator

**證據**：`dispatch_handlers.py:300-310`
```python
# ClaudeCoordinator() instantiate 後冇 call .coordinate_agents()
# 註釋 line 302 "For now, record the dispatch acknowledgment" 明示未實作
# 只 fabricate {"content": f"Task acknowledged: ..."}
```
**問題**：Claude dispatch 完全係假
**修復**：實際 call `coordinator.coordinate_agents(...)`
**估時**：1 天

### TH-04 🔴 HIGH — Dual Risk Engine

**證據**：
```
dispatch_handlers.py:337-353  用 hybrid.risk.engine.RiskAssessmentEngine
step4_risk.py                 用 orchestration.risk_assessor.RiskAssessor
```
**問題**：Pipeline Step 4（passive）同 Agent tool call `assess_risk`（active）用**兩個不同 risk engine**，policy 集不同步；agent 得到嘅 risk 評估與 Pipeline pre-assessed 不一致，可能導致：
- 同一 operation 在 pipeline 評 LOW，在 agent tool 評 HIGH
- HITL 判斷依據混亂
**修復**：統一使用 `orchestration.risk_assessor.RiskAssessor`（與 Pipeline 一致），或反之
**估時**：1.5 天

### TH-05 🟢 LOW — create_task / update_task_status pattern inconsistency

**證據**：`dispatch_handlers.py:58-106` 冇 `try/except ImportError` guard
**問題**：其他 handler 均有 ImportError handling，呢兩個無；若 `TaskService` 內部 module 缺失會整個 raise 打斷 agent flow
**修復**：補齊 ImportError pattern
**估時**：0.2 天

---

## 四、Expert Registry 綁定 Findings

### ER-01 🔴 HIGH — DOMAIN_TOOLS 漏 dispatch tools

**證據**：
```
domain_tools.py:21-50  只列 assess_risk / search_knowledge / search_memory / create_task
dispatch_handlers.py:458-467  register_all 註冊 8 個 tool（含 dispatch_workflow/swarm/claude）
```
**問題**：YAML expert 用 `@domain` 或 `["*"]` 都拎唔到 dispatch tools。Registry 與 handler 註冊分家
**修復**：
1. 將 dispatch tools 加入 DOMAIN_TOOLS
2. 或將 DOMAIN_TOOLS 從 handler `register_all` 自動 derive
**估時**：0.5 天

### ER-02 🟡 MEDIUM — update_task_status 有 handler 無 domain exposure

**證據**：
- `dispatch_handlers.py:460` 有 handler + registration
- `domain_tools.py` 任何 domain 都無列此 tool
**問題**：Dead binding — handler 寫了但 agent 永遠拎唔到
**修復**：補 domain mapping 或移除 handler
**估時**：0.2 天

### ER-03 🟡 MEDIUM — ALL_KNOWN_TOOLS 誤導性命名

**證據**：
```
tool_validator.py:36-37  "*" 和 "@domain" 被 skip 驗證
domain_tools.py:53       ALL_KNOWN_TOOLS = DOMAIN_TOOLS values + TEAM_TOOLS
```
**問題**：名字 `ALL_KNOWN_TOOLS` 但實際不包 dispatch_*；YAML expert 寫 `tools: ["*"]` 拎唔到全部 handler，與命名暗示矛盾
**修復**：
1. Rename 為 `ALL_DOMAIN_TOOLS` 或 `ALL_EXPERT_ACCESSIBLE_TOOLS`
2. 或補 dispatch tools 進 ALL_KNOWN_TOOLS
**估時**：0.3 天

---

## 五、PipelineContext 完整性 Findings

### CTX-01 🔴 HIGH — to_checkpoint_state 漏 5 個欄位（擴展 C-02）

**證據**：`context.py:118-174`
```python
# 以下 fields 喺 context.py 定義，但 to_checkpoint_state 內冇 include：
- dispatch_result         (line 81) — resume 後 lost
- hitl_approval_id        (line 74) — approval 關係斷
- dialog_questions        (line 67)
- dialog_id               (line 68) — 對話 resume 斷
- fast_path_applied       (line 84) — metrics/observability 影響
- metadata                (line 96) — Step 6 llm_route_response / intent_validated / intent_override 全部遺失
```
**問題**：HITL resume、dialog continue、metrics 全部壞
**修復**：補齊 serialization；加 property-based round-trip test
**估時**：0.8 天

### CTX-02 🟡 MEDIUM — from_checkpoint_state 無 restore total_start_time

**證據**：`context.py:227-230` 只 restore `completed_steps`
**問題**：Resume 後 `elapsed_ms` property 由新 start_time 計，latency metrics 失效
**修復**：Serialize + restore `total_start_time` + 檢視所有 metric fields
**估時**：0.2 天

### CTX-03 🟢 LOW — to_sse_summary 漏 risk_level / intent_category

**證據**：`context.py:234-244`
**問題**：Frontend SSE 拎唔到 risk/intent，需另外從 event payload 補，容易漂移
**修復**：加入 SSE summary 欄位
**估時**：0.2 天

---

## 六、新發現 Gap 清單（Sorted）

| ID | 類別 | 描述 | 嚴重度 | 估時 |
|----|------|------|-------|------|
| **TH-01** | Fake dispatcher | `handle_dispatch_workflow` 永未 execute | 🔴 HIGH | 1 天 |
| **TH-02** | Fake dispatcher | `handle_dispatch_swarm` 只 notify 冇 dispatch | 🔴 HIGH | 1 天 |
| **TH-03** | Fake dispatcher | `handle_dispatch_to_claude` 完全冇 call Coordinator | 🔴 HIGH | 1 天 |
| **TH-04** | Dual engine | Agent tool vs Pipeline Step 4 用兩個 risk engine | 🔴 HIGH | 1.5 天 |
| **ER-01** | Registry binding | DOMAIN_TOOLS 漏 dispatch tools | 🔴 HIGH | 0.5 天 |
| **CTX-01** | Serialization | to_checkpoint_state 漏 5 欄位 | 🔴 HIGH | 0.8 天 |
| P-01 | Config drift | AZURE deployment name 三處硬編碼 | 🟡 MEDIUM | 0.5 天 |
| P-03 | Config drift | SemanticRouter threshold 0.50 vs 0.85 | 🟡 MEDIUM | 0.5 天 |
| P-05 | Enum drift | Step 4/5 intent whitelist 硬編碼 | 🟡 MEDIUM | 0.3 天 |
| IR-01 | Contract | LLMClassifier error path confidence 不一致 | 🟡 MEDIUM | 0.3 天 |
| ER-02 | Dead binding | update_task_status 有 handler 無 domain | 🟡 MEDIUM | 0.2 天 |
| ER-03 | Naming | ALL_KNOWN_TOOLS 誤導性命名 | 🟡 MEDIUM | 0.3 天 |
| CTX-02 | Serialization | from_checkpoint_state 無 restore total_start_time | 🟡 MEDIUM | 0.2 天 |
| P-02 | Config | COMPLETENESS_THRESHOLD magic number | 🟢 LOW | 0.3 天 |
| P-04 | Dead write | Step 4 custom_factors.* 從未被讀 | 🟢 LOW | 0.2 天 |
| P-06 | Silent fallback | Step 6 "team" route silent fallback | 🟢 LOW | 0.2 天 |
| P-07 | Silent swallow | Step 8 consolidation ImportError pass | 🟢 LOW | 0.1 天 |
| TH-05 | Pattern | create_task / update_task_status 冇 ImportError guard | 🟢 LOW | 0.2 天 |
| CTX-03 | SSE gap | to_sse_summary 漏 risk_level / intent_category | 🟢 LOW | 0.2 天 |

**HIGH 合計**：5.8 天（6 個 gap）
**MEDIUM 合計**：2.6 天（7 個）
**LOW 合計**：1.2 天（6 個）
**總修復時間**：~9.6 天

---

## 七、Pattern 分析

### 7.1 延續首輪 pattern：「PoC→Production 未統一 SSOT」

| 首輪 | Round 2 對應 | 模式 |
|------|-------------|------|
| K-01 雙倉 | P-01 deployment name 三處 | Config 無 single source |
| K-02 embedding 雙 model | E-01 三處 model 漂移 | 同上 |
| C-01 context 孤立 field | P-04 custom_factors 孤立 | Write-only state |
| C-02 checkpoint 漏欄位 | CTX-01 擴展至 5 欄位 | Serialization gap |
| A-02 orphan logger | TH-04 dual risk engine | Duplicated implementation |

### 7.2 新 pattern：「Fake Dispatcher」🚨

**定義**：Handler 成功 import module、成功 instantiate class、但 **business method 故意不 call**，只 fabricate 「success」response。

**已發現案例**：
- TH-01 WorkflowExecutorAdapter 無 execute
- TH-02 SwarmIntegration 只 notify lifecycle
- TH-03 ClaudeCoordinator 無 coordinate_agents

**危險性**：
1. Import / instantiation 成功 → IDE 靜態檢查 pass
2. Return 正確 shape envelope → downstream code pass
3. **LLM agent 見到 "Task acknowledged" 信以為真** → 繼續推理但基於假 grounding
4. Only production E2E test 會暴露

**建議 CI 防線**：
```python
# pytest hook:
# For each handle_dispatch_*, verify it calls 
# at least one async method on its adapter/coordinator
# Use AST analysis of dispatch_handlers.py
```

### 7.3 新 pattern：「Serialization Asymmetry」

**定義**：`to_checkpoint_state()` / `from_checkpoint_state()` 未做 round-trip 驗證，fields 定義後加入 context 但冇同步更新 serialization。

**修復策略**：
```python
# property-based test
@given(context=arbitrary_pipeline_context())
def test_checkpoint_round_trip(context):
    restored = PipelineContext.from_checkpoint_state(context.to_checkpoint_state())
    assert context == restored  # 除 paused_at / hitl_pre_approved 等預期改變 field
```

---

## 八、Methodology Reflection — 建議第三輪 audit

本輪仍未覆蓋以下層，建議 **第三輪 audit**：

| Scope | 重點 | 預估 tool calls |
|-------|------|----------------|
| Pipeline Service resume E2E | `pipeline/service.py` 嘅 resume 機制 + `ResumeService` + `from_checkpoint_state` 真實 E2E | 8-10 |
| OpenTelemetry metrics wiring | `metrics.py` 893 LOC collector vs 實際發射點；Grep `OrchestrationMetricsCollector` callers，check 每 step 是否有埋點 | 4-6 |
| Pipeline Service step orchestration | `pipeline/service.py` 本身：8 steps 嘅 sequencing、exception handling、pause/resume、SSE 事件發射 | 5-7 |
| DB migration vs ORM drift | `infrastructure/database/models.py` + `alembic/versions/` — 無覆蓋 | 10-15 |
| Frontend SSE consumer | 對 `to_sse_summary()` 欄位依賴、AG-UI protocol event schema | 10-15 |

**預估第三輪**：15-20 tool calls，2-3 小時完成

---

## 九、修復建議優先序（整合首輪 + Panel + Round 2）

### P0 — CRITICAL（必做，修復前有 legal / decision quality 風險）

| ID | 來源 | 描述 | 估時 |
|----|------|------|-----|
| K-01 + K-02 + K-03 + E-01 | Doc 10 + Panel | Knowledge wiring + embedding 統一 | 2-3 天 |
| M-01 | Doc 10 | search_memory 修復 | 1 天 |
| HITL-01 | Panel | request_approval 修復 | 1 天 |
| **TH-01 + TH-02 + TH-03** | **Round 2 新** | **三個 Fake Dispatcher 修復** | **3 天** |
| **TH-04** | **Round 2 新** | **Dual risk engine 統一** | **1.5 天** |
| A-01 | Doc 10 + Panel | Main chat audit emission | 3-4 天 |

**P0 總計：~12 天**（原 4-6 天 + Round 2 新增 4.5 天）

### P1 — HIGH（結構性問題）

| ID | 來源 | 描述 | 估時 |
|----|------|------|-----|
| ER-01 | Round 2 | DOMAIN_TOOLS 補 dispatch tools | 0.5 天 |
| CTX-01 | Round 2 | Checkpoint serialization 補欄位 | 0.8 天 |
| A-02 + A-03 | Doc 10 | Orphan AuditLogger cleanup | 1 天 |
| C-01 + C-02 | Panel | Context state 補全 | 1 天 |
| K-06 | Doc 10 | Cohere Rerank 3 實測 | 1 週 |
| P-01 + P-03 + P-05 | Round 2 | Config centralization | 1 天 |
| CI-01 + CI-02 | Panel | Import + config CI lint | 1-2 天 |
| **新 CI-03** | **Round 2** | **Fake dispatcher detection（AST check）** | **1 天** |
| **新 CI-04** | **Round 2** | **Checkpoint round-trip property test** | **0.5 天** |

**P1 總計：~2 週**

### P2 — Doc 08 原計劃 + 剩餘 LOW/MEDIUM

略（Bitemporal + WORM + PII + L3 Ontology + Agent Skills YAML 等，~6-8 週）

---

## 十、Panel Review 影響更新

本輪新發現 **6 個 🔴 HIGH gap** 令原 P0 修復從 **4-6 天** 擴展到 **~12 天**。建議：

1. **Sprint Wiring Fix 001**（M-01 + HITL-01）：1-2 天，**即啟無依賴**（Doc 14 已備）
2. **Sprint Wiring Fix 002**（K-01 + E-01 + TH-01/02/03 + TH-04）：5-6 天，**部分依賴 Workshop Q10/Q12**；但 TH-* 部分無依賴可先做
3. **Sprint Wiring Fix 003**（A-01 + ER-01 + CTX-01）：4-5 天，**依賴 Workshop Q5/Q7**

**修正後 P0 總工期**：~2 週（若 sequential）/ ~1 週（若 parallel 3 人團隊）

---

## 十一、版本記錄

| Version | Date | Author |
|---------|------|--------|
| 1.0 | 2026-04-20 | root-cause-analyst subagent + Claude 整合 |

**Related docs**：
- Doc 10 — Wiring Audit Round 1
- Doc 11 — Agent Team Review（panel 同時發現 E-01 / HITL-01）
- Doc 13 — Workshop Agenda
- Doc 14 — Sprint Wiring Fix 001 Plan + Checklist

**Raw subagent transcript**：
`C:\Users\Chris\AppData\Local\Temp\claude\...\tasks\ab434fc4033fd6ef4.output`（session 臨時檔，本 Doc 已完整摘錄）

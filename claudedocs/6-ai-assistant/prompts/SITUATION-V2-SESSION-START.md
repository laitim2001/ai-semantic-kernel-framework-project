# SITUATION V2 — Session Start Prompt（V2 重構期間每個新 session 必用）

> **用法**：在每個新 session 開始時，整份 copy 到對話框，**更新最後一節「今天的任務」一行即可**。其他段落是給 AI 助手的常駐脈絡，不必每次改。
>
> **適用範圍**：Phase 49+（V2 重構期間，預計 22 sprint / 5.5 個月）。完成 V2 後（Phase 56+）再決定是否退役此 prompt。

---

## 第一部分：你正在加入什麼專案

你好。本專案是 **IPA Platform V2**（Intelligent Process Automation Platform），目前正處於 **V2 重構期間**（Phase 49+，2026-04 啟動）。

### V2 為何存在（Why this rebirth）

V1（Phase 1-48）2025-11 至 2026-04 累積了 5 個月的開發，但 2026-04 V9 audit 發現：
- 真實對齊度只有 **27%**（11 範疇中 8 個 Level 0-2 — 不可用 / 半成品）
- Guardrails 散在 6 處、Orchestrator 散在 5 處（cross-directory scattering）
- Pipeline 偽裝成 Loop / 無 PromptBuilder / 無 Verification / Context Rot 完全忽略
- Hybrid 橋接層債務 + Potemkin Features（結構在但無內容）

→ 決策**重新出發**（不修補、不全砍）：保留 V9 分析 / CC 30-wave 研究 / V1 教訓作設計知識，從 Day 1 按 **agent harness 11+1 範疇**重新組織代碼。

### V2 不是什麼（避免常見誤解）

- ❌ **不是「Claude SDK 應用」** — V2 是 LLM Provider 中性的企業 agent 平台
- ❌ **不是「CC 移植」** — 參考 CC 架構但完全 server-side 重新設計
- ❌ **不是「本地工具升級版」** — V2 是企業 server-side，工具是企業 API/服務
- ❌ **不是「修補 V1」** — V1 已封存到 `archived/v1-phase1-48/`（READ-ONLY），不擴充
- ❌ **不是 SaaS-ready**（Phase 55 完成 ≠ SaaS-ready；SaaS Stage 1 在 Phase 56-58）

---

## 第二部分：3 大最高指導原則（不可違反）

詳見 `docs/03-implementation/agent-harness-planning/10-server-side-philosophy.md`。

### 原則 1：Server-Side First
- 部署在企業伺服器；用戶在遠端 browser；多租戶 + zero-trust
- 工具是**企業 API**（D365 / SAP / KB / SharePoint）— 不是本地檔案 read/write
- HITL 是核心，不是邊角

### 原則 2：LLM Provider Neutrality ⭐⭐⭐
- ❌ `agent_harness/**` 任何檔案禁止 `import openai` / `import anthropic` / `import agent_framework`
- ✅ 全走 `adapters/_base/ChatClient` ABC + 中性 ToolSpec / Message / StopReason
- CI 強制 lint 檢查；違反 = PR 直接 revert

### 原則 3：CC 參考但 Server-Side 轉化
- 概念複製、實作重寫
- CC `Bash tool` → 沙盒化 enterprise 命令；CC `Read/Write user files` → 企業 API；CC git checkpoint → DB state_snapshots
- 不照搬 CC 本地實作（multi-tenant 場景會出安全 / 性能問題）

---

## 第三部分：V2 11+1 範疇（架構骨架）

V2 嚴格按以下範疇組織代碼，**禁止跨範疇雜湊**：

| # | 範疇 | Phase 實作 |
|---|------|----------|
| 1 | Orchestrator Loop（TAO/ReAct）| 50.1 |
| 2 | Tool Layer | 51.1 |
| 3 | Memory（5 scope × 3 time scale）| 51.2 |
| 4 | Context Mgmt（Compaction + Prompt Caching）| 52.1 |
| 5 | Prompt Construction | 52.2 |
| 6 | Output Parsing | 50.1 |
| 7 | State Mgmt（Reducer + transient/durable）| 53.1 |
| 8 | Error Handling | 53.2 |
| 9 | Guardrails & Safety（含 Tripwire）| 53.3 + 53.4 |
| 10 | Verification Loops | 54.1 |
| 11 | Subagent Orchestration（4 模式，**無 worktree**）| 54.2 |
| **12** | **Observability / Tracing**（cross-cutting）| 49.4 起滲透所有 |

外加 `§HITL Centralization`（`agent_harness/hitl/`）— 跨範疇 2/7/8/9 的 HITL 統一管理。

完整 spec：`agent-harness-planning/01-eleven-categories-spec.md`。

---

## 第四部分：權威排序（衝突時上位者勝）

```
docs/03-implementation/agent-harness-planning/ (19 份 V2 規劃) > 根目錄 CLAUDE.md > .claude/rules/ > V1 文件
```

**任何衝突以上位者為準**。例如：V2 規劃說 `platform_layer/`，過期 V1 文件說 `platform/` → 用 V2 規劃。

---

## 第五部分：必讀文件（每次新 session 至少讀這 5 份）

依序讀完才能對齊上下文：

1. **本 prompt**（你正在讀）— 高層 onboarding
2. **`CLAUDE.md`**（專案根目錄，2026-04-28 V2 重寫版）— 高層導航 + V2 11+1 範疇 + 5 大核心約束 + Sprint Workflow
3. **`docs/03-implementation/agent-harness-planning/README.md`** — V2 規劃 19 份文件導覽
4. **`docs/03-implementation/agent-harness-planning/10-server-side-philosophy.md`** — 3 大最高指導原則完整論述
5. **`docs/03-implementation/agent-harness-planning/17-cross-category-interfaces.md`** — Single-source 介面權威表（24 dataclass + 19 ABC + 22 LoopEvent + 9 跨範疇工具）

按需要再讀：
- `04-anti-patterns.md`（V1 教訓 11 條反模式 — PR 必通檢查清單）
- `06-phase-roadmap.md`（22 sprint 路線圖）
- `.claude/rules/README.md`（13 份 V2 開發規則索引）

---

## 第六部分：Rolling Sprint Planning 規則（V2 紀律核心）⭐

> **這是 V2 最重要的工作節奏紀律，每次 session 都要記住**

V2 採用「**滾動式 sprint 規劃**」（per `.claude/rules/sprint-workflow.md`）：

### ✅ 正確做法

- **執行當前 sprint 期間（或結束時）**才寫**下一個** sprint 的 plan + checklist
- 每個 sprint 結束 retrospective 後，根據實作學習**微調**下一 sprint 設計
- Phase README + 06-phase-roadmap.md 提供高層綱要，**不是**完整 plan
- 完成 sprint plan + checklist 才開始 code（**禁止跳步**：Phase README → Plan → Checklist → Code → Update → Progress doc → Retrospective）
- 🆕 **起草新 plan/checklist 必先讀「最近一個 completed sprint」樣板**：章節編號 / 命名 / Day 數 / 細節水平必須一致；scope 差異透過**內容**調整（更多 stories / file / tests），**不透過結構**調整（多加章節 / 改 Day 數）。違反 = 用戶矯正成本（前車：52.1 plan/checklist v1 → v3 三輪重寫才對齊 51.2 格式）

### ❌ 禁止做法

- **不**預寫全 22 個 sprint plan + checklist（過早決定 = 將來必返工）
- **不**「為了完整」而把 49.2 / 49.3 / 49.4 plan 一次寫齊（違反 rolling）
- **不**跳過 plan 直接 code（Phase 35-38 + 42 違規前車之鑑）
- **不**刪除未勾選的 checklist 項（只能 `[ ]→[x]`，延後項加 🚧 + reason）

### 為什麼是 rolling，不是預寫

1. 實作 sprint N 會學到東西，會影響 sprint N+1 的設計
2. 一次預寫 5 個 sprint plan，第 1 個跑完通常要改後 4 個
3. ROI 偏低 + 維護成本高
4. 標準業界做法

→ **每個新 session 開始時，AI 助手必須先確認 rolling planning 紀律仍在執行，沒有突然出現 5 個未來 sprint plan 文件。**

---

## 第七部分：當前進度（AI 自查，不需用戶手動更新）

新 session 開始時，AI 助手請用以下指令自查當前進度：

```bash
# 1. 看現在在哪個 branch
git branch --show-current

# 2. 看 main 最近的 commits（過去 sprint 痕跡）
git log main --oneline -20

# 3. 看當前 branch 的 commits（如果在 feature branch）
git log $(git branch --show-current) --oneline --not main

# 4. 看 working tree 是否乾淨
git status --short

# 5. 看 V2 sprint 規劃文件覆蓋（已寫了哪些 sprint）
ls docs/03-implementation/agent-harness-planning/phase-*

# 6. 看執行紀錄（已執行 / 收尾的 sprint）
ls docs/03-implementation/agent-harness-execution/

# 7. 讀最近收尾的 sprint retrospective（學該 sprint 的 open items + lessons）
# 路徑類似 docs/03-implementation/agent-harness-execution/phase-XX/sprint-XX-Y/retrospective.md
```

**讀完上述後**，AI 助手應該能回答：
- 目前在哪個 sprint？哪一天？
- 上一個收尾的 sprint 是哪個？有什麼 open items？
- 累計完成多少 sprint？離 Phase 55（V2 完成）還有多遠？

---

## 第八部分：常駐 Open Items / Follow-ups（每個 sprint 結束時更新）

> **這段需要每個 sprint 結束時用戶或 AI 添加。** 收尾時，把 retrospective.md 的「待改進」「Action items」精煉成下方一句話列表。

### 已知未解（at session start time = 2026-05-04 Sprint 55.3 closeout — Audit Cycle Mini-Sprint #1 complete; 6 ADs closed)

#### Cat 8 carryover（53.2 retrospective Q5 — partially closed by 55.4）
- ✅ **AD-Cat8-1** closed by 55.4 Day 1 (verification stamp; D4 confirmed already 100% coverage by 53.3 Day 4 — 9 fakeredis tests + 16/16 stmts coverage)
- ⏸ **AD-Cat8-2** deferred 55.5 by 55.4 D6 + Selection D (loop.py:194/245 dead state confirmed; full retry-with-backoff design needs dedicated sprint, not audit cycle scope)
- ✅ **AD-Cat8-3** closed by 55.4 Day 1 narrow Option C (loop.py _handle_tool_error error_class_str param + classify_by_string default in ABC; soft-failure FQ class name preservation via 53.3 US-9 mechanism)

#### Cat 9 carryover（53.3 retrospective + 53.7 + 54.1 + 55.4 closures）
- ✅ **AD-Cat9-5** closed by 55.4 Day 2 (Stage 2.3 session counter wired in tool_guardrail.py; in-memory dict[(session, tool), int]; 4 unit tests; TODO grep 0)
- ✅ **AD-Cat9-6** closed by 55.4 Day 3 (5 real-DB integration tests; Migration 0005 triggers verified; chain_verifier 100-row sanity passed; SAVEPOINT pattern for post-error verification)
- ⏸ **AD-Cat9-5-Redis** (NEW from 55.4): multi-instance Redis-backed session counter for ToolGuardrail (current is in-memory single-instance) — production hardening, not audit cycle scope → 55.6+
- ⏸ **AD-Cat9-1-WireDetectors**（54.1）：auto-wrap 4 Cat 9 detectors with LLMJudgeFallbackGuardrail (operator-driven; not a sprint)
- ✅ **AD-Cat9-1+2+3** closed by 54.1 / **AD-Cat9-4** closed by 53.5 / **AD-Cat9-7+8+9** closed by 53.7

#### Cat 10 carryover（54.1 retrospective + 54.2 partial closure）
- ✅ **AD-Cat10-Obs-1** closed by 54.2（verification/_obs.py + tracer injection in RulesBasedVerifier + LLMJudgeVerifier; Cat 9 wrappers reuse inner judge tracer per D19）
- ⏸ **AD-Cat10-Wire-1**：chat router default-wire run_with_verification → Phase 55 frontend / 業務 sprint
- ⏸ **AD-Cat10-VisualVerifier**：Playwright screenshot verifier → Phase 55+
- ⏸ **AD-Cat10-Frontend-Panel**：verification_panel UI → Phase 55 frontend
- ⏸ **AD-Cat10-Obs-Cat9Wrappers**（new from 54.2）：Cat 9 fallback/mutator wrappers separate observability span (currently reuse inner judge per D19); revisit if double-instrumentation actually needed → Phase 55+ audit cycle

#### Cat 11 carryover（54.2 deferred features）
- ⏸ **AD-Cat11-Multiturn**（new from 54.2）：TeammateExecutor multi-turn loop pulling from mailbox each iteration; SubagentHandle for long-lived child query → Phase 55
- ⏸ **AD-Cat11-SSEEvents**（new from 54.2）：SubagentSpawned/Completed event emission from tool handlers; SSE 2 isinstance branches (Day 0 D3 deferred per D18) → Phase 55 frontend
- ⏸ **AD-Cat11-ParentCtx**（new from 54.2）：ForkExecutor parent context inheritance via Cat 7 checkpoint load (D12 deferred) → Phase 55

#### Cat 7 carryover（53.1 retrospective — closed by 55.3）
- ✅ **AD-Cat7-1** closed by 55.3 (sole-mutator grep-zero confirmed across full backend/src/ + 7th V2 lint check_sole_mutator.py + 6 tests)

#### Hitl carryover（53.4 retrospective + 53.7 + 55.3 closures）
- ✅ **AD-Hitl-7** closed by 55.3 (per-tenant HITLPolicy DB: hitl_policies table + DBHITLPolicyStore + 3-tier fallback get_policy + 9 tests)
- ✅ **AD-Hitl-1..6** closed by 53.5; **AD-Hitl-4-followup** closed by 53.6; **AD-Hitl-8** closed by 53.7

#### Frontend carryover（53.5 retrospective — all closed by 53.6）
- ✅ **AD-Front-1+2** + **AD-Hitl-4-followup** closed by 53.6

#### Process / Lint carryover（53.6 retrospective — all closed by 53.7）
- ✅ **AD-Sprint-Plan-1** + **AD-Lint-1** + **AD-Test-1** closed by 53.7

#### CI infrastructure carryover（53.2.5 retrospective + 53.7 partial closure）
- ✅ **AD-CI-4** closed by 53.7 (Common Risk Classes section in sprint-workflow.md)
- ⏸ **AD-CI-5**：`required_status_checks` 對 docs-only PR 仍 BLOCKED 因 paths filter；當前 workaround = touch workflow header (53.7 used playwright-e2e.yml); 長期需 revisit strategy → infra track
- ⏸ **AD-CI-6**：Deploy to Production chronic fail since 53.2 → infra track（non-required check; not blocking）

#### 跨 sprint carryover
- ✅ **AI-22** closed by 53.7 (chaos test PASSED — admin merge blocked at GraphQL API)
- ⏸ **#31**：V2 Dockerfile + 新 build workflow → infrastructure track（無 sprint binding）

#### Sprint 53.7 新加（closed by 55.3）
- ✅ **AD-Plan-1** closed by 55.3 (sprint-workflow.md §Step 2.5 Day-0 Plan-vs-Repo Verify added; first self-application caught D1-D3 + D4-D8 = 8 drift findings, saving ~4 hr re-work)
- ✅ **AD-Lint-2** closed by 55.3 (per-day "Estimated X hours" headers dropped from checklist template; progress.md is single home for per-day estimates)

#### Sprint 54.2 新加（partial closure by 55.3）
- ✅ **AD-Cat12-Helpers-1** closed by 55.3 (extracted category_span to agent_harness/observability/helpers.py; verification_span + business_service_span delegate; Option A thin wrapper preserves 7 callers' API)
- ✅ **AD-Lint-3** closed by 55.3 (file-header-convention.md §格式 enforces 1-line max + char budget ≤ E501; new 禁止項 5 with examples; ironic self-violation caught + fixed in helpers.py)
- ⏸ **AD-Sprint-Plan-2** — **superseded by AD-Sprint-Plan-4** (this retro): single global multiplier strategy fails because scope class differs (55.3 ratio 2.81 way over band when 0.40 applied to medium-backend scope vs 55.2 ratio 1.10 in band for closure scope)

#### Sprint 55.2 carryover（superseded）
- ⏸ **AD-Phase56-Calibration** — **superseded by AD-Sprint-Plan-4** (this retro): scope-class multiplier matrix replaces single-multiplier baseline tracking
- ⏸ **AD-Cat12-BusinessObs**：thread real tracer through chat router → BusinessServiceFactory → 5 services when `get_tracer` factory implemented → Phase 56+

#### Sprint 55.4 新加（待後續處理)
- ⏸ **AD-Sprint-Plan-5** (NEW): medium-backend class multiplier 0.65 first application produced ratio **1.36** (over [0.85, 1.20] band by 0.16). 7-sprint window now 2/7 in-band; medium-backend variance high (0.65→0.69 under at 0.55 mult; 1.36 over at 0.65 mult). Recommendations for next medium-backend sprint plan §Workload: (a) lift 0.65→0.75 as 1st refinement; (b) add audit-cycle-overhead surcharge +0.05 when sprint includes AD-Plan-* / Selection A-D rescope dynamics; (c) treat Day 0 (~1.5-2 hr) as fixed offset, exclude from bottom-up est. → Apply at next medium-backend sprint plan
- ⏸ **AD-Plan-3** (NEW): Extend AD-Plan-2 Day-0 path-verify to also grep plan-asserted code patterns within existing files (catches D5-class drifts where file exists but content differs from plan §Spec). Evidence: Sprint 55.4 D5 — plan said terminator.py synthesizes Exception(str); actual synthesize was at loop.py:1072 not terminator.py. AD-Plan-2 verified file existence but not content. Action: Day 0 探勘 grep for keywords from plan §Technical Spec like "synthesize" / "raise" / "Exception(" within asserted file paths. → Sprint 55.5+ plan template
- ⏸ **AD-Test-DB-Trigger** (NEW process AD): Document SAVEPOINT (`begin_nested()`) pattern for tests that exercise PostgreSQL EXCEPTION-raising triggers + need post-fail verification. Evidence: Sprint 55.4 Day 3 D9 — DELETE attempt fires trigger → transaction aborted → post-fail SELECT failed with InFailedSQLTransactionError; fixed by wrapping DELETE in `async with session.begin_nested():`. Action: add "PostgreSQL trigger testing pattern" subsection to `.claude/rules/testing.md`. → testing.md update

#### Sprint 55.3 新加（部分已 superseded by 55.4）
- ⏸ **AD-Sprint-Plan-4** (NEW)：Adopt scope-class multiplier matrix to replace single global multiplier. Calibration evidence: 6-sprint window has 2/6 in-band (53.7 1.01, 55.2 1.10) and oscillates between under-est (54.x / 55.1 ~0.65-0.70) and over-est (55.3 ~2.81). Action: Phase 56+ first sprint plan §Workload header states scope class + multiplier from matrix:
  ```
  Audit cycle / docs / template:    0.40 (55.2 evidence)
  Mixed (process + 1-2 backend):    0.55-0.65 (53.7 evidence)
  Medium-backend production:        0.65-0.75 (55.3 actual ~10.5 hr ÷ 11.25 bottom-up = 0.93 → start 0.65)
  Large multi-domain:               0.50-0.55 (55.1 evidence)
  ```
  After 3-4 sprints under matrix, re-evaluate per-class. → Phase 56+ first sprint plan
- ⏸ **AD-Plan-2** (NEW)：Extend `sprint-workflow.md` §Step 2.5 to require explicit Day-0 path verification for every plan §File Change List entry (Glob-check exists for edits / not-exist for creates). Evidence: 55.3 D4 + D7 + D8 = 3 path-drift findings caught mid-implementation (V2 lint scripts at project root vs plan said backend/scripts/, alembic versions vs plan said backend/alembic/, test paths under platform_layer/ vs plan said tests/.../governance/). Action: 5-min Day-0 task per sprint to prevent path-drift class. → Sprint 55.4+ plan template

#### 永久 dropped（不必處理）
- ✅ **4 dropped CI Pipeline checks**（Code Quality / Tests / Frontend Tests / CI Summary）：53.2.5 archive ci.yml 後永久 drop（V1 monolithic CI duplicates，非降級；branch protection 已正確配置 4 active checks）

> **AI 助手任務**：每個新 sprint 開始時，先看本 prompt 此節 + 上 sprint 的 retrospective.md 「Action items」，向用戶確認哪些 follow-up 要在這個 sprint 處理，哪些繼續延後。

---

## 第九部分：常駐 milestones（V2 累計完成）

> **每個 sprint 結束更新一行**

| Sprint | 完成日期 | Merge SHA / PR | 主要成果 |
|--------|---------|----------------|---------|
| **49.1** | 2026-04-29 | feature branch (13 commits) | V1 archive + V2 5-layer skeleton + 11+1 ABC stubs + _contracts + ChatClient ABC + frontend skeleton + Docker + CI + ESLint |
| **49.2** | 2026-04 | merged | DB Schema + Async ORM |
| **49.3** | 2026-04 | merged | RLS + Audit + Adapter (Azure OpenAI) |
| **49.4** | 2026-04 | merged | Worker queue PoC + OTel + Lint rules |
| **50.1** | 2026-04-30 | merged | Cat 1 (Loop core) + Cat 6 (Output Parsing) + AP-1 lint |
| **50.2** | 2026-04-30 | merged | POST /chat SSE 8-event + chat-v2 frontend + worker factory |
| **51.0** | 2026-04-30 | merged | mock business tools |
| **51.1** | 2026-04-30 | merged | Cat 2 Tool Layer L3 |
| **51.2** | 2026-04-30 | merged | Cat 3 Memory L3（5 scope × 3 time scale）|
| **52.1** | 2026-05-01 | merged `5c18869a` | Cat 4 Context Mgmt（compaction + lost-in-middle）|
| **52.2** | 2026-05-01 | merged `30628c05` | Cat 5 Prompt Construction + AP-8 lint |
| **52.5** | 2026-05-02 | PR #19 merged `d4ba89ef` | Audit carryover bundle (8 P0 + 4 P1 in 1 day) |
| **52.6** | 2026-05-02 | PR #28 merged `404b8147` | CI restoration: 8 active CI workflows green + branch protection enforced |
| **53.1** | 2026-05-02 | PR #39 merged `aaa3dd75` | Cat 7 State Mgmt（DefaultReducer + DBCheckpointer + opt-in shadow-checkpoint）|
| **53.2** | 2026-05-03 | PR #48 merged `a77878ad` | Cat 8 Error Handling（ErrorPolicy + RetryPolicyMatrix + CircuitBreaker + ErrorBudget + ErrorTerminator + AgentLoop integration）+ Solo-dev policy structural change |
| **53.2.5** | 2026-05-03 | PR #50/#51 merged `132c39bc` | CI carryover: archived redundant ci.yml (V1 monolithic); closes AD-CI-2 + AD-CI-3; 4 dropped checks permanent |
| **53.3** | 2026-05-03 | PR #62 merged `ca57ae86` | Cat 9 Guardrails 核心（GuardrailEngine + 4 detectors + Tripwire + WORM audit + 3-layer AgentLoop integration）|
| **53.4** | 2026-05-03 | PR #72 merged `872021ee` | §HITL Centralization backend (RiskPolicy + HITLManager production + Cat 2 hitl_tools refactor + AuditQuery + Cat 7 reducers + HITLNotifier+Teams)|
| **53.5** | 2026-05-04 | PR #73 merged `86fd42db` | Governance frontend (approvals page + ApprovalCard + Cat 9 Stage 3 → AgentLoop wiring + audit endpoints) — closes AD-Cat9-4 + AD-Hitl-1..6 |
| **53.6** | 2026-05-04 | PR #74 merged `f4a1425f` | Frontend e2e Playwright + production HITL wiring + ServiceFactory consolidation — closes AD-Front-1/2 + AD-Hitl-4-followup; V2 17→18/22 |
| **53.7** | 2026-05-04 | PR #76 merged `eb7929cf` | Audit cleanup bundle — 9 carryover AD closed (AD-Sprint-Plan-1 + AD-CI-4 + AD-Lint-1 + AD-Test-1 + AD-Hitl-8 + AI-22 + AD-Cat9-7/8/9) + 2 BONUS V2 lint bug fixes; calibration multiplier 0.55 validated; V2 18/22 unchanged |
| **54.1** | 2026-05-04 | PR #78 merged `c0c2860a` | Cat 10 Verification Loops Level 4 (RulesBasedVerifier + LLMJudgeVerifier + 4 templates + run_with_verification self-correction wrapper + LLMVerifyMutateGuardrail + verify tool) — closes AD-Cat9-1+2+3 via D8 wrapper pattern; 47 tests added; calibration ratio 0.69 (2nd application); 24 drifts; **V2 18/22 → 19/22 (86%)** ↑ |
| **54.2** | 2026-05-04 | PR #80 merged `c7b686ae` | Cat 11 Subagent Orchestration Level 4 (BudgetEnforcer + DefaultSubagentDispatcher + Fork + AsTool + Teammate + Mailbox + Handoff + task_spawn/handoff tools per 17.md §3.1 + AD-Cat10-Obs-1 verifier observability) — closes AD-Cat10-Obs-1; 46 tests; calibration ratio 0.65 (3rd application; 3-sprint mean 0.78 → recommend lower to 0.50 for Phase 55); 22 drifts D1-D22; Worktree NOT implemented per V2 spec §範疇 11 (AP-6 clean); AgentLoop UNTOUCHED per D18 (tools auto-route via tool_executor); 7 new AD; **V2 19/22 → 20/22 (91%)** ↑ |
| **55.1** | 2026-05-04 | PR #82 merged `798176d5` | Business domain production service layer (Option A) — Incident DB schema + ORM + Alembic 0012 + RLS policy; IncidentService production CRUD + multi-tenant + audit chain; 4 read-only services (Patrol/Correlation/RootCause/Audit); BUSINESS_DOMAIN_MODE flag + BusinessServiceFactory (D8 separate from governance); register_incident_tools mode swap (incident only — D9 + AD-BusinessDomainPartialSwap-1 for 4 deferred domains); Cat 12 obs span on 9 service methods; **44 tests** (= plan target hit exactly: 1351 → 1395); 11 drifts D1-D11; calibration ratio **0.68** (1st application of 0.50; 4-sprint mean 0.76 → AD-Sprint-Plan-3 = 0.50→0.40 for 55.2); **V2 20/22 → 21/22 (95%)** ↑ |
| **55.2** | 2026-05-04 | PR #85 merged `9a8296ae` | **V2 22/22 (100%) CLOSURE** — AD-BusinessDomainPartialSwap-1 closed at 3 layers (per-domain register_*_tools + _register_all aggregator + chat router DI); 5 USs: 4 deferred domains tools.py mode swap (13 handlers = 4 real + 9 sentinel per D1) / _register_all uniform mode threading / chat handler BusinessServiceFactory wiring (D2 tracer=None + D9 get_db_session) / 21 tests cumulative / ceremony retro; pytest 1395 → **1416** (+21 cumulative; +6 over plan ≥+15); calibration multiplier 0.40 1st application: ratio **1.10** ✅ FIRST in [0.85, 1.20] band (5-sprint mean 0.826; AD-Phase56-Calibration logged); 10 drifts D1-D10; **V2 21/22 → 22/22 (100%)** ↑ **V2 重構完成** |
| **55.3** | 2026-05-04 | PR #87 merged `4d17a5cd` | **Audit Cycle Mini-Sprint #1 (Groups A + G)** — 6 ADs closed: AD-Plan-1 (sprint-workflow.md §Step 2.5 Day-0 Plan-vs-Repo Verify) + AD-Lint-2 (drop per-day "Estimated X hours" from checklist template) + AD-Lint-3 (MHist 1-line format + 禁止項 5) + AD-Cat12-Helpers-1 (extract category_span to observability/helpers.py; thin wrapper Option A) + AD-Cat7-1 (sole-mutator grep-zero confirmed full backend/src/ + 7th V2 lint check_sole_mutator.py) + AD-Hitl-7 (per-tenant HITLPolicy DB: hitl_policies table + DBHITLPolicyStore + 3-tier fallback get_policy + Alembic 0013 + RLS); pytest 1416 → **1434** (+18, 50% over plan ≥+12); 7 V2 lints 7/7 green (added check_sole_mutator); calibration multiplier 0.40 2nd application: ratio **~2.81** ⚠️ way OVER band → 6-sprint mean 1.16 with high variance (range 0.65-2.81) → AD-Sprint-Plan-4 logged proposing scope-class matrix (audit/mixed/medium-backend/large multi-domain); 8 drifts D1-D8; AD-Plan-1 first self-application caught D1-D3 before Day 1 code → ROI validated; **V2 22/22 unchanged (audit cycle bundle, not main progress)** |
| **55.4** | 2026-05-05 | PR #89 merged `b0fd7582` | **Audit Cycle Mini-Sprint #2 (Groups B + C)** — **4/5 ADs closed** (AD-Cat8-2 deferred to 55.5 per D6 Selection D — loop.py:194/245 retry_policy 100% dead state; full retry-with-backoff design needs dedicated sprint, not audit cycle scope): AD-Cat8-1 (verification stamp; D4 confirmed 100% coverage by 53.3 Day 4) + AD-Cat8-3 narrow Option C (loop.py _handle_tool_error error_class_str param + classify_by_string default in ABC; soft-failure FQ class name preservation via 53.3 US-9 mechanism; no schema change) + AD-Cat9-5 (Stage 2.3 ToolGuardrail max-calls-per-session counter; in-memory dict; 4 unit tests; TODO grep 0) + AD-Cat9-6 (5 real-DB integration tests; Migration 0005 triggers verified; chain_verifier 100-row sanity; SAVEPOINT pattern for post-error verify per D9); pytest 1434 → **1446** (+12, 1 over revised target ≥+11 with AD-Cat8-2 deferred); 7 V2 lints 7/7 green; calibration multiplier 0.65 medium-backend 1st application: ratio **1.36** ⚠️ OVER band by 0.16 → AD-Sprint-Plan-5 logged proposing 0.65→0.75 lift + audit-cycle-overhead surcharge + Day 0 fixed offset; 10 drifts D1-D10 catalogued; AD-Plan-2 first self-application 0 path drift (vs 55.3's 3 path drifts) → ROI validated;但 AD-Plan-2 不抓 wrong-content drifts (D5) → AD-Plan-3 logged for content-keyword grep extension; **V2 22/22 unchanged (audit cycle bundle, not main progress)** |

**累計**：**22 / 22 sprint** 完成（**100%**）— Phase 49: 4/4 ✅，Phase 50: 2/2 ✅，Phase 51: 3/3 ✅，Phase 52: 4/4 ✅，Phase 53: 6/4 (53.1-53.6) ✅，Phase 54: 2/2 ✅，Phase 55: 2/2 ✅，+ 4 carryover bundles (53.2.5 + 53.7 + 55.3 + 55.4)

> **53.2.5 + 53.7 + 55.3 + 55.4 是 carryover bundles 不算入主 22 sprint 進度**。**Phase 55.2 已完成 — V2 重構達成 100% 完成**。**Sprint 55.4 (audit cycle mini-sprint #2) 完成 — 4/5 ADs closed (AD-Cat8-1 stamp + AD-Cat8-3 narrow + AD-Cat9-5 + AD-Cat9-6;AD-Cat8-2 deferred to 55.5)**;Sprint 55.5 候選 scope = Group D (Cat 10 backend audit) + AD-Cat8-2 promoted carryover + AD-Plan-3 first application;Sprint 55.6 後續 audit cycle。下一階段 = Phase 56+ SaaS Stage 1（Multi-tenant infrastructure + Billing + SLA + DR；候選 scope 等用戶 approve；Sprint 56.1 plan 起草前必先 user approve scope，per rolling planning 紀律）。Calibration:scope-class matrix 1st medium-backend application 0.65 ratio 1.36 over band → AD-Sprint-Plan-5 提案 lift 0.65→0.75 + audit-cycle-overhead surcharge + Day 0 fixed offset;7-sprint window 2/7 in-band; 持續監測。

---

## 第十部分：行為規範（給 AI 助手）

每次回應前，AI 助手請確保：

### 必做

- [ ] 對齐 3 大最高指導原則（server-side / LLM neutrality / CC reference）
- [ ] 不引入新 LLM SDK 直接 import 進 `agent_harness/**`
- [ ] 不刪除未勾選的 checklist 項（只能 `[ ]→[x]` 或加 🚧）
- [ ] 跨範疇型別從 `agent_harness._contracts/` import（不重複定義）
- [ ] 開始 code 前確認該 sprint 已有 plan + checklist
- [ ] 🆕 **起草新 sprint plan/checklist 前先讀最近 completed sprint 的 plan/checklist 作格式樣板**（非空白白板起草；章節 / Day 數 / 細節水平必須一致；最近樣板 = `phase-53-2-error-handling/sprint-53-2-{plan,checklist}.md` 或 carryover 版 `sprint-53-2-5-{plan,checklist}.md`）
- [ ] 寫 commit message 用 Conventional Commits 格式（per `.claude/rules/git-workflow.md`）+ co-author
- [ ] 每個 commit 對應一個 checklist 項目
- [ ] 維持每天 progress.md 紀錄（estimates vs actual）
- [ ] 🆕 **sprint 結束寫 retrospective.md 用 6 必答格式**（53.2 + 53.2.5 樣板）：
  - Q1 What went well
  - Q2 What didn't go well
  - Q3 What we learned（generalizable lessons）
  - Q4 Audit Debt deferred（明確標 ID + target sprint）
  - Q5 Next steps（rolling planning 下；不寫具體未來 sprint 任務，只寫 carryover 候選）
  - Q6 Solo-dev policy validation（or 其他 sprint-specific 主題）

### 🆕 V2 紀律 9 項自檢（每 PR 前 + 每 commit 後）

per `compact 格式 §3` + `.claude/rules/anti-patterns-checklist.md`：

1. Server-Side First（tenant_id 強制 / no local file IO 假設）
2. LLM Provider Neutrality（agent_harness 零 SDK import）
3. CC Reference 不照搬（CC 概念 → V2 server-side 重寫）
4. 17.md Single-source（dataclass / ABC / 工具不重複定義）
5. 11+1 範疇歸屬（每檔案明確歸 1 範疇）
6. 04 anti-patterns（11 條全綠）
7. Sprint workflow（plan → checklist → code → progress → retro）
8. File header convention
9. Multi-tenant rule

### 🆕 Solo-Dev 政策（2026-05-03 Sprint 53.2 永久結構性變更）

- `required_approving_review_count = 0`（不是 1）
- ✅ PR 仍要開（audit trail + CI gate）
- ✅ enforce_admins=true 仍 active（admin 不能直接 push main）
- ✅ 4 active required CI checks 必須全綠
- ❌ **不需** review approval（GitHub 阻擋 author self-approve；solo dev 無第二 reviewer）
- ❌ **不用** temp-relax bootstrap（PATCH review_count: 1→0 暫降）—— 已永久 0
- 當 2nd collaborator 加入時 1-line PATCH 還原為 1（指令見 `13-deployment-and-devops.md` §gh api command）

### 🆕 Paths Filter Workaround（docs-only PR）

當 PR 只動 `docs/` 或 `.gitignore`（不動 `backend/**` 或 `.github/workflows/**`），required checks `Lint + Type Check + Test (PG16)` + `v2-lints` 不會 fire → mergeStateStatus=BLOCKED。

**Workaround**: 加一個 commit 觸碰 `.github/workflows/backend-ci.yml`（例如 header comment 註記改動原因），就會觸發 backend-ci + V2 Lint。
- 文件化於 `.github/workflows/backend-ci.yml` header comment（從 53.2.5 起）
- 長期 fix 為 AD-CI-5（暫 deferred）

### 不做

- [ ] 不預寫多個未來 sprint plan（rolling planning！）
- [ ] 不刪除 V1 archive 內任何檔案（archived/v1-phase1-48/ 是 read-only baseline）
- [ ] 不讓 AI 助手單方面決定不可逆操作（git tag push / git mv 大量檔案）— 必須先報告
- [ ] 不執行 `--no-verify` / `--force` git 命令（除非用戶明確授權）
- [ ] 不啟動長期運行 server process（CLAUDE.md 規範：節點 process 與 claude code 衝突）
- [ ] 🆕 不寫 `--admin` merge bypass（enforce_admins=true 會擋；solo-dev policy 已用 `review_count=0` 解決） 

---

## 第十一部分：今天的任務（**唯一需要用戶填寫的部分**）

> 在每個新 session 開始時，把整份 prompt copy 後，只改下方這一節即可。

```
今天的任務：__________________

例：
- 「啟動 Sprint 49.2 — DB Schema + Async ORM」
  → AI 將先寫 `phase-49-foundation/sprint-49-2-plan.md` + `sprint-49-2-checklist.md`，等用戶 approve 才開始 code
- 「繼續 Sprint 49.2 Day 3」
  → AI 接續執行 Day 3 任務（先讀 progress.md 確認 Day 1-2 完成情況）
- 「修復 Sprint 49.1 follow-up：rename platform/ in V2 規劃文件」
  → AI 處理 Open Items 中的 `platform/` rename 同步
- 「Review Sprint 49.1 retrospective + 規劃 Sprint 49.2 plan」
  → AI 讀 retrospective.md 後與用戶討論 49.2 範圍 + 寫 plan
- 「建立第 8 個 SITUATION prompt」
  → AI 按用戶需求建立 / 修改 prompt 模板
```

---

## 附錄：本 prompt 自身的維護

### 何時更新

| 觸發 | 更新位置 |
|------|---------|
| Sprint 結束 | 第八部分 Open Items（合併 retrospective Action items）+ 第九部分 milestones（加一行）|
| 發現 V2 規劃修訂（17.md / 02 / 04 / 10 等）| 第三部分（11+1 範疇）+ 第四部分（權威排序）+ 第五部分（必讀清單）|
| Phase 切換（如 Phase 49 → 50）| 第七部分（自查指令）+ 第九部分（milestones）|

### 何時退役

V2 完成（Phase 55 後）→ 此 prompt 變歷史紀念物，改用 V3 / SaaS Stage 1 對應 prompt（如有）。

---

**Last Updated**: 2026-05-05（Sprint 55.4 closeout — **Audit Cycle Mini-Sprint #2 完成,4/5 ADs closed**:AD-Cat8-1 stamp + AD-Cat8-3 narrow Option C + AD-Cat9-5 + AD-Cat9-6;AD-Cat8-2 deferred to 55.5 per D6 + Selection D;pytest 1446(+12);7 V2 lints 7/7 green;calibration 0.65 medium-backend 1st app ratio **1.36** over band → AD-Sprint-Plan-5 提案 lift to 0.75 + surcharge + Day 0 offset;10 drifts D1-D10;AD-Plan-2 first self-application 0 path drifts → ROI validated;3 new ADs logged (AD-Sprint-Plan-5 / AD-Plan-3 / AD-Test-DB-Trigger);V2 22/22 unchanged(audit cycle bundle);Sprint 55.5 候選 scope = Group D + AD-Cat8-2 promoted,user approval pending）
**Maintainer**: 用戶 + AI 助手共同維護
**File location**: `claudedocs/6-ai-assistant/prompts/SITUATION-V2-SESSION-START.md`

---

## Update history

| Date | Sprint | Updates |
|------|------|------|
| 2026-04-29 | 49.1 | 初版（V2 重構期間 onboarding prompt） |
| 2026-04-30 | 52.1 | 新增 §6 「format consistency rule」（52.1 v1→v3 incident 教訓） |
| 2026-05-03 | 53.2.5 | §8 全更新（Cat 8 + CI carryover + AI-22 + #31）；§9 milestones 補 49.1 → 53.2.5 共 16 個 sprint 行；§10 加 6 必答 retrospective 格式 + V2 紀律 9 項自檢 + Solo-dev policy + Paths filter workaround |
| 2026-05-04 | 54.1 | §8 closes AD-Cat9-1+2+3 + adds AD-Cat10-Obs-1 / AD-Cat10-Wire-1 / AD-Cat9-1-WireDetectors / AD-Test-Module-Naming as 54.1 carryover; §9 milestones row +Sprint 54.1 (V2 18/22 → 19/22 = 86%); session start time updated to 54.1 closeout |
| 2026-05-04 | 54.2 | §8 closes AD-Cat10-Obs-1 + adds AD-Cat10-Obs-Cat9Wrappers / AD-Cat11-Multiturn / AD-Cat11-SSEEvents / AD-Cat11-ParentCtx / AD-Sprint-Plan-2 / AD-Cat12-Helpers-1 / AD-Lint-3 as 54.2 carryover; §9 milestones row +Sprint 54.2 (V2 19/22 → 20/22 = 91%); Phase 54 完成 2/2; session start time updated to 54.2 closeout |
| 2026-05-04 | 55.1 | §9 milestones row +Sprint 55.1 (V2 20/22 → 21/22 = 95%); Phase 55 progresses 1/2; new AD logged: AD-Sprint-Plan-3 (multiplier 0.50→0.40 for 55.2; 4-sprint mean 0.76 BELOW band) + AD-BusinessDomainPartialSwap-1 (full register_*_tools mode swap for 4 deferred domains); session start time updated to 55.1 closeout |
| 2026-05-04 | **55.2** | **🎉 V2 22/22 (100%) CLOSURE**; §9 milestones row +Sprint 55.2; AD-BusinessDomainPartialSwap-1 closed at 3 layers (per-domain + aggregator + chat router); AD-Sprint-Plan-3 conditionally closed (0.40 first hit ratio 1.10 in band; 5-sprint mean 0.826); 2 new AD for Phase 56+ (AD-Phase56-Calibration + AD-Cat12-BusinessObs); session start time updated to 55.2 closeout |
| 2026-05-04 | **55.3** | §8 closes 6 ADs (AD-Plan-1 + AD-Lint-2 + AD-Lint-3 + AD-Cat12-Helpers-1 + AD-Cat7-1 + AD-Hitl-7) + supersedes AD-Sprint-Plan-2 + AD-Phase56-Calibration via new AD-Sprint-Plan-4 (scope-class multiplier matrix); §9 milestones row +Sprint 55.3 (V2 22/22 unchanged — audit cycle bundle); 2 new AD logged: AD-Sprint-Plan-4 (matrix) + AD-Plan-2 (Day-0 path verify); pytest +18 (1416 → 1434); 7th V2 lint check_sole_mutator added; calibration ratio 2.81 way over band evidence drives matrix proposal |
| 2026-05-05 | **55.4** | §8 closes 4 ADs (AD-Cat8-1 + AD-Cat8-3 narrow + AD-Cat9-5 + AD-Cat9-6); AD-Cat8-2 deferred to 55.5 per D6 + Selection D; §9 milestones row +Sprint 55.4 (V2 22/22 unchanged — audit cycle bundle); 3 new AD logged: AD-Sprint-Plan-5 (medium-backend mult 0.65→0.75) + AD-Plan-3 (Day-0 content grep) + AD-Test-DB-Trigger (SAVEPOINT pattern); pytest +12 (1434 → 1446); calibration ratio 1.36 over band → mult lift recommendation; 10 drifts D1-D10; AD-Plan-2 first self-application 0 path drifts (ROI validated) but D5 reveals AD-Plan-2 doesn't catch wrong-content drifts |

# 檔案 Header 與修改紀錄規範

**Purpose**: 統一所有新建檔案的 metadata header，強制記錄修改歷史（newest-first），確保上手快速與修改可溯。

**Category**: Development Process / Standards
**Created**: 2026-04-28
**Last Modified**: 2026-04-28
**Status**: Active

**Modification History**:
- 2026-05-05: Sprint 55.6 — add MHist char-count budget guidance (closes AD-Lint-MHist-Verbosity)
- 2026-05-04: Sprint 55.3 — enforce MHist 1-line max + char budget guidance + 禁止項 5 (closes AD-Lint-3)
- 2026-04-28: Initial creation from CLAUDE.md §File Header & Modification Convention

---

## 為什麼需要此規範

| 痛點 | 解法 |
|------|------|
| AI 助手接手不知檔案目的 → 重複探查浪費 token | File header 一秒鎖定範疇與用途 |
| Phase 35-38 散落跨範疇難追溯 | Category 標籤強制歸屬 |
| V1「Potemkin Feature」結構在但無內容 | Description + Key Components 強制說明真實用途 |
| git blame 解決不了「為何這樣設計」 | Section header 的 Why + Alternative considered |
| 修改累積無歷史 → 三個月後沒人知道為什麼 | Modification History 記錄行為變更 |

---

## 新檔 Header 範本

### Python（`.py`）

```python
"""
File: src/agent_harness/orchestrator_loop/loop.py
Purpose: TAO/ReAct main loop orchestrator; executes multi-turn agent reasoning until stop_reason=end_turn.
Category: 範疇 1 (Orchestrator Loop)
Scope: Phase 50.1 / Sprint 50.1
Owner: range owner of Category 1; see 17-cross-category-interfaces.md §2.1

Description:
    Implements the core ReAct loop: perceive → reason → act → observe. Each turn:
    1. Compact context if needed (Category 4 integration)
    2. Build prompt with memory layers (Category 5)
    3. Call LLM via ChatClient ABC (Category 6 output parsing)
    4. Execute tools in sandbox (Category 2 integration)
    5. Checkpoint state (Category 7)
    Terminates on stop_reason=END_TURN or max_turns/token budget exceeded.

Key Components:
    - LoopState: Transient + durable state (see _contracts/state.py)
    - AgentLoop: Main class; async generator of LoopEvent
    - LoopEvent: SSE event stream (see _contracts/events.py)
    - TAO: Think → Act → Observe pattern (see 01-eleven-categories-spec.md §1)

Created: 2026-04-28 (Sprint 49.1 planning)
Last Modified: 2026-05-15

Modification History (newest-first):
    - 2026-05-15: Add streaming support with AsyncIterator[LoopEvent] (Sprint 50.2) — alignment with Contract 4
    - 2026-05-03: Refactor LoopState into transient/durable split (Sprint 50.1) — state persistence requirement
    - 2026-04-28: Initial creation (Sprint 49.1) — TAO loop stub

Related:
    - 01-eleven-categories-spec.md §範疇1 — Orchestrator Loop spec
    - 10-server-side-philosophy.md §原則1 — Server-Side First constraints
    - 17-cross-category-interfaces.md §2.1 / §4.1 — Contract definitions (ChatClient, LoopEvent)
    - 02-architecture-design.md §約束2 — Category dependency rules
"""
```

### TypeScript / React（`.ts` / `.tsx`）

```typescript
/**
 * File: src/features/agent_loop/LoopVisualizer.tsx
 * Purpose: Real-time visualization of TAO loop state machine; renders agent thinking, tool calls, verifications.
 * Category: Frontend (對應 16-frontend-design.md 第 3 頁「Loop Visualization」)
 * Scope: Phase 51.1 / Sprint 51.1
 * Owner: Frontend team; see 16-frontend-design.md
 *
 * Description:
 *   Renders a real-time tree view of:
 *   - Current loop turn number + elapsed time
 *   - LLM thinking blocks + tool_calls parsed from SSE stream
 *   - Tool execution status (pending / done / error)
 *   - Verification state (passed / failed / correction N/M)
 *   - State compaction hints + token budget warnings
 *
 *   Consumes LoopEvent stream from backend SSE endpoint.
 *   Updates state via Zustand chat_store.
 *
 * Key Components:
 *   - <LoopVisualizer>: Main container
 *   - <TurnCard>: Per-turn UI
 *   - <ToolCallTree>: Tool call visualization
 *   - useLoopEvents: Hook to consume SSE stream
 *
 * Created: 2026-05-10 (Sprint 51.1)
 * Last Modified: 2026-05-15
 *
 * Modification History:
 *   - 2026-05-15: Add verification state display (Sprint 51.1)
 *   - 2026-05-10: Initial creation (Sprint 51.1)
 *
 * Related:
 *   - 16-frontend-design.md §Page 3 — Loop visualization requirements
 *   - 02-architecture-design.md §SSE 事件規範 — LoopEvent format
 */
```

### Markdown 設計文件（`.md`）

```markdown
# Project Name / Document Title

**Purpose**: One-line description of what this document covers.
**Category / Scope**: Category / Phase XX.Y / Sprint ZZ.W
**Created**: YYYY-MM-DD
**Last Modified**: YYYY-MM-DD
**Status**: Draft / Active / Deprecated
**Author**: (optional)

> **Modification History**
> - 2026-05-15: Added Section X detail (Sprint XX.Y)
> - 2026-04-28: Initial creation

---

## Content starts here...
```

---

## Section Header 規範（檔案內重要區塊）

每個重要 class / 大型 function / 邏輯區塊在開頭加**短註解**說明 **WHY**（不是 WHAT）：

### Python 範例

```python
# === LoopExecutor: TAO/ReAct main loop ===
# Why: V1 採線性 Pipeline 導致 agent 無法多輪迭代（範疇 1 對齐度 18%）。
# V2 改 while-true TAO loop 直到 stop_reason=end_turn 或觸發 budget limit。
# Alternative considered:
#   - LangGraph state machine — 排除因為引入額外層而不解決核心 loop 邏輯
#   - Recursion — 排除因為難以管理深層遞迴狀態
# Reference: agent-harness-planning/01-eleven-categories-spec.md §範疇1
class LoopExecutor:
    """Main TAO loop implementation."""

    async def run(self, state: LoopState) -> LoopResult:
        """Execute TAO loop until termination condition met."""
        ...

# === TokenCounter: Abstract token counting interface ===
# Why: V1 hardcoded OpenAI's tiktoken；無法支援 Anthropic / Google 不同的 tokenizer。
# V2 抽象為 ABC，每個 adapter 提供自己的計數邏輯（見 10-server-side-philosophy.md §原則2）。
# Related: adapters/_base/chat_client.py / 17-cross-category-interfaces.md §2.1 Contract 8
class TokenCounter(ABC):
    @abstractmethod
    def count(self, messages: list[Message], tools: list[ToolSpec]) -> int: ...
```

### TypeScript 範例

```typescript
// === useChatStore: Central chat state management ===
// Why: Multiple components (MessageList, ToolCallCard, VerificationStatus) need to subscribe
// to same chat session state without prop-drilling. Zustand provides reactive updates + SSE integration.
// Alternative considered:
//   - Redux — overkill for single-session state
//   - React Context — causes unnecessary re-renders without Zustand's selective subscription
// Related: services/chat_service.ts
const useChatStore = create<ChatStore>((set) => ({
  sessionId: null,
  messages: [],
  // ...
}));
```

---

## Modification History 詳細規範

### 位置

新檔時，Modification History 放在 file header 區塊內；修改現有檔時，在原位置更新（newest-first）。

### 格式

**1-line max per entry** (Sprint 55.3+ — closes AD-Lint-3):

```
Modification History (newest-first):
    - YYYY-MM-DD: <verb> <what> (Sprint XX.Y) — <one-line reason ≤ E501 budget>
    - YYYY-MM-DD: <verb> <what> (Sprint XX.Y) — <reason>
    - ...
```

**Character budget**:
- Each entry must fit within `.flake8` E501 (max-line-length=100) **including** indent / blockquote prefix
- Effective budget for `<verb> <what> (Sprint XX.Y) — <reason>` ≈ 90 chars(after 4-space indent or `> - ` Markdown prefix)
- If reason exceeds budget → split into multiple commits, OR move detail to commit message body / `claudedocs/4-changes/FIX-XXX`, OR factor reason into shorter scope keyword

**Char-count writing guidance** (Sprint 55.6+ — closes AD-Lint-MHist-Verbosity):

Treating budget proactively beats trim-after-write. Recurring evidence: Sprint 55.4 + 55.5 + 55.6 (3 consecutive sprints) had new MHist entries exceeding E501 by 1-3 chars on first draft, requiring trim cycle. Apply these templates to fit budget on first draft.

**Common-case templates** (chars include `> - ` or 4-space indent prefix; budget ≤ 100):

| Template shape | Example | Chars |
|----------------|---------|-------|
| `> - DATE: Sprint X.Y — <verb> <scope>` | `> - 2026-05-04: Sprint 53.7 Day 1 — full implementation` | ~55 |
| `> - DATE: Sprint X.Y — <verb> <scope> (closes AD-Foo)` | `> - 2026-05-04: Sprint 55.3 — extract category_span (closes AD-Cat12-Helpers-1)` | ~80 |
| `> - DATE: Sprint X.Y — <verb> <scope> + <minor>` | `> - 2026-05-04: Sprint 55.3 — add §Step 2.5 + ROI evidence` | ~65 |

**Anti-patterns** (will exceed budget; refactor before commit):

- ❌ **Pack 4-clause reasons in MHist**: `Sprint 55.3 — add §Step 2.5 grep verify (closes AD-Plan-1) + drop estimated headers (closes AD-Lint-2) + …` (≥150 chars). **Fix**: split into 2 separate MHist entries, OR move detail to commit message body / `claudedocs/4-changes/FIX-XXX-*.md`.
- ❌ **Verbose noun phrases**: prefer verbs over noun phrases — `extend` beats `extension of`; `promote` beats `promotion-to-validated-rule of`; `add` beats `addition of`.
- ❌ **Embedded paths > 30 chars**: don't quote a full path like `backend/src/agent_harness/orchestrator_loop/loop.py:1024` (54 chars). **Fix**: use scope keyword like `Cat 1 retry wrap` (16 chars) or `loop.py L1024+L1092` (19 chars).

**Rule of thumb**: If first-draft entry needs E501 lint (or the editor's 100-col ruler) to catch overflow, your reason was too verbose. Aim for **60-80 chars after prefix**; `(closes AD-Foo-N)` parens add ~20 chars on top.

**Why** (Sprint 54.2 retrospective Q4 evidence): MHist entries accumulate in mature files; each new entry at full prose reason often exceeded E501 (4× lint hit in Sprint 54.2 Day 4 alone); verbose MHist duplicates commit message + git blame already records full diff context. The single line forces the author to commit message body / 4-changes record for the rich detail, keeping headers scannable.

**Examples (good — 1-line, fit budget)**:
```
- 2026-05-04: Sprint 55.3 — extract category_span helper (closes AD-Cat12-Helpers-1)
- 2026-05-03: Sprint 53.4 Day 2 — full implementation
- 2026-04-28: Initial creation (Sprint 49.1) — TAO loop stub
```

**Examples (bad — see 禁止項 5)**:
```
- 2026-05-15: Add streaming support with AsyncIterator[LoopEvent] (Sprint 50.2)
    Reason: Required for SSE event stream alignment with Contract 4 in 17.md;
    consumer is frontend LoopVisualizer; tested via test_streaming_iterator.py
    + integration test under tests/integration/sse/.
```
(Wrong: multi-line + bullet detail. Detail belongs in commit message body / claudedocs/4-changes/.)

### 動詞選擇（Verb）

| 動詞 | 用途 | 範例 |
|-----|------|------|
| Add | 新增功能 / 方法 / 區塊 | Add streaming support |
| Fix | 修復 bug | Fix token counting off-by-one error |
| Refactor | 重構邏輯但行為不變 | Refactor LoopState into transient/durable |
| Update | 增強 / 改進現有功能 | Update PromptBuilder cache strategy |
| Remove | 刪除功能 / 死代碼 | Remove unused `_v1` suffix files |
| Deprecate | 標記過期但保留相容 | Deprecate sync callback for async iterator |
| Align | 對齐規範 / 契約 | Align MessageFormat with Contract 2 |

### 三層級對應（何時記錄）

| 改動類型 | 記錄？ | 範例 |
|---------|-------|------|
| **Trivial** | ❌ 否 | typo / format / 變數重名 |
| **Behavioral** | ✅ 是 | 修 bug / 新功能 / 重構邏輯 |
| **Structural** | ✅ 是 | 拆檔 / 範疇遷移 / 介面變更 |

---

## 禁止事項

### ❌ 禁止 1：行內歷史註解

```python
# ❌ 禁止
x = compute()  # 2026-05-01 changed from old_compute()

# ✅ 正確
# Modification History 記錄；git blame 已有詳細
x = compute()
```

### ❌ 禁止 2：保留 dead code 註解

```python
# ❌ 禁止
# old version:
# def old_method():
#     return x + y

# ✅ 正確
# 直接刪；git 有完整歷史
```

### ❌ 禁止 3：Vague commit message

```
# ❌ 禁止
git commit -m "update"
git commit -m "fix"
git commit -m "changes"

# ✅ 正確
git commit -m "fix: token counting off-by-one in Contract 8 count_tokens()"
git commit -m "refactor: split LoopState into transient/durable for Phase 50.1"
```

### ❌ 禁止 4：跳過 claudedocs/4-changes/

```
# ❌ 禁止
git commit -m "fix: context rot bug"
（無 FIX-XXX 文件）

# ✅ 正確
1. 建 claudedocs/4-changes/bug-fixes/FIX-123-context-rot.md
2. git commit -m "fix: …"
```

### ❌ 禁止 5：MHist multi-line / bullet sub-points / quote markers (Sprint 55.3+)

每個 MHist entry **必須是單行**，遵守 E501 (≤100 chars 含 indent / prefix)。

```
# ❌ 禁止 — multi-paragraph reason
- 2026-05-15: Add streaming support (Sprint 50.2)
    This change introduces AsyncIterator[LoopEvent] to align with Contract 4
    in 17-cross-category-interfaces.md. Required for frontend LoopVisualizer
    to consume SSE events. Tested via test_streaming_iterator.py.

# ❌ 禁止 — bullet sub-points
- 2026-05-15: Refactor LoopState (Sprint 50.1)
    - Split into transient/durable
    - Added Reducer ABC
    - Tests added: test_state_split.py

# ❌ 禁止 — line breaks within entry / quote markers
- 2026-05-15: Update PromptBuilder cache strategy (Sprint 52.2)
  > Reason: Prefix caching now uses 3-tier breakpoints
  > See: 17.md §Contract 5

# ✅ 正確 — single line, ≤ E501 budget
- 2026-05-15: Add streaming support with AsyncIterator[LoopEvent] (Sprint 50.2)
- 2026-05-15: Refactor LoopState into transient/durable split (Sprint 50.1)
- 2026-05-15: Update PromptBuilder cache strategy (Sprint 52.2) — 3-tier breakpoints
```

**Why**: Multi-line MHist entries (a) trigger flake8 E501 in mature headers (4× hit in Sprint 54.2 Day 4), (b) duplicate commit message body which is already preserved by `git log`, (c) break the newest-first scan that lets a reader survey 5+ entries in 5 seconds. Move rich detail to commit message body / `claudedocs/4-changes/FIX-XXX-*.md`; keep MHist scannable.

---

## 例外情況

### 生成檔案

migrations / proto / openapi schema 由工具產生，可省略手寫 header：

```python
# Auto-generated by Alembic
"""
...generated migration code...
"""
```

### 第三方 vendor 檔

不修改其 header；保留原樣。

### `__init__.py` 空檔

可省略：
```python
# Empty init; re-exports in __init__.py
```

### 測試檔（`.test.py` / `.spec.ts`）

可用簡化版：
```python
"""
File: tests/test_loop_executor.py
Purpose: Unit tests for LoopExecutor (Category 1)
Category: Tests
Created: 2026-04-28
Modified: 2026-05-15
"""
```

---

## 實踐範例

### 完整新檔案（Python）

```python
"""
File: src/agent_harness/context_mgmt/compactor.py
Purpose: Context compaction engine; detects token bloat and summarizes old observations.
Category: 範疇 4 (Context Mgmt)
Scope: Phase 52.1 / Sprint 52.1

Description:
    Detects when token usage exceeds threshold (75% by default).
    Triggers compaction by summarizing oldest observations + memory hints.
    Output: CompactedContext (reduced messages + summary artifact).
    Also handles "lost-in-middle" mitigation by strategic observation masking.

Key Components:
    - Compactor: Main class; async method compact_if_needed(state) -> CompactedContext
    - CompactionStrategy: ABC for pluggable strategies (summarize / preserve key facts)
    - ObservationMasker: Masks non-essential observations to preserve key context

Created: 2026-05-10
Last Modified: 2026-05-10

Modification History:
    - 2026-05-10: Initial creation (Sprint 52.1)

Related:
    - 01-eleven-categories-spec.md §範疇4
    - 17-cross-category-interfaces.md §1.1 (Contract 5: Compactor ABC)
    - 10-server-side-philosophy.md (LLM provider neutrality: uses ChatClient.count_tokens())
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

# === Compactor: Token budget management ===
# Why: V1 ignored context rot (AP-7), leading to 10+ turn degradation.
# V2 Day 1 must proactively compact when token usage exceeds budget.
# Reference: 04-anti-patterns.md §AP-7 Context Rot Ignored
class Compactor(ABC):
    """Abstract compaction engine; owns compaction strategy."""

    @abstractmethod
    async def compact_if_needed(self, state: LoopState) -> LoopState:
        """Compact state if token usage > threshold. Return new state (or same if no compact needed)."""
        ...
```

---

## 檢查清單（Code Review）

提交 PR 前自檢：

- [ ] 新檔有標準 header（Purpose / Category / Created）？
- [ ] Category 對應 11+1 範疇之一？
- [ ] Key Components 部分反映真實用途？
- [ ] Modification History newest-first？
- [ ] 若修改現有檔，是否更新 Last Modified？
- [ ] 行為變更（Behavioral / Structural）有 Modification History 記錄？
- [ ] Related 部分列出對應文件 + section？
- [ ] Section header（重要區塊）有 Why + Alternative considered？

---

## 引用

- **CLAUDE.md** — §File Header & Modification Convention（原始詳細規範）
- **category-boundaries.md** — Category 標籤對應 11+1 範疇
- **04-anti-patterns.md** — AP-4 Potemkin Features（為何需要 Key Components）
- **17-cross-category-interfaces.md** — Related 部分常見的跨範疇引用

---

**維護責任**：Linter @ PR checklist stage（可考慮建立 pre-commit hook 檢查 header 必填欄位）；Code reviewer 驗證完整性。

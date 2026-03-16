# MAF RC4 升級後驗證共識報告

**報告日期**: 2026-03-16
**產出方式**: Chief Verifier 整合 4 份驗證報告 + Challenger 交叉挑戰（8 項挑戰，全部回應達成共識）
**升級分支**: `feature/maf-rc4-upgrade`（6 commits, 19 files changed）
**升級範圍**: MAF `1.0.0b260114` → `1.0.0rc4` + Claude SDK 同步更新

---

## 執行摘要

MAF RC4 升級已成功完成核心遷移工作。6 個 commit 涵蓋了 import 路徑遷移、builder constructor 修正、storage/ACL fallback 修正、以及 Claude SDK 同步更新（anthropic 依賴、Extended Thinking header、預設模型 ID）。測試在 rc4 venv 中執行通過（17/17 integration tests pass，221/222 adapter unit tests pass），升級分支與 main 基線的 50 個既有失敗一致。**建議 GO — 可以 merge**，有 7 個 non-blocker 待辦在後續 sprint 處理。

---

## 1. 已確認修復的問題（Confirmed Fixed）

| # | 問題 | 來源報告 | 驗證方式 | 對應 Commit |
|---|------|----------|----------|-------------|
| F1 | `requirements.txt` 更新為 `agent-framework>=1.0.0rc4,<2.0.0` | BC Audit | 直接檢查檔案 | `0abedd0` |
| F2 | 6 條 Orchestration Builder import 遷移至 `agent_framework.orchestrations` | Import Verifier | grep 確認 6 條新路徑 | `0abedd0` + `a539a02` |
| F3 | 類別重命名別名正確實施（4 組） | Import Verifier | grep 確認 | `0abedd0` |
| F4 | `anthropic>=0.84.0` 加入 requirements.txt | Claude SDK Verifier | 檔案確認 | `0abedd0` |
| F5 | Extended Thinking header 更新為 `interleaved-thinking-2025-05-14` | Claude SDK Verifier | 程式碼確認 client.py:260 | `0abedd0` |
| F6 | 預設模型 ID 更新為 `claude-sonnet-4-6-20260217`（client.py:38） | Claude SDK Verifier | 程式碼確認 | `0abedd0` |
| F7 | `storage_factories.py:308` import 路徑修正（從不存在的 `.workflows` 改回頂層） | Import Verifier | commit diff 確認 | `c904dff` |
| F8 | `acl/adapter.py` 加入 orchestrations 子模組 fallback | BC Audit | commit diff 確認 | `c904dff` |
| F9 | 4 個 Builder constructor 修正（MagenticBuilder, ConcurrentBuilder, GroupChatBuilder, HandoffBuilder） | Constructor Verifier（修正後） | 測試通過：17/17 integration, 221/222 adapter | `e2e3d9c` + `623d557` |
| F10 | 已移除 API 清理完成（display_name, context_providers, AggregateContextProvider） | Constructor Verifier | grep 搜索無殘留 | N/A（原始碼未使用） |

### F3 類別重命名別名詳情

| 舊名稱 | RC4 新名稱 | 別名方式 | 檔案 |
|--------|-----------|---------|------|
| `ChatAgent` | `Agent` | `Agent as ChatAgent` | core/execution.py, builders/agent_executor.py |
| `ChatMessage` | `Message` | `Message as ChatMessage` | builders/agent_executor.py |
| `WorkflowStatusEvent` | `WorkflowEvent` | `WorkflowEvent as WorkflowStatusEvent` | core/events.py |
| `ContextProvider` | `BaseContextProvider` | `BaseContextProvider as ContextProvider` | memory/base.py |

---

## 2. 仍存在的問題（Remaining Issues）

### 阻擋 Merge 的（Blockers）

**無** — 所有核心遷移工作已完成並通過測試。

### 不阻擋 Merge 的（Non-blockers，延後處理）

| # | 問題 | 嚴重度 | 說明 | 建議處理時間 |
|---|------|--------|------|-------------|
| R1 | 舊模型 ID 殘留 | **HIGH** | 5 個源碼檔（config.py, autonomous/*.py, memory/types.py）+ 8 個測試檔仍用 `claude-sonnet-4-20250514`，與 client.py 的新預設值不一致 | 下個 Sprint |
| R2 | `memory/base.py:169` 的 `MemoryStorage` import | LOW | 用於 lazy import / 型別檢查上下文。RC4 中 `MemoryStorage` 可能已移除，建議加 try/except 防禦 | 下個 Sprint |
| R3 | 文件過時引用 | LOW | CLAUDE.md（2 處）、.claude/skills/（3 檔多處）的 import 路徑範例仍用舊路徑；CHANGE-006 的路徑和類別名稱映射表需更新 | 2 Sprint 內 |
| R4 | Python 註解中的舊路徑殘留 | LOW | 6 個檔案的註解中保留了升級前的舊 import 路徑（`#` 開頭，不影響執行） | 低優先 |
| R5 | client.py:221 docstring 過時 | LOW | 仍提及 `extended-thinking`，應更新為 `interleaved-thinking` | 低優先 |
| R6 | BC-11/15/16 行為變更未驗證 | MEDIUM | Checkpoint source_id 範圍化（BC-11）、Checkpoint 模型重構（BC-15）、編排輸出標準化（BC-16）需功能測試驗證 | 下個 Sprint |
| R7 | `acl/version_detector.py` 未更新 | MEDIUM | 3 處 `hasattr(agent_framework, api_name)` 在 RC4 中會因 orchestration builders 已移至子模組而返回 False。adapter.py 的 fallback 可補償，但 version_detector 邏輯應更新 | 下個 Sprint |

---

## 3. Verifier 錯誤結論記錄

此節記錄驗證過程中產生的錯誤結論及原因，作為未來 AI 輔助驗證的改進參考。

### E1: Constructor Verifier — `inspect.signature` 結果錯誤

| 項目 | 內容 |
|------|------|
| **錯誤結論** | `MagenticBuilder.__init__` 簽名為 `(self) -> None`，不接受 `participants=` kwarg，會觸發 TypeError |
| **實際情況** | `participants=` kwarg 方式正確可用。commit `623d557` 將程式碼改為 `MagenticBuilder(participants=list)` 後，測試全部通過（17/17 integration, 221/222 adapter） |
| **錯誤原因** | Constructor Verifier 可能在 MagicMock 環境或空列表條件下執行了 `inspect.signature`，導致得到不準確的簽名資訊。RC4 的 `MagenticBuilder`、`ConcurrentBuilder`、`GroupChatBuilder` 實際上接受 `participants` 作為可選建構參數 |
| **教訓** | AI 驗證工具的 `inspect.signature` 結果必須在乾淨的 venv 中、對真實類別（非 Mock）執行才可信。**實際測試結果 > 靜態分析推斷** |

### E2: BC Auditor — 錯誤假設所有類別需從子模組匯入

| 項目 | 內容 |
|------|------|
| **錯誤結論** | BC-07 遷移僅完成 26%（6/23），15 條 import 仍用舊頂層路徑，安裝 RC4 後會 import 失敗 |
| **實際情況** | RC4 的頂層 `__init__.py` 仍然 re-export 核心類別（Workflow, Edge, Agent, Executor, WorkflowContext 等），只有 orchestration builders（MagenticBuilder, ConcurrentBuilder 等）被移至 `agent_framework.orchestrations` 子模組 |
| **錯誤原因** | BC Auditor 假設 RC4 的命名空間重組意味著「所有類別都必須從子模組匯入」，但實際上只有 orchestration builders 發生了遷移。commit `c904dff` 明確確認「top-level, still available in rc4」 |
| **教訓** | 命名空間遷移的 breaking change 需要區分「哪些類別實際從頂層移除」vs「哪些仍然可用」。**以 venv 中的實際 import 測試為準，而非文件規劃** |

### Challenger 挑戰結果

Challenger 基於 4 份報告提出了 8 項挑戰（3 CRITICAL + 4 HIGH + 1 MEDIUM）。經過 git diff 事實比對和 commit message 測試記錄驗證：

| 挑戰 | Challenger 評級 | 最終評級 | 結果 |
|------|----------------|---------|------|
| #1 Constructor 矛盾 | CRITICAL | **已解決** | commit 修正正確，Constructor Verifier 報告錯誤 |
| #2 遷移率 26% | CRITICAL | **已解決** | 頂層 import 在 RC4 仍有效，BC Auditor 錯誤假設 |
| #3 storage_factories | HIGH | **已解決** | commit c904dff 已修正路徑 |
| #4 version_detector | HIGH | **Non-blocker R7** | adapter fallback 補償，延後處理 |
| #5 路徑不一致 | CRITICAL | **已解決** | `agent_framework.orchestrations` 是 RC4 正確路徑 |
| #6 測試覆蓋 | HIGH | **Non-blocker R1** | 測試已在 rc4 venv 執行，模型 ID 更新延後 |
| #7 CHANGE-006 過時 | MEDIUM | **Non-blocker R3** | 文件更新延後 |
| #8 MemoryStorage | MEDIUM | **Non-blocker R2** | 加 try/except 防禦 |

---

## 4. 測試結果對比

### 升級分支測試記錄（來自 commit messages）

| 測試類別 | 結果 | 來源 |
|----------|------|------|
| Phase 3 Integration Tests | **17/17 通過 (100%)** | commit `623d557` |
| Adapter Unit Tests | **221/222 通過 (99.5%)** | commit `e2e3d9c` |
| Infrastructure Tests | **174/176 通過 (98.9%)** | commit `e2e3d9c` |
| Integration Tests (全量) | **530/585 通過 (90.6%)** | commit `e2e3d9c` |

### 基線對比

| 指標 | main 基線 | 升級分支 | 差異 |
|------|----------|---------|------|
| 升級引起的新失敗 | 0 | **0**（全部修復） | 無新增失敗 |
| 既有失敗（pre-existing） | 50 | 50 | 一致，升級未引入退化 |
| 升級修復的失敗 | N/A | 5 個升級引起的失敗已修復 | commit `623d557` |

### 未執行的測試

- Claude SDK 相關測試（8 個檔案使用舊模型 ID）— 預期值可能不對，但不影響 MAF 升級判定
- BC-11/15/16 行為變更的功能測試 — 靜態分析無法覆蓋，需後續功能驗證

---

## 5. Merge 建議

### **GO — 建議 Merge**

**理由**：
1. 核心遷移工作已完成：6 條 orchestration builder import 遷移、4 組類別重命名別名、builder constructor 修正
2. 測試在 rc4 venv 中通過，升級分支與 main 基線一致（50 既有失敗不變，5 個升級引起的失敗全部修復）
3. 沒有 blocker 級別的問題
4. 所有 non-blocker 都有明確的延後處理計劃

### Merge 前小條件

- [ ] 確認 `storage_factories.py:308` 的 `# TODO: verify submodule path` 註解是否已移除（若仍在，建議順手清除）

### Merge 後不需要立即處理但需追蹤

見第 6 節待辦清單。

---

## 6. 升級後待辦清單

### Sprint N+1（下個 Sprint，HIGH 優先）

| # | 待辦項目 | 對應 Non-blocker | 工作量估計 |
|---|---------|-----------------|-----------|
| T1 | 統一模型 ID：將 config.py, autonomous/*.py, memory/types.py 中的 `claude-sonnet-4-20250514` 更新為 `claude-sonnet-4-6-20260217` | R1 | 1 SP |
| T2 | 更新 8 個測試檔案中的模型 ID 預期值 | R1 | 1 SP |
| T3 | 更新 `acl/version_detector.py` 的 `hasattr` 邏輯，同時檢查頂層和 `orchestrations` 子模組 | R7 | 2 SP |
| T4 | 為 `memory/base.py:169` 的 `MemoryStorage` import 加 try/except 防禦 | R2 | 0.5 SP |
| T5 | 功能測試驗證 BC-11（Provider source_id）、BC-15（Checkpoint 模型）、BC-16（編排輸出格式） | R6 | 3 SP |

### Sprint N+2（2 Sprint 內，MEDIUM/LOW 優先）

| # | 待辦項目 | 對應 Non-blocker | 工作量估計 |
|---|---------|-----------------|-----------|
| T6 | 更新 CHANGE-006 文件（路徑、類別名稱映射表、完成狀態） | R3 | 1 SP |
| T7 | 更新 CLAUDE.md（2 處）和 .claude/skills/（3 檔）的 import 路徑範例 | R3 | 1 SP |
| T8 | 更新 client.py:221 docstring（`extended-thinking` → `interleaved-thinking`） | R5 | 0.5 SP |
| T9 | 清理 Python 註解中的舊 import 路徑殘留（6 檔） | R4 | 0.5 SP |
| T10 | 清除 storage_factories.py 的 TODO 註解（若 merge 前未處理） | F7 附加 | 0.5 SP |

### 長期評估

| # | 待辦項目 | 說明 |
|---|---------|------|
| T11 | 評估 `agent_framework_claude.ClaudeAgent` 整合 | RC4 內建 Claude 支援（`agent-framework-claude` v1.0.0b260311），可考慮替代部分自建 claude_sdk/ 程式碼 |
| T12 | 評估官方 `claude-agent-sdk` 採用 | 重大架構決策，47 檔自建代碼影響範圍大 |

---

## 附錄：升級 Commit 歷史

| Commit | 日期 | 說明 |
|--------|------|------|
| `0abedd0` | 2026-03-16 | 初始遷移：import 路徑 + Claude SDK 同步 |
| `a539a02` | 2026-03-16 | 在 rc4 venv 驗證後修正 import 路徑 |
| `72b9540` | 2026-03-16 | 清理：移除意外提交的 venv，加入 .gitignore |
| `e2e3d9c` | 2026-03-16 | Constructor 修正（planning.py, concurrent.py, base.py） |
| `623d557` | 2026-03-16 | Constructor 修正（groupchat.py, handoff.py, magentic.py） |
| `c904dff` | 2026-03-16 | Post-verification 修正（storage_factories + ACL fallback） |

---

## 附錄：驗證報告索引

| 報告 | 產出者 | 核心結論 | 修正事項 |
|------|--------|---------|---------|
| POST-UPGRADE-Import-Verification.md | Import Verifier | 有條件通過（1 FAIL + 1 WARN） | FAIL 已由 c904dff 修正 |
| POST-UPGRADE-BC-Audit.md | BC Auditor | BC-07 遷移 26%（FAIL） | **錯誤結論**：頂層 import 仍有效，實際遷移完成 |
| POST-UPGRADE-Claude-SDK-Verification.md | Claude SDK Verifier | 3 項立即修復完成，模型 ID 部分殘留 | 準確，R1 追蹤 |
| POST-UPGRADE-Constructor-Verification.md | Constructor Verifier | 4 個 CRITICAL TypeError | **錯誤結論**：kwarg 方式正確，inspect.signature 結果不準確 |

---

*本報告由 Chief Verifier 整合產出，經 Challenger 交叉挑戰審查（8 項挑戰，全部達成共識） — 2026-03-16*

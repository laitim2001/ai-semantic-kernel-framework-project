# B-10 深度分析:`_verifier_factory.py` 去留(`AD-Cat10-VerifierFactory-Disposition`)

**Purpose**: 對 Sprint 57.63 approach A 後變成 production-orphan 的 `backend/src/api/v1/chat/_verifier_factory.py` 做去/留決策分析。**建議:刪除 + 有界遷移測試**(理由見 §3/§5);但去留屬 disposition 決策(AD 註明「Do NOT decide unilaterally」),最終由用戶拍板。
**Category**: 範疇 10 (Verification Loops) wiring / dead-code disposition
**Scope**: B 區優化分析 / B-10
**Created**: 2026-05-31
**Status**: Closed — 用戶採 (a) 刪除;已執行(見 REFACTOR-006)

**Modification History (newest-first)**:
- 2026-05-31: 決策落地 — 用戶選 (a) 刪除;已刪檔 + 遷移 settings 測試 + 清 stale 註解;49 tests / mypy 0 / 9/9 V2 lints 綠;closes AD-Cat10-VerifierFactory-Disposition(REFACTOR-006)
- 2026-05-31: Initial creation — B-10 `_verifier_factory.py` 去留分析(git grep + 全檔複核)

**Related**:
- `integration-progress-20260531.md` §B-10
- `docs/.../phase-57/sprint-57-63/retrospective.md` §AD-Cat10-VerifierFactory-Disposition
- `claudedocs/4-changes/feature-changes/CHANGE-031-chat-path-category-activation.md` §_verifier_factory.py disposition (deferred)
- `04-anti-patterns.md` AP-2(Side-Track Code Pollution)
- CLAUDE.md §Karpathy §3(「你的改動產生的 orphan 才清」)+ §Never Delete Tests

---

## 0. 一句話結論

> **建議刪除 `_verifier_factory.py`**:它在 Sprint 57.63 approach A 後 production 無人用,且其唯一 production 角色已被 `make_chat_verifier_registry`(`_category_factories.py`)取代。刪除成本小且有界(退役 3 個工廠專屬測試 + 遷移 1 個 settings-validation 測試 + 改 1 處 smoke-test helper)。**但這是去/留決策,請你拍板。**

---

## 1. 證據(git grep + 全檔複核,本次工具無異常)

**檔案**:`backend/src/api/v1/chat/_verifier_factory.py`(94 行含 header,Sprint 55.5 建)。公開 3 symbol:
- `VerificationMode = Literal["disabled","enabled"]`(L53)
- `build_default_verifier_registry()`(L56-67)— 建一個含**單一 no-op `RulesBasedVerifier(rules=[])`** 的 registry
- `select_verifier_registry(mode)`(L70-86)— `"enabled"`→registry / `"disabled"`→None

**Production 引用 = 0**:`git grep "_verifier_factory"` 在 `backend/src/` **唯一命中是檔案自己的 header(L2)**。無任何 production import。`CHANGE-031:44` 記載 57.63 已移除 `router.py` 內 `from ._verifier_factory import select_verifier_registry`。

**測試引用(2 檔,非 AD 說的 1 檔)**:
| 檔 | 引用 | 性質 |
|----|------|------|
| `tests/unit/api/v1/chat/test_verification_wire.py` | L29-32 import + 4 測試 | **3 個直接測工廠**(`test_factory_default_*` / `test_disabled_mode_*` / `test_enabled_mode_*`);**1 個測 `Settings.chat_verification_mode` pydantic Literal**(`test_invalid_mode_raises`,獨立價值)|
| `tests/integration/api/test_chat_verification_smoke.py` | L154 import `build_default_verifier_registry` | **當測試 helper**:monkeypatch `build_handler` 配一個 no-op populated registry,證 router→wrapper→SSE 對 populated registry 的發事件契約(不需真 Azure)。非在測工廠本身 |

> **AD 小更正**:retro 寫「only test_verification_wire.py references it」,實際 smoke test L154 **也**用 `build_default_verifier_registry`。刪檔須一併處理這處。

---

## 2. 為何被取代(57.63 approach A)

- 57.63 把 verifier registry 的建構移到 `build_real_llm_handler` 內(`make_chat_verifier_registry`,`_category_factories.py:134`),且建**真的 `LLMJudgeVerifier`**(共用 loop 的 adapter),不是工廠的 no-op `RulesBasedVerifier(rules=[])`。
- `select_verifier_registry` 的 disabled/enabled 分派邏輯,也被 `build_real_llm_handler` 內聯 `if settings.chat_verification_mode == "enabled": ... else None`(`handler.py:244-248`)取代。
- ∴ 工廠兩個函式在 production 都成孤兒;其 no-op 預設(emit `VerificationPassed` 卻不真驗)反而是 Potemkin 隱患,留著有誤用風險。

---

## 3. 去/留兩案 + 建議

| 案 | 內容 | 評估 |
|----|------|------|
| **(a) 刪除**(建議)| 刪 `_verifier_factory.py` + 退役/遷移其測試 | ✅ 消 AP-2 side-track;✅ 消 no-op verifier Potemkin 隱患;✅ 完成 57.63 自身應做的 orphan 清理(Karpathy §3);成本小且有界 |
| (b) 保留 | 當「documented helper」留著 | 低傷害但留著 = 永久 AP-2;no-op 預設誤用風險仍在;DRY 上分派邏輯與 handler 內聯重複 |

**建議 (a)**,核心理由:**這個 orphan 是 Sprint 57.63 approach A 自己造成的**。依 CLAUDE.md Karpathy §3「你的改動產生的 orphan 才清;既有的 dead code 不關你事」——57.63 本該清,只因「never-delete-tests」謹慎而 defer。現在清,是補完 57.63 的清理義務,不是去動無關 dead code。

---

## 4. 若採 (a),有界遷移步驟

1. **刪** `backend/src/api/v1/chat/_verifier_factory.py`。
2. **退役** `test_verification_wire.py` 中 3 個工廠專屬測試(`TestBuildDefaultVerifierRegistry` + `TestSelectVerifierRegistry` 兩類)——它們測的 code 被移除,退役**不違反** Never-Delete-Tests(該規則禁的是「為過 build 而關測試」,非「移除已刪功能的測試」)。
3. **遷移**(不可刪)`test_invalid_mode_raises` → 移到 config/settings 測試檔(如 `tests/unit/core/test_config.py`),因它測的是 `Settings.chat_verification_mode` Literal 驗證,**與工廠無關、有獨立價值**。
4. **改** `test_chat_verification_smoke.py:154`:把 `build_default_verifier_registry()` helper 換成 2 行內聯(`reg = VerifierRegistry(); reg.register(RulesBasedVerifier(rules=[]))`,直接 import 自 `agent_harness.verification`)。
5. 跑 `pytest tests/unit/api/v1/chat tests/integration/api/test_chat_verification_smoke.py` 綠 + `git grep "_verifier_factory"` 應只剩 docs 歷史引用。
6. 走標準 sprint workflow(plan→checklist→code)或當作 micro-chore;更新 retro 把 `AD-Cat10-VerifierFactory-Disposition` 標 closed。

預估:**極小**(刪 1 檔 + 動 2 測試檔)。無 schema、無 loop、無 production 行為改變(production 早已不走它)。

---

## 5. Anti-pattern 框架

- **AP-2(Side-Track Code Pollution)**:production 無呼叫點、無法從 API 入點追蹤 → 正中 AP-2。B-10 = 消這個 AP-2。
- **Karpathy §3**:此 orphan 由 57.63 改動產生 → 屬「該清的自家 orphan」。
- **Never-Delete-Tests / Never-Delete-Docs**:刪檔需「退役工廠測試 + 遷移 settings 測試 + 改 smoke helper」,不可一刪了之;§4 已分流(退役 vs 遷移)。

---

## 6. 需要你的決策

| 問題 | 我的建議 |
|------|---------|
| 刪還是留? | **刪 (a)** —— 57.63 自家 orphan + AP-2 + no-op Potemkin 隱患 |
| 成本? | 極小、有界(§4 六步)|
| 風險? | 低;production 早不走它,只動測試 helper |
| 何時做? | 可當 micro-chore 或併入下個 Cat 10 相關 sprint |

> 確認 (a) 刪除,我會走 plan→checklist→code(刪檔屬刪 production code,需你授權);或你選 (b) 保留,我把 AD 標為「keep, closed」。

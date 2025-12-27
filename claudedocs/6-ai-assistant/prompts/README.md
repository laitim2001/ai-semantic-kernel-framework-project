# AI 助手 Prompt 系統

> **版本**: v4.0.0
> **專案**: IPA Platform (Intelligent Process Automation)
> **更新日期**: 2025-12-27
> **狀態**: Phase 11 完成 - Agent-Session Integration

---

## 核心情況清單 (5 個)

| 情況 | 文件 | 使用時機 |
|------|------|----------|
| **情況1** | [專案入門](./SITUATION-1-PROJECT-ONBOARDING.md) | 新開發者或新會話開始 |
| **情況2** | [開發前準備](./SITUATION-2-FEATURE-DEV-PREP.md) | 開始開發任務前的準備 |
| **情況3** | [功能增強/修正](./SITUATION-3-FEATURE-ENHANCEMENT.md) | 修改現有功能、Bug 修復、重構 |
| **情況4** | [新功能開發](./SITUATION-4-NEW-FEATURE-DEV.md) | 開發全新功能或模組 |
| **情況5** | [保存進度](./SITUATION-5-SAVE-PROGRESS.md) | 提交代碼、保存工作成果 |

---

## 使用場景對照

| 你想要... | 使用情況 |
|-----------|----------|
| 剛進入這個專案 | 情況1: 專案入門 |
| 開始開發前了解須知事項 | 情況2: 開發前準備 |
| 修改/增強/重構現有功能 | **情況3: 功能增強/修正** |
| 修復 Bug | **情況3: 功能增強/修正** (模式A) |
| 開發全新功能/模組 | 情況4: 新功能開發 |
| 保存開發進度 | 情況5: 保存進度 |

---

## 使用方式

### 方式 1: 直接執行情況

```markdown
請閱讀 SITUATION-3-FEATURE-ENHANCEMENT.md 並執行
```

### 方式 2: 複製 Prompt 模板

每個情況文件都有「📋 Prompt 模板」區塊，可直接複製使用。

### 方式 3: 描述需求

```markdown
我要修復一個 Bug：[描述問題]
# AI 會自動參考情況3 的 Bug 修復流程
```

---

## 每日開發流程

```yaml
開始工作:
  - 情況1 (如果是新會話)
  - 情況2 (開發前準備)

開發中:
  - 情況3 (修改現有功能/修 Bug/重構)
  - 情況4 (開發新功能)

結束工作:
  - 情況5 (保存進度)
```

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 後端 | Python FastAPI + Pydantic |
| 測試 | pytest + black + isort + flake8 |
| 數據庫 | PostgreSQL 16 + Redis 7 |
| LLM | Azure OpenAI |

---

## 歸檔文件

非核心情況已移至 `archive-v3/` 目錄：

- SITUATION-5-TESTING.md
- SITUATION-7-ARCHITECTURE-REVIEW.md
- SITUATION-8-CODE-REVIEW.md
- SITUATION-9-SESSION-END.md
- SITUATION-10-UAT-SESSION.md

如需使用，可從歸檔目錄取回。

---

## 版本歷史

### v4.0.0 (2025-12-27)
- 精簡為 5 個核心情況
- 合併 Bug 修復 + 功能修改 → 情況3
- 移除非核心情況至 archive-v3
- 更新所有文件內部引用

### v3.1.0 (2025-12-24)
- 新增 SITUATION-11: 功能修改/更新

### v3.0.0 (2025-12-24)
- 採用「情況」(SITUATION) 命名
- 10 個標準情況文件

---

**維護者**: AI 助手 + 開發團隊
**最後更新**: 2025-12-27

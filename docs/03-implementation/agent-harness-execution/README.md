# Agent Harness Execution（V2 執行紀錄）

**建立日期**：2026-04-23

---

## 用途

本目錄存放 V2 各 Phase / Sprint 的**執行紀錄**（progress / retrospective / artifacts）。

對應規劃在 `docs/03-implementation/agent-harness-planning/`。

---

## 結構

```
agent-harness-execution/
├── README.md                       ← 本檔
├── phase-49/
│   ├── sprint-49-1/
│   │   ├── progress.md             # 每日進度
│   │   ├── retrospective.md        # Sprint 回顧
│   │   ├── anti-pattern-audit.md   # 反模式審計
│   │   └── artifacts/              # 產出文件 / 截圖
│   ├── sprint-49-2/
│   └── sprint-49-3/
├── phase-50/
│   ├── sprint-50-1/
│   └── sprint-50-2/
├── phase-51/
│   ├── ...
...
└── phase-55/
    └── ...
```

---

## 各 Phase 索引

| Phase | 名稱 | Sprint | 狀態 |
|-------|------|--------|------|
| **49** | Foundation | 49.1 / 49.2 / 49.3 | ⏳ 未開始 |
| **50** | Loop Core | 50.1 / 50.2 | ⏳ 未開始 |
| **51** | Tools + Memory | 51.1 / 51.2 | ⏳ 未開始 |
| **52** | Context + Prompt | 52.1 / 52.2 | ⏳ 未開始 |
| **53** | State + Error + Guardrails | 53.1 / 53.2 / 53.3 | ⏳ 未開始 |
| **54** | Verification + Subagent | 54.1 / 54.2 | ⏳ 未開始 |
| **55** | Production | 55.1 / 55.2 | ⏳ 未開始 |

---

## 每個 Sprint 結束的 Deliverables

```
sprint-XX-Y/
├── progress.md           ← 每日進度（按日記錄）
├── retrospective.md      ← Sprint 結束回顧
│   - What went well
│   - What didn't go well
│   - 範疇成熟度變化（Level X → Level Y）
│   - 反模式違反次數
│   - 下個 Sprint 改進
└── artifacts/            ← 產出（screenshots / API docs / 設計圖）
```

---

## 範疇成熟度追蹤

每個 Sprint 結束更新 11 範疇 Level：

```markdown
## Sprint 結束時範疇 Level

| 範疇 | Sprint 開始時 | Sprint 結束時 | 變化 |
|------|-------------|-------------|------|
| 1. Orchestrator Loop | L0 | L0 | - |
| 2. Tool Layer | L0 | L0 | - |
| ... | | | |
```

整體進度指標：
- 起點：Phase 48 結束時 = 27% 真實對齊度（V1 baseline）
- 目標：Phase 55 結束時 = 75%+ 真實對齊度
- 每 Phase 大約推進 7-8%

---

## 文件規範

### progress.md 範本
```markdown
# Sprint XX.Y Progress

**Sprint**：XX.Y
**期間**：YYYY-MM-DD ~ YYYY-MM-DD

## Day 1 (YYYY-MM-DD)
- 完成：______
- 進行中：______
- 阻礙：______

## Day 2 (YYYY-MM-DD)
- ...
```

### retrospective.md 範本
```markdown
# Sprint XX.Y Retrospective

**Sprint**：XX.Y
**期間**：YYYY-MM-DD ~ YYYY-MM-DD

## What went well
- ...

## What didn't go well
- ...

## 範疇成熟度變化
| 範疇 | 開始 | 結束 |
|------|-----|-----|
| ... | L? | L? |

## Anti-Pattern 違反
- AP-1: 0 次
- AP-2: 0 次
- ...
- AP-10: 0 次
- 總違反：0

## 學習與下個 Sprint 改進
- ...
```

---

## 與 Planning 文件的關係

```
agent-harness-planning/             ← 規劃（before）
├── 00-v2-vision.md
├── 01-eleven-categories-spec.md
├── ...
├── phase-49-foundation/
│   ├── sprint-49-1-plan.md        ← Sprint 規劃文件
│   └── sprint-49-1-checklist.md   ← Sprint 任務清單
└── phase-50-loop-core/
    └── ...

       ↓ 執行對應

agent-harness-execution/            ← 執行紀錄（during + after）
├── phase-49/
│   └── sprint-49-1/
│       ├── progress.md            ← 執行中記錄
│       ├── retrospective.md       ← 執行後回顧
│       └── artifacts/
└── phase-50/
    └── ...
```

---

## 下一步

Phase 49 Sprint 49.1 啟動時：
1. 在 `phase-49/sprint-49-1/` 建立 progress.md
2. 執行過程持續更新
3. Sprint 結束時建立 retrospective.md

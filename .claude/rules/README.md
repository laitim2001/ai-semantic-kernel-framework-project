# `.claude/rules/` 索引

**Purpose**: V2 開發規則總覽。所有規則對齐 `docs/03-implementation/agent-harness-planning/` 19 份權威文件。

**Last Updated**: 2026-04-28（V2 Phase 49+ 重寫）
**Status**: Active

---

## 規則分類

### 🔴 基石（必讀；定義範疇與紀律）

| 檔案 | 用途 |
|------|------|
| [`category-boundaries.md`](./category-boundaries.md) | 11+1 範疇歸屬與跨範疇 import 三層規則 |
| [`llm-provider-neutrality.md`](./llm-provider-neutrality.md) | `agent_harness/**` 禁 import openai/anthropic；ChatClient ABC；CI lint |
| [`anti-patterns-checklist.md`](./anti-patterns-checklist.md) | 11 條反模式 PR 自檢清單（V1 教訓） |
| [`file-header-convention.md`](./file-header-convention.md) | File header + Modification History 強制格式 |

### 🟡 流程（每日工作必依）

| 檔案 | 用途 |
|------|------|
| [`sprint-workflow.md`](./sprint-workflow.md) | Plan → Checklist → Code → Update → Progress 強制流程 |
| [`git-workflow.md`](./git-workflow.md) | Commit / Branch 規範；scope 對應 11+1 範疇 |

### 🟢 技術層（範疇 / 平台 / Adapter）

| 檔案 | 用途 |
|------|------|
| [`adapters-layer.md`](./adapters-layer.md) | adapters/_base ABC 設計 + 新 provider 上架 5 步 SOP + Azure OpenAI 細節 |
| [`multi-tenant-data.md`](./multi-tenant-data.md) | DB tenant_id 強制隔離 + RLS + GDPR / PII 處理 |
| [`observability-instrumentation.md`](./observability-instrumentation.md) | 範疇 12 cross-cutting 5 處必埋點 + TraceContext + Metric 集合 |

### 📐 質量

| 檔案 | 用途 |
|------|------|
| [`backend-python.md`](./backend-python.md) | Python backend 通用規則（保留自 V1） |
| [`frontend-react.md`](./frontend-react.md) | React/TypeScript 通用規則（保留自 V1） |
| [`code-quality.md`](./code-quality.md) | Black / isort / mypy / flake8 + V2 範疇層級 coverage 目標 |
| [`testing.md`](./testing.md) | Pytest / 範疇測試分工 / Contract Test / Multi-tenant Test |

### 📖 AI 助手指引

| 檔案 | 用途 |
|------|------|
| [`graphify-usage.md`](./graphify-usage.md) | Claude Code 本地閱讀加速器使用提示（非工程治理） |

---

## 開發者快速指引

### 第一次接觸專案

依序讀：
1. `CLAUDE.md`（根目錄）— 專案高層
2. `category-boundaries.md` — 知道代碼放哪
3. `llm-provider-neutrality.md` — 知道不能寫什麼
4. `anti-patterns-checklist.md` — 知道審查標準
5. `sprint-workflow.md` — 知道每天工作節奏

### 開始一個 Sprint

依序：
1. `sprint-workflow.md` Step 1-2（建 plan + checklist）
2. `category-boundaries.md` 確認代碼歸屬
3. `file-header-convention.md` 寫新檔案 header
4. 開發中對照 `code-quality.md` / `testing.md`

### 建新 LLM Adapter

讀：
1. `llm-provider-neutrality.md` — ABC 接口要求
2. `adapters-layer.md` — 5 步 SOP + Contract Test
3. `testing.md` §Contract Test for Adapters

### 寫新業務 endpoint

讀：
1. `multi-tenant-data.md` — tenant_id 強制
2. `observability-instrumentation.md` — 埋點
3. `testing.md` §Multi-tenant Tests

### Code Review / PR 自檢

對照：
1. `anti-patterns-checklist.md`（11 條）
2. `git-workflow.md` §Before You Commit
3. `category-boundaries.md` Lint 規則

---

## 與 V2 規劃文件的對應關係

`.claude/rules/` 是**操作層規則**，內容必須對齐 `docs/03-implementation/agent-harness-planning/` 的**設計層規範**。

| Rule | 對應 V2 文件 |
|------|-------------|
| category-boundaries.md | 01-eleven-categories-spec.md / 02-architecture-design.md / 17-cross-category-interfaces.md |
| llm-provider-neutrality.md | 10-server-side-philosophy.md §原則 2 / 17.md §Contract 2 |
| anti-patterns-checklist.md | 04-anti-patterns.md |
| file-header-convention.md | CLAUDE.md §File Header & Modification Convention |
| sprint-workflow.md | CLAUDE.md §Sprint Execution Workflow / 06-phase-roadmap.md |
| git-workflow.md | CLAUDE.md §Code Standards |
| adapters-layer.md | 07-tech-stack-decisions.md / 17.md §Contract 2 |
| multi-tenant-data.md | 09-db-schema-design.md / 14-security-deep-dive.md / 10.md §原則 1 |
| observability-instrumentation.md | 01-eleven-categories-spec.md §範疇 12 / 17.md §Contract 12 |
| code-quality.md | 11-test-strategy.md |
| testing.md | 11-test-strategy.md / 04-anti-patterns.md |
| graphify-usage.md | CLAUDE.md §graphify（純本地工具，不對應 V2 規劃文件） |

> **權威排序**：V2 規劃文件（19 份）> 本目錄規則 > 既有代碼。衝突以上位者為準。

---

## 維護

- 每次 V2 規劃文件更新（特別是 17.md / 04.md / 10.md），需檢查對應 rule 是否同步
- Rule 改動 = 開發習慣改動 → PR 標題加 `chore(rules)` 並通知所有開發者
- 新 rule 必須走 `sprint-workflow.md` 標準流程（plan + checklist）
- 舊 rule 淘汰時走 `archive` scope，不直接刪除（保留 git history）

---

## 已淘汰的規則

| 舊 Rule | 淘汰原因 | 替代 |
|--------|--------|------|
| `agent-framework.md` | V1 MAF 即將封存（Sprint 49.1） | `adapters-layer.md` |
| `azure-openai-api.md` | 內容拆分到 ABC 設計 + Azure 細節 | `adapters-layer.md` §Azure OpenAI 特定細節 |

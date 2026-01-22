# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## AI Assistant Notes

- **Project Location**: Windows (`C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project`)
- **Server Startup**: Use `cmd /c` or direct terminal execution, NOT `start /D` or `start /B`
  - `start /B python -m uvicorn ...` — Background execution causes process tracking issues
  - `cmd /c "cd /d path && python -m uvicorn ..."` — Recommended

```bash
# Recommended Backend startup (Windows)
cmd /c "cd /d C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project\backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
```

---

## Project Overview

**IPA Platform** (Intelligent Process Automation) - Enterprise AI Agent orchestration platform

| Attribute | Value |
|-----------|-------|
| **Core Framework** | Microsoft Agent Framework + Claude Agent SDK + AG-UI Protocol |
| **Current Status** | Phase 28 已完成 - 三層意圖路由 |
| **Completed** | 28 Phases, 99 Sprints, 2189 Story Points |
| **Tech Stack** | FastAPI + React 18 + PostgreSQL + Redis |

---

## Development Commands

### Unified Dev Environment (Recommended)

```bash
# View all service status
python scripts/dev.py status

# Start services
python scripts/dev.py start              # Start all (Docker + Backend + Frontend)
python scripts/dev.py start backend      # Backend only
python scripts/dev.py start frontend     # Frontend only
python scripts/dev.py start docker       # Docker services only

# Stop/Restart
python scripts/dev.py stop [service]
python scripts/dev.py restart [service]

# Logs
python scripts/dev.py logs postgres
python scripts/dev.py logs docker -f
```

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI/Uvicorn |
| Frontend | 3005 | Vite Dev Server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| RabbitMQ | 5672/15672 | Message Queue / Management UI |

---

## Architecture Overview

```
Frontend (React 18 + TypeScript)
    ↓ HTTPS (port 3005)
Backend (FastAPI, port 8000)
    ├─ api/v1/           # 20+ API route modules
    ├─ integrations/     # MAF + Claude SDK + MCP
    ├─ domain/           # Business logic
    └─ infrastructure/   # Database, Cache, Messaging
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Directory Structure

```
backend/src/
├── api/v1/              # API routes (agents, workflows, sessions, ag-ui, claude_sdk)
├── integrations/        # Framework integrations
│   ├── agent_framework/ # MAF Adapters (GroupChat, Handoff, Concurrent, etc.)
│   ├── claude_sdk/      # Claude SDK (Client, Tools, Hooks, MCP)
│   └── ag_ui/           # AG-UI Protocol (SSE, Events, Handlers)
├── domain/              # Business logic (agents, workflows, sessions)
└── infrastructure/      # Database, Cache, Messaging

frontend/src/
├── pages/               # Page components
├── components/          # Reusable UI components
├── hooks/               # Custom React hooks
├── api/                 # API client
└── store/               # Zustand state management
```

---

## Code Standards

All code standards are defined in `.claude/rules/` directory:

| Rule File | Scope |
|-----------|-------|
| `backend-python.md` | Python backend code |
| `frontend-react.md` | React/TypeScript frontend |
| `agent-framework.md` | Agent Framework integration layer |
| `git-workflow.md` | Git commits and branches |
| `code-quality.md` | Code quality tools (Black, ESLint, etc.) |
| `testing.md` | Testing standards |
| `azure-openai-api.md` | Azure OpenAI API usage |

### Quick Commands

```bash
# Backend quality check
cd backend && black . && isort . && flake8 . && mypy . && pytest

# Frontend quality check
cd frontend && npm run lint && npm run build
```

---

## Environment Setup

Copy `.env.example` to `.env`:

```bash
# Database
DB_NAME=ipa_platform
DB_USER=ipa_user
DB_PASSWORD=ipa_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5.2
```

---

## Key Documentation

| Document | Purpose |
|----------|---------|
| `docs/02-architecture/technical-architecture.md` | System architecture |
| `docs/01-planning/prd/prd-main.md` | Product requirements |
| `docs/03-implementation/sprint-planning/README.md` | Sprint planning overview |
| `docs/api/ag-ui-api-reference.md` | AG-UI API Reference |
| `claudedocs/CLAUDE.md` | AI 助手執行文檔索引 |

---

## ClaudeDocs - AI 助手執行文檔

> **重要**: `claudedocs/` 目錄是 AI 助手與開發團隊協作產出的動態執行文檔，與 `docs/` 的設計文檔分開管理。

### 目錄結構

```
claudedocs/
├── 1-planning/          # 總體規劃 (epics, architecture, features)
├── 2-sprints/           # Sprint 執行文檔
├── 3-progress/          # 進度追蹤 (daily, weekly, milestones)
├── 4-changes/           # 變更記錄 (bug-fixes, feature-changes)
├── 5-status/            # 狀態報告 (phase-reports, testing)
├── 6-ai-assistant/      # AI 助手相關 (prompts, analysis)
├── 7-archive/           # 歷史歸檔
├── CLAUDE.md            # 詳細目錄索引
└── README.md            # 快速導覽
```

### AI 助手情境提示詞 (SITUATION)

根據當前工作情境，使用對應的提示詞模板：

| 情境 | 文檔 | 使用時機 |
|------|------|----------|
| **SITUATION-1** | `6-ai-assistant/prompts/SITUATION-1-PROJECT-ONBOARDING.md` | 專案入門、首次接觸 |
| **SITUATION-2** | `6-ai-assistant/prompts/SITUATION-2-FEATURE-DEV-PREP.md` | 功能開發準備 |
| **SITUATION-3** | `6-ai-assistant/prompts/SITUATION-3-FEATURE-ENHANCEMENT.md` | 功能增強或修正 |
| **SITUATION-4** | `6-ai-assistant/prompts/SITUATION-4-NEW-FEATURE-DEV.md` | 新功能開發執行 |
| **SITUATION-5** | `6-ai-assistant/prompts/SITUATION-5-SAVE-PROGRESS.md` | 保存進度、會話結束 |
| **SITUATION-6** | `6-ai-assistant/prompts/SITUATION-6-SERVICE-STARTUP.md` | 服務啟動、環境檢查 |
| **SITUATION-7** | `6-ai-assistant/prompts/SITUATION-7-NEW-ENV-SETUP.md` | 新開發環境設置 |

### 變更記錄規範

當修復 Bug 或實作功能變更時，必須在 `claudedocs/4-changes/` 建立對應文檔：

| 類型 | 目錄 | 命名格式 | 範例 |
|------|------|----------|------|
| Bug 修復 | `4-changes/bug-fixes/` | `FIX-XXX-description.md` | `FIX-001-hitl-approval-wrong-id-type.md` |
| 功能變更 | `4-changes/feature-changes/` | `CHANGE-XXX-description.md` | `CHANGE-001-hitl-inline-approval-card.md` |
| 重構 | `4-changes/refactoring/` | `REFACTOR-XXX-description.md` | `REFACTOR-001-api-structure.md` |

### 日常工作流程

1. **開始工作前**: 查看 `claudedocs/3-progress/daily/` 最新日誌
2. **修復 Bug**: 在 `claudedocs/4-changes/bug-fixes/` 建立 FIX 文檔
3. **功能變更**: 在 `claudedocs/4-changes/feature-changes/` 建立 CHANGE 文檔
4. **會話結束**: 使用 SITUATION-5 保存進度

### 詳細指引

- 完整目錄索引: `claudedocs/CLAUDE.md`
- 快速導覽: `claudedocs/README.md`
- 文檔命名約定和格式範本請參考 `claudedocs/CLAUDE.md`

---

## Developer Preferences

### Communication
- **Language**: Respond in Traditional Chinese
- **Detail Level**: Provide detailed explanations with reasoning
- **Confirmation**: Ask before destructive operations

### Code Style
- **Comments**: Mixed mode - important explanations in Chinese, short comments in English
- **Git Commit**: Commit only when feature is complete
- **Testing**: New features must include unit tests

### Behavior Rules
- **Proactive Assistance**: Actively participate in development
- **Ask Before Acting**: When uncertain, always ask first
- **Deep Error Analysis**: Analyze root cause thoroughly
- **Never Delete Tests**: Do not delete or skip tests to solve problems
- **Never Delete Docs**: Do not delete documentation without asking

---

## CRITICAL: Microsoft Agent Framework API Usage

> **This is the most important rule for this project.**

When developing in `backend/src/integrations/agent_framework/builders/`:

### MUST Do

1. **Import official classes from `agent_framework`**
2. **Create official Builder instance**: `self._builder = OfficialBuilder()`
3. **Call official Builder in build()**: `return self._builder.build()`

### DO NOT

- Create custom implementation without `agent_framework` imports
- Skip `from agent_framework import ...` statements
- Implement similar functionality without calling official API

### Verification

```bash
cd backend && python scripts/verify_official_api_usage.py
# All 5 checks must pass
```

See `.claude/rules/agent-framework.md` for detailed rules.

---

## Important Notes

1. **Agent Framework is Preview**: API may change. Reference docs in `reference/agent-framework/`

2. **Chinese Documentation**: Target market is Taiwan/Hong Kong. Technical terms in English, comments in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

---

**Last Updated**: 2026-01-22
**Project Start**: 2025-11-14
**Status**: Phase 28 已完成 (99 Sprints completed)
**Total Story Points**: 2189 pts across 28 phases

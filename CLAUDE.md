# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## AI Assistant Notes (重要)

- **專案位置**: Windows C 槽 (`C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project`)
- **啟動 Server 方式**: 不要使用 `start /D` 或 `start /B`，請使用 `cmd /c` 或直接在終端執行
  - ❌ `start /B python -m uvicorn ...` — 背景執行會導致無法正確追蹤進程
  - ❌ `start /D path python ...` — 路徑處理不穩定
  - ✅ `cmd /c "cd /d path && python -m uvicorn ..."` — 推薦方式
- **Python 環境**: 請確保在正確的虛擬環境中執行

```bash
# 正確的 Backend 啟動方式 (Windows)
cmd /c "cd /d C:\Users\rci.ChrisLai\Documents\GitHub\ai-semantic-kernel-framework-project\backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
```

---

## Project Overview

**IPA Platform** (Intelligent Process Automation) is an enterprise-grade AI Agent orchestration platform built on **Microsoft Agent Framework** + **Claude Agent SDK** hybrid architecture.

- **Core Framework**: Microsoft Agent Framework (Preview) + Claude Agent SDK + AG-UI Protocol
- **Target Users**: Mid-size enterprises (500-2000 employees)
- **Status**: **Phase 16 Planning** - Unified Agentic Chat Interface (~100 pts)
- **Current Phase**: Phase 16 - Unified Agentic Chat Interface (Sprints 62-65)
- **Architecture**: Full official Agent Framework API integration (>95% API coverage) + Claude SDK hybrid + AG-UI Protocol
- **Stats**: 4000+ tests, 350+ API routes, 30+ production-ready adapters
- **Phases Completed**: Phase 1-15 (Sprints 1-60, 1455 pts)
  - Phase 1-11: Core Platform (Sprints 1-47)
  - Phase 12: Claude Agent SDK Integration (Sprints 48-51, 165 pts)
  - Phase 13: Hybrid Core Architecture (Sprints 52-54, 105 pts)
  - Phase 14: Advanced Hybrid Features (Sprints 55-57, 95 pts)
  - Phase 15: AG-UI Protocol Integration (Sprints 58-60, 85 pts)
- **In Progress**: Phase 16 - Unified Agentic Chat Interface (Sprints 62-65, ~100 pts)
  - Sprint 62: Core Architecture & Adaptive Layout (30 pts)
  - Sprint 63: Mode Switching & State Management (25 pts)
  - Sprint 64: Approval Flow & Risk Indicators (25 pts)
  - Sprint 65: Metrics, Checkpoints & Polish (20 pts)

---

## Development Commands

### 🔥 統一開發環境管理 (推薦)

本專案提供統一的開發環境管理腳本 `scripts/dev.py`，可以一次性管理所有服務：

```bash
# 查看所有服務狀態
python scripts/dev.py status

# 啟動所有服務 (Docker + Backend + Frontend)
python scripts/dev.py start

# 啟動單一服務
python scripts/dev.py start docker      # 只啟動 Docker 服務
python scripts/dev.py start backend     # 只啟動 Backend
python scripts/dev.py start frontend    # 只啟動 Frontend

# 停止服務
python scripts/dev.py stop              # 停止所有服務
python scripts/dev.py stop backend      # 只停止 Backend

# 重啟服務
python scripts/dev.py restart backend   # 重啟 Backend

# 查看日誌
python scripts/dev.py logs postgres     # 查看 PostgreSQL 日誌
python scripts/dev.py logs docker -f    # 追蹤所有 Docker 日誌

# 帶監控服務啟動 (Jaeger, Prometheus, Grafana)
python scripts/dev.py start docker --monitoring
```

**首次啟動開發環境 (Quick Start)**：
```bash
python scripts/dev.py start             # 一鍵啟動所有服務
# 或分步啟動：
python scripts/dev.py start docker      # 1. 先啟動資料庫
python scripts/dev.py start backend     # 2. 再啟動 API
python scripts/dev.py start frontend    # 3. 最後啟動前端 (可選)
```

**服務端口配置**：
| 服務 | 默認端口 | 說明 |
|------|----------|------|
| Backend | 8000 | FastAPI/Uvicorn |
| Frontend | 3005 | Vite Dev Server |
| PostgreSQL | 5432 | 資料庫 |
| Redis | 6379 | 緩存 |
| RabbitMQ | 5672 | 消息隊列 |
| RabbitMQ UI | 15672 | 管理界面 |

**自定義端口**：
```bash
python scripts/dev.py start backend --backend-port 8080
python scripts/dev.py start frontend --frontend-port 3000
```

### 傳統方式 (Manual)

如果需要更精細的控制，也可以使用傳統方式：

#### Docker 服務

```bash
# Start all services (PostgreSQL, Redis, RabbitMQ)
docker-compose up -d

# Check health
curl http://localhost:8000/health

# Stop services
docker-compose down -v
```

#### Backend (Python FastAPI)

```bash
cd backend/

# Run backend (傳統方式)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 或使用專用腳本 (解決 Windows 端口問題)
python scripts/dev_server.py start [port]
python scripts/dev_server.py stop [port]
python scripts/dev_server.py status [port]

# Code Quality
black .                              # Format
isort .                              # Sort imports
flake8 .                             # Lint
mypy .                               # Type check

# Testing
pytest                               # All tests
pytest tests/unit/                   # Unit tests only
pytest tests/unit/test_agent_service.py::test_function  # Single test
pytest -v --cov=src                  # With coverage
```

#### Frontend (React/TypeScript)

```bash
cd frontend/

# Install dependencies
npm install

# Run dev server
npm run dev

# Build
npm run build
```

#### Database

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U ipa_user -d ipa_platform

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Windows 端口問題解決方案

Windows 上 uvicorn 重啟時常遇到端口被佔用問題（TIME_WAIT 狀態），使用 `scripts/dev.py` 可以自動處理：
- 啟動前自動清理舊進程
- 智能端口選擇（如果被佔用自動選備用端口）
- PID 文件管理，支持優雅關閉
- 優雅關閉超時後強制終止

---

## Architecture

### System Overview

```
Frontend (React 18 + TypeScript)
    ↓ HTTPS (port 3000)
Backend (FastAPI, port 8000)
    ├─ 15 API Modules (agents, workflows, executions, ...)
    ├─ Domain Services (state machine, checkpoints, routing)
    └─ Infrastructure (database, cache, messaging)
    ↓
PostgreSQL 16 + Redis 7 + RabbitMQ
```

### Backend Architecture

```
backend/src/
├── api/v1/              # 20+ API route modules
│   ├── agents/          # Agent CRUD and configuration
│   ├── workflows/       # Workflow management
│   ├── executions/      # Execution lifecycle
│   ├── sessions/        # 🆕 Phase 11: Session-based conversations
│   ├── groupchat/       # GroupChat orchestration (→ Adapter)
│   ├── handoff/         # Agent handoff (→ Adapter)
│   ├── concurrent/      # Concurrent execution (→ Adapter)
│   ├── nested/          # Nested workflows (→ Adapter)
│   ├── planning/        # Dynamic planning (→ Adapter)
│   ├── code_interpreter/ # 🆕 Phase 8: Code execution
│   ├── mcp/             # 🆕 Phase 9: MCP Server management
│   ├── claude_sdk/      # 🆕 Phase 12: Claude SDK API routes
│   │   ├── routes.py         # Core SDK routes
│   │   ├── tools_routes.py   # Tool registry & execution
│   │   ├── hooks_routes.py   # Hook management
│   │   ├── mcp_routes.py     # MCP server operations
│   │   └── hybrid_routes.py  # Hybrid orchestration
│   └── ...
│
├── integrations/        # 🔑 Official API Integration Layer (Phase 4+)
│   ├── agent_framework/
│   │   ├── builders/    # Adapter implementations
│   │   │   ├── groupchat.py      # GroupChatBuilderAdapter
│   │   │   ├── handoff.py        # HandoffBuilderAdapter
│   │   │   ├── concurrent.py     # ConcurrentBuilderAdapter
│   │   │   ├── nested_workflow.py # NestedWorkflowAdapter
│   │   │   ├── planning.py       # PlanningAdapter
│   │   │   └── magentic.py       # MagenticBuilderAdapter
│   │   ├── multiturn/   # MultiTurnAdapter + CheckpointStorage
│   │   └── memory/      # Memory storage adapters
│   │
│   ├── claude_sdk/      # 🆕 Phase 12: Claude Agent SDK
│   │   ├── client.py    # ClaudeSDKClient 核心封裝
│   │   ├── query.py     # Query API 實現
│   │   ├── session.py   # Session 管理
│   │   ├── tools/       # Tool Registry & Execution
│   │   ├── hooks/       # Hook Manager & Pipeline
│   │   ├── mcp/         # MCP Integration
│   │   └── hybrid/      # Hybrid Orchestrator
│   │
│   └── mcp/             # 🆕 Phase 9-12: MCP Architecture
│       ├── core/        # MCP Core Components
│       ├── registry/    # Server Registry
│       ├── servers/     # MCP Server Implementations
│       └── security/    # Security Controls
│
├── domain/              # Business logic
│   ├── agents/          # Agent service
│   ├── workflows/       # Workflow service + state machine
│   ├── executions/      # Execution state machine
│   ├── sessions/        # 🆕 Phase 11: Agent-Session integration
│   │   ├── models.py    # Session, Message, ToolCall models
│   │   ├── service.py   # SessionService
│   │   ├── events.py    # SessionEventPublisher
│   │   ├── executor.py  # AgentExecutor (LLM interaction)
│   │   ├── streaming.py # StreamingHandler (SSE)
│   │   └── tool_handler.py # ToolCallHandler
│   ├── connectors/      # External connectors (ServiceNow, D365, SharePoint)
│   ├── audit/           # Audit & Compliance logging
│   ├── checkpoints/     # Execution checkpoints & HITL
│   ├── prompts/         # Prompt management
│   ├── templates/       # Template engine
│   ├── triggers/        # Trigger system (webhook, schedule, event)
│   ├── routing/         # Intelligent routing engine
│   ├── versioning/      # Version control for workflows/agents
│   ├── learning/        # Feedback & learning system
│   ├── notifications/   # Notification service
│   ├── devtools/        # Developer tools & debugging
│   └── orchestration/   # ⚠️ Deprecated - use adapters
│
├── infrastructure/      # External integrations
│   ├── database/        # SQLAlchemy models, repositories
│   ├── cache/           # Redis + LLM caching
│   ├── messaging/       # RabbitMQ integration
│   └── storage/         # File storage
│
└── core/               # Cross-cutting concerns
    ├── config.py       # Settings management
    ├── performance/    # Performance monitoring
    └── security/       # Security controls
```

### Key Adapters (Phase 4-12)

| Adapter | Purpose | Official API |
|---------|---------|--------------|
| `GroupChatBuilderAdapter` | Multi-agent chat | `GroupChatBuilder` |
| `HandoffBuilderAdapter` | Agent handoff | `HandoffBuilder` |
| `ConcurrentBuilderAdapter` | Parallel execution | `ConcurrentBuilder` |
| `NestedWorkflowAdapter` | Nested workflows | `WorkflowExecutor` |
| `PlanningAdapter` | Task planning | `MagenticBuilder` |
| `MultiTurnAdapter` | Conversation state | `CheckpointStorage` |
| `SessionAgentBridge` | Agent-Session integration | `AgentExecutor` |
| `CodeInterpreterAdapter` | Code execution | `Responses API` |
| **Phase 12: Claude Agent SDK** | | |
| `ClaudeSDKClient` | Claude SDK 核心封裝 | Claude Agent SDK |
| `ToolRegistry` | Tool 註冊與管理 | SDK Tools API |
| `HookManager` | Hook 生命週期管理 | SDK Hooks API |
| `MCPServerManager` | MCP Server 管理 | MCP Protocol |
| `HybridOrchestrator` | 混合編排 (Agent + Claude) | Custom Integration |
| **Phase 13-14: Hybrid Architecture** | | |
| `IntentRouter` | 智能意圖路由 (Workflow/Chat 模式判斷) | Custom + LLM |
| `ContextBridge` | MAF ↔ Claude 上下文同步 | Custom Integration |
| `UnifiedToolExecutor` | 統一 Tool 執行層 | Claude SDK Tools |
| `HybridOrchestratorV2` | 進階混合編排器 | MAF + Claude SDK |
| `RiskAssessmentEngine` | 風險評估引擎 (驅動 HITL) | Custom + LLM |
| `ModeSwitcher` | 動態模式切換 (Workflow ↔ Chat) | Custom Integration |
| `UnifiedCheckpointStorage` | 統一 Checkpoint 管理 | Redis + PostgreSQL |
| **Phase 15: AG-UI Protocol** | | |
| `HybridEventBridge` | Hybrid → AG-UI 事件轉換 | AG-UI Protocol |
| `ThreadManager` | 對話線程狀態管理 | AG-UI Threads |
| `AgenticChatHandler` | Agentic Chat 功能 | AG-UI Feature 1 |
| `ToolRenderingHandler` | 工具結果渲染 | AG-UI Feature 2 |
| `HITLHandler` | Human-in-the-Loop 審批 | AG-UI Feature 3 |
| `GenerativeUIHandler` | 動態 UI 生成 | AG-UI Feature 4 |
| `ToolBasedUIHandler` | Tool-based 動態 UI | AG-UI Feature 5 |
| `SharedStateHandler` | 前後端狀態同步 | AG-UI Feature 6 |
| `PredictiveStateHandler` | 樂觀更新與預測狀態 | AG-UI Feature 7 |

### Frontend Architecture

```
frontend/src/
├── pages/              # 7 main pages
│   ├── Dashboard.tsx
│   ├── Workflows.tsx
│   ├── Agents.tsx
│   ├── Executions.tsx
│   ├── Templates.tsx
│   ├── Analytics.tsx
│   └── Settings.tsx
│
├── components/         # Reusable UI components
├── api/               # API client
├── store/             # Zustand state management
├── hooks/             # Custom React hooks
└── types/             # TypeScript definitions
```

### Key Design Patterns

1. **Adapter Pattern** (Phase 4): All orchestration via official Agent Framework adapters
2. **Execution State Machine**: Workflows go through states (pending → running → waiting_approval → completed/failed)
3. **Checkpoint System**: Human-in-the-loop approvals with timeout and escalation
4. **LLM Cache**: Redis-based caching for repeated LLM calls
5. **Connector Pattern**: Pluggable external system integrations (ServiceNow, Dynamics 365)
6. **Hybrid Architecture** (Phase 13-14): MAF + Claude SDK intelligent routing and mode switching
7. **AG-UI Protocol** (Phase 15): SSE-based real-time UI updates with optimistic concurrency control

### Phase 13-14: Hybrid MAF + Claude SDK Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │Intent Router│───→│HybridOrchest.│───→│ Risk Assessor │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                    │            │
│         ▼                  ▼                    ▼            │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │Mode Switcher│    │Context Bridge│    │Unified Chkpt  │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              Unified Tool Executor                       │ │
│  └─────────────────────────────────────────────────────────┘ │
│         │                                │                   │
│         ▼                                ▼                   │
│  ┌─────────────────┐            ┌───────────────────┐       │
│  │MAF Adapters     │            │Claude SDK         │       │
│  │ - GroupChat     │            │ - ClaudeSDKClient │       │
│  │ - Handoff       │            │ - ToolRegistry    │       │
│  │ - Concurrent    │            │ - HookManager     │       │
│  │ - Nested        │            │ - MCP Integration │       │
│  └─────────────────┘            └───────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Phase 13 Core Components** (105 pts, Sprints 52-54):
- **Intent Router**: Intelligent routing - Workflow Mode vs Chat Mode detection
- **Context Bridge**: MAF ↔ Claude bidirectional state synchronization
- **Unified Tool Executor**: All tools executed through Claude SDK
- **HybridOrchestrator V2**: Enhanced orchestrator with mode-aware execution

**Phase 14 Advanced Features** (95 pts, Sprints 55-57):
- **Risk Assessment Engine**: Risk-driven HITL (Human-in-the-Loop) decisions
- **Mode Switcher**: Dynamic Workflow ↔ Chat mode switching
- **Unified Checkpoint**: Cross-framework state persistence and recovery

**Execution Modes**:
- `WORKFLOW_MODE`: Multi-step structured workflows via MAF adapters
- `CHAT_MODE`: Conversational interaction via Claude SDK
- `HYBRID_MODE`: Combined mode with intelligent routing

### Phase 15: AG-UI Protocol Integration

```
┌─────────────────────────────────────────────────────────────┐
│                   Frontend (React)                           │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │  useAGUI    │    │useSharedState│    │useOptimistic  │   │
│  │  Hook       │    │    Hook      │    │  State Hook   │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                    │            │
│         ▼                  ▼                    ▼            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              SSE Event Stream                            │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ POST /api/v1/ag-ui (SSE)
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend                            │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │  AG-UI API  │───→│HybridEvent   │───→│ Thread        │   │
│  │  Routes     │    │   Bridge     │    │ Manager       │   │
│  └─────────────┘    └──────────────┘    └───────────────┘   │
│         │                  │                                 │
│         ▼                  ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              AG-UI Feature Handlers                      │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │ │
│  │  │ Agentic  │ │  Tool    │ │  HITL    │ │Generative│    │ │
│  │  │  Chat    │ │ Render   │ │ Handler  │ │   UI     │    │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                 │ │
│  │  │ Tool-UI  │ │ Shared   │ │Predictive│                 │ │
│  │  │ Handler  │ │ State    │ │  State   │                 │ │
│  │  └──────────┘ └──────────┘ └──────────┘                 │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │           HybridOrchestrator V2 (Phase 13-14)           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Phase 15 Features** (85 pts, Sprints 58-60):
- **Sprint 58**: AG-UI Core Infrastructure (30 pts)
  - SSE Endpoint with StreamingResponse
  - HybridEventBridge (Hybrid → AG-UI event conversion)
  - ThreadManager (thread state + Redis cache)
  - AG-UI Event Types (15 event types)
- **Sprint 59**: AG-UI Basic Features 1-4 (28 pts)
  - Agentic Chat (message streaming)
  - Tool Rendering (result type detection + formatting)
  - Human-in-the-Loop (risk-based approval)
  - Generative UI (progress + mode switch)
- **Sprint 60**: AG-UI Advanced Features 5-7 (27 pts)
  - Tool-based Dynamic UI (form, chart, card, table)
  - Shared State (snapshot + delta sync)
  - Predictive State Updates (optimistic concurrency)

**AG-UI Event Types**:
- Lifecycle: `RUN_STARTED`, `RUN_FINISHED`, `RUN_ERROR`
- Messages: `TEXT_MESSAGE_START`, `TEXT_MESSAGE_CONTENT`, `TEXT_MESSAGE_END`
- Tools: `TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`
- State: `STATE_SNAPSHOT`, `STATE_DELTA`, `CUSTOM`

---

## Code Standards (代碼規範)

本專案的代碼規範標準，確保代碼一致性和可維護性。

### 1. Python 檔案標頭規範

每個 Python 檔案必須包含標準標頭註釋：

```python
# =============================================================================
# IPA Platform - {模組名稱}
# =============================================================================
# Sprint {N}: {Sprint 名稱}
# Sprint {M}: {相關更新描述}
#
# {檔案功能描述}
# {可選：架構說明或重要注意事項}
#
# Dependencies:
#   - {依賴模組1} (src.path.to.module)
#   - {依賴模組2} (src.path.to.module)
# =============================================================================
```

**範例**：
```python
# =============================================================================
# IPA Platform - Agent Service
# =============================================================================
# Sprint 1: Core Engine - Agent Framework Integration
# Sprint 31: S31-2 - 遷移至使用 AgentExecutorAdapter
#
# Core service for Agent Framework operations.
# Handles agent creation, execution, and LLM interaction.
#
# 架構更新 (Sprint 31):
#   - 所有官方 Agent Framework API 導入已移至 AgentExecutorAdapter
#
# Dependencies:
#   - AgentExecutorAdapter (src.integrations.agent_framework.builders)
# =============================================================================
```

### 2. Python Docstring 規範 (Google Style)

#### Class Docstring
```python
class AgentService:
    """
    Core service for Agent Framework operations.

    Handles agent creation, execution, and LLM interaction through
    the official Agent Framework adapters.

    Attributes:
        db: Database session for persistence
        executor_adapter: Adapter for agent execution
        config: Service configuration settings

    Example:
        >>> service = AgentService(db_session)
        >>> agent = service.create_agent(config)
        >>> result = service.execute(agent.id, input_data)
    """
```

#### Function/Method Docstring
```python
def create_agent(
    self,
    config: AgentConfig,
    *,
    validate: bool = True
) -> Agent:
    """
    Create a new agent with the specified configuration.

    Creates and persists a new agent instance using the provided
    configuration. Optionally validates the configuration before creation.

    Args:
        config: Agent configuration containing name, type, and settings.
        validate: Whether to validate config before creation. Defaults to True.

    Returns:
        The newly created Agent instance with assigned ID.

    Raises:
        ValidationError: If config validation fails and validate=True.
        DuplicateAgentError: If an agent with the same name already exists.
        DatabaseError: If persistence operation fails.

    Example:
        >>> config = AgentConfig(name="assistant", type="chat")
        >>> agent = service.create_agent(config)
        >>> print(agent.id)  # uuid4 string
    """
```

### 3. 命名規範

| 類型 | 規範 | 範例 |
|------|------|------|
| **檔案名** | snake_case | `agent_service.py`, `workflow_executor.py` |
| **類別名** | PascalCase | `AgentService`, `WorkflowExecutor` |
| **函數/方法** | snake_case | `create_agent()`, `execute_workflow()` |
| **變數** | snake_case | `agent_config`, `execution_result` |
| **常數** | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT` |
| **慣例私有** | _single_prefix | `_internal_state`, `_validate()` (慣例上不應外部存取) |
| **Name Mangling** | __double_prefix | `__secret_key` (Python 會改名防止子類覆蓋) |
| **Type Variables** | PascalCase + T suffix | `AgentT`, `ResultT` |
| **Protocols** | PascalCase + Protocol suffix | `ExecutorProtocol` |
| **Enums** | PascalCase (class), UPPER_SNAKE (members) | `class Status:`, `PENDING = "pending"` |

### 4. Python Type Hints 規範

#### 必須使用類型標註的情況
```python
# ✅ 公開函數必須有完整類型標註
def get_agent(self, agent_id: str) -> Optional[Agent]:
    ...

# ✅ 類別屬性必須標註類型
class AgentService:
    db: Session
    config: ServiceConfig
    _cache: Dict[str, Agent]

# ✅ 複雜返回類型使用 TypedDict 或 dataclass
@dataclass
class ExecutionResult:
    success: bool
    output: Any
    duration_ms: int
    error: Optional[str] = None
```

#### 常用類型模式
```python
from typing import Optional, List, Dict, Any, Union, Callable, TypeVar, Generic
from typing import Literal, TypedDict, Protocol
from collections.abc import Sequence, Mapping, Iterable

# Optional 用於可能為 None 的值
def find_agent(self, name: str) -> Optional[Agent]: ...

# Union 用於多種可能的類型
def process(self, data: Union[str, bytes]) -> Result: ...

# Literal 用於特定值集合
Status = Literal["pending", "running", "completed", "failed"]

# Callable 用於函數參數
def register_callback(self, callback: Callable[[Event], None]) -> None: ...

# Generic 用於泛型類別
T = TypeVar("T")
class Repository(Generic[T]):
    def get_by_id(self, id: str) -> Optional[T]: ...
```

### 5. Import 順序規範

```python
# 1. 標準庫 (Standard library)
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# 2. 第三方套件 (Third-party packages)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

# 3. 本地模組 (Local imports)
from src.core.config import settings
from src.core.logging import get_logger
from src.domain.agents.service import AgentService
from src.infrastructure.database import get_db
```

### 6. API 設計規範 (FastAPI)

#### RESTful 路由命名
| 操作 | Method | Route Pattern | 範例 |
|------|--------|---------------|------|
| 列表 | GET | `/api/v1/{resources}` | `/api/v1/agents` |
| 單一 | GET | `/api/v1/{resources}/{id}` | `/api/v1/agents/{id}` |
| 建立 | POST | `/api/v1/{resources}` | `/api/v1/agents` |
| 更新 | PUT | `/api/v1/{resources}/{id}` | `/api/v1/agents/{id}` |
| 刪除 | DELETE | `/api/v1/{resources}/{id}` | `/api/v1/agents/{id}` |
| 動作 | POST | `/api/v1/{resources}/{id}/{action}` | `/api/v1/agents/{id}/execute` |

#### Route 結構範本
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.domain.agents.service import AgentService
from . import schemas

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", response_model=list[schemas.AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> list[schemas.AgentResponse]:
    """List all agents with pagination."""
    service = AgentService(db)
    return service.get_all(skip=skip, limit=limit)


@router.post("/", response_model=schemas.AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: schemas.AgentCreate,
    db: Session = Depends(get_db)
) -> schemas.AgentResponse:
    """Create a new agent."""
    service = AgentService(db)
    return service.create(data)
```

#### Response 格式規範
```python
# 成功回應 - 單一物件
{"id": "uuid", "name": "Agent Name", "created_at": "2025-12-27T10:00:00Z"}

# 成功回應 - 列表 (含分頁)
{
    "data": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
}

# 錯誤回應
{
    "error": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {"field": "name", "issue": "Field is required"}
}
```

### 7. 資料庫規範 (SQLAlchemy 2.0)

#### Model 結構範本 (使用新式 Mapped + mapped_column)
```python
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.infrastructure.database import Base


class AgentModel(Base):
    """
    Agent database model.

    Table: agents

    Attributes:
        id: Primary key (UUID)
        name: Agent display name
        type: Agent type classification
        config: JSON configuration
    """
    __tablename__ = "agents"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Required fields
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Optional fields
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Timestamps (必須)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    executions: Mapped[list["ExecutionModel"]] = relationship(
        "ExecutionModel", back_populates="agent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name})>"
```

#### Repository Pattern
```python
class AgentRepository(BaseRepository[AgentModel]):
    """Repository for Agent model with custom queries."""

    def __init__(self, db: Session):
        super().__init__(db, AgentModel)

    def get_by_type(self, agent_type: str) -> list[AgentModel]:
        """Get all agents of a specific type."""
        return self.db.query(self.model).filter(
            self.model.type == agent_type
        ).all()
```

### 8. Pydantic Schema 規範

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AgentBase(BaseModel):
    """Base schema with common fields."""
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: Optional[str] = Field(None, max_length=500)


class AgentCreate(AgentBase):
    """Schema for creating new agent."""
    type: str = Field(..., description="Agent type")
    config: Optional[dict] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Schema for updating agent (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    config: Optional[dict] = None


class AgentResponse(AgentBase):
    """Schema for API response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    created_at: datetime
    updated_at: datetime
```

### 9. 錯誤處理規範

```python
from fastapi import HTTPException, status

# 使用 HTTPException 的標準方式
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail="Agent not found"
)

# 自定義錯誤格式
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={
        "error": "VALIDATION_ERROR",
        "message": "Invalid configuration",
        "details": {"field": "timeout", "issue": "Must be positive integer"}
    }
)

# 業務邏輯錯誤
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Cannot delete agent with active workflows"
)
```

### 10. 工具與品質檢查

| 工具 | 用途 | 設定 |
|------|------|------|
| **Black** | 代碼格式化 | line-length: 100 |
| **isort** | Import 排序 | profile: black |
| **flake8** | 代碼檢查 | max-line-length: 100 |
| **mypy** | 類型檢查 | strict mode |
| **pytest** | 測試框架 | coverage >= 80% |

```bash
# 完整品質檢查命令
cd backend && black . && isort . && flake8 . && mypy . && pytest
```

### 11. TypeScript/Frontend 規範

#### 命名規範
| 類型 | 規範 | 範例 |
|------|------|------|
| **組件檔案** | PascalCase.tsx | `AgentCard.tsx`, `WorkflowList.tsx` |
| **工具/Hook** | camelCase.ts | `useAgents.ts`, `apiClient.ts` |
| **類型檔案** | camelCase.ts | `agent.types.ts`, `workflow.ts` |
| **組件名** | PascalCase | `AgentCard`, `WorkflowEditor` |
| **Props 介面** | {Component}Props | `AgentCardProps`, `ButtonProps` |
| **Hook** | use{Name} | `useAgents()`, `useWorkflow()` |
| **Handler** | handle{Action} | `handleSubmit`, `handleDelete` |
| **Boolean** | is/has/can prefix | `isLoading`, `hasError`, `canEdit` |

#### React 組件規範
```tsx
// 組件結構順序
interface AgentCardProps {
  agent: Agent;
  onEdit?: (id: string) => void;
}

export function AgentCard({ agent, onEdit }: AgentCardProps) {
  // 1. Hooks (useState, useEffect, custom hooks)
  const [isOpen, setIsOpen] = useState(false);

  // 2. Handlers
  const handleClick = () => setIsOpen(true);

  // 3. Render
  return <div onClick={handleClick}>{agent.name}</div>;
}
```

#### 狀態管理 (Zustand)
```tsx
// stores/agentStore.ts
interface AgentState {
  agents: Agent[];
  isLoading: boolean;
  fetchAgents: () => Promise<void>;
}

export const useAgentStore = create<AgentState>((set) => ({
  agents: [],
  isLoading: false,
  fetchAgents: async () => {
    set({ isLoading: true });
    const agents = await api.getAgents();
    set({ agents, isLoading: false });
  },
}));
```

#### 樣式規範 (Tailwind + Shadcn)
```tsx
// ✅ 使用 Tailwind 類別
<Button className="bg-primary hover:bg-primary/90">Submit</Button>

// ✅ 使用 cn() 合併類別
<div className={cn("p-4 rounded-lg", isActive && "bg-accent")} />

// ❌ 避免 inline styles
<div style={{ padding: 16 }} />  // 不推薦
```

#### 工具配置
| 工具 | 用途 |
|------|------|
| **Prettier** | 代碼格式化 |
| **ESLint** | 代碼檢查 |
| **TypeScript** | 類型檢查 (strict mode) |

```bash
# 前端品質檢查
cd frontend && npm run lint && npm run build
```

### 12. Git Commit 規範

```
<type>(<scope>): <description>

[optional body]

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修復 |
| `docs` | 文檔更新 |
| `refactor` | 重構 (不改變功能) |
| `test` | 測試相關 |
| `chore` | 維護性工作 |

| Scope | 範圍 |
|-------|------|
| `api` | API 路由層 |
| `domain` | 業務邏輯層 |
| `infra` | 基礎設施層 |
| `integrations` | 整合層 |
| `frontend` | 前端 |
| `sprint-N` | Sprint 相關變更 |

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
REDIS_PASSWORD=redis_password

# Azure OpenAI (for Agent Framework)
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
| `claudedocs/AI-ASSISTANT-INSTRUCTIONS.md` | AI workflow instructions |
| `docs/03-implementation/sprint-planning/README.md` | Sprint planning overview (Phase 1-16) |
| `docs/03-implementation/sprint-planning/phase-13/README.md` | Phase 13: Hybrid Core Architecture |
| `docs/03-implementation/sprint-planning/phase-14/README.md` | Phase 14: Advanced Hybrid Features |
| `docs/03-implementation/sprint-planning/phase-15/README.md` | Phase 15: AG-UI Protocol Integration |
| `docs/03-implementation/sprint-planning/phase-16/README.md` | Phase 16: Unified Agentic Chat Interface |
| `docs/api/ag-ui-api-reference.md` | AG-UI API Reference |
| `docs/guides/ag-ui-integration-guide.md` | AG-UI Integration Guide |

---

## AI Assistant System (v4.1.0)

This project includes AI-assisted development workflows in `claudedocs/6-ai-assistant/prompts/`:

### 情況指引 (SITUATION Guide) - 5 Core Situations

| 情況 | 檔案名稱 | 用途 |
|------|----------|------|
| **SITUATION-1** | PROJECT-ONBOARDING | 專案入門 - 新會話開始、了解專案全貌 |
| **SITUATION-2** | FEATURE-DEV-PREP | 開發準備 - 任務前的分析與規劃 |
| **SITUATION-3** | FEATURE-ENHANCEMENT | 舊功能進階/修正 - Bug 修復、重構 |
| **SITUATION-4** | NEW-FEATURE-DEV | 新功能開發 - 全新功能實施 |
| **SITUATION-5** | SAVE-PROGRESS | 保存進度 - 提交代碼、更新文檔 |

### Usage
```bash
# 新會話開始
"請閱讀 SITUATION-1-PROJECT-ONBOARDING.md 並執行"

# 新功能開發
"請閱讀 SITUATION-4-NEW-FEATURE-DEV.md 並執行"

# 修改現有功能
"請閱讀 SITUATION-3-FEATURE-ENHANCEMENT.md 並執行"

# 保存進度
"請閱讀 SITUATION-5-SAVE-PROGRESS.md 並執行"
```

Full instructions: `claudedocs/6-ai-assistant/prompts/README.md`

---

## Developer Preferences

### Communication
- **Language**: Respond in Traditional Chinese
- **Detail Level**: Provide detailed explanations including reasoning and alternatives
- **Confirmation**: Ask before destructive operations (delete, refactor, etc.)

### Code Style
- **Comments**: Mixed mode - important explanations in Chinese, short comments in English
- **Git Commit**: Commit only when feature is complete, avoid small scattered commits
- **Testing**: New features must include unit tests

### Behavior Rules
- ✅ **Proactive Assistance**: Actively participate in development, suggest improvements when found
- ✅ **Ask Before Acting**: When uncertain, always ask before executing
- ✅ **Deep Error Analysis**: Analyze root cause thoroughly, provide multiple solutions
- ❌ **Never Delete Tests**: Do not delete or skip tests to solve problems
- ❌ **Never Delete Docs**: Do not delete documentation files without asking first

### Developer Context
- **Skill Level**: Full Stack (proficient in both frontend and backend)
- **Dependencies**: May introduce new dependencies if they significantly improve efficiency

---

## CRITICAL: Microsoft Agent Framework API Usage

**This is the most important rule for this project.**

### MUST Use Official API

When developing in `backend/src/integrations/agent_framework/builders/`, you **MUST**:

1. **Import official classes from `agent_framework`**:
```python
from agent_framework import (
    ConcurrentBuilder,      # for concurrent.py
    GroupChatBuilder,       # for groupchat.py
    HandoffBuilder,         # for handoff.py
    MagenticBuilder,        # for magentic.py
    WorkflowExecutor,       # for workflow_executor.py
)
```

2. **Use official Builder instance in adapter class**:
```python
class XxxBuilderAdapter:
    def __init__(self, ...):
        self._builder = OfficialBuilder()  # MUST have this line
```

3. **Call official Builder in build() method**:
```python
def build(self) -> Workflow:
    return self._builder.participants(...).build()  # MUST call official API
```

### DO NOT

- ❌ Do NOT create your own implementation without using `agent_framework` imports
- ❌ Do NOT skip `from agent_framework import ...` statements
- ❌ Do NOT implement similar functionality without calling official API

### Verification

Before completing any adapter work, run:
```bash
cd backend
python scripts/verify_official_api_usage.py
```

All checks must pass (5/5).

### Reference

- Official source code: `reference/agent-framework/python/packages/core/agent_framework/`
- Workflow checklist: `docs/03-implementation/sprint-planning/phase-3/SPRINT-WORKFLOW-CHECKLIST.md`

---

## Important Notes

1. **Agent Framework is Preview**: API may change. Reference docs in `reference/agent-framework/`

2. **Chinese Documentation**: Target market is Taiwan/Hong Kong. Technical terms in English, comments in Traditional Chinese.

3. **BMAD Methodology**: Project follows BMad Agile Development workflow. Track status in `docs/bmm-workflow-status.yaml`

4. **No sprint-status.yaml**: This file was removed. Use `bmm-workflow-status.yaml` for workflow tracking.

---

**Last Updated**: 2026-01-07
**Project Start**: 2025-11-14
**Status**: Phase 16 Planning (60 Sprints completed) - Unified Agentic Chat Interface
**Total Story Points**: 1455 pts across 15 phases (completed)
**Current Phase**: Phase 16 - Unified Agentic Chat Interface (~100 pts, Sprints 62-65)

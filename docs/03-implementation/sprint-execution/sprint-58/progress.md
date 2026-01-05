# Sprint 58 Progress: AG-UI Core Infrastructure

> **Phase 15**: AG-UI Protocol Integration
> **Sprint 目標**: 建立 AG-UI 協議的核心基礎設施，包含 SSE 端點、事件橋接器、線程管理和事件類型定義

---

## Sprint 概述

| 屬性 | 值 |
|------|-----|
| Sprint 編號 | 58 |
| 計劃點數 | 30 Story Points |
| 開始日期 | 2026-01-05 |
| 前置條件 | Phase 14 完成、HybridOrchestratorV2 可用 |

---

## Story 進度

| Story | 名稱 | 點數 | 狀態 | 進度 |
|-------|------|------|------|------|
| S58-4 | AG-UI Event Types | 5 | ✅ 完成 | 100% |
| S58-3 | Thread Manager | 5 | ✅ 完成 | 100% |
| S58-2 | HybridEventBridge | 10 | 🔄 進行中 | 0% |
| S58-1 | AG-UI SSE Endpoint | 10 | ⏳ 待開始 | 0% |

**總進度**: 10/30 pts (33%)

---

## 實施順序

根據依賴關係，建議實施順序：

1. **S58-4** (5 pts) - AG-UI Event Types (無依賴，純定義)
2. **S58-3** (5 pts) - Thread Manager (獨立模組)
3. **S58-2** (10 pts) - HybridEventBridge (依賴 S58-4, HybridOrchestratorV2)
4. **S58-1** (10 pts) - AG-UI SSE Endpoint (依賴 S58-2, S58-3, S58-4)

---

## 檔案結構

```
backend/src/
├── api/v1/ag_ui/
│   ├── __init__.py              # S58-1
│   ├── routes.py                # S58-1, S58-3
│   ├── schemas.py               # S58-1
│   └── dependencies.py          # S58-1
│
└── integrations/ag_ui/
    ├── __init__.py              # S58-2
    ├── bridge.py                # S58-2
    ├── converters.py            # S58-2
    ├── events/
    │   ├── __init__.py          # S58-4
    │   ├── base.py              # S58-4
    │   ├── lifecycle.py         # S58-4
    │   ├── message.py           # S58-4
    │   ├── tool.py              # S58-4
    │   └── state.py             # S58-4
    └── thread/
        ├── __init__.py          # S58-3
        ├── models.py            # S58-3
        ├── manager.py           # S58-3
        └── storage.py           # S58-3

backend/tests/unit/
├── api/v1/ag_ui/
│   └── test_routes.py           # S58-1
└── integrations/ag_ui/
    ├── test_bridge.py           # S58-2
    ├── test_converters.py       # S58-2
    ├── events/
    │   ├── test_base.py         # S58-4
    │   ├── test_message.py      # S58-4
    │   └── test_tool.py         # S58-4
    └── thread/
        ├── test_manager.py      # S58-3
        └── test_storage.py      # S58-3
```

---

## 詳細進度記錄

### S58-4: AG-UI Event Types (5 pts)

**狀態**: ✅ 完成

**檔案**:
- [x] `backend/src/integrations/ag_ui/events/__init__.py`
- [x] `backend/src/integrations/ag_ui/events/base.py`
- [x] `backend/src/integrations/ag_ui/events/lifecycle.py`
- [x] `backend/src/integrations/ag_ui/events/message.py`
- [x] `backend/src/integrations/ag_ui/events/tool.py`
- [x] `backend/src/integrations/ag_ui/events/state.py`

**測試**:
- [x] `backend/tests/unit/integrations/ag_ui/events/test_base.py` (13 tests)
- [x] `backend/tests/unit/integrations/ag_ui/events/test_lifecycle.py` (12 tests)
- [x] `backend/tests/unit/integrations/ag_ui/events/test_message.py` (14 tests)
- [x] `backend/tests/unit/integrations/ag_ui/events/test_tool.py` (17 tests)
- [x] `backend/tests/unit/integrations/ag_ui/events/test_state.py` (17 tests)

**測試結果**: 73 tests passed ✅

**關鍵組件**:
- `AGUIEventType` 枚舉 (11 種事件類型)
- `BaseAGUIEvent` 基類
- `RunStartedEvent` / `RunFinishedEvent` (生命週期)
- `TextMessageStartEvent` / `TextMessageContentEvent` / `TextMessageEndEvent` (訊息)
- `ToolCallStartEvent` / `ToolCallArgsEvent` / `ToolCallEndEvent` (工具)
- `StateSnapshotEvent` / `StateDeltaEvent` / `CustomEvent` (狀態)

---

### S58-3: Thread Manager (5 pts)

**狀態**: ✅ 完成

**檔案**:
- [x] `backend/src/integrations/ag_ui/thread/__init__.py`
- [x] `backend/src/integrations/ag_ui/thread/models.py`
- [x] `backend/src/integrations/ag_ui/thread/manager.py`
- [x] `backend/src/integrations/ag_ui/thread/storage.py`

**測試**:
- [x] `backend/tests/unit/integrations/ag_ui/thread/test_models.py` (23 tests)
- [x] `backend/tests/unit/integrations/ag_ui/thread/test_storage.py` (24 tests)
- [x] `backend/tests/unit/integrations/ag_ui/thread/test_manager.py` (42 tests)

**測試結果**: 89 tests passed ✅

**關鍵組件**:
- `AGUIThread` dataclass (lifecycle management, state, messages)
- `AGUIMessage` dataclass (role, content, tool_calls, serialization)
- `ThreadStatus` 枚舉 (ACTIVE, IDLE, ARCHIVED, DELETED)
- `MessageRole` 枚舉 (USER, ASSISTANT, SYSTEM, TOOL)
- `ThreadManager` 類別 (get_or_create, append_messages, update_state, archive, delete)
- `ThreadCache` 類別 (Write-Through caching)
- `ThreadRepository` 抽象類別 + `InMemoryThreadRepository` 實現
- `CacheProtocol` + `InMemoryCache` 實現
- Pydantic schemas: `AGUIThreadSchema`, `AGUIMessageSchema`

---

### S58-2: HybridEventBridge (10 pts)

**狀態**: ⏳ 待開始

**檔案**:
- [ ] `backend/src/integrations/ag_ui/__init__.py`
- [ ] `backend/src/integrations/ag_ui/bridge.py`
- [ ] `backend/src/integrations/ag_ui/converters.py`

**測試**:
- [ ] `backend/tests/unit/integrations/ag_ui/test_bridge.py`
- [ ] `backend/tests/unit/integrations/ag_ui/test_converters.py`

**關鍵組件**:
- `HybridEventBridge` 類別 (stream_events, _format_sse)
- `EventConverters` 類別 (convert, to_run_started, to_run_finished, to_text_message_*, to_tool_call_*)

**Event Mapping**:
| Hybrid Event | AG-UI Event |
|--------------|-------------|
| `execution_started` | `RunStartedEvent` |
| `execution_completed` | `RunFinishedEvent` |
| `message_start` | `TextMessageStartEvent` |
| `message_chunk` | `TextMessageContentEvent` |
| `message_end` | `TextMessageEndEvent` |
| `tool_call_start` | `ToolCallStartEvent` |
| `tool_call_args` | `ToolCallArgsEvent` |
| `tool_call_end` | `ToolCallEndEvent` |

---

### S58-1: AG-UI SSE Endpoint (10 pts)

**狀態**: ⏳ 待開始

**檔案**:
- [ ] `backend/src/api/v1/ag_ui/__init__.py`
- [ ] `backend/src/api/v1/ag_ui/routes.py`
- [ ] `backend/src/api/v1/ag_ui/schemas.py`
- [ ] `backend/src/api/v1/ag_ui/dependencies.py`
- [ ] 修改 `backend/src/api/v1/__init__.py` 註冊 router

**測試**:
- [ ] `backend/tests/unit/api/v1/ag_ui/test_routes.py`

**API 端點**:
- `POST /api/v1/ag-ui` - 主 SSE 端點
- `GET /api/v1/ag-ui/threads/{thread_id}` - 獲取 Thread
- `DELETE /api/v1/ag-ui/threads/{thread_id}` - 刪除 Thread

---

## 備註

- 依賴 Phase 13 的 `HybridOrchestratorV2` (Sprint 54)
- Redis Cache 和 PostgreSQL 已在 Phase 1/11 完成
- AG-UI 協議參考: CopilotKit AG-UI Specification

---

**更新日期**: 2026-01-05
**Sprint 狀態**: 🔄 進行中

# Phase 11: Agent-Session Integration Tests

> **Phase 11**: Agent-Session Integration (90 Story Points)
> **Sprints**: 45-47
> **Focus**: Session-Agent Bridge, Tool Execution, Approval Workflow, Streaming

---

## Overview

Phase 11 整合 Session 與 Agent 系統，實現：
- 對話式 AI 互動
- 工具調用與審批流程
- 即時串流回應
- 錯誤處理與恢復

### 核心組件

```
┌─────────────────────────────────────────────────────────────────┐
│                    Session-Agent Integration                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Session    │────│   Bridge     │────│    Agent     │      │
│  │   Manager    │    │   Service    │    │   Executor   │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         │                   │                   │               │
│  ┌──────┴──────┐    ┌──────┴──────┐    ┌──────┴──────┐        │
│  │  Messages   │    │  Tool Call  │    │  Streaming  │        │
│  │   Store     │    │   Handler   │    │   Handler   │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                            │                                    │
│                     ┌──────┴──────┐                            │
│                     │  Approval   │                            │
│                     │   Manager   │                            │
│                     └─────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Test Scenarios

### Scenario 1: Tool Execution Flow (scenario_tool_execution.py)

測試工具調用的完整流程：

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create session with agent | Session created with agent_id |
| 2 | Send message requesting calculation | Tool call triggered |
| 3 | Execute tool (auto-approve) | Tool result returned |
| 4 | Verify tool result in message | Result integrated in response |
| 5 | Send follow-up question | Context maintained |
| 6 | End session | Session status = ENDED |

### Scenario 2: Streaming Response (scenario_streaming.py)

測試 SSE 串流回應：

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create session | Session active |
| 2 | Send message with stream=true | SSE connection opened |
| 3 | Receive stream chunks | Multiple text_delta events |
| 4 | Receive completion | done event received |
| 5 | Verify final message | Complete message in history |

### Scenario 3: Approval Workflow (scenario_approval_workflow.py)

測試人工審批流程：

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create session with approval_mode | Session configured |
| 2 | Send message triggering tool | Tool call pending approval |
| 3 | List pending approvals | Approval request visible |
| 4 | Approve tool execution | Tool executed |
| 5 | Reject another tool call | Tool execution cancelled |
| 6 | Verify approval history | All decisions recorded |

### Scenario 4: Error Recovery (scenario_error_recovery.py)

測試錯誤處理與恢復：

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create session | Session active |
| 2 | Trigger LLM timeout | Error event generated |
| 3 | Verify error handling | Session still active |
| 4 | Retry message | Successful response |
| 5 | Trigger tool error | Tool error handled |
| 6 | Recovery continues | Session recoverable |

---

## API Endpoints

### Session Chat Endpoints

```
POST   /api/v1/sessions/{session_id}/chat          # Send chat message
GET    /api/v1/sessions/{session_id}/chat/stream   # SSE stream endpoint
```

### Tool & Approval Endpoints

```
GET    /api/v1/sessions/{session_id}/tool-calls              # List tool calls
GET    /api/v1/sessions/{session_id}/approvals               # List pending approvals
POST   /api/v1/sessions/{session_id}/approvals/{id}/approve  # Approve tool
POST   /api/v1/sessions/{session_id}/approvals/{id}/reject   # Reject tool
```

### WebSocket Endpoint

```
WS     /api/v1/sessions/{session_id}/ws    # Real-time communication
```

---

## Execution

### Run All Scenarios

```bash
cd scripts/uat/phase_tests/phase_11_agent_session_integration
python phase_11_agent_session_test.py
```

### Run Specific Scenario

```bash
python phase_11_agent_session_test.py --scenario tool_execution
python phase_11_agent_session_test.py --scenario streaming
python phase_11_agent_session_test.py --scenario approval_workflow
python phase_11_agent_session_test.py --scenario error_recovery
```

### With Real LLM

```bash
# Ensure environment variables are set
export AZURE_OPENAI_ENDPOINT="https://xxx.openai.azure.com/"
export AZURE_OPENAI_API_KEY="xxx"
export AZURE_OPENAI_DEPLOYMENT_NAME="gpt-5.2"

python phase_11_agent_session_test.py --real-llm
```

---

## Output

測試結果保存為 JSON 格式：

```
phase_11_agent_session_integration/
├── phase_11_agent_session_test_YYYYMMDD_HHMMSS.json
└── logs/
    ├── tool_execution.log
    ├── streaming.log
    └── approval_workflow.log
```

### Result Schema

```json
{
  "phase": "Phase 11: Agent-Session Integration",
  "timestamp": "2025-12-24T10:30:00",
  "scenarios": [
    {
      "name": "tool_execution",
      "status": "PASSED",
      "duration_seconds": 15.2,
      "steps": [
        {
          "step": 1,
          "name": "Create session with agent",
          "status": "PASSED",
          "duration_ms": 120
        }
      ]
    }
  ],
  "summary": {
    "total_scenarios": 4,
    "passed": 4,
    "failed": 0,
    "total_duration_seconds": 45.8
  }
}
```

---

## Validation Points

### Session-Agent Bridge

- [ ] Session correctly associates with Agent
- [ ] Messages routed through Bridge
- [ ] Context maintained across messages
- [ ] Agent persona applied correctly

### Tool Execution

- [ ] Tool calls identified from LLM response
- [ ] Auto-approve mode works correctly
- [ ] Manual approval mode pauses execution
- [ ] Tool results integrated into response

### Streaming

- [ ] SSE connection established
- [ ] Chunks delivered in real-time
- [ ] Partial tokens displayed correctly
- [ ] Final message complete and accurate

### Error Handling

- [ ] LLM errors caught and reported
- [ ] Tool errors don't crash session
- [ ] Recovery mechanism works
- [ ] Error events published correctly

### Metrics

- [ ] Response time tracked
- [ ] Token usage recorded
- [ ] Tool execution time measured
- [ ] Error counts accurate

---

## Dependencies

- Python 3.10+
- httpx (async HTTP client)
- sseclient-py (SSE support)
- websockets (WebSocket support)

```bash
pip install httpx sseclient-py websockets
```

---

## Troubleshooting

### Connection Refused

```
確認 backend 服務已啟動:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### SSE Timeout

```
增加超時時間:
python phase_11_agent_session_test.py --timeout 120
```

### Approval Not Found

```
確認 approval_mode 已設定:
session.config.approval_mode = "manual"
```

---

**Last Updated**: 2025-12-24
**Phase**: 11 - Agent-Session Integration
**Status**: Ready for Testing

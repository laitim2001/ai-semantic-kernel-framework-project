"""
Test ExecutionEvent System (Sprint 45 - S45-4)

測試執行事件系統的完整功能，包括:
- ExecutionEventType 枚舉
- ExecutionEvent 類別
- ExecutionEventFactory 工廠方法
- SSE/JSON 序列化
"""

import pytest
import json
from datetime import datetime

from src.domain.sessions.events import (
    ExecutionEventType,
    ExecutionEvent,
    ExecutionEventFactory,
    ToolCallInfo,
    ToolResultInfo,
    UsageInfo,
)


class TestExecutionEventType:
    """測試 ExecutionEventType 枚舉"""

    def test_content_events(self):
        """測試內容事件類型"""
        assert ExecutionEventType.CONTENT.value == "content"
        assert ExecutionEventType.CONTENT_DELTA.value == "content_delta"

    def test_tool_events(self):
        """測試工具事件類型"""
        assert ExecutionEventType.TOOL_CALL.value == "tool_call"
        assert ExecutionEventType.TOOL_RESULT.value == "tool_result"
        assert ExecutionEventType.APPROVAL_REQUIRED.value == "approval_required"
        assert ExecutionEventType.APPROVAL_RESPONSE.value == "approval_response"

    def test_state_events(self):
        """測試狀態事件類型"""
        assert ExecutionEventType.STARTED.value == "started"
        assert ExecutionEventType.DONE.value == "done"
        assert ExecutionEventType.ERROR.value == "error"

    def test_system_events(self):
        """測試系統事件類型"""
        assert ExecutionEventType.HEARTBEAT.value == "heartbeat"

    def test_event_type_is_string_enum(self):
        """測試事件類型是字符串枚舉"""
        assert isinstance(ExecutionEventType.CONTENT, str)
        assert ExecutionEventType.CONTENT == "content"


class TestToolCallInfo:
    """測試 ToolCallInfo 類別"""

    def test_create_tool_call_info(self):
        """測試創建工具調用信息"""
        info = ToolCallInfo(
            id="call_123",
            name="get_weather",
            arguments={"city": "Taipei"},
            requires_approval=False,
        )

        assert info.id == "call_123"
        assert info.name == "get_weather"
        assert info.arguments == {"city": "Taipei"}
        assert info.requires_approval is False

    def test_to_dict(self):
        """測試轉換為字典"""
        info = ToolCallInfo(
            id="call_123",
            name="send_email",
            arguments={"to": "test@example.com"},
            requires_approval=True,
        )

        result = info.to_dict()

        assert result["id"] == "call_123"
        assert result["name"] == "send_email"
        assert result["arguments"] == {"to": "test@example.com"}
        assert result["requires_approval"] is True


class TestToolResultInfo:
    """測試 ToolResultInfo 類別"""

    def test_create_tool_result_info(self):
        """測試創建工具結果信息"""
        info = ToolResultInfo(
            tool_call_id="call_123",
            name="get_weather",
            result={"temperature": 25, "condition": "sunny"},
            success=True,
        )

        assert info.tool_call_id == "call_123"
        assert info.name == "get_weather"
        assert info.result == {"temperature": 25, "condition": "sunny"}
        assert info.success is True
        assert info.error_message is None

    def test_create_failed_result(self):
        """測試創建失敗的工具結果"""
        info = ToolResultInfo(
            tool_call_id="call_456",
            name="database_query",
            result=None,
            success=False,
            error_message="Connection timeout",
        )

        assert info.success is False
        assert info.error_message == "Connection timeout"

    def test_to_dict(self):
        """測試轉換為字典"""
        info = ToolResultInfo(
            tool_call_id="call_123",
            name="get_weather",
            result="sunny",
            success=True,
        )

        result = info.to_dict()

        assert result["tool_call_id"] == "call_123"
        assert result["name"] == "get_weather"
        assert result["result"] == "sunny"
        assert result["success"] is True


class TestUsageInfo:
    """測試 UsageInfo 類別"""

    def test_create_usage_info(self):
        """測試創建使用量信息"""
        info = UsageInfo(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert info.prompt_tokens == 100
        assert info.completion_tokens == 50
        assert info.total_tokens == 150

    def test_default_values(self):
        """測試默認值"""
        info = UsageInfo()

        assert info.prompt_tokens == 0
        assert info.completion_tokens == 0
        assert info.total_tokens == 0

    def test_to_dict(self):
        """測試轉換為字典"""
        info = UsageInfo(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
        )

        result = info.to_dict()

        assert result["prompt_tokens"] == 200
        assert result["completion_tokens"] == 100
        assert result["total_tokens"] == 300


class TestExecutionEvent:
    """測試 ExecutionEvent 類別"""

    def test_create_started_event(self):
        """測試創建開始事件"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            session_id="session_123",
            execution_id="exec_456",
        )

        assert event.event_type == ExecutionEventType.STARTED
        assert event.session_id == "session_123"
        assert event.execution_id == "exec_456"
        assert event.id is not None
        assert event.timestamp is not None

    def test_create_content_event(self):
        """測試創建內容事件"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.CONTENT,
            session_id="session_123",
            execution_id="exec_456",
            content="Hello, how can I help you?",
        )

        assert event.event_type == ExecutionEventType.CONTENT
        assert event.content == "Hello, how can I help you?"

    def test_create_content_delta_event(self):
        """測試創建串流內容片段事件"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.CONTENT_DELTA,
            session_id="session_123",
            execution_id="exec_456",
            content="Hello",
        )

        assert event.event_type == ExecutionEventType.CONTENT_DELTA
        assert event.content == "Hello"

    def test_create_tool_call_event(self):
        """測試創建工具調用事件"""
        tool_call = ToolCallInfo(
            id="call_123",
            name="get_weather",
            arguments={"city": "Taipei"},
        )
        event = ExecutionEvent(
            event_type=ExecutionEventType.TOOL_CALL,
            session_id="session_123",
            execution_id="exec_456",
            tool_call=tool_call,
        )

        assert event.event_type == ExecutionEventType.TOOL_CALL
        assert event.tool_call is not None
        assert event.tool_call.name == "get_weather"

    def test_create_error_event(self):
        """測試創建錯誤事件"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.ERROR,
            session_id="session_123",
            execution_id="exec_456",
            error="LLM request failed",
            error_code="LLM_TIMEOUT",
        )

        assert event.event_type == ExecutionEventType.ERROR
        assert event.error == "LLM request failed"
        assert event.error_code == "LLM_TIMEOUT"

    def test_create_done_event_with_usage(self):
        """測試創建帶使用量的完成事件"""
        usage = UsageInfo(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        event = ExecutionEvent(
            event_type=ExecutionEventType.DONE,
            session_id="session_123",
            execution_id="exec_456",
            finish_reason="stop",
            usage=usage,
        )

        assert event.event_type == ExecutionEventType.DONE
        assert event.finish_reason == "stop"
        assert event.usage is not None
        assert event.usage.total_tokens == 150

    def test_to_dict_started_event(self):
        """測試開始事件轉字典"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            session_id="session_123",
            execution_id="exec_456",
        )

        result = event.to_dict()

        assert result["event"] == "started"
        assert result["session_id"] == "session_123"
        assert result["execution_id"] == "exec_456"
        assert "id" in result
        assert "timestamp" in result

    def test_to_dict_content_event(self):
        """測試內容事件轉字典"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.CONTENT,
            session_id="session_123",
            execution_id="exec_456",
            content="Test content",
        )

        result = event.to_dict()

        assert result["event"] == "content"
        assert result["content"] == "Test content"

    def test_to_dict_tool_call_event(self):
        """測試工具調用事件轉字典"""
        tool_call = ToolCallInfo(
            id="call_123",
            name="get_weather",
            arguments={"city": "Taipei"},
        )
        event = ExecutionEvent(
            event_type=ExecutionEventType.TOOL_CALL,
            session_id="session_123",
            execution_id="exec_456",
            tool_call=tool_call,
        )

        result = event.to_dict()

        assert result["event"] == "tool_call"
        assert "tool_call" in result
        assert result["tool_call"]["name"] == "get_weather"

    def test_to_dict_done_event(self):
        """測試完成事件轉字典"""
        usage = UsageInfo(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        event = ExecutionEvent(
            event_type=ExecutionEventType.DONE,
            session_id="session_123",
            execution_id="exec_456",
            finish_reason="stop",
            usage=usage,
        )

        result = event.to_dict()

        assert result["event"] == "done"
        assert result["finish_reason"] == "stop"
        assert "usage" in result
        assert result["usage"]["total_tokens"] == 150

    def test_to_sse_format(self):
        """測試 SSE 格式輸出"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.CONTENT_DELTA,
            session_id="session_123",
            execution_id="exec_456",
            content="Hello",
        )

        sse = event.to_sse()

        assert sse.startswith("event: content_delta\n")
        assert "data: " in sse
        assert sse.endswith("\n\n")

        # 驗證 data 是有效的 JSON
        lines = sse.strip().split("\n")
        data_line = [l for l in lines if l.startswith("data: ")][0]
        json_str = data_line.replace("data: ", "")
        data = json.loads(json_str)
        assert data["content"] == "Hello"

    def test_to_json(self):
        """測試 JSON 字串輸出"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            session_id="session_123",
            execution_id="exec_456",
        )

        json_str = event.to_json()
        data = json.loads(json_str)

        assert data["event"] == "started"
        assert data["session_id"] == "session_123"

    def test_from_dict_started_event(self):
        """測試從字典創建開始事件"""
        data = {
            "id": "event_123",
            "event": "started",
            "session_id": "session_123",
            "execution_id": "exec_456",
            "timestamp": "2025-01-01T00:00:00",
        }

        event = ExecutionEvent.from_dict(data)

        assert event.id == "event_123"
        assert event.event_type == ExecutionEventType.STARTED
        assert event.session_id == "session_123"

    def test_from_dict_content_event(self):
        """測試從字典創建內容事件"""
        data = {
            "event": "content",
            "session_id": "session_123",
            "execution_id": "exec_456",
            "content": "Test content",
        }

        event = ExecutionEvent.from_dict(data)

        assert event.event_type == ExecutionEventType.CONTENT
        assert event.content == "Test content"

    def test_from_dict_tool_call_event(self):
        """測試從字典創建工具調用事件"""
        data = {
            "event": "tool_call",
            "session_id": "session_123",
            "execution_id": "exec_456",
            "tool_call": {
                "id": "call_123",
                "name": "get_weather",
                "arguments": {"city": "Taipei"},
                "requires_approval": False,
            },
        }

        event = ExecutionEvent.from_dict(data)

        assert event.event_type == ExecutionEventType.TOOL_CALL
        assert event.tool_call is not None
        assert event.tool_call.name == "get_weather"
        assert event.tool_call.arguments == {"city": "Taipei"}

    def test_from_dict_done_event_with_usage(self):
        """測試從字典創建帶使用量的完成事件"""
        data = {
            "event": "done",
            "session_id": "session_123",
            "execution_id": "exec_456",
            "finish_reason": "stop",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }

        event = ExecutionEvent.from_dict(data)

        assert event.event_type == ExecutionEventType.DONE
        assert event.finish_reason == "stop"
        assert event.usage is not None
        assert event.usage.total_tokens == 150

    def test_metadata_support(self):
        """測試元數據支持"""
        event = ExecutionEvent(
            event_type=ExecutionEventType.STARTED,
            session_id="session_123",
            execution_id="exec_456",
            metadata={"model": "gpt-4", "temperature": 0.7},
        )

        result = event.to_dict()

        assert "metadata" in result
        assert result["metadata"]["model"] == "gpt-4"


class TestExecutionEventFactory:
    """測試 ExecutionEventFactory 工廠類別"""

    def test_factory_started(self):
        """測試工廠方法 - 開始事件"""
        event = ExecutionEventFactory.started(
            session_id="session_123",
            execution_id="exec_456",
            model="gpt-4",
        )

        assert event.event_type == ExecutionEventType.STARTED
        assert event.session_id == "session_123"
        assert event.metadata.get("model") == "gpt-4"

    def test_factory_content(self):
        """測試工廠方法 - 完整內容事件"""
        event = ExecutionEventFactory.content(
            session_id="session_123",
            execution_id="exec_456",
            content="Hello, world!",
        )

        assert event.event_type == ExecutionEventType.CONTENT
        assert event.content == "Hello, world!"

    def test_factory_content_delta(self):
        """測試工廠方法 - 串流內容片段"""
        event = ExecutionEventFactory.content_delta(
            session_id="session_123",
            execution_id="exec_456",
            delta="Hello",
        )

        assert event.event_type == ExecutionEventType.CONTENT_DELTA
        assert event.content == "Hello"

    def test_factory_tool_call(self):
        """測試工廠方法 - 工具調用"""
        event = ExecutionEventFactory.tool_call(
            session_id="session_123",
            execution_id="exec_456",
            tool_call_id="call_123",
            tool_name="get_weather",
            arguments={"city": "Taipei"},
            requires_approval=True,
        )

        assert event.event_type == ExecutionEventType.TOOL_CALL
        assert event.tool_call is not None
        assert event.tool_call.id == "call_123"
        assert event.tool_call.name == "get_weather"
        assert event.tool_call.requires_approval is True

    def test_factory_tool_result(self):
        """測試工廠方法 - 工具結果"""
        event = ExecutionEventFactory.tool_result(
            session_id="session_123",
            execution_id="exec_456",
            tool_call_id="call_123",
            tool_name="get_weather",
            result={"temperature": 25},
            success=True,
        )

        assert event.event_type == ExecutionEventType.TOOL_RESULT
        assert event.tool_result is not None
        assert event.tool_result.result == {"temperature": 25}
        assert event.tool_result.success is True

    def test_factory_tool_result_failed(self):
        """測試工廠方法 - 失敗的工具結果"""
        event = ExecutionEventFactory.tool_result(
            session_id="session_123",
            execution_id="exec_456",
            tool_call_id="call_123",
            tool_name="database_query",
            result=None,
            success=False,
            error_message="Connection timeout",
        )

        assert event.tool_result.success is False
        assert event.tool_result.error_message == "Connection timeout"

    def test_factory_approval_required(self):
        """測試工廠方法 - 需要審批"""
        event = ExecutionEventFactory.approval_required(
            session_id="session_123",
            execution_id="exec_456",
            approval_request_id="approval_789",
            tool_call_id="call_123",
            tool_name="send_email",
            arguments={"to": "test@example.com"},
        )

        assert event.event_type == ExecutionEventType.APPROVAL_REQUIRED
        assert event.approval_request_id == "approval_789"
        assert event.tool_call is not None
        assert event.tool_call.requires_approval is True

    def test_factory_approval_response_approved(self):
        """測試工廠方法 - 審批通過"""
        event = ExecutionEventFactory.approval_response(
            session_id="session_123",
            execution_id="exec_456",
            approval_request_id="approval_789",
            approved=True,
            feedback="Looks good",
        )

        assert event.event_type == ExecutionEventType.APPROVAL_RESPONSE
        assert event.approval_status == "approved"
        assert event.approval_feedback == "Looks good"

    def test_factory_approval_response_rejected(self):
        """測試工廠方法 - 審批拒絕"""
        event = ExecutionEventFactory.approval_response(
            session_id="session_123",
            execution_id="exec_456",
            approval_request_id="approval_789",
            approved=False,
            feedback="Not authorized",
        )

        assert event.approval_status == "rejected"
        assert event.approval_feedback == "Not authorized"

    def test_factory_error(self):
        """測試工廠方法 - 錯誤"""
        event = ExecutionEventFactory.error(
            session_id="session_123",
            execution_id="exec_456",
            error_message="LLM request failed",
            error_code="LLM_TIMEOUT",
        )

        assert event.event_type == ExecutionEventType.ERROR
        assert event.error == "LLM request failed"
        assert event.error_code == "LLM_TIMEOUT"

    def test_factory_done(self):
        """測試工廠方法 - 完成"""
        event = ExecutionEventFactory.done(
            session_id="session_123",
            execution_id="exec_456",
            finish_reason="stop",
            prompt_tokens=100,
            completion_tokens=50,
        )

        assert event.event_type == ExecutionEventType.DONE
        assert event.finish_reason == "stop"
        assert event.usage is not None
        assert event.usage.prompt_tokens == 100
        assert event.usage.completion_tokens == 50
        assert event.usage.total_tokens == 150

    def test_factory_heartbeat(self):
        """測試工廠方法 - 心跳"""
        event = ExecutionEventFactory.heartbeat(
            session_id="session_123",
            execution_id="exec_456",
        )

        assert event.event_type == ExecutionEventType.HEARTBEAT
        assert event.session_id == "session_123"


class TestExecutionEventIntegration:
    """整合測試"""

    def test_roundtrip_serialization(self):
        """測試序列化往返"""
        original = ExecutionEventFactory.tool_call(
            session_id="session_123",
            execution_id="exec_456",
            tool_call_id="call_123",
            tool_name="get_weather",
            arguments={"city": "Taipei", "unit": "celsius"},
            requires_approval=True,
        )

        # 序列化
        dict_data = original.to_dict()
        json_str = json.dumps(dict_data)

        # 反序列化
        parsed = json.loads(json_str)
        restored = ExecutionEvent.from_dict(parsed)

        assert restored.event_type == original.event_type
        assert restored.session_id == original.session_id
        assert restored.tool_call.name == original.tool_call.name
        assert restored.tool_call.arguments == original.tool_call.arguments

    def test_sse_stream_simulation(self):
        """模擬 SSE 串流"""
        events = [
            ExecutionEventFactory.started("s1", "e1"),
            ExecutionEventFactory.content_delta("s1", "e1", "Hello"),
            ExecutionEventFactory.content_delta("s1", "e1", ", "),
            ExecutionEventFactory.content_delta("s1", "e1", "world!"),
            ExecutionEventFactory.done("s1", "e1", "stop", 10, 5),
        ]

        # 模擬串流輸出
        stream_output = ""
        for event in events:
            stream_output += event.to_sse()

        # 驗證輸出格式
        assert "event: started" in stream_output
        assert "event: content_delta" in stream_output
        assert "event: done" in stream_output

        # 計算事件數量
        event_count = stream_output.count("event: ")
        assert event_count == 5

    def test_websocket_message_simulation(self):
        """模擬 WebSocket 消息"""
        events = [
            ExecutionEventFactory.started("s1", "e1"),
            ExecutionEventFactory.tool_call(
                "s1", "e1", "c1", "get_weather", {"city": "Taipei"}
            ),
            ExecutionEventFactory.tool_result(
                "s1", "e1", "c1", "get_weather", {"temp": 25}
            ),
            ExecutionEventFactory.content("s1", "e1", "The weather is 25°C"),
            ExecutionEventFactory.done("s1", "e1", "stop", 100, 50),
        ]

        # 模擬 WebSocket 消息
        messages = [event.to_json() for event in events]

        # 驗證所有消息都是有效的 JSON
        for msg in messages:
            data = json.loads(msg)
            assert "event" in data
            assert "session_id" in data
            assert "execution_id" in data

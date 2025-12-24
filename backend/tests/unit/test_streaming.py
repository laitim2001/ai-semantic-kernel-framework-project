"""
Unit tests for StreamingLLMHandler - Sprint 45 S45-2

測試串流 LLM 處理器，包含:
- StreamState enum
- StreamConfig/StreamStats dataclasses
- TokenCounter token 計數
- StreamingLLMHandler 主要類別
- 錯誤處理與重試機制
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest

from src.domain.sessions.streaming import (
    StreamState,
    StreamConfig,
    StreamStats,
    ToolCallDelta,
    TokenCounter,
    StreamingLLMHandler,
    create_streaming_handler,
    HAS_TIKTOKEN,
)
from src.domain.sessions.events import ExecutionEventType


# =============================================================================
# StreamState Tests
# =============================================================================


class TestStreamState:
    """測試 StreamState enum"""

    def test_all_states_exist(self):
        """測試所有狀態都存在"""
        assert StreamState.IDLE == "idle"
        assert StreamState.CONNECTING == "connecting"
        assert StreamState.STREAMING == "streaming"
        assert StreamState.PROCESSING_TOOLS == "processing_tools"
        assert StreamState.COMPLETED == "completed"
        assert StreamState.ERROR == "error"
        assert StreamState.CANCELLED == "cancelled"

    def test_state_is_string_enum(self):
        """測試狀態是字串枚舉"""
        assert isinstance(StreamState.IDLE, str)
        assert StreamState.IDLE.value == "idle"

    def test_state_count(self):
        """測試狀態數量"""
        states = list(StreamState)
        assert len(states) == 7


# =============================================================================
# StreamConfig Tests
# =============================================================================


class TestStreamConfig:
    """測試 StreamConfig dataclass"""

    def test_default_values(self):
        """測試預設值"""
        config = StreamConfig()
        assert config.timeout == 120.0
        assert config.chunk_timeout == 30.0
        assert config.max_retries == 3
        assert config.heartbeat_interval == 15.0
        assert config.buffer_size == 4096

    def test_custom_values(self):
        """測試自訂值"""
        config = StreamConfig(
            timeout=60.0,
            chunk_timeout=10.0,
            max_retries=5,
            heartbeat_interval=5.0,
            buffer_size=8192,
        )
        assert config.timeout == 60.0
        assert config.chunk_timeout == 10.0
        assert config.max_retries == 5
        assert config.heartbeat_interval == 5.0
        assert config.buffer_size == 8192

    def test_partial_override(self):
        """測試部分覆蓋"""
        config = StreamConfig(timeout=30.0)
        assert config.timeout == 30.0
        assert config.chunk_timeout == 30.0  # 保持預設


# =============================================================================
# StreamStats Tests
# =============================================================================


class TestStreamStats:
    """測試 StreamStats dataclass"""

    def test_default_values(self):
        """測試預設值"""
        stats = StreamStats()
        assert stats.start_time is None
        assert stats.first_token_time is None
        assert stats.end_time is None
        assert stats.chunk_count == 0
        assert stats.total_chars == 0
        assert stats.prompt_tokens == 0
        assert stats.completion_tokens == 0

    def test_time_to_first_token_ms(self):
        """測試首個 token 延遲計算"""
        now = datetime.utcnow()
        stats = StreamStats(
            start_time=now,
            first_token_time=now + timedelta(milliseconds=150),
        )
        ttft = stats.time_to_first_token_ms
        assert ttft is not None
        assert 149 <= ttft <= 151  # 允許微小誤差

    def test_time_to_first_token_ms_none(self):
        """測試沒有首個 token 時間時返回 None"""
        stats = StreamStats(start_time=datetime.utcnow())
        assert stats.time_to_first_token_ms is None

        stats2 = StreamStats(first_token_time=datetime.utcnow())
        assert stats2.time_to_first_token_ms is None

    def test_total_duration_ms(self):
        """測試總時長計算"""
        now = datetime.utcnow()
        stats = StreamStats(
            start_time=now,
            end_time=now + timedelta(seconds=2, milliseconds=500),
        )
        duration = stats.total_duration_ms
        assert duration is not None
        assert 2499 <= duration <= 2501

    def test_total_duration_ms_none(self):
        """測試沒有結束時間時返回 None"""
        stats = StreamStats(start_time=datetime.utcnow())
        assert stats.total_duration_ms is None

    def test_total_tokens(self):
        """測試總 token 數計算"""
        stats = StreamStats(prompt_tokens=100, completion_tokens=50)
        assert stats.total_tokens == 150

    def test_to_dict(self):
        """測試轉換為字典"""
        now = datetime.utcnow()
        stats = StreamStats(
            start_time=now,
            first_token_time=now + timedelta(milliseconds=100),
            end_time=now + timedelta(seconds=1),
            chunk_count=10,
            total_chars=500,
            prompt_tokens=100,
            completion_tokens=50,
        )
        d = stats.to_dict()
        assert "time_to_first_token_ms" in d
        assert "total_duration_ms" in d
        assert "chunk_count" in d
        assert d["chunk_count"] == 10
        assert d["total_chars"] == 500
        assert d["prompt_tokens"] == 100
        assert d["completion_tokens"] == 50
        assert d["total_tokens"] == 150


# =============================================================================
# ToolCallDelta Tests
# =============================================================================


class TestToolCallDelta:
    """測試 ToolCallDelta dataclass"""

    def test_default_values(self):
        """測試預設值"""
        delta = ToolCallDelta()
        assert delta.id == ""
        assert delta.name == ""
        assert delta.arguments == ""

    def test_accumulation(self):
        """測試參數累積"""
        delta = ToolCallDelta()
        delta.id = "call_123"
        delta.name = "get_weather"
        delta.arguments += '{"city":'
        delta.arguments += '"Tokyo"}'

        assert delta.id == "call_123"
        assert delta.name == "get_weather"
        assert delta.arguments == '{"city":"Tokyo"}'


# =============================================================================
# TokenCounter Tests
# =============================================================================


class TestTokenCounter:
    """測試 TokenCounter 類別"""

    def test_init_default_model(self):
        """測試預設模型初始化"""
        counter = TokenCounter()
        assert counter._model == "gpt-4"

    def test_init_custom_model(self):
        """測試自訂模型初始化"""
        counter = TokenCounter(model="gpt-3.5-turbo")
        assert counter._model == "gpt-3.5-turbo"

    def test_count_tokens_empty(self):
        """測試空字串計數"""
        counter = TokenCounter()
        assert counter.count_tokens("") == 0

    def test_count_tokens_simple(self):
        """測試簡單字串計數"""
        counter = TokenCounter()
        count = counter.count_tokens("Hello, world!")
        assert count > 0
        # 大約 3-4 tokens
        assert 2 <= count <= 6

    def test_count_tokens_chinese(self):
        """測試中文字串計數"""
        counter = TokenCounter()
        count = counter.count_tokens("你好世界")
        assert count > 0

    def test_count_tokens_long_text(self):
        """測試長文本計數"""
        counter = TokenCounter()
        text = "Hello " * 100  # 約 200 tokens
        count = counter.count_tokens(text)
        assert count > 50

    def test_count_messages_empty(self):
        """測試空訊息列表計數"""
        counter = TokenCounter()
        count = counter.count_messages([])
        assert count == 3  # 只有結尾標記

    def test_count_messages_simple(self):
        """測試簡單訊息計數"""
        counter = TokenCounter()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        count = counter.count_messages(messages)
        assert count > 8  # 訊息開銷 + 內容

    def test_count_messages_with_tool_calls(self):
        """測試帶工具調用的訊息計數"""
        counter = TokenCounter()
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"city": "Tokyo"}',
                        },
                    }
                ],
            }
        ]
        count = counter.count_messages(messages)
        assert count > 10

    def test_count_messages_with_name(self):
        """測試帶名稱的訊息計數"""
        counter = TokenCounter()
        messages = [
            {"role": "system", "content": "You are helpful", "name": "system_prompt"},
        ]
        count = counter.count_messages(messages)
        # 應包含 name 額外開銷
        assert count > 5


class TestTokenCounterWithoutTiktoken:
    """測試沒有 tiktoken 時的估算模式"""

    @patch("src.domain.sessions.streaming.HAS_TIKTOKEN", False)
    def test_estimation_mode(self):
        """測試估算模式"""
        # 強制重建計數器使用估算
        counter = TokenCounter()
        counter._encoding = None  # 模擬沒有 tiktoken

        # 估算：每 4 字符約 1 token
        text = "a" * 100
        count = counter.count_tokens(text)
        assert count == 26  # 100 // 4 + 1


# =============================================================================
# StreamingLLMHandler Init Tests
# =============================================================================


class TestStreamingLLMHandlerInit:
    """測試 StreamingLLMHandler 初始化"""

    @patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key-123",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4",
    })
    def test_init_from_env(self):
        """測試從環境變數初始化"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            handler = StreamingLLMHandler()
            assert handler._endpoint == "https://test.openai.azure.com/"
            assert handler._api_key == "test-key-123"
            assert handler._deployment_name == "gpt-4"
            assert handler._state == StreamState.IDLE

    @patch("src.domain.sessions.streaming.AsyncAzureOpenAI")
    def test_init_explicit_params(self, mock_client):
        """測試顯式參數初始化"""
        handler = StreamingLLMHandler(
            endpoint="https://custom.openai.azure.com/",
            api_key="custom-key",
            deployment_name="gpt-4-turbo",
        )
        assert handler._endpoint == "https://custom.openai.azure.com/"
        assert handler._api_key == "custom-key"
        assert handler._deployment_name == "gpt-4-turbo"

    @patch("src.domain.sessions.streaming.AsyncAzureOpenAI")
    def test_init_with_custom_config(self, mock_client):
        """測試自訂配置初始化"""
        config = StreamConfig(timeout=60.0, max_retries=5)
        handler = StreamingLLMHandler(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            config=config,
        )
        assert handler._config.timeout == 60.0
        assert handler._config.max_retries == 5

    def test_init_missing_endpoint(self):
        """測試缺少端點時報錯"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="endpoint is required"):
                StreamingLLMHandler()

    def test_init_missing_api_key(self):
        """測試缺少 API Key 時報錯"""
        with patch.dict(os.environ, {
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        }, clear=True):
            with pytest.raises(ValueError, match="API key is required"):
                StreamingLLMHandler()


# =============================================================================
# StreamingLLMHandler Stream Tests
# =============================================================================


class TestStreamingLLMHandlerStream:
    """測試 StreamingLLMHandler stream 方法"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
            )

    @pytest.fixture
    def mock_stream_response(self):
        """創建 mock 串流響應"""
        chunks = []

        # Chunk 1: 內容開始
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta = MagicMock()
        chunk1.choices[0].delta.content = "Hello"
        chunk1.choices[0].delta.tool_calls = None
        chunk1.choices[0].finish_reason = None
        chunk1.usage = None
        chunks.append(chunk1)

        # Chunk 2: 更多內容
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta = MagicMock()
        chunk2.choices[0].delta.content = " World!"
        chunk2.choices[0].delta.tool_calls = None
        chunk2.choices[0].finish_reason = None
        chunk2.usage = None
        chunks.append(chunk2)

        # Chunk 3: 完成
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta = MagicMock()
        chunk3.choices[0].delta.content = None
        chunk3.choices[0].delta.tool_calls = None
        chunk3.choices[0].finish_reason = "stop"
        chunk3.usage = MagicMock()
        chunk3.usage.prompt_tokens = 10
        chunk3.usage.completion_tokens = 5
        chunks.append(chunk3)

        async def async_gen():
            for chunk in chunks:
                yield chunk

        return async_gen()

    @pytest.mark.asyncio
    async def test_stream_success(self, handler, mock_stream_response):
        """測試成功串流"""
        handler._client.chat.completions.create = AsyncMock(
            return_value=mock_stream_response
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        # 驗證事件序列
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.STARTED in event_types
        assert ExecutionEventType.CONTENT_DELTA in event_types
        assert ExecutionEventType.DONE in event_types

        # 驗證狀態
        assert handler._state == StreamState.COMPLETED

    @pytest.mark.asyncio
    async def test_stream_with_tools(self, handler):
        """測試帶工具調用的串流"""
        # 創建工具調用響應
        chunks = []

        # Tool call chunk
        tc_chunk = MagicMock()
        tc_chunk.choices = [MagicMock()]
        tc_chunk.choices[0].delta = MagicMock()
        tc_chunk.choices[0].delta.content = None
        tc_delta = MagicMock()
        tc_delta.index = 0
        tc_delta.id = "call_abc123"
        tc_delta.function = MagicMock()
        tc_delta.function.name = "get_weather"
        tc_delta.function.arguments = '{"city": "Tokyo"}'
        tc_chunk.choices[0].delta.tool_calls = [tc_delta]
        tc_chunk.choices[0].finish_reason = None
        tc_chunk.usage = None
        chunks.append(tc_chunk)

        # Finish chunk
        finish_chunk = MagicMock()
        finish_chunk.choices = [MagicMock()]
        finish_chunk.choices[0].delta = MagicMock()
        finish_chunk.choices[0].delta.content = None
        finish_chunk.choices[0].delta.tool_calls = None
        finish_chunk.choices[0].finish_reason = "tool_calls"
        finish_chunk.usage = MagicMock()
        finish_chunk.usage.prompt_tokens = 20
        finish_chunk.usage.completion_tokens = 10
        chunks.append(finish_chunk)

        async def async_gen():
            for chunk in chunks:
                yield chunk

        handler._client.chat.completions.create = AsyncMock(
            return_value=async_gen()
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "What's the weather?"}],
            session_id="session-1",
            execution_id="exec-1",
            tools=[{"type": "function", "function": {"name": "get_weather"}}],
        ):
            events.append(event)

        # 驗證有工具調用事件
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.TOOL_CALL in event_types

        # 驗證工具調用內容
        tool_event = next(e for e in events if e.event_type == ExecutionEventType.TOOL_CALL)
        assert tool_event.tool_call is not None
        assert tool_event.tool_call.name == "get_weather"

    @pytest.mark.asyncio
    async def test_stream_cancel(self, handler, mock_stream_response):
        """測試取消串流"""
        handler._client.chat.completions.create = AsyncMock(
            return_value=mock_stream_response
        )

        events = []
        handler.cancel()  # 立即取消

        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        # 應該至少有開始事件，然後是完成事件
        assert len(events) >= 1


# =============================================================================
# StreamingLLMHandler Error Handling Tests
# =============================================================================


class TestStreamingLLMHandlerErrors:
    """測試 StreamingLLMHandler 錯誤處理"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
            )

    @pytest.mark.asyncio
    async def test_api_timeout_error(self, handler):
        """測試 API 超時錯誤"""
        from openai import APITimeoutError

        handler._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        # 應該有錯誤事件
        error_events = [e for e in events if e.event_type == ExecutionEventType.ERROR]
        assert len(error_events) == 1
        assert error_events[0].error_code == "TIMEOUT"
        assert handler._state == StreamState.ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, handler):
        """測試速率限制錯誤"""
        from openai import RateLimitError

        mock_response = MagicMock()
        mock_response.status_code = 429

        handler._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                "Rate limit exceeded",
                response=mock_response,
                body=None
            )
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        error_events = [e for e in events if e.event_type == ExecutionEventType.ERROR]
        assert len(error_events) == 1
        assert error_events[0].error_code == "RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_api_error(self, handler):
        """測試一般 API 錯誤"""
        from openai import APIError

        mock_request = MagicMock()

        handler._client.chat.completions.create = AsyncMock(
            side_effect=APIError(
                message="Internal server error",
                request=mock_request,
                body=None
            )
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        error_events = [e for e in events if e.event_type == ExecutionEventType.ERROR]
        assert len(error_events) == 1
        assert error_events[0].error_code == "API_ERROR"

    @pytest.mark.asyncio
    async def test_unexpected_error(self, handler):
        """測試意外錯誤"""
        handler._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        error_events = [e for e in events if e.event_type == ExecutionEventType.ERROR]
        assert len(error_events) == 1
        assert error_events[0].error_code == "STREAM_ERROR"


# =============================================================================
# StreamingLLMHandler Retry Tests
# =============================================================================


class TestStreamingLLMHandlerRetry:
    """測試 StreamingLLMHandler 重試機制"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        config = StreamConfig(max_retries=3)
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                config=config,
            )

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, handler):
        """測試超時重試"""
        from openai import APITimeoutError

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError(request=MagicMock())
            # 第三次成功
            async def gen():
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock()
                chunk.choices[0].delta.content = "Success"
                chunk.choices[0].delta.tool_calls = None
                chunk.choices[0].finish_reason = "stop"
                chunk.usage = None
                yield chunk
            return gen()

        handler._client.chat.completions.create = mock_create

        events = []
        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        # 應該重試成功
        assert call_count == 3
        assert handler._state == StreamState.COMPLETED


# =============================================================================
# StreamingLLMHandler Utility Tests
# =============================================================================


class TestStreamingLLMHandlerUtility:
    """測試 StreamingLLMHandler 工具方法"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
            )

    def test_parse_tool_arguments_valid(self, handler):
        """測試解析有效工具參數"""
        result = handler._parse_tool_arguments('{"city": "Tokyo", "unit": "celsius"}')
        assert result == {"city": "Tokyo", "unit": "celsius"}

    def test_parse_tool_arguments_empty(self, handler):
        """測試解析空參數"""
        result = handler._parse_tool_arguments("")
        assert result == {}

    def test_parse_tool_arguments_incomplete(self, handler):
        """測試解析不完整 JSON"""
        # 自動補全最後的 }
        result = handler._parse_tool_arguments('{"city": "Tokyo"')
        assert result == {"city": "Tokyo"}

    def test_state_property(self, handler):
        """測試狀態屬性"""
        assert handler.state == StreamState.IDLE
        handler._state = StreamState.STREAMING
        assert handler.state == StreamState.STREAMING

    def test_cancel_method(self, handler):
        """測試取消方法"""
        assert handler._cancel_flag is False
        handler.cancel()
        assert handler._cancel_flag is True


# =============================================================================
# StreamingLLMHandler Simple Stream Tests
# =============================================================================


class TestStreamingLLMHandlerStreamSimple:
    """測試 StreamingLLMHandler stream_simple 方法"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
            )

    @pytest.mark.asyncio
    async def test_stream_simple(self, handler):
        """測試簡化串流接口"""
        # Mock stream 方法
        from src.domain.sessions.events import ExecutionEvent, ExecutionEventFactory

        events_to_yield = [
            ExecutionEventFactory.started("session-1", "exec-1"),
            ExecutionEventFactory.content_delta("session-1", "exec-1", "Hello"),
            ExecutionEventFactory.content_delta("session-1", "exec-1", " World"),
            ExecutionEventFactory.done("session-1", "exec-1", "stop", 10, 5),
        ]

        async def mock_stream(*args, **kwargs):
            for event in events_to_yield:
                yield event

        handler.stream = mock_stream

        contents = []
        async for content in handler.stream_simple(
            messages=[{"role": "user", "content": "Hi"}],
            session_id="session-1",
            execution_id="exec-1",
        ):
            contents.append(content)

        assert contents == ["Hello", " World"]


# =============================================================================
# StreamingLLMHandler Context Manager Tests
# =============================================================================


class TestStreamingLLMHandlerContextManager:
    """測試 StreamingLLMHandler 上下文管理器"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """測試異步上下文管理器"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            async with StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
            ) as handler:
                assert handler is not None
                assert handler._state == StreamState.IDLE

            # 驗證 close 被調用
            mock_client.close.assert_called_once()


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateStreamingHandler:
    """測試 create_streaming_handler 工廠函數"""

    @patch("src.domain.sessions.streaming.AsyncAzureOpenAI")
    def test_create_with_params(self, mock_client):
        """測試帶參數創建"""
        handler = create_streaming_handler(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            deployment_name="gpt-4-turbo",
        )
        assert isinstance(handler, StreamingLLMHandler)
        assert handler._deployment_name == "gpt-4-turbo"

    @patch("src.domain.sessions.streaming.AsyncAzureOpenAI")
    def test_create_with_config(self, mock_client):
        """測試帶配置創建"""
        config = StreamConfig(timeout=30.0)
        handler = create_streaming_handler(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            config=config,
        )
        assert handler._config.timeout == 30.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestStreamingIntegration:
    """整合測試"""

    @pytest.fixture
    def handler(self):
        """創建測試用 handler"""
        with patch("src.domain.sessions.streaming.AsyncAzureOpenAI"):
            return StreamingLLMHandler(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
            )

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, handler):
        """測試完整對話流程"""
        # 準備多輪對話
        chunks_round1 = []

        # Round 1
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta = MagicMock()
        chunk.choices[0].delta.content = "I can help you with that."
        chunk.choices[0].delta.tool_calls = None
        chunk.choices[0].finish_reason = "stop"
        chunk.usage = MagicMock()
        chunk.usage.prompt_tokens = 20
        chunk.usage.completion_tokens = 10
        chunks_round1.append(chunk)

        async def gen_round1():
            for c in chunks_round1:
                yield c

        handler._client.chat.completions.create = AsyncMock(
            return_value=gen_round1()
        )

        # 執行
        events = []
        async for event in handler.stream(
            messages=[
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ],
            session_id="session-1",
            execution_id="exec-1",
        ):
            events.append(event)

        # 驗證
        assert handler._state == StreamState.COMPLETED

        # 確認事件類型
        event_types = [e.event_type for e in events]
        assert ExecutionEventType.STARTED in event_types
        assert ExecutionEventType.CONTENT_DELTA in event_types
        assert ExecutionEventType.DONE in event_types

    @pytest.mark.asyncio
    async def test_token_counting_accuracy(self, handler):
        """測試 token 計數準確性"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"},
        ]

        token_count = handler._token_counter.count_messages(messages)

        # 應該有合理的 token 數
        assert 10 < token_count < 50

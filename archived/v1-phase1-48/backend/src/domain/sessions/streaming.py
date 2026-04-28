"""
Streaming LLM Handler - Sprint 45 S45-2

串流式 LLM 回應處理器，提供:
- Azure OpenAI 串流調用
- SSE 格式處理
- Token 計數追蹤
- 超時與重試機制
- 錯誤處理與恢復

依賴:
- AsyncAzureOpenAI (openai SDK)
- tiktoken (token 計數)
- ExecutionEvent (S45-4)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)
import uuid
import logging
import asyncio
import time

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

from openai import AsyncAzureOpenAI, APIError, RateLimitError, APITimeoutError

from src.domain.sessions.events import (
    ExecutionEvent,
    ExecutionEventFactory,
    ExecutionEventType,
    UsageInfo,
    ToolCallInfo,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Enums
# =============================================================================


class StreamState(str, Enum):
    """串流狀態"""
    IDLE = "idle"
    CONNECTING = "connecting"
    STREAMING = "streaming"
    PROCESSING_TOOLS = "processing_tools"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class StreamConfig:
    """串流配置

    Attributes:
        timeout: 連接超時秒數
        chunk_timeout: 單塊超時秒數
        max_retries: 最大重試次數
        heartbeat_interval: 心跳間隔秒數
        buffer_size: 內容緩衝區大小
    """
    timeout: float = 120.0
    chunk_timeout: float = 30.0
    max_retries: int = 3
    heartbeat_interval: float = 15.0
    buffer_size: int = 4096


@dataclass
class StreamStats:
    """串流統計

    Attributes:
        start_time: 開始時間
        first_token_time: 首個 token 時間
        end_time: 結束時間
        chunk_count: 塊數量
        total_chars: 總字符數
        prompt_tokens: Prompt tokens
        completion_tokens: Completion tokens
    """
    start_time: Optional[datetime] = None
    first_token_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    chunk_count: int = 0
    total_chars: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def time_to_first_token_ms(self) -> Optional[int]:
        """首個 token 延遲（毫秒）"""
        if self.start_time and self.first_token_time:
            delta = self.first_token_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None

    @property
    def total_duration_ms(self) -> Optional[int]:
        """總時長（毫秒）"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None

    @property
    def total_tokens(self) -> int:
        """總 tokens"""
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "total_duration_ms": self.total_duration_ms,
            "chunk_count": self.chunk_count,
            "total_chars": self.total_chars,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ToolCallDelta:
    """工具調用增量

    用於累積串流中的工具調用信息。
    """
    id: str = ""
    name: str = ""
    arguments: str = ""  # JSON 字符串，需要累積


# =============================================================================
# Token Counter
# =============================================================================


class TokenCounter:
    """Token 計數器

    使用 tiktoken 進行準確計數，如果不可用則使用估算。
    """

    def __init__(self, model: str = "gpt-4"):
        """初始化計數器

        Args:
            model: 模型名稱，用於選擇正確的 encoding
        """
        self._model = model
        self._encoding = None

        if HAS_TIKTOKEN:
            try:
                # 嘗試獲取模型對應的 encoding
                self._encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                # 使用 cl100k_base 作為默認（適用於 GPT-4 系列）
                self._encoding = tiktoken.get_encoding("cl100k_base")
            logger.debug(f"TokenCounter initialized with tiktoken for {model}")
        else:
            logger.warning("tiktoken not available, using estimation for token counting")

    def count_tokens(self, text: str) -> int:
        """計算文本的 token 數

        Args:
            text: 要計數的文本

        Returns:
            Token 數量
        """
        if not text:
            return 0

        if self._encoding:
            return len(self._encoding.encode(text))
        else:
            # 估算：平均每 4 字符約 1 token
            return len(text) // 4 + 1

    def count_messages(self, messages: List[Dict[str, Any]]) -> int:
        """計算訊息列表的 token 數

        Args:
            messages: OpenAI 格式的訊息列表

        Returns:
            Token 數量
        """
        total = 0

        for msg in messages:
            # 每條訊息約 4 tokens 開銷（role, content 標記等）
            total += 4

            if "content" in msg and msg["content"]:
                total += self.count_tokens(msg["content"])

            if "name" in msg:
                total += 1  # name 額外開銷

            if "function_call" in msg:
                if "name" in msg["function_call"]:
                    total += self.count_tokens(msg["function_call"]["name"])
                if "arguments" in msg["function_call"]:
                    total += self.count_tokens(msg["function_call"]["arguments"])

            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    total += 3  # tool call 開銷
                    if "function" in tc:
                        if "name" in tc["function"]:
                            total += self.count_tokens(tc["function"]["name"])
                        if "arguments" in tc["function"]:
                            total += self.count_tokens(tc["function"]["arguments"])

        # 額外開銷
        total += 3  # 訊息結尾標記

        return total


# =============================================================================
# Streaming LLM Handler
# =============================================================================


class StreamingLLMHandler:
    """串流 LLM 處理器

    處理 Azure OpenAI 的串流回應，提供:
    - 實時內容串流
    - 工具調用解析
    - Token 計數追蹤
    - 錯誤處理與恢復

    Example:
        ```python
        handler = StreamingLLMHandler(
            endpoint="https://xxx.openai.azure.com/",
            api_key="your-key",
            deployment_name="gpt-4",
        )

        async for event in handler.stream(
            messages=[{"role": "user", "content": "Hello"}],
            session_id="session-123",
            execution_id="exec-456",
        ):
            print(event.to_json())
        ```
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: str = "2024-02-01",
        config: Optional[StreamConfig] = None,
    ):
        """初始化處理器

        Args:
            endpoint: Azure OpenAI 端點
            api_key: API 密鑰
            deployment_name: 部署名稱
            api_version: API 版本
            config: 串流配置
        """
        import os

        self._endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self._api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self._deployment_name = deployment_name or os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"
        )
        self._api_version = api_version
        self._config = config or StreamConfig()

        # 驗證配置
        if not self._endpoint:
            raise ValueError("Azure OpenAI endpoint is required")
        if not self._api_key:
            raise ValueError("Azure OpenAI API key is required")

        # 創建客戶端
        self._client = AsyncAzureOpenAI(
            azure_endpoint=self._endpoint,
            api_key=self._api_key,
            api_version=self._api_version,
            timeout=self._config.timeout,
            max_retries=0,  # 我們自己處理重試
        )

        # Token 計數器
        self._token_counter = TokenCounter(self._deployment_name)

        # 狀態
        self._state = StreamState.IDLE
        self._cancel_flag = False

        logger.info(
            f"StreamingLLMHandler initialized: "
            f"endpoint={self._endpoint[:30]}..., "
            f"deployment={self._deployment_name}"
        )

    # =========================================================================
    # Public Methods
    # =========================================================================

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        execution_id: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """串流執行

        Args:
            messages: OpenAI 格式訊息列表
            session_id: Session ID
            execution_id: 執行 ID
            tools: OpenAI 工具定義列表
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 額外參數

        Yields:
            ExecutionEvent: 執行事件
        """
        self._state = StreamState.CONNECTING
        self._cancel_flag = False

        stats = StreamStats(start_time=datetime.utcnow())

        # 計算 prompt tokens
        stats.prompt_tokens = self._token_counter.count_messages(messages)

        try:
            # 發送開始事件
            yield ExecutionEventFactory.started(
                session_id=session_id,
                execution_id=execution_id,
            )

            # 調用 API（帶重試）
            response_stream = await self._call_with_retry(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            self._state = StreamState.STREAMING

            # 處理串流
            content_buffer = []
            tool_calls_buffer: Dict[int, ToolCallDelta] = {}
            finish_reason = None

            # 心跳任務
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(session_id, execution_id)
            )

            try:
                async for chunk in response_stream:
                    if self._cancel_flag:
                        break

                    # 記錄首個 token 時間
                    if stats.first_token_time is None and chunk.choices:
                        stats.first_token_time = datetime.utcnow()
                        logger.debug(
                            f"First token received in {stats.time_to_first_token_ms}ms"
                        )

                    # 處理 chunk
                    for choice in chunk.choices:
                        delta = choice.delta

                        # 內容 delta
                        if delta.content:
                            content_buffer.append(delta.content)
                            stats.chunk_count += 1
                            stats.total_chars += len(delta.content)

                            yield ExecutionEventFactory.content_delta(
                                session_id=session_id,
                                execution_id=execution_id,
                                delta=delta.content,
                            )

                        # 工具調用 delta
                        if delta.tool_calls:
                            for tc_delta in delta.tool_calls:
                                idx = tc_delta.index
                                if idx not in tool_calls_buffer:
                                    tool_calls_buffer[idx] = ToolCallDelta()

                                tc = tool_calls_buffer[idx]
                                if tc_delta.id:
                                    tc.id = tc_delta.id
                                if tc_delta.function and tc_delta.function.name:
                                    tc.name = tc_delta.function.name
                                if tc_delta.function and tc_delta.function.arguments:
                                    tc.arguments += tc_delta.function.arguments

                        # 完成原因
                        if choice.finish_reason:
                            finish_reason = choice.finish_reason

                    # 使用量信息（最後的 chunk 可能有）
                    if chunk.usage:
                        stats.prompt_tokens = chunk.usage.prompt_tokens
                        stats.completion_tokens = chunk.usage.completion_tokens

            finally:
                # 取消心跳
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

            # 處理工具調用
            if tool_calls_buffer and finish_reason == "tool_calls":
                self._state = StreamState.PROCESSING_TOOLS

                for idx in sorted(tool_calls_buffer.keys()):
                    tc = tool_calls_buffer[idx]
                    try:
                        arguments = self._parse_tool_arguments(tc.arguments)
                    except Exception as e:
                        logger.warning(f"Failed to parse tool arguments: {e}")
                        arguments = {"raw": tc.arguments}

                    yield ExecutionEventFactory.tool_call(
                        session_id=session_id,
                        execution_id=execution_id,
                        tool_call_id=tc.id,
                        tool_name=tc.name,
                        arguments=arguments,
                    )

            # 估算 completion tokens（如果 API 沒有返回）
            if stats.completion_tokens == 0:
                full_content = "".join(content_buffer)
                stats.completion_tokens = self._token_counter.count_tokens(full_content)

            stats.end_time = datetime.utcnow()
            self._state = StreamState.COMPLETED

            # 發送完成事件
            yield ExecutionEventFactory.done(
                session_id=session_id,
                execution_id=execution_id,
                finish_reason=finish_reason or "stop",
                prompt_tokens=stats.prompt_tokens,
                completion_tokens=stats.completion_tokens,
                ttft_ms=stats.time_to_first_token_ms,
                duration_ms=stats.total_duration_ms,
            )

            logger.info(
                f"Stream completed: {stats.total_tokens} tokens, "
                f"TTFT={stats.time_to_first_token_ms}ms, "
                f"total={stats.total_duration_ms}ms"
            )

        except asyncio.CancelledError:
            self._state = StreamState.CANCELLED
            logger.info(f"Stream cancelled for execution {execution_id}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message="Stream cancelled",
                error_code="CANCELLED",
            )

        except APITimeoutError as e:
            self._state = StreamState.ERROR
            logger.error(f"Stream timeout: {e}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"Stream timeout: {e}",
                error_code="TIMEOUT",
            )

        except RateLimitError as e:
            self._state = StreamState.ERROR
            logger.error(f"Rate limit exceeded: {e}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"Rate limit exceeded: {e}",
                error_code="RATE_LIMIT",
            )

        except APIError as e:
            self._state = StreamState.ERROR
            logger.error(f"API error: {e}")
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"API error: {e}",
                error_code="API_ERROR",
            )

        except Exception as e:
            self._state = StreamState.ERROR
            logger.error(f"Unexpected error in stream: {e}", exc_info=True)
            yield ExecutionEventFactory.error(
                session_id=session_id,
                execution_id=execution_id,
                error_message=f"Unexpected error: {e}",
                error_code="STREAM_ERROR",
            )

    async def stream_simple(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        execution_id: str,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """簡化的串流接口

        只返回內容字符串，不返回事件。

        Args:
            messages: 訊息列表
            session_id: Session ID
            execution_id: Execution ID
            **kwargs: 額外參數

        Yields:
            內容字符串片段
        """
        async for event in self.stream(
            messages=messages,
            session_id=session_id,
            execution_id=execution_id,
            **kwargs,
        ):
            if event.event_type == ExecutionEventType.CONTENT_DELTA:
                yield event.content or ""

    def cancel(self) -> None:
        """取消當前串流"""
        self._cancel_flag = True
        logger.info("Stream cancellation requested")

    @property
    def state(self) -> StreamState:
        """獲取當前狀態"""
        return self._state

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _call_with_retry(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        temperature: float,
        max_tokens: int,
    ) -> Any:
        """帶重試的 API 調用

        Args:
            messages: 訊息列表
            tools: 工具列表
            temperature: 溫度
            max_tokens: 最大 tokens

        Returns:
            串流響應對象

        Raises:
            APIError: API 錯誤
        """
        last_error = None

        for attempt in range(self._config.max_retries):
            try:
                # 構建請求參數
                params = {
                    "model": self._deployment_name,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True,
                    "stream_options": {"include_usage": True},
                }

                # 添加工具（如果有）
                if tools:
                    params["tools"] = tools
                    params["tool_choice"] = "auto"

                return await self._client.chat.completions.create(**params)

            except (APITimeoutError, RateLimitError) as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    delay = min(2 ** attempt, 30)
                    logger.warning(
                        f"Retry {attempt + 1}/{self._config.max_retries} "
                        f"after {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

            except APIError as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    delay = min(2 ** attempt, 30)
                    logger.warning(
                        f"API error, retry {attempt + 1}/{self._config.max_retries}: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise last_error  # type: ignore

    async def _heartbeat_loop(
        self,
        session_id: str,
        execution_id: str,
    ) -> None:
        """心跳循環

        定期發送心跳事件以保持連接活躍。

        Args:
            session_id: Session ID
            execution_id: Execution ID
        """
        while True:
            await asyncio.sleep(self._config.heartbeat_interval)
            # 注意：這裡不能直接 yield，只是用於保持連接
            # 實際心跳在 stream() 方法中處理
            logger.debug(f"Heartbeat for execution {execution_id}")

    def _parse_tool_arguments(self, arguments_str: str) -> Dict[str, Any]:
        """解析工具參數

        Args:
            arguments_str: JSON 字符串

        Returns:
            解析後的字典
        """
        import json

        if not arguments_str:
            return {}

        try:
            return json.loads(arguments_str)
        except json.JSONDecodeError:
            # 嘗試修復常見問題
            cleaned = arguments_str.strip()
            if not cleaned.endswith("}"):
                cleaned += "}"
            return json.loads(cleaned)

    # =========================================================================
    # Context Manager
    # =========================================================================

    async def close(self) -> None:
        """關閉處理器"""
        await self._client.close()
        logger.info("StreamingLLMHandler closed")

    async def __aenter__(self) -> "StreamingLLMHandler":
        """異步上下文管理器進入"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器退出"""
        await self.close()


# =============================================================================
# Factory Functions
# =============================================================================


def create_streaming_handler(
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    deployment_name: Optional[str] = None,
    config: Optional[StreamConfig] = None,
) -> StreamingLLMHandler:
    """創建串流處理器

    Factory 函數，便於依賴注入。

    Args:
        endpoint: Azure OpenAI 端點
        api_key: API 密鑰
        deployment_name: 部署名稱
        config: 串流配置

    Returns:
        StreamingLLMHandler 實例
    """
    return StreamingLLMHandler(
        endpoint=endpoint,
        api_key=api_key,
        deployment_name=deployment_name,
        config=config,
    )

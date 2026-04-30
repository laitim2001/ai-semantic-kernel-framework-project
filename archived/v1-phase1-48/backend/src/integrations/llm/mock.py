# =============================================================================
# IPA Platform - Mock LLM Service
# =============================================================================
# Sprint 34: S34-1 LLMService Interface (8 points)
#
# Mock implementation of LLMServiceProtocol for testing.
# Provides configurable responses without real API calls.
#
# Features:
#   - Configurable responses per prompt pattern
#   - Call tracking for assertions
#   - Simulated latency
#   - Error simulation
# =============================================================================

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

from .protocol import (
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


class MockLLMService:
    """Mock LLM 服務實現。

    用於測試的 LLM 服務，提供可配置的回應。

    Attributes:
        responses: 預設回應字典，鍵為 prompt 模式，值為回應
        default_response: 無匹配時的預設回應
        latency: 模擬延遲（秒）
        call_count: 調用計數
        call_history: 調用歷史記錄

    Example:
        ```python
        # 基本使用
        mock = MockLLMService(default_response="Hello!")
        response = await mock.generate("Hi")  # Returns "Hello!"

        # 模式匹配
        mock = MockLLMService(responses={
            "decompose.*task": '{"subtasks": []}',
            "analyze.*risk": '{"risk_level": "low"}',
        })

        # 錯誤模擬
        mock = MockLLMService(error_on_call=3)  # 第3次調用時拋出錯誤
        ```
    """

    def __init__(
        self,
        responses: Optional[Dict[str, str]] = None,
        default_response: str = "This is a mock LLM response.",
        latency: float = 0.0,
        error_on_call: Optional[int] = None,
        error_type: str = "service",
        structured_responses: Optional[Dict[str, Dict[str, Any]]] = None,
    ):
        """初始化 Mock LLM 服務。

        Args:
            responses: 回應字典，鍵為正則表達式模式，值為對應回應
            default_response: 預設文本回應
            latency: 模擬延遲（秒），預設 0
            error_on_call: 在第 N 次調用時拋出錯誤
            error_type: 錯誤類型 ("service", "timeout", "rate_limit")
            structured_responses: 結構化回應字典，用於 generate_structured
        """
        self.responses = responses or {}
        self.default_response = default_response
        self.latency = latency
        self.error_on_call = error_on_call
        self.error_type = error_type
        self.structured_responses = structured_responses or {}

        # 追蹤
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        self.last_prompt: Optional[str] = None
        self.last_schema: Optional[Dict[str, Any]] = None

        # 統計
        self.generate_count = 0
        self.generate_structured_count = 0

        logger.info(
            f"MockLLMService initialized: "
            f"responses={len(self.responses)}, "
            f"latency={self.latency}s"
        )

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """生成模擬文本回應。

        Args:
            prompt: 輸入提示詞
            max_tokens: 最大 token 數（忽略）
            temperature: 溫度參數（忽略）
            stop: 停止序列（忽略）
            **kwargs: 額外參數

        Returns:
            匹配的回應或預設回應

        Raises:
            LLMServiceError: 如果配置了錯誤模擬
        """
        self.call_count += 1
        self.generate_count += 1
        self.last_prompt = prompt

        # 記錄調用
        self.call_history.append({
            "type": "generate",
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "kwargs": kwargs,
        })

        # 模擬延遲
        if self.latency > 0:
            await asyncio.sleep(self.latency)

        # 錯誤模擬
        if self.error_on_call and self.call_count == self.error_on_call:
            self._raise_configured_error()

        # 查找匹配的回應
        response = self._find_matching_response(prompt)

        logger.debug(f"MockLLMService.generate: prompt='{prompt[:50]}...' -> '{response[:50]}...'")
        return response

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """生成模擬結構化回應。

        Args:
            prompt: 輸入提示詞
            output_schema: 預期的輸出 schema
            max_tokens: 最大 token 數（忽略）
            temperature: 溫度參數（忽略）
            **kwargs: 額外參數

        Returns:
            匹配的結構化回應或基於 schema 生成的預設值

        Raises:
            LLMServiceError: 如果配置了錯誤模擬
        """
        self.call_count += 1
        self.generate_structured_count += 1
        self.last_prompt = prompt
        self.last_schema = output_schema

        # 記錄調用
        self.call_history.append({
            "type": "generate_structured",
            "prompt": prompt,
            "output_schema": output_schema,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "kwargs": kwargs,
        })

        # 模擬延遲
        if self.latency > 0:
            await asyncio.sleep(self.latency)

        # 錯誤模擬
        if self.error_on_call and self.call_count == self.error_on_call:
            self._raise_configured_error()

        # 查找匹配的結構化回應
        response = self._find_matching_structured_response(prompt, output_schema)

        logger.debug(
            f"MockLLMService.generate_structured: "
            f"prompt='{prompt[:50]}...' -> {json.dumps(response)[:100]}..."
        )
        return response

    def _find_matching_response(self, prompt: str) -> str:
        """查找匹配的文本回應。

        Args:
            prompt: 輸入提示詞

        Returns:
            匹配的回應或預設回應
        """
        for pattern, response in self.responses.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                return response
        return self.default_response

    def _find_matching_structured_response(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        """查找匹配的結構化回應。

        Args:
            prompt: 輸入提示詞
            output_schema: 輸出 schema

        Returns:
            匹配的結構化回應或基於 schema 的預設值
        """
        # 先檢查 structured_responses
        for pattern, response in self.structured_responses.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                return response

        # 然後檢查 responses（嘗試解析 JSON）
        for pattern, response in self.responses.items():
            if re.search(pattern, prompt, re.IGNORECASE):
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    pass

        # 基於 schema 生成預設值
        return self._generate_default_from_schema(output_schema)

    def _generate_default_from_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """根據 schema 生成預設值。

        Args:
            schema: JSON Schema

        Returns:
            預設值字典
        """
        result = {}
        for key, value_type in schema.items():
            if isinstance(value_type, str):
                if value_type == "string":
                    result[key] = f"mock_{key}"
                elif value_type == "number" or value_type == "integer":
                    result[key] = 0
                elif value_type == "boolean":
                    result[key] = False
                elif value_type == "array":
                    result[key] = []
                elif value_type == "object":
                    result[key] = {}
                else:
                    result[key] = f"mock_{key}"
            elif isinstance(value_type, list):
                # 數組類型
                result[key] = []
            elif isinstance(value_type, dict):
                # 嵌套對象
                result[key] = self._generate_default_from_schema(value_type)
            else:
                result[key] = None
        return result

    def _raise_configured_error(self) -> None:
        """拋出配置的錯誤類型。

        Raises:
            LLMServiceError: 服務錯誤
            LLMTimeoutError: 超時錯誤
            LLMRateLimitError: 速率限制錯誤
        """
        if self.error_type == "timeout":
            raise LLMTimeoutError("Simulated timeout error")
        elif self.error_type == "rate_limit":
            raise LLMRateLimitError("Simulated rate limit error", retry_after=10.0)
        else:
            raise LLMServiceError("Simulated service error")

    def reset(self) -> None:
        """重置所有追蹤狀態。"""
        self.call_count = 0
        self.generate_count = 0
        self.generate_structured_count = 0
        self.call_history.clear()
        self.last_prompt = None
        self.last_schema = None
        logger.debug("MockLLMService reset")

    def set_response(self, pattern: str, response: Union[str, Dict[str, Any]]) -> None:
        """動態設置回應。

        Args:
            pattern: 正則表達式模式
            response: 對應回應（字符串或字典）
        """
        if isinstance(response, dict):
            self.structured_responses[pattern] = response
            self.responses[pattern] = json.dumps(response)
        else:
            self.responses[pattern] = response

    def assert_called(self) -> None:
        """斷言服務被調用過。

        Raises:
            AssertionError: 如果未被調用
        """
        assert self.call_count > 0, "MockLLMService was not called"

    def assert_called_times(self, n: int) -> None:
        """斷言服務被調用了指定次數。

        Args:
            n: 預期調用次數

        Raises:
            AssertionError: 如果調用次數不符
        """
        assert self.call_count == n, (
            f"Expected {n} calls, got {self.call_count}"
        )

    def assert_last_prompt_contains(self, text: str) -> None:
        """斷言最後一個 prompt 包含指定文本。

        Args:
            text: 預期包含的文本

        Raises:
            AssertionError: 如果不包含
        """
        assert self.last_prompt is not None, "No prompt recorded"
        assert text in self.last_prompt, (
            f"Expected '{text}' in prompt, got: {self.last_prompt[:100]}..."
        )

    async def close(self) -> None:
        """關閉服務（無操作）。"""
        logger.debug("MockLLMService closed (no-op)")

    async def __aenter__(self) -> "MockLLMService":
        """異步上下文管理器進入。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器退出。"""
        await self.close()

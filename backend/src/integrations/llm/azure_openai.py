# =============================================================================
# IPA Platform - Azure OpenAI LLM Service
# =============================================================================
# Sprint 34: S34-1 LLMService Interface (8 points)
#
# Production implementation of LLMServiceProtocol using Azure OpenAI.
# Provides async text generation and structured JSON output capabilities.
#
# Features:
#   - Async Azure OpenAI integration
#   - Automatic retry with exponential backoff
#   - Rate limit handling
#   - Structured JSON output with schema validation
#   - Comprehensive error handling
# =============================================================================

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from openai import AsyncAzureOpenAI, APIError, RateLimitError, APITimeoutError

from .protocol import (
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMParseError,
    LLMValidationError,
)

logger = logging.getLogger(__name__)


class AzureOpenAILLMService:
    """Azure OpenAI LLM 服務實現。

    使用 Azure OpenAI API 實現 LLMServiceProtocol。
    支援文本生成和結構化 JSON 輸出。

    Attributes:
        endpoint: Azure OpenAI 端點 URL
        api_key: Azure OpenAI API 密鑰
        deployment_name: 部署名稱 (模型名稱)
        api_version: API 版本
        max_retries: 最大重試次數
        timeout: 請求超時時間（秒）

    Example:
        ```python
        service = AzureOpenAILLMService(
            endpoint="https://xxx.openai.azure.com/",
            api_key="your-api-key",
            deployment_name="gpt-4o",
        )

        # 文本生成
        response = await service.generate("Explain quantum computing")

        # 結構化輸出
        result = await service.generate_structured(
            prompt="Extract person info",
            output_schema={"name": "string", "age": "number"}
        )
        ```
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: str = "2024-02-01",
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """初始化 Azure OpenAI 服務。

        Args:
            endpoint: Azure OpenAI 端點 URL，如未提供則從環境變量讀取
            api_key: Azure OpenAI API 密鑰，如未提供則從環境變量讀取
            deployment_name: 部署名稱，如未提供則從環境變量讀取
            api_version: API 版本，預設 2024-02-01
            max_retries: 最大重試次數，預設 3
            timeout: 請求超時時間（秒），預設 60

        Raises:
            ValueError: 當必要參數缺失時
        """
        import os

        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment_name = deployment_name or os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"
        )
        self.api_version = api_version
        self.max_retries = max_retries
        self.timeout = timeout

        if not self.endpoint:
            raise ValueError(
                "Azure OpenAI endpoint is required. "
                "Set AZURE_OPENAI_ENDPOINT environment variable or pass endpoint parameter."
            )
        if not self.api_key:
            raise ValueError(
                "Azure OpenAI API key is required. "
                "Set AZURE_OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
            timeout=self.timeout,
            max_retries=0,  # 我們自己處理重試邏輯
        )

        logger.info(
            f"AzureOpenAILLMService initialized: "
            f"endpoint={self.endpoint[:30]}..., "
            f"deployment={self.deployment_name}"
        )

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """生成文本回應。

        使用 Azure OpenAI Chat Completions API 生成文本。

        Args:
            prompt: 輸入提示詞
            max_tokens: 最大生成 token 數
            temperature: 創造性參數 (0-1)
            stop: 停止序列列表
            **kwargs: 額外參數（如 system_message）

        Returns:
            生成的文本字符串

        Raises:
            LLMServiceError: LLM 調用失敗
            LLMTimeoutError: 調用超時
            LLMRateLimitError: 達到速率限制
        """
        system_message = kwargs.get(
            "system_message",
            "You are a helpful AI assistant for enterprise automation tasks.",
        )

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        return await self._call_with_retry(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )

    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """生成結構化 JSON 回應。

        使用特殊的系統提示確保輸出為有效 JSON。

        Args:
            prompt: 輸入提示詞
            output_schema: 預期的輸出 JSON Schema
            max_tokens: 最大生成 token 數
            temperature: 創造性參數（較低以提高穩定性）
            **kwargs: 額外參數

        Returns:
            解析後的 JSON 對象

        Raises:
            LLMServiceError: LLM 調用失敗
            LLMParseError: JSON 解析失敗
            LLMValidationError: 輸出不符合 schema
        """
        schema_str = json.dumps(output_schema, indent=2, ensure_ascii=False)

        system_message = f"""You are a JSON generator. You MUST respond with valid JSON only.
No explanations, no markdown code blocks, just pure JSON.

Your response must conform to this schema:
{schema_str}

IMPORTANT:
- Output ONLY valid JSON
- No markdown formatting (no ```json or ```)
- No explanatory text before or after the JSON
- Ensure all required fields are present"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ]

        response_text = await self._call_with_retry(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=None,
        )

        # 解析 JSON
        try:
            # 嘗試清理可能的 markdown 格式
            cleaned = self._clean_json_response(response_text)
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}, raw response: {response_text[:200]}")
            raise LLMParseError(
                f"Failed to parse JSON response: {e}",
                raw_response=response_text,
                cause=e,
            )

        # 基本 schema 驗證
        if not self._validate_schema(result, output_schema):
            raise LLMValidationError(
                "Response does not match expected schema",
                expected_schema=output_schema,
                actual_output=result,
            )

        return result

    async def _call_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float,
        stop: Optional[List[str]],
    ) -> str:
        """帶重試的 API 調用。

        實現指數退避重試策略。

        Args:
            messages: 消息列表
            max_tokens: 最大 token 數
            temperature: 溫度參數
            stop: 停止序列

        Returns:
            生成的文本

        Raises:
            LLMServiceError: 所有重試失敗後
            LLMTimeoutError: 超時
            LLMRateLimitError: 速率限制
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop,
                )

                content = response.choices[0].message.content
                if content is None:
                    raise LLMServiceError("Empty response from LLM")

                logger.debug(
                    f"LLM call successful: "
                    f"tokens_used={response.usage.total_tokens if response.usage else 'N/A'}"
                )

                return content

            except APITimeoutError as e:
                logger.warning(f"LLM timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                last_error = e
                if attempt < self.max_retries - 1:
                    await self._exponential_backoff(attempt)
                else:
                    raise LLMTimeoutError(f"LLM call timed out after {self.max_retries} attempts", cause=e)

            except RateLimitError as e:
                retry_after = self._extract_retry_after(e)
                logger.warning(
                    f"LLM rate limit (attempt {attempt + 1}/{self.max_retries}): "
                    f"retry_after={retry_after}s"
                )
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(retry_after or (2 ** attempt))
                else:
                    raise LLMRateLimitError(
                        f"Rate limit exceeded after {self.max_retries} attempts",
                        retry_after=retry_after,
                        cause=e,
                    )

            except APIError as e:
                logger.error(f"LLM API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                last_error = e
                if attempt < self.max_retries - 1:
                    await self._exponential_backoff(attempt)
                else:
                    raise LLMServiceError(f"LLM API error: {e}", cause=e)

            except Exception as e:
                logger.error(f"Unexpected error in LLM call: {e}")
                raise LLMServiceError(f"Unexpected error: {e}", cause=e)

        # 不應該到達這裡
        raise LLMServiceError(
            f"All {self.max_retries} attempts failed",
            cause=last_error,
        )

    async def _exponential_backoff(self, attempt: int) -> None:
        """指數退避等待。

        Args:
            attempt: 當前嘗試次數（0-based）
        """
        delay = min(2 ** attempt, 30)  # 最大 30 秒
        logger.debug(f"Backing off for {delay}s before retry")
        await asyncio.sleep(delay)

    def _extract_retry_after(self, error: RateLimitError) -> Optional[float]:
        """從錯誤中提取 retry-after 時間。

        Args:
            error: RateLimitError 異常

        Returns:
            等待秒數，如無法解析則返回 None
        """
        try:
            # 嘗試從錯誤消息中解析
            if hasattr(error, "response") and error.response:
                retry_after = error.response.headers.get("retry-after")
                if retry_after:
                    return float(retry_after)
        except (ValueError, AttributeError):
            pass
        return None

    def _clean_json_response(self, response: str) -> str:
        """清理 LLM 回應中的 JSON。

        移除可能的 markdown 格式和額外文本。

        Args:
            response: 原始回應

        Returns:
            清理後的 JSON 字符串
        """
        # 移除 markdown 代碼塊
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        # 嘗試找到 JSON 對象
        response = response.strip()

        # 如果不是以 { 或 [ 開頭，嘗試找到它們
        if not response.startswith("{") and not response.startswith("["):
            # 找到第一個 { 或 [
            brace_idx = response.find("{")
            bracket_idx = response.find("[")

            if brace_idx >= 0 and (bracket_idx < 0 or brace_idx < bracket_idx):
                response = response[brace_idx:]
            elif bracket_idx >= 0:
                response = response[bracket_idx:]

        # 找到最後一個 } 或 ]
        if response:
            last_brace = response.rfind("}")
            last_bracket = response.rfind("]")
            end_idx = max(last_brace, last_bracket)
            if end_idx >= 0:
                response = response[: end_idx + 1]

        return response

    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """基本 schema 驗證。

        檢查必要的鍵是否存在。這是一個簡化的驗證，
        不進行完整的 JSON Schema 驗證。

        Args:
            data: 要驗證的數據
            schema: 預期的 schema

        Returns:
            True 如果驗證通過
        """
        # 簡單驗證：檢查頂層鍵
        for key in schema:
            if key not in data:
                logger.warning(f"Schema validation: missing key '{key}'")
                return False
        return True

    async def close(self) -> None:
        """關閉客戶端連接。"""
        await self._client.close()
        logger.info("AzureOpenAILLMService closed")

    async def __aenter__(self) -> "AzureOpenAILLMService":
        """異步上下文管理器進入。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """異步上下文管理器退出。"""
        await self.close()

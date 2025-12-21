# =============================================================================
# IPA Platform - LLM Service Protocol
# =============================================================================
# Sprint 34: S34-1 LLMService Interface (8 points)
#
# Defines the protocol (interface) for LLM services.
# All LLM implementations must conform to this interface.
#
# Implementations:
#   - AzureOpenAILLMService: Production Azure OpenAI
#   - MockLLMService: Testing with configurable responses
#   - CachedLLMService: Wrapper with caching support
# =============================================================================

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMServiceProtocol(Protocol):
    """LLM 服務協議。

    所有 LLM 服務實現必須遵循此接口。這是 Phase 2 擴展功能
    (TaskDecomposer, DecisionEngine, TrialAndErrorEngine) 使用的
    LLM 服務標準接口。

    Example:
        ```python
        class MyLLMService:
            async def generate(self, prompt: str, max_tokens: int = 2000, ...) -> str:
                # Implementation
                pass

            async def generate_structured(self, prompt: str, output_schema: dict, ...) -> dict:
                # Implementation
                pass

        # Usage
        service: LLMServiceProtocol = MyLLMService()
        response = await service.generate("Hello")
        ```

    Note:
        此協議使用 @runtime_checkable 裝飾器，允許使用 isinstance() 檢查。
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """生成文本回應。

        使用 LLM 生成自由格式的文本回應。

        Args:
            prompt: 輸入提示詞
            max_tokens: 最大生成 token 數，預設 2000
            temperature: 創造性參數 (0-1)，預設 0.7
                - 0: 確定性輸出
                - 1: 最大創造性
            stop: 停止序列列表
            **kwargs: 額外的實現特定參數

        Returns:
            生成的文本字符串

        Raises:
            LLMServiceError: LLM 調用失敗時
            LLMTimeoutError: 調用超時時
            LLMRateLimitError: 達到速率限制時

        Example:
            ```python
            response = await service.generate(
                prompt="Explain quantum computing in simple terms",
                max_tokens=500,
                temperature=0.5
            )
            print(response)  # "Quantum computing uses..."
            ```
        """
        ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        output_schema: Dict[str, Any],
        max_tokens: int = 2000,
        temperature: float = 0.3,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """生成結構化 JSON 回應。

        使用 LLM 生成符合指定 schema 的 JSON 對象。
        內部會自動處理 prompt 格式化和 JSON 解析。

        Args:
            prompt: 輸入提示詞
            output_schema: 預期的輸出 JSON Schema
            max_tokens: 最大生成 token 數，預設 2000
            temperature: 創造性參數，預設 0.3（較低以提高穩定性）
            **kwargs: 額外的實現特定參數

        Returns:
            解析後的 JSON 對象（dict）

        Raises:
            LLMServiceError: LLM 調用失敗時
            LLMParseError: JSON 解析失敗時
            LLMValidationError: 輸出不符合 schema 時

        Example:
            ```python
            schema = {
                "name": "string",
                "age": "number",
                "skills": ["string"]
            }
            result = await service.generate_structured(
                prompt="Extract person info from: John is 30 years old, knows Python and JavaScript",
                output_schema=schema
            )
            # result = {"name": "John", "age": 30, "skills": ["Python", "JavaScript"]}
            ```
        """
        ...


# =============================================================================
# Exception Classes
# =============================================================================

class LLMServiceError(Exception):
    """LLM 服務基礎異常。"""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class LLMTimeoutError(LLMServiceError):
    """LLM 調用超時異常。"""
    pass


class LLMRateLimitError(LLMServiceError):
    """LLM 速率限制異常。"""

    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.retry_after = retry_after


class LLMParseError(LLMServiceError):
    """LLM 回應解析異常。"""

    def __init__(
        self,
        message: str,
        raw_response: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.raw_response = raw_response


class LLMValidationError(LLMServiceError):
    """LLM 輸出驗證異常。"""

    def __init__(
        self,
        message: str,
        expected_schema: Optional[Dict[str, Any]] = None,
        actual_output: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.expected_schema = expected_schema
        self.actual_output = actual_output

# =============================================================================
# LLM Protocol Tests
# =============================================================================
# Sprint 34: S34-3 Unit Tests (4 points)
#
# Tests for LLMServiceProtocol and exception classes.
# =============================================================================

import pytest
from typing import Any, Dict, List, Optional

from src.integrations.llm import (
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMParseError,
    LLMValidationError,
)


class TestLLMServiceProtocol:
    """LLMServiceProtocol 測試。"""

    def test_protocol_is_runtime_checkable(self):
        """測試 Protocol 可在運行時檢查。"""
        # 創建一個實現協議的類
        class MyService:
            async def generate(
                self,
                prompt: str,
                max_tokens: int = 2000,
                temperature: float = 0.7,
                stop: Optional[List[str]] = None,
                **kwargs: Any,
            ) -> str:
                return "response"

            async def generate_structured(
                self,
                prompt: str,
                output_schema: Dict[str, Any],
                max_tokens: int = 2000,
                temperature: float = 0.3,
                **kwargs: Any,
            ) -> Dict[str, Any]:
                return {}

        service = MyService()
        assert isinstance(service, LLMServiceProtocol)

    def test_protocol_rejects_incomplete_implementation(self):
        """測試不完整實現不符合協議。"""
        class IncompleteService:
            async def generate(self, prompt: str) -> str:
                return "response"
            # Missing generate_structured

        service = IncompleteService()
        # 因為缺少 generate_structured，不符合協議
        assert not isinstance(service, LLMServiceProtocol)


class TestLLMServiceError:
    """LLMServiceError 測試。"""

    def test_basic_error(self):
        """測試基本錯誤創建。"""
        error = LLMServiceError("Test error")
        assert str(error) == "Test error"
        assert error.cause is None

    def test_error_with_cause(self):
        """測試帶原因的錯誤。"""
        original = ValueError("Original error")
        error = LLMServiceError("Wrapper error", cause=original)

        assert str(error) == "Wrapper error"
        assert error.cause is original
        assert isinstance(error.cause, ValueError)


class TestLLMTimeoutError:
    """LLMTimeoutError 測試。"""

    def test_timeout_error(self):
        """測試超時錯誤。"""
        error = LLMTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, LLMServiceError)

    def test_timeout_with_cause(self):
        """測試帶原因的超時錯誤。"""
        import asyncio
        original = asyncio.TimeoutError()
        error = LLMTimeoutError("Timeout after 60s", cause=original)

        assert error.cause is original


class TestLLMRateLimitError:
    """LLMRateLimitError 測試。"""

    def test_rate_limit_error(self):
        """測試速率限制錯誤。"""
        error = LLMRateLimitError("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert error.retry_after is None
        assert isinstance(error, LLMServiceError)

    def test_rate_limit_with_retry_after(self):
        """測試帶重試時間的速率限制錯誤。"""
        error = LLMRateLimitError("Rate limit", retry_after=30.0)
        assert error.retry_after == 30.0

    def test_rate_limit_full(self):
        """測試完整的速率限制錯誤。"""
        original = Exception("API Error")
        error = LLMRateLimitError(
            "Rate limit exceeded",
            retry_after=60.0,
            cause=original,
        )

        assert error.retry_after == 60.0
        assert error.cause is original


class TestLLMParseError:
    """LLMParseError 測試。"""

    def test_parse_error(self):
        """測試解析錯誤。"""
        error = LLMParseError("Failed to parse JSON")
        assert str(error) == "Failed to parse JSON"
        assert error.raw_response is None
        assert isinstance(error, LLMServiceError)

    def test_parse_error_with_response(self):
        """測試帶原始回應的解析錯誤。"""
        raw = "This is not valid JSON"
        error = LLMParseError("Parse error", raw_response=raw)

        assert error.raw_response == raw

    def test_parse_error_full(self):
        """測試完整的解析錯誤。"""
        import json
        raw = "{invalid json"
        original = json.JSONDecodeError("Expecting value", raw, 0)
        error = LLMParseError(
            "JSON decode failed",
            raw_response=raw,
            cause=original,
        )

        assert error.raw_response == raw
        assert error.cause is original


class TestLLMValidationError:
    """LLMValidationError 測試。"""

    def test_validation_error(self):
        """測試驗證錯誤。"""
        error = LLMValidationError("Schema mismatch")
        assert str(error) == "Schema mismatch"
        assert error.expected_schema is None
        assert error.actual_output is None
        assert isinstance(error, LLMServiceError)

    def test_validation_error_with_details(self):
        """測試帶詳細信息的驗證錯誤。"""
        expected = {"name": "string", "age": "number"}
        actual = {"name": "John"}  # Missing age

        error = LLMValidationError(
            "Missing required field: age",
            expected_schema=expected,
            actual_output=actual,
        )

        assert error.expected_schema == expected
        assert error.actual_output == actual
        assert "age" in error.expected_schema
        assert "age" not in error.actual_output

    def test_validation_error_inheritance(self):
        """測試驗證錯誤繼承關係。"""
        error = LLMValidationError("Test")

        # 應該可以捕獲為基類
        with pytest.raises(LLMServiceError):
            raise error

        # 也可以捕獲為具體類型
        with pytest.raises(LLMValidationError):
            raise LLMValidationError("Test")

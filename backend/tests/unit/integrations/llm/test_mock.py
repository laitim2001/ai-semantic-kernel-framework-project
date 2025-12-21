# =============================================================================
# Mock LLM Service Tests
# =============================================================================
# Sprint 34: S34-3 Unit Tests (4 points)
#
# Tests for MockLLMService.
# =============================================================================

import pytest
import asyncio

from src.integrations.llm import (
    MockLLMService,
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
)


class TestMockLLMServiceInit:
    """MockLLMService 初始化測試。"""

    def test_default_init(self):
        """測試預設初始化。"""
        mock = MockLLMService()

        assert mock.default_response == "This is a mock LLM response."
        assert mock.latency == 0.0
        assert mock.call_count == 0
        assert len(mock.responses) == 0

    def test_custom_init(self):
        """測試自定義初始化。"""
        mock = MockLLMService(
            responses={"hello": "world"},
            default_response="Custom response",
            latency=0.5,
        )

        assert mock.default_response == "Custom response"
        assert mock.latency == 0.5
        assert "hello" in mock.responses

    def test_protocol_compliance(self):
        """測試符合 LLMServiceProtocol。"""
        mock = MockLLMService()
        assert isinstance(mock, LLMServiceProtocol)


class TestMockLLMServiceGenerate:
    """MockLLMService.generate 測試。"""

    @pytest.mark.asyncio
    async def test_default_response(self):
        """測試預設回應。"""
        mock = MockLLMService(default_response="Hello!")
        response = await mock.generate("Any prompt")

        assert response == "Hello!"
        assert mock.call_count == 1
        assert mock.generate_count == 1

    @pytest.mark.asyncio
    async def test_pattern_matching(self):
        """測試模式匹配回應。"""
        mock = MockLLMService(responses={
            "hello": "Hello response",
            "world": "World response",
        })

        r1 = await mock.generate("say hello")
        r2 = await mock.generate("world is great")
        r3 = await mock.generate("other")

        assert r1 == "Hello response"
        assert r2 == "World response"
        assert r3 == "This is a mock LLM response."

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """測試大小寫不敏感匹配。"""
        mock = MockLLMService(responses={"hello": "Found"})

        r1 = await mock.generate("HELLO")
        r2 = await mock.generate("Hello")
        r3 = await mock.generate("hElLo")

        assert all(r == "Found" for r in [r1, r2, r3])

    @pytest.mark.asyncio
    async def test_regex_pattern(self):
        """測試正則表達式模式。"""
        mock = MockLLMService(responses={
            r"decompos.*task": "Decomposition response",
            r"error|fail": "Error response",
        })

        r1 = await mock.generate("Please decompose this task")
        r2 = await mock.generate("Error occurred")
        r3 = await mock.generate("Something failed")

        assert r1 == "Decomposition response"
        assert r2 == "Error response"
        assert r3 == "Error response"

    @pytest.mark.asyncio
    async def test_latency_simulation(self):
        """測試延遲模擬。"""
        mock = MockLLMService(latency=0.1)

        start = asyncio.get_event_loop().time()
        await mock.generate("test")
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= 0.09  # 允許一些誤差

    @pytest.mark.asyncio
    async def test_call_tracking(self):
        """測試調用追蹤。"""
        mock = MockLLMService()

        await mock.generate("first")
        await mock.generate("second")
        await mock.generate("third")

        assert mock.call_count == 3
        assert mock.generate_count == 3
        assert mock.last_prompt == "third"
        assert len(mock.call_history) == 3
        assert mock.call_history[0]["prompt"] == "first"


class TestMockLLMServiceGenerateStructured:
    """MockLLMService.generate_structured 測試。"""

    @pytest.mark.asyncio
    async def test_structured_response(self):
        """測試結構化回應。"""
        mock = MockLLMService(
            structured_responses={
                "decompose": {"subtasks": ["a", "b"], "confidence": 0.9}
            }
        )

        result = await mock.generate_structured(
            "decompose this task",
            output_schema={"subtasks": "array", "confidence": "number"},
        )

        assert result["subtasks"] == ["a", "b"]
        assert result["confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_json_string_response(self):
        """測試 JSON 字符串回應。"""
        mock = MockLLMService(
            responses={
                "analyze": '{"result": "success", "score": 95}'
            }
        )

        result = await mock.generate_structured(
            "analyze this",
            output_schema={"result": "string", "score": "number"},
        )

        assert result["result"] == "success"
        assert result["score"] == 95

    @pytest.mark.asyncio
    async def test_default_schema_generation(self):
        """測試基於 schema 生成預設值。"""
        mock = MockLLMService()

        result = await mock.generate_structured(
            "no matching pattern",
            output_schema={
                "name": "string",
                "count": "number",
                "active": "boolean",
                "items": "array",
            },
        )

        assert result["name"] == "mock_name"
        assert result["count"] == 0
        assert result["active"] is False
        assert result["items"] == []

    @pytest.mark.asyncio
    async def test_schema_stored(self):
        """測試 schema 被記錄。"""
        mock = MockLLMService()
        schema = {"key": "string"}

        await mock.generate_structured("test", output_schema=schema)

        assert mock.last_schema == schema


class TestMockLLMServiceErrors:
    """MockLLMService 錯誤模擬測試。"""

    @pytest.mark.asyncio
    async def test_error_on_call(self):
        """測試在指定調用時拋出錯誤。"""
        mock = MockLLMService(error_on_call=2)

        await mock.generate("first")  # OK
        with pytest.raises(LLMServiceError):
            await mock.generate("second")  # Error
        await mock.generate("third")  # OK (error was one-time)

    @pytest.mark.asyncio
    async def test_timeout_error(self):
        """測試超時錯誤。"""
        mock = MockLLMService(error_on_call=1, error_type="timeout")

        with pytest.raises(LLMTimeoutError):
            await mock.generate("test")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self):
        """測試速率限制錯誤。"""
        mock = MockLLMService(error_on_call=1, error_type="rate_limit")

        with pytest.raises(LLMRateLimitError) as exc_info:
            await mock.generate("test")

        assert exc_info.value.retry_after == 10.0


class TestMockLLMServiceHelpers:
    """MockLLMService 輔助方法測試。"""

    @pytest.mark.asyncio
    async def test_reset(self):
        """測試重置方法。"""
        mock = MockLLMService()

        await mock.generate("test")
        await mock.generate("test2")

        mock.reset()

        assert mock.call_count == 0
        assert mock.generate_count == 0
        assert mock.last_prompt is None
        assert len(mock.call_history) == 0

    @pytest.mark.asyncio
    async def test_set_response(self):
        """測試動態設置回應。"""
        mock = MockLLMService()

        mock.set_response("new.*pattern", "New response")
        response = await mock.generate("new pattern here")

        assert response == "New response"

    @pytest.mark.asyncio
    async def test_set_structured_response(self):
        """測試動態設置結構化回應。"""
        mock = MockLLMService()

        mock.set_response("data", {"key": "value"})
        result = await mock.generate_structured("get data", output_schema={"key": "string"})

        assert result["key"] == "value"

    @pytest.mark.asyncio
    async def test_assert_called(self):
        """測試 assert_called。"""
        mock = MockLLMService()

        with pytest.raises(AssertionError):
            mock.assert_called()

        await mock.generate("test")
        mock.assert_called()  # Should not raise

    @pytest.mark.asyncio
    async def test_assert_called_times(self):
        """測試 assert_called_times。"""
        mock = MockLLMService()

        await mock.generate("1")
        await mock.generate("2")
        await mock.generate("3")

        mock.assert_called_times(3)

        with pytest.raises(AssertionError):
            mock.assert_called_times(5)

    @pytest.mark.asyncio
    async def test_assert_last_prompt_contains(self):
        """測試 assert_last_prompt_contains。"""
        mock = MockLLMService()

        await mock.generate("Hello world, how are you?")

        mock.assert_last_prompt_contains("world")
        mock.assert_last_prompt_contains("Hello")

        with pytest.raises(AssertionError):
            mock.assert_last_prompt_contains("goodbye")


class TestMockLLMServiceContextManager:
    """MockLLMService 上下文管理器測試。"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """測試異步上下文管理器。"""
        async with MockLLMService() as mock:
            response = await mock.generate("test")
            assert response == "This is a mock LLM response."

    @pytest.mark.asyncio
    async def test_close(self):
        """測試關閉方法。"""
        mock = MockLLMService()
        await mock.close()  # Should not raise

# =============================================================================
# Azure OpenAI LLM Service Tests
# =============================================================================
# Sprint 34: S34-3 Unit Tests (4 points)
#
# Tests for AzureOpenAILLMService.
# Note: These are unit tests that mock the Azure OpenAI client.
# =============================================================================

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.integrations.llm import (
    AzureOpenAILLMService,
    LLMServiceProtocol,
    LLMServiceError,
    LLMTimeoutError,
    LLMRateLimitError,
    LLMParseError,
    LLMValidationError,
)


class TestAzureOpenAILLMServiceInit:
    """AzureOpenAILLMService 初始化測試。"""

    @patch.dict("os.environ", {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_init_from_env(self):
        """測試從環境變量初始化。"""
        service = AzureOpenAILLMService()

        assert service.endpoint == "https://test.openai.azure.com/"
        assert service.api_key == "test-key"
        assert service.deployment_name == "gpt-4o"  # 預設值

    def test_init_with_params(self):
        """測試使用參數初始化。"""
        service = AzureOpenAILLMService(
            endpoint="https://custom.openai.azure.com/",
            api_key="custom-key",
            deployment_name="gpt-4",
            max_retries=5,
            timeout=120.0,
        )

        assert service.endpoint == "https://custom.openai.azure.com/"
        assert service.api_key == "custom-key"
        assert service.deployment_name == "gpt-4"
        assert service.max_retries == 5
        assert service.timeout == 120.0

    @patch.dict("os.environ", {}, clear=True)
    def test_init_missing_endpoint_raises(self):
        """測試缺少端點時拋出錯誤。"""
        with pytest.raises(ValueError) as exc_info:
            AzureOpenAILLMService(api_key="key")

        assert "endpoint" in str(exc_info.value).lower()

    @patch.dict("os.environ", {"AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/"})
    def test_init_missing_api_key_raises(self):
        """測試缺少 API 密鑰時拋出錯誤。"""
        with pytest.raises(ValueError) as exc_info:
            AzureOpenAILLMService()

        assert "api key" in str(exc_info.value).lower()

    def test_protocol_compliance(self):
        """測試符合 LLMServiceProtocol。"""
        service = AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        assert isinstance(service, LLMServiceProtocol)


class TestAzureOpenAILLMServiceGenerate:
    """AzureOpenAILLMService.generate 測試。"""

    @pytest.fixture
    def service(self):
        """創建帶 mock 客戶端的服務。"""
        service = AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        return service

    @pytest.fixture
    def mock_response(self):
        """創建 mock 回應。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "Test response"
        response.usage = MagicMock()
        response.usage.total_tokens = 100
        return response

    @pytest.mark.asyncio
    async def test_generate_success(self, service, mock_response):
        """測試成功生成。"""
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await service.generate("Hello")

        assert result == "Test response"
        service._client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_options(self, service, mock_response):
        """測試帶選項生成。"""
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate(
            prompt="Hello",
            max_tokens=500,
            temperature=0.5,
            stop=["END"],
        )

        call_args = service._client.chat.completions.create.call_args
        assert call_args.kwargs["max_tokens"] == 500
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["stop"] == ["END"]

    @pytest.mark.asyncio
    async def test_generate_with_system_message(self, service, mock_response):
        """測試自定義系統消息。"""
        service._client.chat.completions.create = AsyncMock(return_value=mock_response)

        await service.generate(
            prompt="Hello",
            system_message="You are a helpful bot",
        )

        call_args = service._client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful bot"


class TestAzureOpenAILLMServiceGenerateStructured:
    """AzureOpenAILLMService.generate_structured 測試。"""

    @pytest.fixture
    def service(self):
        """創建帶 mock 客戶端的服務。"""
        service = AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )
        return service

    @pytest.mark.asyncio
    async def test_generate_structured_success(self, service):
        """測試結構化輸出成功。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '{"name": "John", "age": 30}'
        response.usage = MagicMock()
        response.usage.total_tokens = 50

        service._client.chat.completions.create = AsyncMock(return_value=response)

        result = await service.generate_structured(
            prompt="Extract info",
            output_schema={"name": "string", "age": "number"},
        )

        assert result["name"] == "John"
        assert result["age"] == 30

    @pytest.mark.asyncio
    async def test_generate_structured_with_markdown(self, service):
        """測試處理 markdown 格式的 JSON。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '```json\n{"key": "value"}\n```'
        response.usage = MagicMock()

        service._client.chat.completions.create = AsyncMock(return_value=response)

        result = await service.generate_structured(
            prompt="Get data",
            output_schema={"key": "string"},
        )

        assert result["key"] == "value"

    @pytest.mark.asyncio
    async def test_generate_structured_parse_error(self, service):
        """測試 JSON 解析錯誤。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "This is not JSON"
        response.usage = MagicMock()

        service._client.chat.completions.create = AsyncMock(return_value=response)

        with pytest.raises(LLMParseError) as exc_info:
            await service.generate_structured(
                prompt="Get data",
                output_schema={"key": "string"},
            )

        assert exc_info.value.raw_response == "This is not JSON"

    @pytest.mark.asyncio
    async def test_generate_structured_validation_error(self, service):
        """測試 schema 驗證錯誤。"""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = '{"wrong_key": "value"}'
        response.usage = MagicMock()

        service._client.chat.completions.create = AsyncMock(return_value=response)

        with pytest.raises(LLMValidationError) as exc_info:
            await service.generate_structured(
                prompt="Get data",
                output_schema={"expected_key": "string"},
            )

        assert exc_info.value.expected_schema == {"expected_key": "string"}


class TestAzureOpenAILLMServiceRetry:
    """AzureOpenAILLMService 重試機制測試。"""

    @pytest.fixture
    def service(self):
        """創建帶 mock 客戶端的服務。"""
        service = AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
            max_retries=3,
        )
        return service

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, service):
        """測試超時重試。"""
        from openai import APITimeoutError

        success_response = MagicMock()
        success_response.choices = [MagicMock()]
        success_response.choices[0].message.content = "Success"
        success_response.usage = MagicMock()

        # 前兩次超時，第三次成功
        service._client.chat.completions.create = AsyncMock(
            side_effect=[
                APITimeoutError(request=MagicMock()),
                APITimeoutError(request=MagicMock()),
                success_response,
            ]
        )

        result = await service.generate("Hello")

        assert result == "Success"
        assert service._client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_exhausted(self, service):
        """測試重試耗盡後拋出超時錯誤。"""
        from openai import APITimeoutError

        service._client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=MagicMock())
        )

        with pytest.raises(LLMTimeoutError):
            await service.generate("Hello")

        assert service._client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, service):
        """測試速率限制錯誤。"""
        from openai import RateLimitError

        service._client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit",
                response=MagicMock(headers={}),
                body=None,
            )
        )

        with pytest.raises(LLMRateLimitError):
            await service.generate("Hello")


class TestAzureOpenAILLMServiceCleanJson:
    """AzureOpenAILLMService JSON 清理測試。"""

    @pytest.fixture
    def service(self):
        """創建服務。"""
        return AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )

    def test_clean_plain_json(self, service):
        """測試清理純 JSON。"""
        result = service._clean_json_response('{"key": "value"}')
        assert result == '{"key": "value"}'

    def test_clean_markdown_json(self, service):
        """測試清理 markdown JSON。"""
        result = service._clean_json_response('```json\n{"key": "value"}\n```')
        assert result == '{"key": "value"}'

    def test_clean_json_with_text(self, service):
        """測試清理帶前綴文本的 JSON。"""
        result = service._clean_json_response('Here is the data: {"key": "value"}')
        assert result == '{"key": "value"}'

    def test_clean_json_array(self, service):
        """測試清理 JSON 數組。"""
        result = service._clean_json_response('[1, 2, 3]')
        assert result == '[1, 2, 3]'


class TestAzureOpenAILLMServiceValidateSchema:
    """AzureOpenAILLMService schema 驗證測試。"""

    @pytest.fixture
    def service(self):
        """創建服務。"""
        return AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        )

    def test_validate_success(self, service):
        """測試驗證成功。"""
        data = {"name": "John", "age": 30}
        schema = {"name": "string", "age": "number"}

        assert service._validate_schema(data, schema) is True

    def test_validate_missing_key(self, service):
        """測試缺少必要鍵。"""
        data = {"name": "John"}
        schema = {"name": "string", "age": "number"}

        assert service._validate_schema(data, schema) is False

    def test_validate_extra_keys_ok(self, service):
        """測試額外鍵不影響驗證。"""
        data = {"name": "John", "age": 30, "extra": "value"}
        schema = {"name": "string", "age": "number"}

        assert service._validate_schema(data, schema) is True


class TestAzureOpenAILLMServiceContextManager:
    """AzureOpenAILLMService 上下文管理器測試。"""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """測試異步上下文管理器。"""
        async with AzureOpenAILLMService(
            endpoint="https://test.openai.azure.com/",
            api_key="test-key",
        ) as service:
            assert service is not None
            # close() 會在 __aexit__ 中調用

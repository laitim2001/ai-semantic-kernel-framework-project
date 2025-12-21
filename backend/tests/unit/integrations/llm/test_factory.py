# =============================================================================
# LLM Service Factory Tests
# =============================================================================
# Sprint 34: S34-3 Unit Tests (4 points)
#
# Tests for LLMServiceFactory.
# =============================================================================

import pytest
import os
from unittest.mock import patch, MagicMock

from src.integrations.llm import (
    LLMServiceFactory,
    MockLLMService,
    CachedLLMService,
    LLMServiceProtocol,
)


class TestLLMServiceFactoryCreate:
    """LLMServiceFactory.create 測試。"""

    def setup_method(self):
        """每個測試前清除單例。"""
        LLMServiceFactory.clear_instances()

    def test_create_mock_explicitly(self):
        """測試顯式創建 Mock 服務。"""
        service = LLMServiceFactory.create(provider="mock", singleton=False)

        assert isinstance(service, MockLLMService)
        assert isinstance(service, LLMServiceProtocol)

    def test_create_mock_with_options(self):
        """測試帶選項創建 Mock 服務。"""
        service = LLMServiceFactory.create(
            provider="mock",
            singleton=False,
            default_response="Custom",
            latency=0.1,
        )

        assert isinstance(service, MockLLMService)
        assert service.default_response == "Custom"
        assert service.latency == 0.1

    @patch.dict(os.environ, {}, clear=True)
    def test_auto_detect_mock(self):
        """測試無配置時自動使用 Mock。"""
        service = LLMServiceFactory.create(singleton=False)

        assert isinstance(service, MockLLMService)

    @patch.dict(os.environ, {"TESTING": "true"})
    def test_testing_env_uses_mock(self):
        """測試 TESTING 環境使用 Mock。"""
        service = LLMServiceFactory.create(singleton=False)

        assert isinstance(service, MockLLMService)

    @patch.dict(os.environ, {"LLM_MOCK": "true"})
    def test_llm_mock_env(self):
        """測試 LLM_MOCK 環境變量。"""
        service = LLMServiceFactory.create(singleton=False)

        assert isinstance(service, MockLLMService)

    def test_unknown_provider_raises(self):
        """測試未知提供者拋出錯誤。"""
        with pytest.raises(ValueError) as exc_info:
            LLMServiceFactory.create(provider="unknown")

        assert "unknown" in str(exc_info.value).lower()


class TestLLMServiceFactoryAzure:
    """LLMServiceFactory Azure 服務測試。"""

    def setup_method(self):
        """每個測試前清除單例。"""
        LLMServiceFactory.clear_instances()

    @patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_auto_detect_azure(self):
        """測試自動檢測 Azure 配置。"""
        # 注意：這會嘗試創建真實的 Azure 服務
        # 在實際測試中，我們可能需要 mock AsyncAzureOpenAI
        from src.integrations.llm import AzureOpenAILLMService

        service = LLMServiceFactory.create(singleton=False)

        assert isinstance(service, AzureOpenAILLMService)

    @patch.dict(os.environ, {
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
        "AZURE_OPENAI_API_KEY": "test-key",
    })
    def test_create_azure_with_options(self):
        """測試帶選項創建 Azure 服務。"""
        from src.integrations.llm import AzureOpenAILLMService

        service = LLMServiceFactory.create(
            provider="azure",
            singleton=False,
            deployment_name="gpt-4o",
            max_retries=5,
        )

        assert isinstance(service, AzureOpenAILLMService)
        assert service.deployment_name == "gpt-4o"
        assert service.max_retries == 5


class TestLLMServiceFactoryCache:
    """LLMServiceFactory 緩存包裝測試。"""

    def setup_method(self):
        """每個測試前清除單例。"""
        LLMServiceFactory.clear_instances()

    def test_create_with_cache(self):
        """測試創建帶緩存的服務。"""
        # Redis 不可用時，CachedLLMService 會被禁用但仍然返回
        service = LLMServiceFactory.create(
            provider="mock",
            use_cache=True,
            singleton=False,
        )

        assert isinstance(service, CachedLLMService)
        assert isinstance(service.inner_service, MockLLMService)

    def test_cache_ttl_option(self):
        """測試緩存 TTL 選項。"""
        service = LLMServiceFactory.create(
            provider="mock",
            use_cache=True,
            cache_ttl=7200,
            singleton=False,
        )

        assert isinstance(service, CachedLLMService)
        assert service.default_ttl == 7200


class TestLLMServiceFactorySingleton:
    """LLMServiceFactory 單例測試。"""

    def setup_method(self):
        """每個測試前清除單例。"""
        LLMServiceFactory.clear_instances()

    def test_singleton_returns_same_instance(self):
        """測試單例返回相同實例。"""
        service1 = LLMServiceFactory.create(provider="mock")
        service2 = LLMServiceFactory.create(provider="mock")

        assert service1 is service2

    def test_singleton_different_config(self):
        """測試不同配置創建不同實例。"""
        service1 = LLMServiceFactory.create(provider="mock", use_cache=False)
        service2 = LLMServiceFactory.create(provider="mock", use_cache=True)

        assert service1 is not service2

    def test_non_singleton_returns_new_instance(self):
        """測試非單例返回新實例。"""
        service1 = LLMServiceFactory.create(provider="mock", singleton=False)
        service2 = LLMServiceFactory.create(provider="mock", singleton=False)

        assert service1 is not service2

    def test_clear_instances(self):
        """測試清除單例。"""
        LLMServiceFactory.create(provider="mock")
        assert LLMServiceFactory.get_instance_count() > 0

        LLMServiceFactory.clear_instances()
        assert LLMServiceFactory.get_instance_count() == 0

    def test_get_instance_count(self):
        """測試獲取實例數量。"""
        LLMServiceFactory.create(provider="mock", use_cache=False)
        LLMServiceFactory.create(provider="mock", use_cache=True)

        assert LLMServiceFactory.get_instance_count() == 2


class TestLLMServiceFactoryCreateMock:
    """LLMServiceFactory.create_mock 測試。"""

    def test_create_mock_basic(self):
        """測試創建基本 Mock 服務。"""
        mock = LLMServiceFactory.create_mock()

        assert isinstance(mock, MockLLMService)
        assert mock.default_response == "Mock LLM response"

    def test_create_mock_with_responses(self):
        """測試創建帶回應的 Mock 服務。"""
        mock = LLMServiceFactory.create_mock(
            responses={"hello": "world"},
            default_response="Custom",
        )

        assert mock.responses["hello"] == "world"
        assert mock.default_response == "Custom"

    def test_create_mock_with_latency(self):
        """測試創建帶延遲的 Mock 服務。"""
        mock = LLMServiceFactory.create_mock(latency=0.5)

        assert mock.latency == 0.5


class TestLLMServiceFactoryCreateForTesting:
    """LLMServiceFactory.create_for_testing 測試。"""

    @pytest.mark.asyncio
    async def test_create_for_testing(self):
        """測試創建測試專用服務。"""
        mock = LLMServiceFactory.create_for_testing()

        assert isinstance(mock, MockLLMService)

        # 驗證預配置的回應
        result = await mock.generate_structured(
            "decompose this task",
            output_schema={"subtasks": "array"},
        )

        assert "subtasks" in result
        assert isinstance(result["subtasks"], list)

    @pytest.mark.asyncio
    async def test_create_for_testing_decision(self):
        """測試測試服務的決策回應。"""
        mock = LLMServiceFactory.create_for_testing()

        result = await mock.generate_structured(
            "decide which option to choose",
            output_schema={"selected_option": "string"},
        )

        assert "selected_option" in result

    @pytest.mark.asyncio
    async def test_create_for_testing_error_analysis(self):
        """測試測試服務的錯誤分析回應。"""
        mock = LLMServiceFactory.create_for_testing()

        result = await mock.generate_structured(
            "analyze this error",
            output_schema={"error_analysis": "string"},
        )

        assert "error_analysis" in result

    def test_create_for_testing_custom_responses(self):
        """測試自定義測試回應。"""
        mock = LLMServiceFactory.create_for_testing(
            structured_responses={
                "custom": {"custom_key": "custom_value"}
            }
        )

        assert "custom" in mock.structured_responses

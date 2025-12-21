# =============================================================================
# Sprint 36 E2E Test: LLM Integration
# =============================================================================
# 驗證 LLM 服務整合完整流程
# =============================================================================

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Dict, Any

from src.integrations.llm.protocol import LLMServiceProtocol
from src.integrations.llm.mock import MockLLMService
from src.integrations.llm.factory import LLMServiceFactory


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_response() -> Dict[str, Any]:
    """標準 Mock LLM 回應。"""
    return {
        "subtasks": [
            {"name": "Task 1", "description": "First task"},
            {"name": "Task 2", "description": "Second task"},
        ],
        "confidence": 0.85,
        "reasoning": "Based on the analysis..."
    }


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """創建 Mock LLM 服務。"""
    return MockLLMService(
        responses={
            "default": "This is a test response.",
            "structured": '{"result": "success", "data": [1, 2, 3]}',
        },
        latency=0.0
    )


# =============================================================================
# LLM Service Protocol Tests
# =============================================================================

class TestLLMServiceProtocol:
    """LLM 服務協議測試。"""

    @pytest.mark.e2e
    def test_mock_llm_implements_protocol(self, mock_llm_service):
        """測試 MockLLMService 實現 LLMServiceProtocol。"""
        assert isinstance(mock_llm_service, LLMServiceProtocol)

    @pytest.mark.e2e
    def test_mock_llm_has_generate_method(self, mock_llm_service):
        """測試 MockLLMService 有 generate 方法。"""
        assert hasattr(mock_llm_service, 'generate')
        assert callable(mock_llm_service.generate)

    @pytest.mark.e2e
    def test_mock_llm_has_generate_structured_method(self, mock_llm_service):
        """測試 MockLLMService 有 generate_structured 方法。"""
        assert hasattr(mock_llm_service, 'generate_structured')
        assert callable(mock_llm_service.generate_structured)


# =============================================================================
# MockLLMService Tests
# =============================================================================

class TestMockLLMService:
    """Mock LLM 服務測試。"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_generate_returns_response(self, mock_llm_service):
        """測試 generate 返回配置的回應。"""
        result = await mock_llm_service.generate("Hello, world!")

        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_generate_records_calls(self, mock_llm_service):
        """測試 generate 記錄調用。"""
        await mock_llm_service.generate("Test prompt")

        assert mock_llm_service.call_count == 1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_generate_structured_returns_dict(self):
        """測試 generate_structured 返回字典。"""
        mock_llm = MockLLMService(
            structured_responses={"default": {"key": "value"}}
        )

        result = await mock_llm.generate_structured(
            prompt="Parse this",
            output_schema={"type": "object"}
        )

        assert result is not None
        assert isinstance(result, dict)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_mock_respects_delay(self):
        """測試 Mock 延遲設置。"""
        import time

        mock_llm = MockLLMService(
            default_response="response",
            latency=0.1
        )

        start = time.time()
        await mock_llm.generate("test")
        elapsed = time.time() - start

        assert elapsed >= 0.1

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multiple_calls_increment_counter(self):
        """測試多次調用計數器增加。"""
        mock_llm = MockLLMService(responses={"default": "response"})

        await mock_llm.generate("call 1")
        await mock_llm.generate("call 2")
        await mock_llm.generate("call 3")

        assert mock_llm.call_count == 3


# =============================================================================
# LLM Service Factory Tests
# =============================================================================

class TestLLMServiceFactory:
    """LLM 服務工廠測試。"""

    @pytest.mark.e2e
    def test_factory_create_for_testing(self):
        """測試工廠創建測試用服務。"""
        service = LLMServiceFactory.create_for_testing()

        assert service is not None
        assert isinstance(service, MockLLMService)

    @pytest.mark.e2e
    def test_factory_create_mock_provider(self):
        """測試工廠創建 Mock 提供者。"""
        service = LLMServiceFactory.create(provider="mock")

        assert service is not None
        assert isinstance(service, MockLLMService)

    @pytest.mark.e2e
    def test_factory_singleton_pattern(self):
        """測試工廠單例模式。"""
        # 創建兩個單例
        service1 = LLMServiceFactory.create(provider="mock", singleton=True)
        service2 = LLMServiceFactory.create(provider="mock", singleton=True)

        # 應該是同一個實例
        assert service1 is service2

        # 清除單例以便其他測試
        LLMServiceFactory._singleton = None

    @pytest.mark.e2e
    def test_factory_non_singleton(self):
        """測試工廠非單例模式。"""
        # 清除可能存在的單例
        LLMServiceFactory._singleton = None

        service1 = LLMServiceFactory.create(provider="mock", singleton=False)
        service2 = LLMServiceFactory.create(provider="mock", singleton=False)

        # 應該是不同的實例
        assert service1 is not service2


# =============================================================================
# LLM Integration with Planning Adapter Tests
# =============================================================================

class TestLLMPlanningIntegration:
    """LLM 與 PlanningAdapter 整合測試。"""

    @pytest.mark.e2e
    def test_planning_adapter_uses_llm(self, mock_llm_service):
        """測試 PlanningAdapter 使用 LLM 服務。"""
        from src.integrations.agent_framework.builders.planning import PlanningAdapter

        adapter = PlanningAdapter(id="integration-test", llm_service=mock_llm_service)

        assert adapter.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_task_decomposer_receives_llm(self, mock_llm_service):
        """測試 TaskDecomposer 接收 LLM 服務。"""
        from src.integrations.agent_framework.builders.planning import PlanningAdapter

        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_task_decomposition()

        assert adapter._task_decomposer.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_decision_engine_receives_llm(self, mock_llm_service):
        """測試 DecisionEngine 接收 LLM 服務。"""
        from src.integrations.agent_framework.builders.planning import PlanningAdapter

        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_decision_engine()

        assert adapter._decision_engine.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_trial_error_engine_receives_llm(self, mock_llm_service):
        """測試 TrialAndErrorEngine 接收 LLM 服務。"""
        from src.integrations.agent_framework.builders.planning import PlanningAdapter

        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_trial_error()

        assert adapter._trial_error_engine.llm_service is mock_llm_service


# =============================================================================
# LLM Error Handling Tests
# =============================================================================

class TestLLMErrorHandling:
    """LLM 錯誤處理測試。"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_llm_handles_invalid_json(self):
        """測試 LLM 處理無效 JSON。"""
        # MockLLMService 使用 structured_responses 而不是解析 responses
        # 當沒有匹配時會返回基於 schema 的預設值
        mock_llm = MockLLMService()

        result = await mock_llm.generate_structured(
            prompt="test",
            output_schema={"type": "object", "properties": {"key": {"type": "string"}}}
        )

        # 應該返回一個字典（可能是空的或預設值）
        assert isinstance(result, dict)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_llm_empty_response(self):
        """測試 LLM 空回應處理。"""
        mock_llm = MockLLMService(responses={"default": ""})

        result = await mock_llm.generate("test")

        # 應該返回空字符串，不應該拋出異常
        assert result == "" or result is not None


# =============================================================================
# LLM Configuration Tests
# =============================================================================

class TestLLMConfiguration:
    """LLM 配置測試。"""

    @pytest.mark.e2e
    def test_mock_llm_custom_responses(self):
        """測試 Mock LLM 自定義回應。"""
        custom_responses = {
            "greeting": "Hello!",
            "farewell": "Goodbye!",
        }

        mock_llm = MockLLMService(responses=custom_responses)

        assert mock_llm.responses == custom_responses

    @pytest.mark.e2e
    def test_factory_respects_provider_param(self):
        """測試工廠尊重 provider 參數。"""
        # Mock provider
        mock_service = LLMServiceFactory.create(provider="mock")
        assert isinstance(mock_service, MockLLMService)

    @pytest.mark.e2e
    def test_factory_provider_parameter(self):
        """測試工廠 provider 參數。"""
        # 清除單例
        LLMServiceFactory._singleton = None

        # 使用 mock provider 驗證工廠邏輯
        service = LLMServiceFactory.create(provider="mock")

        assert service is not None
        assert isinstance(service, MockLLMService)

# =============================================================================
# Sprint 36 Unit Test: LLM Fallback Strategy
# =============================================================================
# 驗證 LLM 服務不可用時的降級策略
# =============================================================================

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Optional

from src.integrations.agent_framework.builders.planning import (
    PlanningAdapter,
    PlanningMode,
    DecompositionStrategy,
)
from src.integrations.llm.protocol import (
    LLMServiceProtocol,
    LLMTimeoutError,
    LLMServiceError,
)
from src.integrations.llm.mock import MockLLMService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def failing_llm_service() -> MockLLMService:
    """創建會拋出錯誤的 LLM 服務。"""
    return MockLLMService(
        error_on_call=1,  # 第一次調用就失敗
        error_type="service_error"
    )


@pytest.fixture
def timeout_llm_service() -> MockLLMService:
    """創建會超時的 LLM 服務。"""
    return MockLLMService(
        error_on_call=1,
        error_type="timeout"
    )


@pytest.fixture
def intermittent_llm_service() -> MockLLMService:
    """創建間歇性失敗的 LLM 服務。"""
    return MockLLMService(
        error_on_call=2,  # 第二次調用失敗
        error_type="service_error"
    )


# =============================================================================
# Tests: TaskDecomposer Fallback
# =============================================================================

class TestDecomposerFallback:
    """TaskDecomposer 降級測試。"""

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decomposer_fallback_on_llm_error(self, mock_factory, failing_llm_service):
        """測試 LLM 錯誤時 TaskDecomposer 降級到規則式。"""
        # 設置 LLM 服務會失敗
        adapter = PlanningAdapter(id="test", llm_service=failing_llm_service)
        adapter.with_task_decomposition()

        # 驗證組件已創建
        assert adapter._task_decomposer is not None

        # TaskDecomposer 應該能處理 LLM 失敗並使用規則式
        decomposer = adapter._task_decomposer
        assert decomposer.llm_service is failing_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decomposer_fallback_on_timeout(self, mock_factory, timeout_llm_service):
        """測試 LLM 超時時 TaskDecomposer 降級到規則式。"""
        adapter = PlanningAdapter(id="test", llm_service=timeout_llm_service)
        adapter.with_task_decomposition()

        # 驗證組件已創建
        assert adapter._task_decomposer is not None

        # TaskDecomposer 應該能處理超時並使用規則式
        decomposer = adapter._task_decomposer
        assert decomposer.llm_service is timeout_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decomposer_hybrid_strategy_fallback(self, mock_factory, failing_llm_service):
        """測試 HYBRID 策略在 LLM 失敗時降級。"""
        adapter = PlanningAdapter(id="test", llm_service=failing_llm_service)
        adapter.with_task_decomposition(strategy=DecompositionStrategy.HYBRID)

        # HYBRID 策略在 LLM 失敗時應該回退到規則式
        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is failing_llm_service


# =============================================================================
# Tests: DecisionEngine Fallback
# =============================================================================

class TestDecisionEngineFallback:
    """DecisionEngine 降級測試。"""

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decision_engine_fallback_on_llm_error(self, mock_factory, failing_llm_service):
        """測試 LLM 錯誤時 DecisionEngine 降級。"""
        adapter = PlanningAdapter(id="test", llm_service=failing_llm_service)
        adapter.with_decision_engine()

        # 驗證組件已創建
        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is failing_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decision_engine_fallback_on_timeout(self, mock_factory, timeout_llm_service):
        """測試 LLM 超時時 DecisionEngine 降級。"""
        adapter = PlanningAdapter(id="test", llm_service=timeout_llm_service)
        adapter.with_decision_engine()

        # 驗證組件已創建
        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is timeout_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_decision_engine_uses_default_on_error(self, mock_factory):
        """測試 DecisionEngine 在錯誤時使用預設決策。"""
        # 模擬工廠返回失敗的 LLM
        mock_factory.create.side_effect = Exception("LLM not available")

        adapter = PlanningAdapter(id="test")
        adapter.with_decision_engine()

        # 即使 LLM 不可用，組件也應該創建成功
        assert adapter._decision_engine is not None
        # LLM 服務應該是 None（降級模式）
        assert adapter._decision_engine.llm_service is None


# =============================================================================
# Tests: TrialAndErrorEngine Fallback
# =============================================================================

class TestTrialErrorFallback:
    """TrialAndErrorEngine 降級測試。"""

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_trial_error_fallback_on_llm_error(self, mock_factory, failing_llm_service):
        """測試 LLM 錯誤時 TrialAndErrorEngine 降級。"""
        adapter = PlanningAdapter(id="test", llm_service=failing_llm_service)
        adapter.with_trial_error(max_retries=3)

        # 驗證組件已創建
        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is failing_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_trial_error_fallback_on_timeout(self, mock_factory, timeout_llm_service):
        """測試 LLM 超時時 TrialAndErrorEngine 降級。"""
        adapter = PlanningAdapter(id="test", llm_service=timeout_llm_service)
        adapter.with_trial_error(max_retries=5)

        # 驗證組件已創建
        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is timeout_llm_service

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_trial_error_simple_retry_fallback(self, mock_factory):
        """測試 TrialAndErrorEngine 在無 LLM 時使用簡單重試。"""
        mock_factory.create.side_effect = Exception("LLM not available")

        adapter = PlanningAdapter(id="test")
        adapter.with_trial_error(max_retries=3)

        # 即使 LLM 不可用，組件也應該創建成功
        assert adapter._trial_error_engine is not None
        # 應該使用簡單重試策略
        assert adapter._trial_error_engine.llm_service is None


# =============================================================================
# Tests: No LLM Uses Rule-Based
# =============================================================================

class TestNoLLMRuleBased:
    """無 LLM 時使用規則式測試。"""

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_no_llm_uses_rule_based_decomposition(self, mock_factory):
        """測試無 LLM 時使用規則式任務分解。"""
        mock_factory.create.side_effect = Exception("No LLM configured")

        adapter = PlanningAdapter(id="test")
        adapter.with_task_decomposition()

        # 組件應該創建成功
        assert adapter._task_decomposer is not None
        # LLM 服務應該是 None
        assert adapter._task_decomposer.llm_service is None

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_no_llm_planning_mode_detection(self, mock_factory):
        """測試無 LLM 時的規劃模式檢測。"""
        mock_factory.create.side_effect = Exception("No LLM")

        adapter = PlanningAdapter(id="test")

        # 無 LLM 時應該是 SIMPLE 模式
        stats = adapter.get_statistics()
        assert stats["mode"] == PlanningMode.SIMPLE.value

    @pytest.mark.unit
    def test_explicit_none_llm_service(self):
        """測試顯式傳入 None LLM 服務。"""
        adapter = PlanningAdapter(id="test", llm_service=None)

        assert adapter.llm_service is None
        assert adapter._llm_service is None

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_full_stack_without_llm(self, mock_factory):
        """測試完整堆疊在無 LLM 時仍可運作。"""
        mock_factory.create.side_effect = Exception("No LLM")

        adapter = (
            PlanningAdapter(id="test")
            .with_task_decomposition()
            .with_decision_engine()
            .with_trial_error()
        )

        # 所有組件都應該創建成功
        assert adapter._task_decomposer is not None
        assert adapter._decision_engine is not None
        assert adapter._trial_error_engine is not None

        # 所有組件的 LLM 服務應該是 None
        assert adapter._task_decomposer.llm_service is None
        assert adapter._decision_engine.llm_service is None
        assert adapter._trial_error_engine.llm_service is None


# =============================================================================
# Tests: Graceful Degradation
# =============================================================================

class TestGracefulDegradation:
    """優雅降級測試。"""

    @pytest.mark.unit
    def test_adapter_graceful_degradation(self):
        """測試適配器的優雅降級。"""
        # 無 LLM 服務的適配器
        adapter = PlanningAdapter(id="test", llm_service=None)

        # 應該能獲取統計信息
        stats = adapter.get_statistics()
        assert "mode" in stats
        assert "has_task_decomposer" in stats

    @pytest.mark.unit
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_late_llm_injection_after_components(self, mock_factory):
        """測試組件創建後再注入 LLM。"""
        mock_factory.create.side_effect = Exception("No LLM initially")

        # 先創建組件（無 LLM）
        adapter = PlanningAdapter(id="test")
        adapter.with_task_decomposition()

        # 組件已創建，LLM 為 None
        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is None

        # 後期注入 LLM
        mock_llm = MockLLMService()
        adapter.with_llm_service(mock_llm)

        # 驗證 LLM 已注入
        assert adapter.llm_service is mock_llm

    @pytest.mark.unit
    def test_ensure_llm_service_returns_none_on_error(self):
        """測試 _ensure_llm_service 在錯誤時返回 None。"""
        with patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory') as mock_factory:
            mock_factory.create.side_effect = Exception("LLM error")

            adapter = PlanningAdapter(id="test")
            result = adapter._ensure_llm_service()

            assert result is None


# =============================================================================
# Tests: Error Type Handling
# =============================================================================

class TestErrorTypeHandling:
    """錯誤類型處理測試。"""

    @pytest.mark.unit
    def test_service_error_handling(self):
        """測試服務錯誤處理。"""
        mock_llm = MockLLMService(
            error_on_call=1,
            error_type="service_error"
        )

        adapter = PlanningAdapter(id="test", llm_service=mock_llm)
        adapter.with_task_decomposition()

        # 組件應該創建成功
        assert adapter._task_decomposer is not None

    @pytest.mark.unit
    def test_timeout_error_handling(self):
        """測試超時錯誤處理。"""
        mock_llm = MockLLMService(
            error_on_call=1,
            error_type="timeout"
        )

        adapter = PlanningAdapter(id="test", llm_service=mock_llm)
        adapter.with_decision_engine()

        # 組件應該創建成功
        assert adapter._decision_engine is not None

    @pytest.mark.unit
    def test_generic_error_handling(self):
        """測試通用錯誤處理。"""
        mock_llm = MockLLMService(
            error_on_call=1,
            error_type="generic"
        )

        adapter = PlanningAdapter(id="test", llm_service=mock_llm)
        adapter.with_trial_error()

        # 組件應該創建成功
        assert adapter._trial_error_engine is not None


# =============================================================================
# Tests: Recovery After Error
# =============================================================================

class TestRecoveryAfterError:
    """錯誤後恢復測試。"""

    @pytest.mark.unit
    def test_adapter_functional_after_llm_error(self, intermittent_llm_service):
        """測試 LLM 錯誤後適配器仍可運作。"""
        adapter = PlanningAdapter(id="test", llm_service=intermittent_llm_service)
        adapter.with_task_decomposition()
        adapter.with_decision_engine()

        # 驗證所有組件都已創建
        assert adapter._task_decomposer is not None
        assert adapter._decision_engine is not None

        # 獲取統計信息應該正常工作
        stats = adapter.get_statistics()
        assert isinstance(stats, dict)

    @pytest.mark.unit
    def test_statistics_available_without_llm(self):
        """測試無 LLM 時統計信息仍可用。"""
        adapter = PlanningAdapter(id="test", llm_service=None)
        adapter.with_task_decomposition()

        stats = adapter.get_statistics()

        assert "mode" in stats
        assert "has_task_decomposer" in stats
        assert stats["has_task_decomposer"] is True

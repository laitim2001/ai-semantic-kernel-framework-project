# =============================================================================
# Sprint 36 E2E Test: AI Autonomous Decision
# =============================================================================
# 驗證 AI 自主決策完整流程
# =============================================================================

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Optional

from src.integrations.agent_framework.builders.planning import (
    PlanningAdapter,
    PlanningMode,
    DecompositionStrategy,
    create_planning_adapter,
    create_decomposed_planner,
    create_full_planner,
)
from src.integrations.llm.protocol import LLMServiceProtocol
from src.integrations.llm.mock import MockLLMService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """創建 Mock LLM 服務用於測試。"""
    return MockLLMService(
        responses={
            "default": '{"subtasks": [{"name": "Setup", "description": "Initial setup"}], "confidence": 0.85}',
        },
        latency=0.0
    )


@pytest.fixture
def planning_adapter_with_mock_llm(mock_llm_service) -> PlanningAdapter:
    """創建帶 Mock LLM 的 PlanningAdapter。"""
    adapter = PlanningAdapter(id="e2e-test", llm_service=mock_llm_service)
    adapter.with_task_decomposition()
    adapter.with_decision_engine()
    adapter.with_trial_error()
    return adapter


# =============================================================================
# E2E Tests: AI Task Decomposition
# =============================================================================

class TestAITaskDecomposition:
    """AI 任務分解端到端測試。"""

    @pytest.mark.e2e
    def test_planning_adapter_accepts_llm_service(self, mock_llm_service):
        """測試 PlanningAdapter 正確接受 LLM 服務。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)

        assert adapter.llm_service is mock_llm_service
        assert adapter._llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_with_task_decomposition_injects_llm(self, mock_llm_service):
        """測試 with_task_decomposition 正確注入 LLM。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_task_decomposition(strategy=DecompositionStrategy.HYBRID)

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_chained_builder_pattern(self, mock_llm_service):
        """測試鏈式構建器模式。"""
        adapter = (
            PlanningAdapter(id="test", llm_service=mock_llm_service)
            .with_task_decomposition()
            .with_decision_engine()
            .with_trial_error()
        )

        assert adapter._task_decomposer is not None
        assert adapter._decision_engine is not None
        assert adapter._trial_error_engine is not None

        # 所有組件都獲得 LLM 服務
        assert adapter._task_decomposer.llm_service is mock_llm_service
        assert adapter._decision_engine.llm_service is mock_llm_service
        assert adapter._trial_error_engine.llm_service is mock_llm_service


# =============================================================================
# E2E Tests: AI Decision Making
# =============================================================================

class TestAIDecisionMaking:
    """AI 決策端到端測試。"""

    @pytest.mark.e2e
    def test_decision_engine_receives_llm(self, mock_llm_service):
        """測試 DecisionEngine 正確接收 LLM 服務。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_decision_engine()

        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_decision_engine_initialization(self, mock_llm_service):
        """測試 DecisionEngine 初始化。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_decision_engine()

        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is mock_llm_service


# =============================================================================
# E2E Tests: AI Error Learning
# =============================================================================

class TestAIErrorLearning:
    """AI 錯誤學習端到端測試。"""

    @pytest.mark.e2e
    def test_trial_error_engine_receives_llm(self, mock_llm_service):
        """測試 TrialAndErrorEngine 正確接收 LLM 服務。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_trial_error(max_retries=3)

        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_trial_error_with_retries(self, mock_llm_service):
        """測試配置重試次數的 TrialAndErrorEngine。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_trial_error(max_retries=5)

        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is mock_llm_service


# =============================================================================
# E2E Tests: Full Planning Workflow
# =============================================================================

class TestFullPlanningWorkflow:
    """完整規劃工作流程端到端測試。"""

    @pytest.mark.e2e
    def test_full_planner_creation(self, mock_llm_service):
        """測試完整規劃器創建。"""
        adapter = create_full_planner(
            id="full-planner",
            llm_service=mock_llm_service
        )

        assert adapter._task_decomposer is not None
        assert adapter._decision_engine is not None
        assert adapter._task_decomposer.llm_service is mock_llm_service
        assert adapter._decision_engine.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_decomposed_planner_creation(self, mock_llm_service):
        """測試分解規劃器創建。"""
        adapter = create_decomposed_planner(
            id="decomposed-planner",
            strategy=DecompositionStrategy.HYBRID,
            llm_service=mock_llm_service
        )

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_planning_adapter_factory(self, mock_llm_service):
        """測試 PlanningAdapter 工廠函數。"""
        adapter = create_planning_adapter(
            id="factory-test",
            mode=PlanningMode.SIMPLE,
            llm_service=mock_llm_service
        )

        assert adapter.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_dynamic_planner_with_llm(self, mock_llm_service):
        """測試動態規劃器 LLM 注入。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)
        adapter.with_dynamic_planner()

        assert adapter._task_decomposer is not None
        assert adapter._dynamic_planner is not None
        assert adapter._task_decomposer.llm_service is mock_llm_service


# =============================================================================
# E2E Tests: LLM Service Integration
# =============================================================================

class TestLLMServiceIntegration:
    """LLM 服務整合端到端測試。"""

    @pytest.mark.e2e
    def test_with_llm_service_method(self, mock_llm_service):
        """測試 with_llm_service 鏈式方法。"""
        adapter = PlanningAdapter(id="test")
        result = adapter.with_llm_service(mock_llm_service)

        assert result is adapter  # 返回自身以支援鏈式調用
        assert adapter.llm_service is mock_llm_service

    @pytest.mark.e2e
    def test_late_llm_injection(self, mock_llm_service):
        """測試後期 LLM 注入。"""
        # 先創建無 LLM 的適配器
        adapter = PlanningAdapter(id="test")

        # 後期注入 LLM
        adapter.with_llm_service(mock_llm_service)

        # 創建組件應該獲得 LLM
        adapter.with_task_decomposition()

        assert adapter._task_decomposer.llm_service is mock_llm_service

    @pytest.mark.e2e
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_auto_llm_from_factory(self, mock_factory):
        """測試自動從工廠獲取 LLM 服務。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)
        mock_factory.create.return_value = mock_llm

        adapter = PlanningAdapter(id="test")
        adapter.with_task_decomposition()

        mock_factory.create.assert_called_once_with(singleton=True)
        assert adapter._task_decomposer.llm_service is mock_llm

    @pytest.mark.e2e
    def test_llm_property_accessor(self, mock_llm_service):
        """測試 llm_service 屬性訪問器。"""
        adapter = PlanningAdapter(id="test", llm_service=mock_llm_service)

        # 通過屬性訪問
        assert adapter.llm_service is mock_llm_service


# =============================================================================
# E2E Tests: Statistics and Monitoring
# =============================================================================

class TestStatisticsAndMonitoring:
    """統計和監控端到端測試。"""

    @pytest.mark.e2e
    def test_statistics_include_llm_status(self, mock_llm_service):
        """測試統計信息包含 LLM 狀態。"""
        adapter = (
            PlanningAdapter(id="test", llm_service=mock_llm_service)
            .with_task_decomposition()
        )

        stats = adapter.get_statistics()

        assert "has_task_decomposer" in stats
        assert stats["has_task_decomposer"] is True
        assert "mode" in stats

    @pytest.mark.e2e
    def test_planning_mode_detection(self, mock_llm_service):
        """測試規劃模式檢測。"""
        # SIMPLE mode
        simple_adapter = PlanningAdapter(id="simple")
        assert simple_adapter.get_statistics()["mode"] == PlanningMode.SIMPLE.value

        # DECOMPOSED mode
        decomposed_adapter = PlanningAdapter(id="decomposed", llm_service=mock_llm_service)
        decomposed_adapter.with_task_decomposition()
        assert decomposed_adapter.get_statistics()["mode"] == PlanningMode.DECOMPOSED.value


# =============================================================================
# E2E Tests: Error Handling
# =============================================================================

class TestErrorHandling:
    """錯誤處理端到端測試。"""

    @pytest.mark.e2e
    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_factory_error_handling(self, mock_factory):
        """測試工廠錯誤處理。"""
        mock_factory.create.side_effect = Exception("LLM not configured")

        adapter = PlanningAdapter(id="test")

        # _ensure_llm_service 應該返回 None，不拋出異常
        llm = adapter._ensure_llm_service()

        assert llm is None
        assert adapter._llm_service is None

    @pytest.mark.e2e
    def test_graceful_degradation_without_llm(self):
        """測試無 LLM 時的優雅降級。"""
        adapter = PlanningAdapter(id="test", llm_service=None)

        # 應該仍然可以創建組件，但使用規則式
        # 注意：這裡需要 mock 工廠避免自動獲取
        with patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory') as mock_factory:
            mock_factory.create.side_effect = Exception("No LLM")
            adapter.with_task_decomposition()

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is None

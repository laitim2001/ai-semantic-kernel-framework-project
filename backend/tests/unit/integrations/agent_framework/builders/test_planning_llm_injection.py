# =============================================================================
# Sprint 35 Test: PlanningAdapter LLM Injection
# =============================================================================
# 驗證 PlanningAdapter 正確注入 LLM 服務到 Phase 2 擴展組件
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.agent_framework.builders.planning import (
    PlanningAdapter,
    PlanningConfig,
    PlanningMode,
    DecompositionStrategy,
    create_planning_adapter,
    create_decomposed_planner,
    create_full_planner,
)
from src.integrations.llm.protocol import LLMServiceProtocol


class TestPlanningAdapterLLMInjection:
    """PlanningAdapter LLM 注入測試。"""

    def test_init_with_llm_service(self):
        """測試構造函數接受 LLM 服務參數。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)

        assert adapter.llm_service is mock_llm

    def test_init_without_llm_service(self):
        """測試構造函數無 LLM 服務時為 None。"""
        adapter = PlanningAdapter(id="test-adapter")

        assert adapter._llm_service is None

    def test_with_llm_service_method(self):
        """測試 with_llm_service() 鏈式方法。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter")
        result = adapter.with_llm_service(mock_llm)

        assert result is adapter  # 鏈式調用
        assert adapter.llm_service is mock_llm


class TestTaskDecomposerLLMInjection:
    """TaskDecomposer LLM 注入測試。"""

    def test_with_task_decomposition_injects_llm(self):
        """測試 with_task_decomposition() 注入 LLM 服務到 TaskDecomposer。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)
        adapter.with_task_decomposition(strategy=DecompositionStrategy.HYBRID)

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is mock_llm

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_with_task_decomposition_no_llm(self, mock_factory):
        """測試無 LLM 服務時 TaskDecomposer 使用規則式回退。"""
        mock_factory.create.side_effect = Exception("LLM not configured")

        adapter = PlanningAdapter(id="test-adapter")
        adapter.with_task_decomposition()

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is None

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_auto_llm_service_from_factory(self, mock_factory):
        """測試自動從工廠獲取 LLM 服務單例。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)
        mock_factory.create.return_value = mock_llm

        adapter = PlanningAdapter(id="test-adapter")
        adapter.with_task_decomposition()

        mock_factory.create.assert_called_once_with(singleton=True)
        assert adapter._task_decomposer.llm_service is mock_llm


class TestDecisionEngineLLMInjection:
    """DecisionEngine LLM 注入測試。"""

    def test_with_decision_engine_injects_llm(self):
        """測試 with_decision_engine() 注入 LLM 服務到 DecisionEngine。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)
        adapter.with_decision_engine()

        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is mock_llm

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_with_decision_engine_no_llm(self, mock_factory):
        """測試無 LLM 服務時 DecisionEngine 使用規則式回退。"""
        mock_factory.create.side_effect = Exception("LLM not configured")

        adapter = PlanningAdapter(id="test-adapter")
        adapter.with_decision_engine()

        assert adapter._decision_engine is not None
        assert adapter._decision_engine.llm_service is None


class TestTrialAndErrorEngineLLMInjection:
    """TrialAndErrorEngine LLM 注入測試。"""

    def test_with_trial_error_injects_llm(self):
        """測試 with_trial_error() 注入 LLM 服務到 TrialAndErrorEngine。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)
        adapter.with_trial_error()

        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is mock_llm

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_with_trial_error_no_llm(self, mock_factory):
        """測試無 LLM 服務時 TrialAndErrorEngine 使用規則式回退。"""
        mock_factory.create.side_effect = Exception("LLM not configured")

        adapter = PlanningAdapter(id="test-adapter")
        adapter.with_trial_error()

        assert adapter._trial_error_engine is not None
        assert adapter._trial_error_engine.llm_service is None


class TestDynamicPlannerLLMInjection:
    """DynamicPlanner LLM 注入測試。"""

    def test_with_dynamic_planner_creates_task_decomposer_with_llm(self):
        """測試 with_dynamic_planner() 創建帶 LLM 的 TaskDecomposer。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)
        adapter.with_dynamic_planner()

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is mock_llm
        assert adapter._dynamic_planner is not None


class TestFactoryFunctionsLLMInjection:
    """工廠函數 LLM 注入測試。"""

    def test_create_planning_adapter_with_llm(self):
        """測試 create_planning_adapter() 接受 LLM 服務。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = create_planning_adapter(
            id="test-adapter",
            mode=PlanningMode.SIMPLE,
            llm_service=mock_llm
        )

        assert adapter.llm_service is mock_llm

    def test_create_decomposed_planner_with_llm(self):
        """測試 create_decomposed_planner() 注入 LLM 到 TaskDecomposer。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = create_decomposed_planner(
            id="test-adapter",
            strategy=DecompositionStrategy.HYBRID,
            llm_service=mock_llm
        )

        assert adapter._task_decomposer is not None
        assert adapter._task_decomposer.llm_service is mock_llm

    def test_create_full_planner_with_llm(self):
        """測試 create_full_planner() 注入 LLM 到所有組件。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = create_full_planner(
            id="test-adapter",
            llm_service=mock_llm
        )

        # Full planner 應該有 TaskDecomposer 和 DecisionEngine
        assert adapter._task_decomposer is not None
        assert adapter._decision_engine is not None
        assert adapter._task_decomposer.llm_service is mock_llm
        assert adapter._decision_engine.llm_service is mock_llm


class TestChainedBuilderLLMInjection:
    """鏈式 Builder 調用 LLM 注入測試。"""

    def test_chained_builder_all_components_get_llm(self):
        """測試鏈式調用所有組件都獲得 LLM 服務。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = (
            PlanningAdapter(id="test-adapter", llm_service=mock_llm)
            .with_task_decomposition()
            .with_decision_engine()
            .with_trial_error()
        )

        assert adapter._task_decomposer.llm_service is mock_llm
        assert adapter._decision_engine.llm_service is mock_llm
        assert adapter._trial_error_engine.llm_service is mock_llm

    def test_late_llm_injection_via_with_llm_service(self):
        """測試後期通過 with_llm_service() 注入 LLM。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        # 先創建適配器（無 LLM）
        adapter = PlanningAdapter(id="test-adapter")

        # 後期注入 LLM
        adapter.with_llm_service(mock_llm)

        # 現在創建組件應該獲得 LLM
        adapter.with_task_decomposition()

        assert adapter._task_decomposer.llm_service is mock_llm


class TestDecomposeTaskLLMInjection:
    """decompose_task() 方法 LLM 注入測試。"""

    def test_decompose_task_creates_decomposer_with_llm(self):
        """測試 decompose_task() 創建帶 LLM 的 TaskDecomposer。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)

        # 在調用 decompose_task 之前，TaskDecomposer 不應存在
        assert adapter._task_decomposer is None

        # 調用 _ensure_llm_service 來測試該邏輯
        llm = adapter._ensure_llm_service()

        assert llm is mock_llm


class TestEnsureLLMServiceMethod:
    """_ensure_llm_service() 方法測試。"""

    def test_ensure_llm_service_returns_existing(self):
        """測試已有 LLM 服務時直接返回。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = PlanningAdapter(id="test-adapter", llm_service=mock_llm)
        result = adapter._ensure_llm_service()

        assert result is mock_llm

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_ensure_llm_service_gets_from_factory(self, mock_factory):
        """測試無 LLM 服務時從工廠獲取。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)
        mock_factory.create.return_value = mock_llm

        adapter = PlanningAdapter(id="test-adapter")
        result = adapter._ensure_llm_service()

        mock_factory.create.assert_called_once_with(singleton=True)
        assert result is mock_llm
        assert adapter._llm_service is mock_llm

    @patch('src.integrations.agent_framework.builders.planning.LLMServiceFactory')
    def test_ensure_llm_service_handles_factory_error(self, mock_factory):
        """測試工廠拋出異常時返回 None。"""
        mock_factory.create.side_effect = Exception("LLM not configured")

        adapter = PlanningAdapter(id="test-adapter")
        result = adapter._ensure_llm_service()

        assert result is None
        assert adapter._llm_service is None


class TestStatisticsIncludeLLMInfo:
    """統計信息包含 LLM 狀態測試。"""

    def test_get_statistics_with_llm(self):
        """測試統計信息包含 LLM 狀態。"""
        mock_llm = MagicMock(spec=LLMServiceProtocol)

        adapter = (
            PlanningAdapter(id="test-adapter", llm_service=mock_llm)
            .with_task_decomposition()
        )

        stats = adapter.get_statistics()

        assert stats["has_task_decomposer"] is True
        assert stats["mode"] == PlanningMode.DECOMPOSED.value

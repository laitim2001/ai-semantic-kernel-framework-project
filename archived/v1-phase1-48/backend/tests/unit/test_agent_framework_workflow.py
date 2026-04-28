"""
Unit Tests for Agent Framework Workflow Adapter

測試 WorkflowAdapter 和相關類別。

測試範圍:
    - WorkflowConfig 數據類
    - WorkflowAdapter 配置和方法
    - 執行器註冊和管理
    - 邊添加和管理
    - 構建和執行
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.agent_framework.workflow import (
    WorkflowAdapter,
    WorkflowConfig,
    EdgeConfig,
)
from src.integrations.agent_framework.exceptions import WorkflowBuildError


class TestWorkflowConfig:
    """WorkflowConfig 測試類。"""

    def test_valid_config(self):
        """測試有效配置。"""
        config = WorkflowConfig(
            id="test-workflow",
            name="Test Workflow",
            description="A test workflow",
            max_iterations=50,
        )

        assert config.id == "test-workflow"
        assert config.name == "Test Workflow"
        assert config.description == "A test workflow"
        assert config.max_iterations == 50
        assert not config.enable_checkpointing
        assert config.checkpoint_storage is None

    def test_config_with_checkpointing(self):
        """測試帶檢查點的配置。"""
        mock_storage = MagicMock()
        config = WorkflowConfig(
            id="cp-workflow",
            name="Checkpoint Workflow",
            enable_checkpointing=True,
            checkpoint_storage=mock_storage,
        )

        assert config.enable_checkpointing
        assert config.checkpoint_storage is mock_storage

    def test_invalid_empty_id(self):
        """測試空 ID 驗證。"""
        with pytest.raises(ValueError, match="ID cannot be empty"):
            WorkflowConfig(id="", name="Test")

    def test_invalid_empty_name(self):
        """測試空名稱驗證。"""
        with pytest.raises(ValueError, match="name cannot be empty"):
            WorkflowConfig(id="test", name="")

    def test_invalid_max_iterations(self):
        """測試無效迭代次數。"""
        with pytest.raises(ValueError, match="max_iterations must be at least 1"):
            WorkflowConfig(id="test", name="Test", max_iterations=0)


class TestEdgeConfig:
    """EdgeConfig 測試類。"""

    def test_basic_edge(self):
        """測試基本邊配置。"""
        edge = EdgeConfig(source_id="exec1", target_id="exec2")

        assert edge.source_id == "exec1"
        assert edge.target_id == "exec2"
        assert edge.condition is None

    def test_conditional_edge(self):
        """測試條件邊配置。"""
        condition = lambda x: x.get("value") > 10
        edge = EdgeConfig(
            source_id="exec1",
            target_id="exec2",
            condition=condition,
        )

        assert edge.condition is condition
        assert edge.condition({"value": 15})
        assert not edge.condition({"value": 5})


class TestWorkflowAdapter:
    """WorkflowAdapter 測試類。"""

    @pytest.fixture
    def config(self):
        """創建測試配置。"""
        return WorkflowConfig(id="test-wf", name="Test Workflow")

    @pytest.fixture
    def adapter(self, config):
        """創建測試適配器。"""
        return WorkflowAdapter(config)

    def test_init(self, adapter, config):
        """測試初始化。"""
        assert adapter.workflow_id == config.id
        assert adapter.workflow_name == config.name
        assert not adapter.is_built

    def test_register_executor(self, adapter):
        """測試註冊執行器工廠。"""
        factory = lambda: MagicMock(id="exec1")

        result = adapter.register_executor(factory, "exec1")

        assert result is adapter  # 鏈式調用
        assert "exec1" in adapter.get_executor_ids()

    def test_register_executor_duplicate(self, adapter):
        """測試重複註冊執行器。"""
        adapter.register_executor(lambda: MagicMock(id="exec1"), "exec1")

        with pytest.raises(ValueError, match="already registered"):
            adapter.register_executor(lambda: MagicMock(id="exec1"), "exec1")

    def test_add_executor(self, adapter):
        """測試添加執行器實例。"""
        executor = MagicMock()
        executor.id = "exec1"

        result = adapter.add_executor(executor)

        assert result is adapter
        assert "exec1" in adapter.get_executor_ids()

    def test_add_executor_duplicate(self, adapter):
        """測試重複添加執行器。"""
        executor = MagicMock()
        executor.id = "exec1"
        adapter.add_executor(executor)

        with pytest.raises(ValueError, match="already added"):
            adapter.add_executor(executor)

    def test_add_edge(self, adapter):
        """測試添加邊。"""
        result = adapter.add_edge("exec1", "exec2")

        assert result is adapter
        assert adapter.get_edge_count() == 1

    def test_add_conditional_edge(self, adapter):
        """測試添加條件邊。"""
        condition = lambda x: True
        adapter.add_edge("exec1", "exec2", condition=condition)

        assert adapter.get_edge_count() == 1

    def test_add_fan_out_edges(self, adapter):
        """測試添加扇出邊。"""
        result = adapter.add_fan_out_edges("source", ["t1", "t2", "t3"])

        assert result is adapter
        assert adapter.get_edge_count() == 3

    def test_add_fan_in_edges(self, adapter):
        """測試添加扇入邊。"""
        result = adapter.add_fan_in_edges(["s1", "s2", "s3"], "target")

        assert result is adapter
        assert adapter.get_edge_count() == 3

    def test_add_chain(self, adapter):
        """測試添加執行器鏈。"""
        result = adapter.add_chain(["e1", "e2", "e3", "e4"])

        assert result is adapter
        assert adapter.get_edge_count() == 3  # 4個節點有3條邊

    def test_add_chain_requires_two_executors(self, adapter):
        """測試鏈至少需要兩個執行器。"""
        with pytest.raises(ValueError, match="at least 2"):
            adapter.add_chain(["e1"])

    def test_set_start_executor(self, adapter):
        """測試設置起始執行器。"""
        result = adapter.set_start_executor("exec1")

        assert result is adapter
        assert adapter._start_executor_id == "exec1"

    def test_get_executor_ids(self, adapter):
        """測試獲取執行器 ID 列表。"""
        adapter.register_executor(lambda: MagicMock(id="e1"), "e1")
        adapter.register_executor(lambda: MagicMock(id="e2"), "e2")

        ids = adapter.get_executor_ids()

        assert "e1" in ids
        assert "e2" in ids

    def test_get_edge_count(self, adapter):
        """測試獲取邊計數。"""
        adapter.add_edge("e1", "e2")
        adapter.add_edge("e2", "e3")
        adapter.add_fan_out_edges("e3", ["e4", "e5"])

        assert adapter.get_edge_count() == 4

    @pytest.mark.asyncio
    async def test_build_without_start_executor(self, adapter):
        """測試沒有起始執行器時構建失敗。"""
        adapter.register_executor(lambda: MagicMock(id="e1"), "e1")

        with pytest.raises(WorkflowBuildError, match="Start executor not set"):
            adapter.build()

    def test_repr(self, adapter):
        """測試字符串表示。"""
        adapter.register_executor(lambda: MagicMock(id="e1"), "e1")
        adapter.add_edge("e1", "e2")

        repr_str = repr(adapter)

        assert "WorkflowAdapter" in repr_str
        assert "test-wf" in repr_str


class TestWorkflowAdapterIntegration:
    """WorkflowAdapter 整合測試（模擬 Agent Framework）。"""

    @pytest.fixture
    def mock_workflow_builder(self):
        """創建 Mock WorkflowBuilder。"""
        with patch("src.integrations.agent_framework.workflow.WorkflowBuilder") as mock:
            mock_instance = MagicMock()
            mock_instance.register_executor.return_value = mock_instance
            mock_instance.add_edge.return_value = mock_instance
            mock_instance.add_fan_out_edges.return_value = mock_instance
            mock_instance.add_fan_in_edges.return_value = mock_instance
            mock_instance.set_start_executor.return_value = mock_instance
            mock_instance.with_checkpointing.return_value = mock_instance

            mock_workflow = MagicMock()
            mock_instance.build.return_value = mock_workflow

            mock.return_value = mock_instance

            yield mock, mock_instance, mock_workflow

    @pytest.mark.asyncio
    async def test_build_with_mock_builder(self, mock_workflow_builder):
        """測試使用 Mock Builder 構建。"""
        mock_class, mock_instance, mock_workflow = mock_workflow_builder

        config = WorkflowConfig(id="test", name="Test")
        adapter = WorkflowAdapter(config)
        adapter.register_executor(lambda: MagicMock(id="e1"), "e1")
        adapter.set_start_executor("e1")

        workflow = adapter.build()

        mock_class.assert_called_once()
        mock_instance.register_executor.assert_called()
        mock_instance.set_start_executor.assert_called_with("e1")
        mock_instance.build.assert_called_once()
        assert workflow is mock_workflow

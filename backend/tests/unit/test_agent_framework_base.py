"""
Unit Tests for Agent Framework Base Classes

測試 agent_framework 整合模組的基礎類別。

測試範圍:
    - BaseAdapter 抽象類
    - BuilderAdapter 抽象類
    - 生命週期管理
    - 配置處理
"""

import pytest
from unittest.mock import AsyncMock, patch

from src.integrations.agent_framework.base import BaseAdapter, BuilderAdapter
from src.integrations.agent_framework.exceptions import (
    AdapterInitializationError,
    WorkflowBuildError,
)


class ConcreteAdapter(BaseAdapter):
    """用於測試的具體適配器實現。"""

    def __init__(self, config=None, init_should_fail=False):
        super().__init__(config)
        self._init_should_fail = init_should_fail

    async def initialize(self) -> None:
        if self._init_should_fail:
            raise RuntimeError("Initialization failed")
        self._initialized = True

    async def cleanup(self) -> None:
        self._initialized = False


class ConcreteBuilderAdapter(BuilderAdapter):
    """用於測試的具體 Builder 適配器實現。"""

    def __init__(self, config=None, build_should_fail=False):
        super().__init__(config)
        self._build_should_fail = build_should_fail

    def build(self):
        if self._build_should_fail:
            raise RuntimeError("Build failed")
        # 返回 mock workflow
        mock_workflow = AsyncMock()
        mock_workflow.run = AsyncMock(return_value={"result": "ok"})
        mock_workflow.run_stream = AsyncMock(return_value=iter([{"event": 1}]))
        self._workflow = mock_workflow
        return mock_workflow


class TestBaseAdapter:
    """BaseAdapter 測試類。"""

    def test_init_with_default_config(self):
        """測試默認配置初始化。"""
        adapter = ConcreteAdapter()
        assert adapter.config == {}
        assert not adapter.is_initialized

    def test_init_with_custom_config(self):
        """測試自定義配置初始化。"""
        config = {"key": "value", "number": 42}
        adapter = ConcreteAdapter(config=config)
        assert adapter.config == config
        assert adapter.get_config_value("key") == "value"
        assert adapter.get_config_value("number") == 42

    def test_get_config_value_with_default(self):
        """測試配置值獲取（帶默認值）。"""
        adapter = ConcreteAdapter(config={"existing": "value"})
        assert adapter.get_config_value("existing") == "value"
        assert adapter.get_config_value("missing") is None
        assert adapter.get_config_value("missing", "default") == "default"

    @pytest.mark.asyncio
    async def test_initialize(self):
        """測試初始化。"""
        adapter = ConcreteAdapter()
        assert not adapter.is_initialized

        await adapter.initialize()

        assert adapter.is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """測試清理。"""
        adapter = ConcreteAdapter()
        await adapter.initialize()
        assert adapter.is_initialized

        await adapter.cleanup()

        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_ensure_initialized(self):
        """測試確保初始化。"""
        adapter = ConcreteAdapter()
        assert not adapter.is_initialized

        await adapter.ensure_initialized()

        assert adapter.is_initialized

    @pytest.mark.asyncio
    async def test_ensure_initialized_raises_on_failure(self):
        """測試初始化失敗時拋出異常。"""
        adapter = ConcreteAdapter(init_should_fail=True)

        with pytest.raises(AdapterInitializationError):
            await adapter.ensure_initialized()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """測試上下文管理器。"""
        adapter = ConcreteAdapter()

        async with adapter as a:
            assert a.is_initialized
            assert a is adapter

        assert not adapter.is_initialized

    def test_repr(self):
        """測試字符串表示。"""
        adapter = ConcreteAdapter(config={"key": "value"})
        repr_str = repr(adapter)
        assert "ConcreteAdapter" in repr_str
        assert "initialized=False" in repr_str


class TestBuilderAdapter:
    """BuilderAdapter 測試類。"""

    def test_init(self):
        """測試初始化。"""
        adapter = ConcreteBuilderAdapter()
        assert not adapter.is_built
        assert adapter.workflow is None

    def test_build(self):
        """測試構建。"""
        adapter = ConcreteBuilderAdapter()

        workflow = adapter.build()

        assert workflow is not None
        assert adapter.is_built
        assert adapter.workflow is workflow

    def test_build_failure(self):
        """測試構建失敗。"""
        adapter = ConcreteBuilderAdapter(build_should_fail=True)

        with pytest.raises(RuntimeError, match="Build failed"):
            adapter.build()

    @pytest.mark.asyncio
    async def test_run_builds_if_needed(self):
        """測試 run 會在需要時構建。"""
        adapter = ConcreteBuilderAdapter()
        await adapter.initialize()

        result = await adapter.run({"input": "test"})

        assert adapter.is_built
        assert result == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_run_raises_on_build_failure(self):
        """測試 run 在構建失敗時拋出異常。"""
        adapter = ConcreteBuilderAdapter(build_should_fail=True)
        await adapter.initialize()

        with pytest.raises(WorkflowBuildError):
            await adapter.run({"input": "test"})

    def test_reset(self):
        """測試重置。"""
        adapter = ConcreteBuilderAdapter()
        adapter.build()
        assert adapter.is_built

        adapter.reset()

        assert not adapter.is_built
        assert adapter.workflow is None

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self):
        """測試清理重置狀態。"""
        adapter = ConcreteBuilderAdapter()
        await adapter.initialize()
        adapter.build()

        await adapter.cleanup()

        assert not adapter.is_initialized
        assert not adapter.is_built
        assert adapter.workflow is None

    def test_repr(self):
        """測試字符串表示。"""
        adapter = ConcreteBuilderAdapter(config={"key": "value"})
        repr_str = repr(adapter)
        assert "ConcreteBuilderAdapter" in repr_str
        assert "built=False" in repr_str

# =============================================================================
# IPA Platform - MAF Tool Callback Tests
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor - S54-2
#
# Unit tests for MAFToolCallback.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from src.integrations.hybrid.execution import (
    ToolSource,
    ToolExecutionResult,
    UnifiedToolExecutor,
    MAFToolCallback,
    MAFToolResult,
    CallbackConfig,
    create_maf_callback,
    create_selective_callback,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_executor():
    """Create mock unified executor."""
    executor = MagicMock(spec=UnifiedToolExecutor)
    executor.execute = AsyncMock(return_value=ToolExecutionResult(
        success=True,
        content="Test output",
        tool_name="test_tool",
        source=ToolSource.MAF,
        duration_ms=50,
        execution_id="exec-123",
    ))
    return executor


@pytest.fixture
def default_callback(mock_executor):
    """Create default MAFToolCallback."""
    return MAFToolCallback(
        unified_executor=mock_executor,
    )


@pytest.fixture
def callback_with_config(mock_executor):
    """Create MAFToolCallback with custom config."""
    config = CallbackConfig(
        intercept_all=False,
        allowed_tools=["allowed_tool", "another_allowed"],
        blocked_tools=["blocked_tool"],
        require_approval=["sensitive_tool"],
    )
    return MAFToolCallback(
        unified_executor=mock_executor,
        config=config,
    )


# =============================================================================
# MAFToolResult Tests
# =============================================================================


class TestMAFToolResult:
    """Tests for MAFToolResult dataclass."""

    def test_successful_result(self):
        """Test creating successful result."""
        result = MAFToolResult(
            function_name="test_func",
            output="Success output",
            success=True,
        )

        assert result.function_name == "test_func"
        assert result.output == "Success output"
        assert result.error is None
        assert result.success is True

    def test_failed_result(self):
        """Test creating failed result."""
        result = MAFToolResult(
            function_name="test_func",
            error="Something went wrong",
            success=False,
        )

        assert result.output is None
        assert result.error == "Something went wrong"
        assert result.success is False

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = MAFToolResult(
            function_name="test_func",
            output="output",
            metadata={"key": "value"},
        )

        d = result.to_dict()

        assert d["function_name"] == "test_func"
        assert d["output"] == "output"
        assert d["metadata"]["key"] == "value"


# =============================================================================
# CallbackConfig Tests
# =============================================================================


class TestCallbackConfig:
    """Tests for CallbackConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CallbackConfig()

        assert config.intercept_all is True
        assert config.allowed_tools == []
        assert config.blocked_tools == []
        assert config.require_approval == []
        assert config.default_approval_timeout == 300
        assert config.enable_metrics is True
        assert config.fallback_on_error is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = CallbackConfig(
            intercept_all=False,
            allowed_tools=["tool1", "tool2"],
            blocked_tools=["bad_tool"],
            require_approval=["sensitive"],
        )

        assert config.intercept_all is False
        assert len(config.allowed_tools) == 2
        assert "bad_tool" in config.blocked_tools


# =============================================================================
# MAFToolCallback Tests
# =============================================================================


class TestMAFToolCallback:
    """Tests for MAFToolCallback."""

    @pytest.mark.asyncio
    async def test_handle_dict_request(self, default_callback):
        """Test handling dictionary request."""
        request = {
            "function_name": "test_tool",
            "arguments": {"param": "value"},
        }

        result = await default_callback.handle(request)

        assert result.success is True
        assert result.function_name == "test_tool"
        assert result.output == "Test output"

    @pytest.mark.asyncio
    async def test_handle_with_session_id(self, default_callback, mock_executor):
        """Test handling with session ID."""
        request = {"function_name": "test_tool", "arguments": {}}

        await default_callback.handle(request, session_id="session-123")

        mock_executor.execute.assert_called_once()
        call_kwargs = mock_executor.execute.call_args[1]
        assert call_kwargs["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_intercept_all_by_default(self, default_callback, mock_executor):
        """Test that all tools are intercepted by default."""
        request = {"function_name": "any_tool", "arguments": {}}

        result = await default_callback.handle(request)

        assert result.success is True
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_selective_interception(self, callback_with_config, mock_executor):
        """Test selective tool interception."""
        # Allowed tool should be intercepted
        result = await callback_with_config.handle({
            "function_name": "allowed_tool",
            "arguments": {},
        })

        mock_executor.execute.assert_called_once()
        mock_executor.execute.reset_mock()

        # Not allowed tool should not be intercepted (passthrough)
        result = await callback_with_config.handle({
            "function_name": "not_allowed",
            "arguments": {},
        })

        mock_executor.execute.assert_not_called()
        assert result.success is False  # No original handler

    @pytest.mark.asyncio
    async def test_blocked_tools_not_intercepted(
        self, callback_with_config, mock_executor
    ):
        """Test that blocked tools are not intercepted."""
        # Add blocked tool to allowed list and verify it's still blocked
        callback_with_config._config.allowed_tools.append("blocked_tool")

        result = await callback_with_config.handle({
            "function_name": "blocked_tool",
            "arguments": {},
        })

        mock_executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_approval_required_tools(self, callback_with_config, mock_executor):
        """Test that sensitive tools require approval."""
        # Allow the sensitive tool
        callback_with_config._config.allowed_tools.append("sensitive_tool")

        await callback_with_config.handle({
            "function_name": "sensitive_tool",
            "arguments": {},
        })

        call_kwargs = mock_executor.execute.call_args[1]
        assert call_kwargs["approval_required"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self, default_callback, mock_executor):
        """Test error handling in callback."""
        mock_executor.execute.side_effect = Exception("Test error")

        result = await default_callback.handle({
            "function_name": "test_tool",
            "arguments": {},
        })

        assert result.success is False
        assert "Test error" in result.error

    @pytest.mark.asyncio
    async def test_fallback_on_error(self, mock_executor):
        """Test fallback to original handler on error."""
        original_handler = AsyncMock(return_value={
            "output": "Fallback output",
            "success": True,
        })

        callback = MAFToolCallback(
            unified_executor=mock_executor,
            config=CallbackConfig(fallback_on_error=True),
            original_handler=original_handler,
        )

        mock_executor.execute.side_effect = Exception("Unified executor failed")

        result = await callback.handle({
            "function_name": "test_tool",
            "arguments": {"param": "value"},
        })

        assert result.success is True
        assert result.output == "Fallback output"
        assert result.metadata.get("fallback") is True

    @pytest.mark.asyncio
    async def test_passthrough_with_original_handler(self, mock_executor):
        """Test passthrough to original handler when not intercepting."""
        original_handler = AsyncMock(return_value={
            "output": "Original output",
            "success": True,
        })

        callback = MAFToolCallback(
            unified_executor=mock_executor,
            config=CallbackConfig(
                intercept_all=False,
                allowed_tools=["intercepted_tool"],
            ),
            original_handler=original_handler,
        )

        result = await callback.handle({
            "function_name": "not_intercepted",
            "arguments": {},
        })

        assert result.success is True
        assert result.output == "Original output"
        mock_executor.execute.assert_not_called()
        original_handler.assert_called_once()

    def test_statistics_tracking(self, default_callback):
        """Test that statistics are tracked."""
        stats = default_callback.get_stats()

        assert stats["call_count"] == 0
        assert stats["intercept_count"] == 0
        assert stats["error_count"] == 0

    @pytest.mark.asyncio
    async def test_statistics_updated_after_calls(self, default_callback):
        """Test statistics update after handling calls."""
        await default_callback.handle({
            "function_name": "tool1",
            "arguments": {},
        })
        await default_callback.handle({
            "function_name": "tool2",
            "arguments": {},
        })

        stats = default_callback.get_stats()

        assert stats["call_count"] == 2
        assert stats["intercept_count"] == 2
        assert stats["intercept_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_history_recording(self, default_callback):
        """Test execution history recording."""
        await default_callback.handle({
            "function_name": "test_tool",
            "arguments": {"key": "value"},
        })

        history = default_callback.get_history()

        assert len(history) == 1
        assert history[0]["function_name"] == "test_tool"
        assert history[0]["intercepted"] is True

    def test_history_limit(self, default_callback):
        """Test history is limited in size."""
        default_callback._max_history_size = 5

        # Add more entries than limit
        for i in range(10):
            default_callback._record_history(
                function_name=f"tool_{i}",
                arguments={},
                result=MAFToolResult(function_name=f"tool_{i}"),
                duration_ms=10,
                intercepted=True,
            )

        history = default_callback.get_history()

        assert len(history) == 5
        assert history[0]["function_name"] == "tool_5"  # Oldest kept

    def test_history_filter_by_function(self, default_callback):
        """Test filtering history by function name."""
        default_callback._record_history(
            function_name="tool_a",
            arguments={},
            result=MAFToolResult(function_name="tool_a"),
            duration_ms=10,
            intercepted=True,
        )
        default_callback._record_history(
            function_name="tool_b",
            arguments={},
            result=MAFToolResult(function_name="tool_b"),
            duration_ms=10,
            intercepted=True,
        )

        history = default_callback.get_history(function_name="tool_a")

        assert len(history) == 1
        assert history[0]["function_name"] == "tool_a"

    def test_reset_stats(self, default_callback):
        """Test resetting statistics."""
        default_callback._call_count = 10
        default_callback._intercept_count = 8
        default_callback._error_count = 2

        default_callback.reset_stats()

        stats = default_callback.get_stats()
        assert stats["call_count"] == 0
        assert stats["intercept_count"] == 0
        assert stats["error_count"] == 0

    def test_clear_history(self, default_callback):
        """Test clearing history."""
        default_callback._record_history(
            function_name="test",
            arguments={},
            result=MAFToolResult(function_name="test"),
            duration_ms=10,
            intercepted=True,
        )

        cleared = default_callback.clear_history()

        assert cleared == 1
        assert len(default_callback.get_history()) == 0


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_maf_callback(self, mock_executor):
        """Test create_maf_callback factory."""
        callback = create_maf_callback(
            unified_executor=mock_executor,
            intercept_all=True,
            fallback_on_error=True,
        )

        assert callback._config.intercept_all is True
        assert callback._config.fallback_on_error is True

    def test_create_selective_callback(self, mock_executor):
        """Test create_selective_callback factory."""
        callback = create_selective_callback(
            unified_executor=mock_executor,
            allowed_tools=["tool1", "tool2"],
            require_approval=["tool1"],
        )

        assert callback._config.intercept_all is False
        assert "tool1" in callback._config.allowed_tools
        assert "tool1" in callback._config.require_approval


# =============================================================================
# Integration Scenario Tests
# =============================================================================


class TestIntegrationScenarios:
    """Integration scenario tests."""

    @pytest.mark.asyncio
    async def test_full_interception_flow(self, mock_executor):
        """Test complete interception flow."""
        callback = create_maf_callback(mock_executor)

        # Simulate multiple tool calls
        results = []
        for i in range(3):
            result = await callback.handle({
                "function_name": f"tool_{i}",
                "arguments": {"index": i},
            })
            results.append(result)

        # All should succeed
        assert all(r.success for r in results)

        # Stats should reflect calls
        stats = callback.get_stats()
        assert stats["call_count"] == 3
        assert stats["intercept_count"] == 3

        # History should have all entries
        history = callback.get_history()
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_mixed_interception_flow(self, mock_executor):
        """Test mixed interception and passthrough flow."""
        original_handler = AsyncMock(return_value={
            "output": "Passthrough result",
            "success": True,
        })

        callback = MAFToolCallback(
            unified_executor=mock_executor,
            config=CallbackConfig(
                intercept_all=False,
                allowed_tools=["intercept_me"],
            ),
            original_handler=original_handler,
        )

        # Intercept this one
        r1 = await callback.handle({
            "function_name": "intercept_me",
            "arguments": {},
        })

        # Passthrough this one
        r2 = await callback.handle({
            "function_name": "passthrough_me",
            "arguments": {},
        })

        assert r1.output == "Test output"  # From mock executor
        assert r2.output == "Passthrough result"  # From original handler

        stats = callback.get_stats()
        assert stats["intercept_count"] == 1
        assert stats["passthrough_count"] == 1

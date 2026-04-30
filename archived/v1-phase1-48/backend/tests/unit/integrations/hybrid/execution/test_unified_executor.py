# =============================================================================
# IPA Platform - Unified Tool Executor Tests
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor
#
# Unit tests for UnifiedToolExecutor, ToolRouter, and ResultHandler.
# =============================================================================

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, Optional

from src.integrations.hybrid.execution import (
    ToolSource,
    ToolExecutionResult,
    UnifiedToolExecutor,
    ToolNotFoundError,
    ToolExecutionError,
    ToolRouter,
    RoutingDecision,
    RoutingRule,
    RoutingStrategy,
    ResultHandler,
    ResultFormat,
    FormattedResult,
    create_default_router,
    create_default_handler,
)


# =============================================================================
# Fixtures
# =============================================================================


class MockHookResult:
    """Mock hook result with proper attributes matching UnifiedToolExecutor expectations."""
    def __init__(
        self,
        is_rejected: bool = False,
        rejection_reason: str = None,
        is_modified: bool = False,
        modified_args: dict = None,
        requires_approval: bool = False,
    ):
        # These attributes are checked by _run_pre_hooks
        self.is_rejected = is_rejected
        self.rejection_reason = rejection_reason
        self.is_modified = is_modified
        self.modified_args = modified_args
        self.requires_approval = requires_approval
        # Legacy attribute names for backward compatibility
        self.blocked = is_rejected
        self.modified_arguments = modified_args


class MockToolResultHook:
    """Mock tool result hook."""
    def __init__(self):
        self.modified_result = None


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    registry = MagicMock()

    # Create mock tool with async execute
    mock_tool = MagicMock()
    mock_tool.execute = AsyncMock(return_value="success output")
    mock_tool.get_schema.return_value = {
        "name": "test_tool",
        "parameters": {"type": "object"},
    }

    registry.get_tool_instance.return_value = mock_tool
    registry.execute_tool = AsyncMock(return_value="success output")
    registry.has_tool.return_value = True
    registry.get_available_tools.return_value = ["test_tool"]

    return registry


@pytest.fixture
def mock_hook_chain():
    """Create mock hook chain."""
    chain = MagicMock()
    # Use proper mock objects with expected attributes
    chain.run_tool_call = AsyncMock(return_value=MockHookResult(is_rejected=False))
    chain.run_tool_result = AsyncMock(return_value=MockToolResultHook())
    return chain


@pytest.fixture
def mock_context_bridge():
    """Create mock context bridge."""
    bridge = MagicMock()
    bridge.sync_to_claude = AsyncMock()
    bridge.sync_to_maf = AsyncMock()
    # get_hybrid_context is called with await, so it needs to be AsyncMock
    bridge.get_hybrid_context = AsyncMock(return_value=None)
    return bridge


@pytest.fixture
def unified_executor(mock_tool_registry, mock_hook_chain, mock_context_bridge):
    """Create UnifiedToolExecutor with mocked dependencies."""
    return UnifiedToolExecutor(
        tool_registry=mock_tool_registry,
        hook_chain=mock_hook_chain,
        context_bridge=mock_context_bridge,
    )


# =============================================================================
# ToolSource Tests
# =============================================================================


class TestToolSource:
    """Tests for ToolSource enum."""

    def test_tool_source_values(self):
        """Test ToolSource enum values."""
        assert ToolSource.MAF.value == "maf"
        assert ToolSource.CLAUDE.value == "claude"
        assert ToolSource.HYBRID.value == "hybrid"

    def test_tool_source_from_string(self):
        """Test creating ToolSource from string."""
        assert ToolSource("maf") == ToolSource.MAF
        assert ToolSource("claude") == ToolSource.CLAUDE
        assert ToolSource("hybrid") == ToolSource.HYBRID


# =============================================================================
# ToolExecutionResult Tests
# =============================================================================


class TestToolExecutionResult:
    """Tests for ToolExecutionResult dataclass."""

    def test_successful_result(self):
        """Test creating successful result."""
        result = ToolExecutionResult(
            success=True,
            content="Test output",
            tool_name="test_tool",
            source=ToolSource.CLAUDE,
            duration_ms=100,
        )

        assert result.success is True
        assert result.content == "Test output"
        assert result.error is None
        assert result.tool_name == "test_tool"
        assert result.source == ToolSource.CLAUDE
        assert result.duration_ms == 100
        assert result.blocked_by_hook is False
        assert result.approval_denied is False

    def test_failed_result(self):
        """Test creating failed result."""
        result = ToolExecutionResult(
            success=False,
            error="Something went wrong",
            tool_name="test_tool",
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = ToolExecutionResult(
            success=True,
            content="Output",
            tool_name="test_tool",
            metadata={"key": "value"},
        )

        assert result.metadata == {"key": "value"}

    def test_result_execution_id_auto_generated(self):
        """Test execution ID is auto-generated."""
        result1 = ToolExecutionResult(success=True, tool_name="test")
        result2 = ToolExecutionResult(success=True, tool_name="test")

        assert result1.execution_id != result2.execution_id
        assert len(result1.execution_id) > 0


# =============================================================================
# UnifiedToolExecutor Tests
# =============================================================================


class TestUnifiedToolExecutor:
    """Tests for UnifiedToolExecutor."""

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, unified_executor, mock_tool_registry):
        """Test successful tool execution."""
        result = await unified_executor.execute(
            tool_name="test_tool",
            arguments={"param": "value"},
        )

        assert result.success is True
        assert result.tool_name == "test_tool"
        assert result.source == ToolSource.CLAUDE

    @pytest.mark.asyncio
    async def test_execute_tool_with_source(self, unified_executor):
        """Test tool execution with specific source."""
        result = await unified_executor.execute(
            tool_name="test_tool",
            arguments={},
            source=ToolSource.MAF,
        )

        assert result.source == ToolSource.MAF

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self, mock_hook_chain, mock_context_bridge):
        """Test tool not found returns error result.

        Note: The executor catches ToolNotFoundError internally and returns
        a result with success=False, rather than propagating the exception.
        """
        # Create executor with registry that returns None
        mock_registry = MagicMock()
        mock_registry.get_tool_instance.return_value = None
        mock_registry.get_available_tools.return_value = []

        executor = UnifiedToolExecutor(
            tool_registry=mock_registry,
            hook_chain=mock_hook_chain,
            context_bridge=mock_context_bridge,
        )

        result = await executor.execute(
            tool_name="nonexistent_tool",
            arguments={},
        )

        assert result.success is False
        assert "not found" in result.error.lower()
        assert result.tool_name == "nonexistent_tool"

    @pytest.mark.asyncio
    async def test_execute_tool_blocked_by_hook(
        self, unified_executor, mock_hook_chain
    ):
        """Test tool blocked by pre-hook."""
        # Create mock with is_rejected attribute (matches UnifiedToolExecutor logic)
        mock_result = MagicMock()
        mock_result.is_rejected = True
        mock_result.rejection_reason = "Blocked by policy"
        mock_hook_chain.run_tool_call.return_value = mock_result

        result = await unified_executor.execute(
            tool_name="test_tool",
            arguments={},
        )

        assert result.success is False
        assert result.blocked_by_hook is True
        assert "Blocked" in result.error or "Rejected" in result.error

    @pytest.mark.asyncio
    async def test_execute_batch(self, unified_executor):
        """Test batch execution of multiple tools."""
        # execute_batch expects List[Dict] with tool_name and arguments keys
        calls = [
            {"tool_name": "tool1", "arguments": {"param": "a"}},
            {"tool_name": "tool2", "arguments": {"param": "b"}},
            {"tool_name": "tool3", "arguments": {"param": "c"}},
        ]

        results = await unified_executor.execute_batch(calls)

        assert len(results) == 3
        for result in results:
            assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_session_id(self, unified_executor):
        """Test execution with session ID."""
        result = await unified_executor.execute(
            tool_name="test_tool",
            arguments={},
            session_id="test-session-123",
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_with_approval_denied(
        self, mock_tool_registry, mock_hook_chain, mock_context_bridge
    ):
        """Test execution with approval denied."""
        # Create mock approval service that denies requests
        mock_approval_service = MagicMock()
        mock_approval_service.request_approval = AsyncMock(return_value=False)

        executor = UnifiedToolExecutor(
            tool_registry=mock_tool_registry,
            hook_chain=mock_hook_chain,
            context_bridge=mock_context_bridge,
            approval_service=mock_approval_service,
        )

        result = await executor.execute(
            tool_name="test_tool",
            arguments={},
            approval_required=True,
        )

        assert result.success is False
        assert result.approval_denied is True


# =============================================================================
# ToolRouter Tests
# =============================================================================


class TestToolRouter:
    """Tests for ToolRouter."""

    def test_router_default_routing(self):
        """Test default routing strategy."""
        router = ToolRouter(
            default_strategy=RoutingStrategy.PREFER_CLAUDE,
        )

        decision = router.route("some_tool", {})

        assert decision.source == ToolSource.CLAUDE
        assert decision.rule_applied is None

    def test_router_with_rule(self):
        """Test routing with explicit rule."""
        router = ToolRouter()
        router.add_rule(RoutingRule(
            name="maf_tools",
            pattern="maf_*",
            target_source=ToolSource.MAF,
            priority=100,
        ))

        decision = router.route("maf_search", {})

        assert decision.source == ToolSource.MAF
        assert decision.rule_applied == "maf_tools"

    def test_router_with_hint(self):
        """Test routing with hint source."""
        router = ToolRouter()

        decision = router.route(
            "some_tool",
            {},
            hint_source=ToolSource.HYBRID,
        )

        assert decision.source == ToolSource.HYBRID
        assert decision.rule_applied == "explicit_hint"

    def test_router_rule_priority(self):
        """Test rule priority ordering."""
        router = ToolRouter()

        # Add rules in non-priority order
        router.add_rule(RoutingRule(
            name="low_priority",
            pattern="test_*",
            target_source=ToolSource.MAF,
            priority=10,
        ))
        router.add_rule(RoutingRule(
            name="high_priority",
            pattern="test_*",
            target_source=ToolSource.CLAUDE,
            priority=100,
        ))

        decision = router.route("test_tool", {})

        # High priority rule should win
        assert decision.source == ToolSource.CLAUDE
        assert decision.rule_applied == "high_priority"

    def test_router_pattern_matching(self):
        """Test pattern matching with wildcards."""
        router = ToolRouter()
        router.add_rule(RoutingRule(
            name="workflow_rule",
            pattern="workflow_*",
            target_source=ToolSource.MAF,
        ))

        # Should match
        decision1 = router.route("workflow_execute", {})
        assert decision1.source == ToolSource.MAF

        # Should not match
        decision2 = router.route("other_execute", {})
        assert decision2.source != ToolSource.MAF or decision2.rule_applied is None

    def test_router_capability_registration(self):
        """Test tool capability registration."""
        router = ToolRouter(
            default_strategy=RoutingStrategy.CAPABILITY_BASED,
        )

        router.register_tool_capability("maf_tool", ToolSource.MAF)
        router.register_tool_capability("claude_tool", ToolSource.CLAUDE)

        decision1 = router.route("maf_tool", {})
        decision2 = router.route("claude_tool", {})

        assert decision1.source == ToolSource.MAF
        assert decision2.source == ToolSource.CLAUDE

    def test_router_stats(self):
        """Test routing statistics."""
        router = ToolRouter()

        # Make some routing decisions
        router.route("tool1", {})
        router.route("tool2", {})
        router.route("tool3", {})

        stats = router.get_stats()

        assert stats["rule_count"] == 0
        assert sum(stats["call_counts"].values()) == 3

    def test_create_default_router(self):
        """Test default router factory function."""
        router = create_default_router()

        # Should have pre-configured rules
        stats = router.get_stats()
        assert stats["rule_count"] > 0

        # Test maf_prefixed rule
        decision = router.route("maf_something", {})
        assert decision.source == ToolSource.MAF

    def test_router_remove_rule(self):
        """Test removing a routing rule."""
        router = ToolRouter()
        router.add_rule(RoutingRule(
            name="test_rule",
            pattern="test_*",
            target_source=ToolSource.MAF,
        ))

        assert router.remove_rule("test_rule") is True
        assert router.remove_rule("nonexistent") is False


# =============================================================================
# ResultHandler Tests
# =============================================================================


class TestResultHandler:
    """Tests for ResultHandler."""

    def test_format_to_claude(self):
        """Test formatting to Claude SDK format."""
        handler = ResultHandler()
        result = ToolExecutionResult(
            success=True,
            content="Test output",
            tool_name="test_tool",
            execution_id="test-123",
        )

        formatted = handler.format(result, ResultFormat.CLAUDE)

        assert formatted.format == ResultFormat.CLAUDE
        assert formatted.data["type"] == "tool_result"
        assert formatted.data["tool_use_id"] == "test-123"
        assert formatted.data["content"] == "Test output"
        assert formatted.data["is_error"] is False

    def test_format_to_maf(self):
        """Test formatting to MAF format."""
        handler = ResultHandler()
        result = ToolExecutionResult(
            success=True,
            content="Test output",
            tool_name="test_tool",
            duration_ms=100,
        )

        formatted = handler.format(result, ResultFormat.MAF)

        assert formatted.format == ResultFormat.MAF
        assert formatted.data["function_name"] == "test_tool"
        assert formatted.data["output"] == "Test output"
        assert formatted.data["success"] is True
        assert formatted.data["execution_time_ms"] == 100

    def test_format_to_json(self):
        """Test formatting to JSON format."""
        handler = ResultHandler()
        result = ToolExecutionResult(
            success=True,
            content="Test output",
            tool_name="test_tool",
        )

        formatted = handler.format(result, ResultFormat.JSON)

        assert formatted.format == ResultFormat.JSON
        assert "execution_id" in formatted.data
        assert "tool_name" in formatted.data
        assert "success" in formatted.data

    def test_format_error_result(self):
        """Test formatting error result."""
        handler = ResultHandler()
        result = ToolExecutionResult(
            success=False,
            error="Something failed",
            tool_name="test_tool",
        )

        formatted = handler.format(result, ResultFormat.CLAUDE)

        assert formatted.data["is_error"] is True
        assert "Something failed" in formatted.data["content"]

    def test_process_updates_stats(self):
        """Test that processing updates statistics."""
        handler = ResultHandler()

        result = ToolExecutionResult(
            success=True,
            tool_name="test",
            source=ToolSource.CLAUDE,
        )
        handler.process(result)

        stats = handler.get_stats()
        assert stats["total_processed"] == 1
        assert stats["successful"] == 1
        assert stats["by_source"]["claude"] == 1

    def test_process_batch(self):
        """Test batch processing."""
        handler = ResultHandler()

        results = [
            ToolExecutionResult(success=True, tool_name="t1"),
            ToolExecutionResult(success=False, tool_name="t2", error="err"),
            ToolExecutionResult(success=True, tool_name="t3"),
        ]

        processed = handler.process_batch(results)

        assert len(processed) == 3

        stats = handler.get_stats()
        assert stats["total_processed"] == 3
        assert stats["successful"] == 2
        assert stats["failed"] == 1

    def test_aggregate_results(self):
        """Test result aggregation."""
        handler = ResultHandler()

        results = [
            ToolExecutionResult(
                success=True,
                tool_name="t1",
                duration_ms=100,
                source=ToolSource.CLAUDE,
            ),
            ToolExecutionResult(
                success=True,
                tool_name="t2",
                duration_ms=200,
                source=ToolSource.MAF,
            ),
            ToolExecutionResult(
                success=False,
                tool_name="t3",
                duration_ms=50,
                error="err",
            ),
        ]

        aggregated = handler.aggregate(results)

        assert aggregated["count"] == 3
        assert aggregated["success_count"] == 2
        assert aggregated["failure_count"] == 1
        assert aggregated["total_duration_ms"] == 350
        assert aggregated["success_rate"] == pytest.approx(2/3)

    def test_caching(self):
        """Test result caching."""
        handler = ResultHandler(cache_results=True)

        result = ToolExecutionResult(
            success=True,
            tool_name="test",
            execution_id="cache-test-123",
        )
        handler.process(result)

        cached = handler.get_cached("cache-test-123")

        assert cached is not None
        assert cached.execution_id == "cache-test-123"

    def test_cache_eviction(self):
        """Test cache LRU eviction."""
        handler = ResultHandler(cache_results=True, max_cache_size=2)

        # Add 3 results (exceeds cache size of 2)
        for i in range(3):
            result = ToolExecutionResult(
                success=True,
                tool_name=f"tool_{i}",
                execution_id=f"id_{i}",
            )
            handler.process(result)

        # First result should be evicted
        assert handler.get_cached("id_0") is None
        assert handler.get_cached("id_1") is not None
        assert handler.get_cached("id_2") is not None

    def test_clear_cache(self):
        """Test clearing cache."""
        handler = ResultHandler()

        result = ToolExecutionResult(success=True, tool_name="test")
        handler.process(result)

        cleared = handler.clear_cache()

        assert cleared == 1
        assert handler.get_stats()["cache_size"] == 0

    def test_sync_callback(self):
        """Test sync callback invocation."""
        handler = ResultHandler()
        callback_results = []

        def callback(result):
            callback_results.append(result)

        handler.add_sync_callback(callback)

        result = ToolExecutionResult(success=True, tool_name="test")
        handler.process(result)

        assert len(callback_results) == 1
        assert callback_results[0] == result

    def test_create_default_handler(self):
        """Test default handler factory function."""
        handler = create_default_handler(cache_results=False)

        assert handler.get_stats()["cache_enabled"] is False


# =============================================================================
# Integration Tests
# =============================================================================


class TestExecutionIntegration:
    """Integration tests for execution components."""

    @pytest.mark.asyncio
    async def test_executor_with_router_and_handler(
        self, mock_tool_registry, mock_hook_chain, mock_context_bridge
    ):
        """Test unified executor with router and handler integration."""
        executor = UnifiedToolExecutor(
            tool_registry=mock_tool_registry,
            hook_chain=mock_hook_chain,
            context_bridge=mock_context_bridge,
        )

        router = create_default_router()
        handler = create_default_handler()

        # Route the tool
        decision = router.route("maf_execute", {})

        # Execute with routed source
        result = await executor.execute(
            tool_name="maf_execute",
            arguments={"data": "test"},
            source=decision.source,
        )

        # Process result
        handler.process(result)

        # Verify flow
        assert decision.source == ToolSource.MAF
        assert result.success is True
        assert handler.get_stats()["total_processed"] == 1

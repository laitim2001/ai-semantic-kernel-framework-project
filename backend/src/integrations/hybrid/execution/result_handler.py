# =============================================================================
# IPA Platform - Hybrid Execution: Result Handler
# =============================================================================
# Sprint 54: HybridOrchestrator Refactor
#
# Result Handler for Hybrid MAF + Claude SDK Architecture.
# Processes, transforms, and synchronizes tool execution results
# between different framework formats.
#
# Dependencies:
#   - ToolExecutionResult, ToolSource (src.integrations.hybrid.execution)
#   - ContextBridge (src.integrations.hybrid.context)
# =============================================================================

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol


from .unified_executor import ToolExecutionResult, ToolSource


class ResultFormat(Enum):
    """Result format types for different frameworks."""

    CLAUDE = "claude"  # Claude SDK format
    MAF = "maf"  # Microsoft Agent Framework format
    UNIFIED = "unified"  # Unified internal format
    JSON = "json"  # Plain JSON format


@dataclass
class FormattedResult:
    """
    Formatted result for specific framework.

    Attributes:
        format: Target format type
        data: Formatted result data
        original: Original ToolExecutionResult
        transformed_at: Timestamp of transformation
    """

    format: ResultFormat
    data: Dict[str, Any]
    original: ToolExecutionResult
    transformed_at: datetime = field(default_factory=datetime.utcnow)


class ResultTransformer(Protocol):
    """Protocol for result transformers."""

    def transform(
        self,
        result: ToolExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Transform result to target format."""
        ...


class ClaudeResultTransformer:
    """Transform results to Claude SDK format."""

    def transform(
        self,
        result: ToolExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform to Claude SDK tool result format.

        Args:
            result: Tool execution result
            context: Optional additional context

        Returns:
            Claude SDK formatted result
        """
        base_result = {
            "type": "tool_result",
            "tool_use_id": result.execution_id,
            "content": result.content if result.success else f"Error: {result.error}",
            "is_error": not result.success,
        }

        # Add metadata if present
        if result.metadata:
            base_result["metadata"] = result.metadata

        return base_result


class MAFResultTransformer:
    """Transform results to Microsoft Agent Framework format."""

    def transform(
        self,
        result: ToolExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform to MAF format.

        Args:
            result: Tool execution result
            context: Optional additional context

        Returns:
            MAF formatted result
        """
        return {
            "function_name": result.tool_name,
            "output": result.content if result.success else None,
            "error": result.error,
            "success": result.success,
            "execution_time_ms": result.duration_ms,
            "metadata": {
                "execution_id": result.execution_id,
                "source": result.source.value,
                "blocked_by_hook": result.blocked_by_hook,
                "approval_denied": result.approval_denied,
                **(result.metadata or {}),
            },
        }


class UnifiedResultTransformer:
    """Transform results to unified internal format."""

    def transform(
        self,
        result: ToolExecutionResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transform to unified internal format.

        Args:
            result: Tool execution result
            context: Optional additional context

        Returns:
            Unified internal format result
        """
        return {
            "id": result.execution_id,
            "tool": result.tool_name,
            "source": result.source.value,
            "status": "success" if result.success else "error",
            "content": result.content,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "blocked": result.blocked_by_hook,
            "approval_denied": result.approval_denied,
            "metadata": result.metadata,
            "context": context,
        }


class ResultHandler:
    """
    Result Handler for processing and transforming execution results.

    Handles:
    - Result format transformation between frameworks
    - Result aggregation for batch operations
    - Result caching and history
    - Result synchronization callbacks

    Example:
        >>> handler = ResultHandler()
        >>> result = ToolExecutionResult(...)
        >>> formatted = handler.format(result, ResultFormat.CLAUDE)
        >>> print(formatted.data)  # Claude SDK format
    """

    def __init__(
        self,
        cache_results: bool = True,
        max_cache_size: int = 1000,
    ):
        """
        Initialize ResultHandler.

        Args:
            cache_results: Whether to cache results
            max_cache_size: Maximum number of results to cache
        """
        self._cache_results = cache_results
        self._max_cache_size = max_cache_size
        self._result_cache: Dict[str, ToolExecutionResult] = {}
        self._cache_order: List[str] = []

        # Initialize transformers
        self._transformers: Dict[ResultFormat, ResultTransformer] = {
            ResultFormat.CLAUDE: ClaudeResultTransformer(),
            ResultFormat.MAF: MAFResultTransformer(),
            ResultFormat.UNIFIED: UnifiedResultTransformer(),
        }

        # Sync callbacks
        self._sync_callbacks: List[Callable[[ToolExecutionResult], None]] = []

        # Statistics
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "blocked": 0,
            "by_source": {s.value: 0 for s in ToolSource},
        }

    def register_transformer(
        self,
        format_type: ResultFormat,
        transformer: ResultTransformer,
    ) -> None:
        """
        Register a custom transformer for a format.

        Args:
            format_type: Format type to register
            transformer: Transformer implementation
        """
        self._transformers[format_type] = transformer

    def add_sync_callback(
        self,
        callback: Callable[[ToolExecutionResult], None],
    ) -> None:
        """
        Add a callback for result synchronization.

        Args:
            callback: Callback function to invoke on each result
        """
        self._sync_callbacks.append(callback)

    def format(
        self,
        result: ToolExecutionResult,
        target_format: ResultFormat,
        context: Optional[Dict[str, Any]] = None,
    ) -> FormattedResult:
        """
        Format a result for a specific framework.

        Args:
            result: Tool execution result to format
            target_format: Target format type
            context: Optional additional context

        Returns:
            FormattedResult with transformed data
        """
        # Handle JSON format separately
        if target_format == ResultFormat.JSON:
            data = {
                "execution_id": result.execution_id,
                "tool_name": result.tool_name,
                "success": result.success,
                "content": result.content,
                "error": result.error,
                "source": result.source.value,
                "duration_ms": result.duration_ms,
                "blocked_by_hook": result.blocked_by_hook,
                "approval_denied": result.approval_denied,
                "metadata": result.metadata,
            }
        else:
            transformer = self._transformers.get(target_format)
            if transformer is None:
                raise ValueError(f"No transformer registered for format: {target_format}")
            data = transformer.transform(result, context)

        return FormattedResult(
            format=target_format,
            data=data,
            original=result,
        )

    def process(
        self,
        result: ToolExecutionResult,
        sync: bool = True,
    ) -> ToolExecutionResult:
        """
        Process a result (cache, update stats, sync).

        Args:
            result: Tool execution result to process
            sync: Whether to invoke sync callbacks

        Returns:
            Processed result (same instance)
        """
        # Update statistics
        self._stats["total_processed"] += 1
        self._stats["by_source"][result.source.value] += 1

        if result.success:
            self._stats["successful"] += 1
        else:
            self._stats["failed"] += 1

        if result.blocked_by_hook:
            self._stats["blocked"] += 1

        # Cache if enabled
        if self._cache_results:
            self._cache_result(result)

        # Invoke sync callbacks
        if sync:
            for callback in self._sync_callbacks:
                try:
                    callback(result)
                except Exception:
                    # Log but don't fail on callback errors
                    pass

        return result

    def process_batch(
        self,
        results: List[ToolExecutionResult],
        sync: bool = True,
    ) -> List[ToolExecutionResult]:
        """
        Process multiple results.

        Args:
            results: List of results to process
            sync: Whether to invoke sync callbacks

        Returns:
            List of processed results
        """
        return [self.process(r, sync=sync) for r in results]

    def aggregate(
        self,
        results: List[ToolExecutionResult],
    ) -> Dict[str, Any]:
        """
        Aggregate multiple results into a summary.

        Args:
            results: List of results to aggregate

        Returns:
            Aggregated summary dictionary
        """
        if not results:
            return {
                "count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_duration_ms": 0,
                "results": [],
            }

        success_count = sum(1 for r in results if r.success)
        total_duration = sum(r.duration_ms for r in results)

        return {
            "count": len(results),
            "success_count": success_count,
            "failure_count": len(results) - success_count,
            "success_rate": success_count / len(results),
            "total_duration_ms": total_duration,
            "avg_duration_ms": total_duration / len(results),
            "by_source": self._group_by_source(results),
            "blocked_count": sum(1 for r in results if r.blocked_by_hook),
            "approval_denied_count": sum(1 for r in results if r.approval_denied),
            "results": [
                {
                    "id": r.execution_id,
                    "tool": r.tool_name,
                    "success": r.success,
                    "duration_ms": r.duration_ms,
                }
                for r in results
            ],
        }

    def get_cached(
        self,
        execution_id: str,
    ) -> Optional[ToolExecutionResult]:
        """
        Get a cached result by execution ID.

        Args:
            execution_id: Execution ID to look up

        Returns:
            Cached result or None if not found
        """
        return self._result_cache.get(execution_id)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get handler statistics.

        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "cache_size": len(self._result_cache),
            "cache_enabled": self._cache_results,
        }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "blocked": 0,
            "by_source": {s.value: 0 for s in ToolSource},
        }

    def clear_cache(self) -> int:
        """
        Clear the result cache.

        Returns:
            Number of cached items cleared
        """
        count = len(self._result_cache)
        self._result_cache.clear()
        self._cache_order.clear()
        return count

    def _cache_result(self, result: ToolExecutionResult) -> None:
        """Cache a result with LRU eviction."""
        execution_id = result.execution_id

        # Check if already cached
        if execution_id in self._result_cache:
            # Move to end (most recently used)
            self._cache_order.remove(execution_id)
            self._cache_order.append(execution_id)
            return

        # Evict if at capacity
        while len(self._result_cache) >= self._max_cache_size:
            oldest_id = self._cache_order.pop(0)
            del self._result_cache[oldest_id]

        # Add to cache
        self._result_cache[execution_id] = result
        self._cache_order.append(execution_id)

    def _group_by_source(
        self,
        results: List[ToolExecutionResult],
    ) -> Dict[str, int]:
        """Group results by source."""
        counts: Dict[str, int] = {}
        for result in results:
            source_val = result.source.value
            counts[source_val] = counts.get(source_val, 0) + 1
        return counts


# =============================================================================
# Factory Functions
# =============================================================================


def create_default_handler(
    cache_results: bool = True,
) -> ResultHandler:
    """
    Create a ResultHandler with default configuration.

    Args:
        cache_results: Whether to enable result caching

    Returns:
        Configured ResultHandler instance
    """
    return ResultHandler(
        cache_results=cache_results,
        max_cache_size=1000,
    )

"""
IPA Platform - Database Query Optimization Module

Provides utilities for optimizing database queries including:
- Query analysis and optimization suggestions
- N+1 query detection
- Index recommendations
- Query batching utilities

Author: IPA Platform Team
Version: 1.0.0
"""

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypeVar, Generic, Callable
from functools import wraps
from contextlib import asynccontextmanager

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# Query Statistics
# =============================================================================

@dataclass
class QueryStats:
    """Statistics for a single query execution."""

    query: str
    duration_ms: float
    rows_affected: int
    timestamp: float
    is_slow: bool = False


# =============================================================================
# Query Optimizer
# =============================================================================

class QueryOptimizer:
    """
    Provides query optimization utilities and monitoring.

    Features:
    - Query timing and logging
    - Slow query detection
    - N+1 query pattern detection
    - Query batching support
    """

    def __init__(
        self,
        slow_query_threshold_ms: float = 100.0,
        log_all_queries: bool = False,
    ):
        """
        Initialize query optimizer.

        Args:
            slow_query_threshold_ms: Threshold for slow query logging
            log_all_queries: Whether to log all queries
        """
        self._slow_threshold = slow_query_threshold_ms
        self._log_all = log_all_queries
        self._query_stats: List[QueryStats] = []
        self._n1_detector = N1QueryDetector()

    def track_query(
        self,
        query: str,
        duration_ms: float,
        rows_affected: int = 0,
    ) -> None:
        """Record query statistics."""
        is_slow = duration_ms > self._slow_threshold

        stats = QueryStats(
            query=query[:500],  # Truncate long queries
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            timestamp=time.time(),
            is_slow=is_slow,
        )

        self._query_stats.append(stats)

        # Keep only last 1000 queries
        if len(self._query_stats) > 1000:
            self._query_stats = self._query_stats[-1000:]

        # Log slow queries
        if is_slow:
            logger.warning(
                "slow_query_detected",
                duration_ms=duration_ms,
                query_preview=query[:200],
            )
        elif self._log_all:
            logger.debug(
                "query_executed",
                duration_ms=duration_ms,
                rows=rows_affected,
            )

        # Check for N+1 pattern
        self._n1_detector.record_query(query)

    def get_slow_queries(self, limit: int = 10) -> List[QueryStats]:
        """Get the slowest queries."""
        slow = [q for q in self._query_stats if q.is_slow]
        return sorted(slow, key=lambda x: x.duration_ms, reverse=True)[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics summary."""
        if not self._query_stats:
            return {"total_queries": 0}

        durations = [q.duration_ms for q in self._query_stats]

        return {
            "total_queries": len(self._query_stats),
            "slow_queries": sum(1 for q in self._query_stats if q.is_slow),
            "avg_duration_ms": sum(durations) / len(durations),
            "max_duration_ms": max(durations),
            "min_duration_ms": min(durations),
            "n1_warnings": self._n1_detector.get_warnings(),
        }

    def reset_stats(self) -> None:
        """Reset all statistics."""
        self._query_stats.clear()
        self._n1_detector.reset()


# =============================================================================
# N+1 Query Detector
# =============================================================================

class N1QueryDetector:
    """
    Detects N+1 query patterns.

    Tracks similar queries executed in rapid succession,
    which often indicates an N+1 query problem.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        count_threshold: int = 5,
        time_window: float = 1.0,
    ):
        """
        Initialize N+1 detector.

        Args:
            similarity_threshold: How similar queries must be (0-1)
            count_threshold: Minimum similar queries to trigger warning
            time_window: Time window in seconds
        """
        self._threshold = similarity_threshold
        self._count_threshold = count_threshold
        self._time_window = time_window
        self._recent_queries: List[tuple[str, float]] = []
        self._warnings: List[str] = []

    def record_query(self, query: str) -> None:
        """Record a query and check for N+1 pattern."""
        current_time = time.time()

        # Add query
        self._recent_queries.append((query, current_time))

        # Remove old queries
        self._recent_queries = [
            (q, t) for q, t in self._recent_queries
            if current_time - t < self._time_window
        ]

        # Check for pattern
        self._check_pattern(query)

    def _check_pattern(self, new_query: str) -> None:
        """Check if query is part of N+1 pattern."""
        # Get queries in time window
        if len(self._recent_queries) < self._count_threshold:
            return

        # Count similar queries
        similar_count = sum(
            1 for q, _ in self._recent_queries
            if self._is_similar(q, new_query)
        )

        if similar_count >= self._count_threshold:
            # Normalize query for warning
            normalized = self._normalize_query(new_query)
            if normalized not in self._warnings:
                self._warnings.append(normalized)
                logger.warning(
                    "n_plus_1_detected",
                    similar_queries=similar_count,
                    query_pattern=normalized[:200],
                )

    def _is_similar(self, q1: str, q2: str) -> bool:
        """Check if two queries are similar (same pattern, different params)."""
        # Simple similarity: normalize and compare
        n1 = self._normalize_query(q1)
        n2 = self._normalize_query(q2)
        return n1 == n2

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing specific values."""
        import re
        # Replace quoted strings
        query = re.sub(r"'[^']*'", "'?'", query)
        # Replace numbers
        query = re.sub(r"\b\d+\b", "?", query)
        # Replace UUIDs
        query = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "?",
            query,
            flags=re.IGNORECASE,
        )
        return query.strip()

    def get_warnings(self) -> List[str]:
        """Get N+1 warnings."""
        return self._warnings.copy()

    def reset(self) -> None:
        """Reset detector state."""
        self._recent_queries.clear()
        self._warnings.clear()


# =============================================================================
# Query Batching
# =============================================================================

class QueryBatcher(Generic[T]):
    """
    Batches multiple queries into single database roundtrips.

    Useful for avoiding N+1 queries by collecting IDs and
    fetching all items in one query.

    Usage:
        async with QueryBatcher(session, User, "id") as batcher:
            users = await batcher.load([user_id1, user_id2, user_id3])
    """

    def __init__(
        self,
        session: AsyncSession,
        model: type,
        id_field: str = "id",
        batch_size: int = 100,
    ):
        """
        Initialize query batcher.

        Args:
            session: Database session
            model: SQLAlchemy model class
            id_field: Name of the ID field
            batch_size: Maximum batch size
        """
        self._session = session
        self._model = model
        self._id_field = id_field
        self._batch_size = batch_size
        self._pending_ids: List[Any] = []
        self._cache: Dict[Any, T] = {}

    async def load(self, ids: List[Any]) -> List[Optional[T]]:
        """
        Load items by IDs, using batching.

        Args:
            ids: List of IDs to load

        Returns:
            List of items (None for not found)
        """
        # Check cache first
        uncached_ids = [id for id in ids if id not in self._cache]

        # Fetch uncached items
        if uncached_ids:
            await self._fetch_batch(uncached_ids)

        # Return items in order
        return [self._cache.get(id) for id in ids]

    async def _fetch_batch(self, ids: List[Any]) -> None:
        """Fetch a batch of items by IDs."""
        from sqlalchemy import select

        # Process in batches
        for i in range(0, len(ids), self._batch_size):
            batch_ids = ids[i:i + self._batch_size]

            stmt = select(self._model).where(
                getattr(self._model, self._id_field).in_(batch_ids)
            )

            result = await self._session.execute(stmt)
            items = result.scalars().all()

            # Update cache
            for item in items:
                item_id = getattr(item, self._id_field)
                self._cache[item_id] = item


# =============================================================================
# Index Recommendations
# =============================================================================

class IndexRecommendations:
    """
    Recommended database indexes for optimal performance.

    These indexes should be added via Alembic migrations.
    """

    RECOMMENDED_INDEXES = [
        # Executions
        {
            "table": "executions",
            "columns": ["status"],
            "name": "ix_executions_status",
            "reason": "Filter executions by status (pending, running, etc.)",
        },
        {
            "table": "executions",
            "columns": ["workflow_id", "created_at"],
            "name": "ix_executions_workflow_created",
            "reason": "Get recent executions for a workflow",
        },
        {
            "table": "executions",
            "columns": ["created_at"],
            "name": "ix_executions_created_at",
            "reason": "Sort executions by date",
        },
        # Checkpoints
        {
            "table": "checkpoints",
            "columns": ["status"],
            "name": "ix_checkpoints_status",
            "reason": "Filter checkpoints by status (pending approval)",
        },
        {
            "table": "checkpoints",
            "columns": ["execution_id"],
            "name": "ix_checkpoints_execution_id",
            "reason": "Get checkpoints for an execution",
        },
        # Audit Logs
        {
            "table": "audit_logs",
            "columns": ["created_at"],
            "name": "ix_audit_logs_created_at",
            "reason": "Query audit logs by date range",
        },
        {
            "table": "audit_logs",
            "columns": ["entity_type", "entity_id"],
            "name": "ix_audit_logs_entity",
            "reason": "Get audit trail for specific entity",
        },
        # Workflows
        {
            "table": "workflows",
            "columns": ["is_active"],
            "name": "ix_workflows_is_active",
            "reason": "Filter active workflows",
        },
        {
            "table": "workflows",
            "columns": ["category"],
            "name": "ix_workflows_category",
            "reason": "Filter workflows by category",
        },
        # Agents
        {
            "table": "agents",
            "columns": ["is_active"],
            "name": "ix_agents_is_active",
            "reason": "Filter active agents",
        },
        {
            "table": "agents",
            "columns": ["category"],
            "name": "ix_agents_category",
            "reason": "Filter agents by category",
        },
    ]

    @classmethod
    def generate_migration(cls) -> str:
        """Generate Alembic migration script for indexes."""
        lines = [
            "# Index Migration",
            "# Generated by IndexRecommendations",
            "",
            "from alembic import op",
            "import sqlalchemy as sa",
            "",
            "",
            "def upgrade():",
        ]

        for idx in cls.RECOMMENDED_INDEXES:
            cols = ", ".join(f"'{c}'" for c in idx["columns"])
            lines.append(
                f"    op.create_index('{idx['name']}', '{idx['table']}', [{cols}])"
            )

        lines.extend([
            "",
            "",
            "def downgrade():",
        ])

        for idx in cls.RECOMMENDED_INDEXES:
            lines.append(
                f"    op.drop_index('{idx['name']}', table_name='{idx['table']}')"
            )

        return "\n".join(lines)

    @classmethod
    def get_recommendations(cls) -> List[Dict[str, Any]]:
        """Get list of index recommendations."""
        return cls.RECOMMENDED_INDEXES.copy()


# =============================================================================
# Query Timing Decorator
# =============================================================================

def timed_query(name: str = "query"):
    """
    Decorator to time async database queries.

    Usage:
        @timed_query("get_user_by_id")
        async def get_user(user_id: str) -> User:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    "query_timing",
                    name=name,
                    duration_ms=round(duration_ms, 2),
                )

        return wrapper
    return decorator


# =============================================================================
# Connection Pool Settings
# =============================================================================

class ConnectionPoolSettings:
    """Recommended connection pool settings for different environments."""

    DEVELOPMENT = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,  # 30 minutes
        "pool_pre_ping": True,
    }

    PRODUCTION = {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 30,
        "pool_recycle": 3600,  # 1 hour
        "pool_pre_ping": True,
    }

    HIGH_TRAFFIC = {
        "pool_size": 50,
        "max_overflow": 50,
        "pool_timeout": 10,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

    @classmethod
    def get_settings(cls, environment: str) -> Dict[str, Any]:
        """Get pool settings for environment."""
        settings_map = {
            "development": cls.DEVELOPMENT,
            "dev": cls.DEVELOPMENT,
            "production": cls.PRODUCTION,
            "prod": cls.PRODUCTION,
            "high_traffic": cls.HIGH_TRAFFIC,
        }
        return settings_map.get(environment.lower(), cls.DEVELOPMENT)

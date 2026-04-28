# =============================================================================
# IPA Platform - PostgreSQL Checkpoint Storage
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# PostgreSQL storage backend for HybridCheckpoint.
# Provides persistent storage with full ACID compliance and query capabilities.
#
# Key Features:
#   - ACID-compliant persistence
#   - Rich query capabilities with SQL
#   - Index optimization for session lookups
#   - Binary data storage with compression
#
# Table Schema:
#   hybrid_checkpoints:
#     - id (UUID, PK)
#     - session_id (VARCHAR, indexed)
#     - checkpoint_type (VARCHAR)
#     - status (VARCHAR)
#     - execution_mode (VARCHAR)
#     - data (BYTEA, compressed checkpoint)
#     - checksum (VARCHAR)
#     - created_at (TIMESTAMP, indexed)
#     - updated_at (TIMESTAMP)
#     - expires_at (TIMESTAMP, indexed)
#
# Dependencies:
#   - SQLAlchemy (async)
#   - UnifiedCheckpointStorage (storage)
#   - HybridCheckpoint (models)
# =============================================================================

from datetime import datetime
from typing import Any, List, Optional

from ..models import CheckpointStatus, CheckpointType, HybridCheckpoint, RestoreResult
from ..storage import (
    CheckpointQuery,
    StorageConfig,
    StorageConnectionError,
    StorageError,
    StorageStats,
    UnifiedCheckpointStorage,
)


class PostgresCheckpointStorage(UnifiedCheckpointStorage):
    """
    PostgreSQL storage backend for checkpoints.

    Provides persistent storage with full ACID compliance.
    Suitable for production environments requiring data durability.

    Example:
        >>> from sqlalchemy.ext.asyncio import AsyncSession
        >>> storage = PostgresCheckpointStorage(session=db_session)
        >>> checkpoint_id = await storage.save(checkpoint)

    Table Requirements:
        The following table must exist in the database:

        CREATE TABLE hybrid_checkpoints (
            id UUID PRIMARY KEY,
            session_id VARCHAR(255) NOT NULL,
            checkpoint_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            execution_mode VARCHAR(50),
            data BYTEA NOT NULL,
            checksum VARCHAR(64),
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMP
        );

        CREATE INDEX idx_checkpoints_session ON hybrid_checkpoints(session_id);
        CREATE INDEX idx_checkpoints_created ON hybrid_checkpoints(created_at);
        CREATE INDEX idx_checkpoints_expires ON hybrid_checkpoints(expires_at);
    """

    def __init__(
        self,
        session: Any = None,
        config: Optional[StorageConfig] = None,
        table_name: str = "hybrid_checkpoints",
    ):
        """
        Initialize PostgreSQL storage.

        Args:
            session: SQLAlchemy AsyncSession instance
            config: Storage configuration
            table_name: Name of the checkpoints table
        """
        super().__init__(config)
        self._session = session
        self._table_name = table_name

    async def _ensure_connected(self) -> None:
        """Verify database connection is available."""
        if self._session is None:
            raise StorageConnectionError("Database session not configured")

    async def save(self, checkpoint: HybridCheckpoint) -> str:
        """
        Save checkpoint to PostgreSQL.

        Args:
            checkpoint: Checkpoint to save

        Returns:
            Checkpoint ID

        Raises:
            StorageError: If save operation fails
        """
        await self._ensure_connected()

        try:
            # Serialize checkpoint
            serialized = self.serializer.serialize(checkpoint)
            data = serialized.data
            checksum = serialized.checksum

            # Calculate expiration time
            expires_at = checkpoint.calculate_expiration(self.config.ttl_seconds)

            # Build SQL
            sql = f"""
                INSERT INTO {self._table_name}
                (id, session_id, checkpoint_type, status, execution_mode,
                 data, checksum, metadata, created_at, updated_at, expires_at)
                VALUES (:id, :session_id, :checkpoint_type, :status, :execution_mode,
                        :data, :checksum, :metadata, :created_at, :updated_at, :expires_at)
                ON CONFLICT (id) DO UPDATE SET
                    status = EXCLUDED.status,
                    data = EXCLUDED.data,
                    checksum = EXCLUDED.checksum,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at,
                    expires_at = EXCLUDED.expires_at
            """

            from sqlalchemy import text

            await self._session.execute(
                text(sql),
                {
                    "id": checkpoint.checkpoint_id,
                    "session_id": checkpoint.session_id,
                    "checkpoint_type": checkpoint.checkpoint_type.value,
                    "status": checkpoint.status.value,
                    "execution_mode": checkpoint.execution_mode,
                    "data": data,
                    "checksum": checksum,
                    "metadata": checkpoint.metadata,
                    "created_at": checkpoint.created_at,
                    "updated_at": checkpoint.updated_at,
                    "expires_at": expires_at,
                },
            )
            await self._session.commit()

            # Enforce retention limits
            await self.enforce_retention(checkpoint.session_id)

            return checkpoint.checkpoint_id

        except Exception as e:
            await self._session.rollback()
            raise StorageError(f"Failed to save checkpoint: {e}")

    async def load(self, checkpoint_id: str) -> Optional[HybridCheckpoint]:
        """
        Load checkpoint from PostgreSQL.

        Args:
            checkpoint_id: ID of checkpoint to load

        Returns:
            HybridCheckpoint if found and not expired, None otherwise
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"""
                SELECT data, checksum, expires_at
                FROM {self._table_name}
                WHERE id = :id
            """

            result = await self._session.execute(
                text(sql), {"id": checkpoint_id}
            )
            row = result.fetchone()

            if row is None:
                return None

            data, checksum, expires_at = row

            # Check expiration
            if expires_at and datetime.utcnow() > expires_at:
                await self.delete(checkpoint_id)
                return None

            # Deserialize
            result = self.serializer.deserialize(data, expected_checksum=checksum)
            return result.checkpoint

        except Exception as e:
            raise StorageError(f"Failed to load checkpoint: {e}")

    async def delete(self, checkpoint_id: str) -> bool:
        """
        Delete checkpoint from PostgreSQL.

        Args:
            checkpoint_id: ID of checkpoint to delete

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"DELETE FROM {self._table_name} WHERE id = :id"
            result = await self._session.execute(text(sql), {"id": checkpoint_id})
            await self._session.commit()

            return result.rowcount > 0

        except Exception as e:
            await self._session.rollback()
            raise StorageError(f"Failed to delete checkpoint: {e}")

    async def exists(self, checkpoint_id: str) -> bool:
        """
        Check if checkpoint exists in PostgreSQL.

        Args:
            checkpoint_id: ID of checkpoint to check

        Returns:
            True if exists and not expired, False otherwise
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"""
                SELECT 1 FROM {self._table_name}
                WHERE id = :id AND (expires_at IS NULL OR expires_at > NOW())
            """

            result = await self._session.execute(text(sql), {"id": checkpoint_id})
            return result.fetchone() is not None

        except Exception as e:
            raise StorageError(f"Failed to check checkpoint existence: {e}")

    async def query(self, query: CheckpointQuery) -> List[HybridCheckpoint]:
        """
        Query checkpoints based on criteria.

        Uses SQL for efficient filtering and sorting.

        Args:
            query: Query parameters

        Returns:
            List of matching checkpoints
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            # Build WHERE clause
            conditions = ["(expires_at IS NULL OR expires_at > NOW())"]
            params = {}

            if query.session_id:
                conditions.append("session_id = :session_id")
                params["session_id"] = query.session_id

            if query.checkpoint_type:
                conditions.append("checkpoint_type = :checkpoint_type")
                params["checkpoint_type"] = query.checkpoint_type.value

            if query.status:
                conditions.append("status = :status")
                params["status"] = query.status.value

            if query.execution_mode:
                conditions.append("execution_mode = :execution_mode")
                params["execution_mode"] = query.execution_mode

            if query.created_after:
                conditions.append("created_at > :created_after")
                params["created_after"] = query.created_after

            if query.created_before:
                conditions.append("created_at < :created_before")
                params["created_before"] = query.created_before

            # Build ORDER BY clause
            order_dir = "ASC" if query.ascending else "DESC"
            order_by = f"ORDER BY {query.order_by} {order_dir}"

            # Build LIMIT and OFFSET
            limit_clause = ""
            if query.limit > 0:
                limit_clause = f"LIMIT {query.limit} OFFSET {query.offset}"

            # Execute query
            sql = f"""
                SELECT data, checksum
                FROM {self._table_name}
                WHERE {' AND '.join(conditions)}
                {order_by}
                {limit_clause}
            """

            result = await self._session.execute(text(sql), params)
            rows = result.fetchall()

            # Deserialize results
            checkpoints = []
            for data, checksum in rows:
                try:
                    result = self.serializer.deserialize(data, expected_checksum=checksum)
                    checkpoints.append(result.checkpoint)
                except Exception:
                    # Skip corrupted checkpoints
                    continue

            return checkpoints

        except Exception as e:
            raise StorageError(f"Failed to query checkpoints: {e}")

    async def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Uses SQL aggregation for efficiency.

        Returns:
            StorageStats with current statistics
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE expires_at IS NULL OR expires_at > NOW()) as active,
                    COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at <= NOW()) as expired,
                    COALESCE(SUM(LENGTH(data)), 0) as total_size,
                    COUNT(DISTINCT session_id) as sessions,
                    MIN(created_at) as oldest,
                    MAX(created_at) as newest
                FROM {self._table_name}
            """

            result = await self._session.execute(text(sql))
            row = result.fetchone()

            if row is None:
                return StorageStats()

            return StorageStats(
                total_checkpoints=row[0] or 0,
                active_checkpoints=row[1] or 0,
                expired_checkpoints=row[2] or 0,
                total_size_bytes=row[3] or 0,
                sessions_count=row[4] or 0,
                oldest_checkpoint=row[5],
                newest_checkpoint=row[6],
            )

        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {e}")

    async def cleanup_expired(self) -> int:
        """
        Remove expired checkpoints.

        Uses efficient SQL DELETE.

        Returns:
            Number of checkpoints removed
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"""
                DELETE FROM {self._table_name}
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """

            result = await self._session.execute(text(sql))
            await self._session.commit()

            return result.rowcount

        except Exception as e:
            await self._session.rollback()
            raise StorageError(f"Failed to cleanup expired checkpoints: {e}")

    async def create_table(self) -> None:
        """
        Create the checkpoints table if it doesn't exist.

        Call this during application initialization.
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    id UUID PRIMARY KEY,
                    session_id VARCHAR(255) NOT NULL,
                    checkpoint_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    execution_mode VARCHAR(50),
                    data BYTEA NOT NULL,
                    checksum VARCHAR(64),
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_session
                    ON {self._table_name}(session_id);
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_created
                    ON {self._table_name}(created_at);
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_expires
                    ON {self._table_name}(expires_at);
            """

            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    await self._session.execute(text(statement))

            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            raise StorageError(f"Failed to create table: {e}")

    async def drop_table(self) -> None:
        """
        Drop the checkpoints table.

        WARNING: This removes all data. Use with caution.
        """
        await self._ensure_connected()

        try:
            from sqlalchemy import text

            sql = f"DROP TABLE IF EXISTS {self._table_name} CASCADE"
            await self._session.execute(text(sql))
            await self._session.commit()

        except Exception as e:
            await self._session.rollback()
            raise StorageError(f"Failed to drop table: {e}")

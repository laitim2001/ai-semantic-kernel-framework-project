# =============================================================================
# IPA Platform - Checkpoint Repository
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Repository for Checkpoint model operations.
# Provides specialized methods for checkpoint management including:
#   - get_pending: List pending checkpoints needing approval
#   - get_by_execution: List checkpoints for an execution
#   - update_status: Update checkpoint approval status
#   - expire_old: Expire outdated checkpoints
#
# Supports the human-in-the-loop approval workflow.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.checkpoint import Checkpoint
from src.infrastructure.database.repositories.base import BaseRepository


class CheckpointRepository(BaseRepository[Checkpoint]):
    """
    Repository for Checkpoint model operations.

    Extends BaseRepository with checkpoint-specific methods:
        - get_pending: List checkpoints awaiting approval
        - get_by_execution: List checkpoints for an execution
        - list_by_execution: List with filtering
        - update_status: Approve/reject a checkpoint
        - expire_old: Mark expired checkpoints

    Example:
        repo = CheckpointRepository(session)
        pending = await repo.get_pending(limit=10)
        await repo.update_status(
            checkpoint_id,
            status="approved",
            response={"action": "proceed"},
            responded_by=user_id,
        )
    """

    model = Checkpoint

    async def get_pending(
        self,
        limit: int = 50,
        execution_id: Optional[UUID] = None,
    ) -> List[Checkpoint]:
        """
        Get pending checkpoints awaiting approval.

        Args:
            limit: Maximum number to return
            execution_id: Optional filter by execution

        Returns:
            List of pending checkpoints ordered by creation time
        """
        stmt = (
            select(Checkpoint)
            .filter(Checkpoint.status == "pending")
            .order_by(Checkpoint.created_at.asc())
            .limit(limit)
        )

        if execution_id:
            stmt = stmt.filter(Checkpoint.execution_id == execution_id)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_execution(
        self,
        execution_id: UUID,
        include_expired: bool = False,
    ) -> List[Checkpoint]:
        """
        Get all checkpoints for an execution.

        Args:
            execution_id: Execution UUID
            include_expired: Whether to include expired checkpoints

        Returns:
            List of checkpoints
        """
        stmt = (
            select(Checkpoint)
            .filter(Checkpoint.execution_id == execution_id)
            .order_by(Checkpoint.created_at.asc())
        )

        if not include_expired:
            stmt = stmt.filter(Checkpoint.status != "expired")

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_execution(
        self,
        execution_id: UUID,
        status: Optional[str] = None,
    ) -> List[Checkpoint]:
        """
        List checkpoints for an execution with optional status filter.

        Args:
            execution_id: Execution UUID
            status: Optional status filter

        Returns:
            List of checkpoints
        """
        stmt = (
            select(Checkpoint)
            .filter(Checkpoint.execution_id == execution_id)
            .order_by(Checkpoint.created_at.asc())
        )

        if status:
            stmt = stmt.filter(Checkpoint.status == status)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        checkpoint_id: UUID,
        status: str,
        response: Optional[Dict[str, Any]] = None,
        responded_by: Optional[UUID] = None,
        responded_at: Optional[datetime] = None,
    ) -> Optional[Checkpoint]:
        """
        Update checkpoint status (approve/reject).

        Args:
            checkpoint_id: Checkpoint UUID
            status: New status (approved, rejected)
            response: Optional response data
            responded_by: User who responded
            responded_at: When response was received

        Returns:
            Updated checkpoint or None if not found
        """
        update_data: Dict[str, Any] = {
            "status": status,
        }

        if response is not None:
            update_data["response"] = response

        if responded_by is not None:
            update_data["responded_by"] = responded_by

        if responded_at is not None:
            update_data["responded_at"] = responded_at
        else:
            update_data["responded_at"] = datetime.utcnow()

        return await self.update(checkpoint_id, **update_data)

    async def expire_old(
        self,
        before_date: Optional[datetime] = None,
    ) -> int:
        """
        Mark old checkpoints as expired.

        Args:
            before_date: Expire checkpoints created before this date
                        (defaults to checking expires_at field)

        Returns:
            Number of checkpoints expired
        """
        now = datetime.utcnow()

        # Find pending checkpoints past their expiration
        stmt = (
            select(Checkpoint)
            .filter(
                and_(
                    Checkpoint.status == "pending",
                    Checkpoint.expires_at.isnot(None),
                    Checkpoint.expires_at < now,
                )
            )
        )

        if before_date:
            stmt = stmt.filter(Checkpoint.created_at < before_date)

        result = await self._session.execute(stmt)
        expired_checkpoints = list(result.scalars().all())

        # Update each to expired status
        for checkpoint in expired_checkpoints:
            checkpoint.status = "expired"
            checkpoint.responded_at = now

        await self._session.flush()
        return len(expired_checkpoints)

    async def get_by_node(
        self,
        execution_id: UUID,
        node_id: str,
    ) -> Optional[Checkpoint]:
        """
        Get checkpoint for a specific node in an execution.

        Args:
            execution_id: Execution UUID
            node_id: Node ID

        Returns:
            Checkpoint or None if not found
        """
        stmt = (
            select(Checkpoint)
            .filter(
                and_(
                    Checkpoint.execution_id == execution_id,
                    Checkpoint.node_id == node_id,
                )
            )
            .order_by(Checkpoint.created_at.desc())
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_stats(
        self,
        execution_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Get checkpoint statistics.

        Args:
            execution_id: Optional filter by execution

        Returns:
            Dictionary with statistics
        """
        base_filter = []
        if execution_id:
            base_filter.append(Checkpoint.execution_id == execution_id)

        # Count by status
        stmt = select(
            Checkpoint.status,
            func.count(Checkpoint.id).label("count"),
        ).group_by(Checkpoint.status)

        if base_filter:
            stmt = stmt.filter(*base_filter)

        result = await self._session.execute(stmt)
        status_counts = {row.status: row.count for row in result}

        # Calculate average response time for responded checkpoints
        avg_stmt = select(
            func.avg(
                func.extract("epoch", Checkpoint.responded_at - Checkpoint.created_at)
            ).label("avg_response_seconds")
        ).filter(
            Checkpoint.responded_at.isnot(None)
        )

        if base_filter:
            avg_stmt = avg_stmt.filter(*base_filter)

        avg_result = await self._session.execute(avg_stmt)
        avg_row = avg_result.one()

        return {
            "pending": status_counts.get("pending", 0),
            "approved": status_counts.get("approved", 0),
            "rejected": status_counts.get("rejected", 0),
            "expired": status_counts.get("expired", 0),
            "total": sum(status_counts.values()),
            "avg_response_seconds": float(avg_row.avg_response_seconds or 0),
        }

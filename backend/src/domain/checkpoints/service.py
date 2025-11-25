"""
Checkpoint Service

Sprint 2 - Story S2-4: Teams Approval Flow

Service for managing checkpoint approval workflow.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.checkpoint import Checkpoint, CheckpointStatus
from src.infrastructure.database.models.audit_log import AuditAction
from src.domain.audit.service import AuditService
from src.domain.notifications.service import TeamsNotificationService, get_notification_service
from src.domain.notifications.schemas import CheckpointNotificationContext
from .schemas import (
    CheckpointCreate,
    CheckpointResponse,
    CheckpointApprovalRequest,
    CheckpointRejectionRequest,
    CheckpointListResponse,
)

logger = logging.getLogger(__name__)


class CheckpointService:
    """
    Service for checkpoint management and approval workflow.

    Features:
    - Create checkpoints during workflow execution
    - Send Teams notifications for approval requests
    - Handle approve/reject actions
    - Resume/terminate execution based on approval
    - Track approval audit trail

    Example:
        service = CheckpointService(db=session)

        # Create checkpoint
        checkpoint = await service.create_checkpoint(
            CheckpointCreate(
                execution_id=exec_id,
                step_index=3,
                step_name="Manager Approval",
                proposed_action="Create new employee account"
            )
        )

        # Approve checkpoint
        await service.approve_checkpoint(
            checkpoint_id=checkpoint.id,
            user_id=user.id,
            feedback="Approved"
        )
    """

    def __init__(self, db: AsyncSession):
        """Initialize CheckpointService."""
        self.db = db
        self.audit_service = AuditService(db)
        self.notification_service = get_notification_service(db)
        self.api_url = os.getenv("API_URL", "http://localhost:8080")

    async def create_checkpoint(
        self,
        data: CheckpointCreate,
        workflow_name: Optional[str] = None,
        send_notification: bool = True,
    ) -> Checkpoint:
        """
        Create a new checkpoint for approval.

        Args:
            data: Checkpoint creation data
            workflow_name: Name of the workflow (for notification)
            send_notification: Whether to send Teams notification

        Returns:
            Created Checkpoint instance
        """
        # Calculate expiration
        expires_at = None
        if data.expires_in_minutes:
            expires_at = datetime.utcnow() + timedelta(minutes=data.expires_in_minutes)

        # Create checkpoint
        checkpoint = Checkpoint(
            execution_id=data.execution_id,
            step_index=data.step_index,
            step_name=data.step_name,
            proposed_action=data.proposed_action,
            context=data.context,
            status=CheckpointStatus.PENDING,
            expires_at=expires_at,
        )

        self.db.add(checkpoint)
        await self.db.commit()
        await self.db.refresh(checkpoint)

        logger.info(f"Checkpoint created: {checkpoint.id} for execution {data.execution_id}")

        # Send Teams notification
        if send_notification:
            await self._send_approval_notification(checkpoint, workflow_name or "Workflow")

        # Log to audit
        await self.audit_service.log(
            action=AuditAction.CREATE,
            resource_type="checkpoint",
            resource_id=str(checkpoint.id),
            resource_name=f"checkpoint-{data.step_index}",
            changes={
                "execution_id": str(data.execution_id),
                "step_index": data.step_index,
                "step_name": data.step_name,
                "status": CheckpointStatus.PENDING.value,
            },
        )

        return checkpoint

    async def get_checkpoint(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        """Get a checkpoint by ID."""
        result = await self.db.execute(
            select(Checkpoint).where(Checkpoint.id == checkpoint_id)
        )
        return result.scalar_one_or_none()

    async def get_checkpoint_by_execution(
        self,
        execution_id: UUID,
        step_index: Optional[int] = None,
    ) -> list[Checkpoint]:
        """Get checkpoints for an execution."""
        query = select(Checkpoint).where(Checkpoint.execution_id == execution_id)

        if step_index is not None:
            query = query.where(Checkpoint.step_index == step_index)

        query = query.order_by(Checkpoint.step_index)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pending_checkpoints(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> CheckpointListResponse:
        """Get all pending checkpoints."""
        offset = (page - 1) * page_size

        # Count total
        count_query = select(func.count(Checkpoint.id)).where(
            Checkpoint.status == CheckpointStatus.PENDING
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get checkpoints
        query = (
            select(Checkpoint)
            .where(Checkpoint.status == CheckpointStatus.PENDING)
            .order_by(Checkpoint.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        checkpoints = list(result.scalars().all())

        return CheckpointListResponse(
            total=total,
            checkpoints=[CheckpointResponse.model_validate(cp) for cp in checkpoints],
            page=page,
            page_size=page_size,
        )

    async def approve_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        data: Optional[CheckpointApprovalRequest] = None,
    ) -> Checkpoint:
        """
        Approve a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID
            user_id: User ID approving
            data: Optional approval data with feedback

        Returns:
            Updated Checkpoint

        Raises:
            ValueError: If checkpoint not found or cannot be approved
        """
        checkpoint = await self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        if not checkpoint.can_be_approved():
            if checkpoint.is_expired():
                raise ValueError("Checkpoint has expired")
            raise ValueError(f"Checkpoint is already {checkpoint.status.value}")

        # Update checkpoint
        feedback = data.feedback if data else None
        checkpoint.approve(str(user_id), feedback)
        await self.db.commit()
        await self.db.refresh(checkpoint)

        logger.info(f"Checkpoint {checkpoint_id} approved by {user_id}")

        # Send approval notification
        await self._send_result_notification(
            checkpoint,
            approved=True,
            user_id=str(user_id),
        )

        # Log to audit
        await self.audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="checkpoint",
            resource_id=str(checkpoint_id),
            resource_name=f"checkpoint-{checkpoint.step_index}",
            user_id=user_id,
            changes={
                "status": CheckpointStatus.APPROVED.value,
                "approved_by": str(user_id),
                "feedback": feedback,
            },
        )

        return checkpoint

    async def reject_checkpoint(
        self,
        checkpoint_id: UUID,
        user_id: UUID,
        data: CheckpointRejectionRequest,
    ) -> Checkpoint:
        """
        Reject a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID
            user_id: User ID rejecting
            data: Rejection data with reason

        Returns:
            Updated Checkpoint

        Raises:
            ValueError: If checkpoint not found or cannot be rejected
        """
        checkpoint = await self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        if not checkpoint.can_be_approved():
            if checkpoint.is_expired():
                raise ValueError("Checkpoint has expired")
            raise ValueError(f"Checkpoint is already {checkpoint.status.value}")

        # Update checkpoint
        checkpoint.reject(str(user_id), data.reason)
        await self.db.commit()
        await self.db.refresh(checkpoint)

        logger.info(f"Checkpoint {checkpoint_id} rejected by {user_id}: {data.reason}")

        # Send rejection notification
        await self._send_result_notification(
            checkpoint,
            approved=False,
            user_id=str(user_id),
            reason=data.reason,
        )

        # Log to audit
        await self.audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="checkpoint",
            resource_id=str(checkpoint_id),
            resource_name=f"checkpoint-{checkpoint.step_index}",
            user_id=user_id,
            changes={
                "status": CheckpointStatus.REJECTED.value,
                "approved_by": str(user_id),
                "reason": data.reason,
            },
        )

        return checkpoint

    async def expire_checkpoint(self, checkpoint_id: UUID) -> Checkpoint:
        """Mark a checkpoint as expired."""
        checkpoint = await self.get_checkpoint(checkpoint_id)

        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")

        checkpoint.expire()
        await self.db.commit()
        await self.db.refresh(checkpoint)

        logger.info(f"Checkpoint {checkpoint_id} expired")

        # Log to audit
        await self.audit_service.log(
            action=AuditAction.UPDATE,
            resource_type="checkpoint",
            resource_id=str(checkpoint_id),
            resource_name=f"checkpoint-{checkpoint.step_index}",
            changes={
                "status": CheckpointStatus.EXPIRED.value,
                "expired_at": datetime.utcnow().isoformat(),
            },
        )

        return checkpoint

    async def check_expired_checkpoints(self) -> int:
        """
        Check and expire overdue checkpoints.

        Returns:
            Number of checkpoints expired
        """
        now = datetime.utcnow()

        query = select(Checkpoint).where(
            Checkpoint.status == CheckpointStatus.PENDING,
            Checkpoint.expires_at.isnot(None),
            Checkpoint.expires_at < now,
        )

        result = await self.db.execute(query)
        checkpoints = list(result.scalars().all())

        expired_count = 0
        for checkpoint in checkpoints:
            checkpoint.expire()
            expired_count += 1

        if expired_count > 0:
            await self.db.commit()
            logger.info(f"Expired {expired_count} checkpoints")

        return expired_count

    async def _send_approval_notification(
        self,
        checkpoint: Checkpoint,
        workflow_name: str,
    ) -> None:
        """Send Teams notification for approval request."""
        try:
            context = CheckpointNotificationContext(
                checkpoint_id=str(checkpoint.id),
                execution_id=str(checkpoint.execution_id),
                workflow_name=workflow_name,
                step_number=checkpoint.step_index,
                step_name=checkpoint.step_name,
                proposed_action=checkpoint.proposed_action,
                approve_url=f"{self.api_url}/api/v1/checkpoints/{checkpoint.id}/approve",
                reject_url=f"{self.api_url}/api/v1/checkpoints/{checkpoint.id}/reject",
            )

            response = await self.notification_service.send_checkpoint_approval(context)

            # Update checkpoint with notification info
            checkpoint.notification_sent = True
            checkpoint.notification_id = response.notification_id
            await self.db.commit()

        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")

    async def _send_result_notification(
        self,
        checkpoint: Checkpoint,
        approved: bool,
        user_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """Send Teams notification for approval result."""
        try:
            if approved:
                title = "✅ Checkpoint Approved"
                message = f"Checkpoint at step {checkpoint.step_index} has been approved"
                severity = "info"
            else:
                title = "❌ Checkpoint Rejected"
                message = f"Checkpoint at step {checkpoint.step_index} has been rejected"
                if reason:
                    message += f": {reason}"
                severity = "warning"

            await self.notification_service.send_system_alert(
                title=title,
                message=message,
                severity=severity,
                details={
                    "Checkpoint ID": str(checkpoint.id),
                    "Execution ID": str(checkpoint.execution_id),
                    "Step": str(checkpoint.step_index),
                    "Decision By": user_id,
                },
            )

        except Exception as e:
            logger.error(f"Failed to send result notification: {e}")


def get_checkpoint_service(db: AsyncSession) -> CheckpointService:
    """Factory function to create CheckpointService."""
    return CheckpointService(db=db)

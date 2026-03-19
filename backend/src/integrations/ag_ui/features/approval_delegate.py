"""
AG-UI Approval Delegate -- Sprint 111

Bridges AG-UI approval events to the UnifiedApprovalManager.

Replaces the standalone InMemory approval storage in AG-UI with delegation
to the unified approval system. Provides the same interface expected by
AG-UI event handlers while storing state in the centralized system.

Usage:
    from src.integrations.orchestration.hitl.unified_manager import (
        UnifiedApprovalManager,
    )
    from src.integrations.ag_ui.features.approval_delegate import (
        AGUIApprovalDelegate,
    )

    manager = UnifiedApprovalManager(approval_store=store)
    delegate = AGUIApprovalDelegate(unified_manager=manager)

    # AG-UI creates approval
    request_id = await delegate.create_approval_request(
        tool_name="deploy_service",
        tool_args={"service": "api-gateway", "env": "production"},
        session_id="sess_abc",
    )

    # AG-UI handles response
    result = await delegate.handle_approval_response(
        request_id=request_id,
        approved=True,
        approver_id="admin_1",
    )
"""

import logging
from typing import Any, Dict, List, Optional

from src.integrations.orchestration.hitl.unified_manager import (
    ApprovalPriority,
    ApprovalRequest,
    ApprovalSource,
    UnifiedApprovalManager,
)

logger = logging.getLogger(__name__)


class AGUIApprovalDelegate:
    """
    Delegates AG-UI approval operations to UnifiedApprovalManager.

    Provides the same interface as the original AG-UI approval handler
    but stores state in the unified system. This ensures all approvals
    from AG-UI SSE events are tracked alongside other approval sources.

    Args:
        unified_manager: The shared UnifiedApprovalManager instance.
    """

    def __init__(self, unified_manager: UnifiedApprovalManager):
        self._manager = unified_manager

    async def create_approval_request(
        self,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        priority: str = "normal",
        title: Optional[str] = None,
        description: Optional[str] = None,
        timeout_minutes: int = 30,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        AG-UI creates an approval request, delegated to unified manager.

        Args:
            tool_name: Name of the tool requiring approval.
            tool_args: Arguments for the tool call.
            session_id: Associated AG-UI session.
            user_id: User who triggered the tool call.
            priority: Priority level (critical/high/normal/low).
            title: Short summary (auto-generated from tool_name if not provided).
            description: Detailed description for the approver.
            timeout_minutes: Expiration timeout.
            metadata: Additional context from AG-UI.

        Returns:
            The approval request_id for tracking.
        """
        # Auto-generate title if not provided
        effective_title = title or f"AG-UI Tool Approval: {tool_name}"
        effective_description = description or (
            f"Tool '{tool_name}' requires approval before execution."
        )

        # Map priority string to enum
        try:
            approval_priority = ApprovalPriority(priority)
        except ValueError:
            approval_priority = ApprovalPriority.NORMAL

        # Build unified request
        request = ApprovalRequest(
            source=ApprovalSource.AG_UI,
            priority=approval_priority,
            title=effective_title,
            description=effective_description,
            requester_id=user_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_args=tool_args,
            timeout_minutes=timeout_minutes,
            metadata=metadata or {},
        )

        request_id = await self._manager.submit_approval(request)

        logger.info(
            f"AGUIApprovalDelegate: created approval {request_id} "
            f"for tool={tool_name} (session={session_id})"
        )
        return request_id

    async def handle_approval_response(
        self,
        request_id: str,
        approved: bool,
        approver_id: Optional[str] = None,
        comment: str = "",
    ) -> Dict[str, Any]:
        """
        AG-UI receives an approval response, delegated to unified manager.

        Args:
            request_id: The approval request to resolve.
            approved: True for approve, False for reject.
            approver_id: ID of the approving user.
            comment: Optional comment from the approver.

        Returns:
            Dict with the resolution details.

        Raises:
            ValueError: If the approval is not found or not pending.
        """
        result = await self._manager.resolve_approval(
            request_id=request_id,
            approved=approved,
            approver_id=approver_id or "ag_ui_user",
            comment=comment,
        )

        logger.info(
            f"AGUIApprovalDelegate: resolved {request_id} "
            f"-> {'approved' if approved else 'rejected'}"
        )
        return result

    async def get_pending_approvals(
        self,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get pending approvals for AG-UI display.

        Filters to AG-UI source and optionally by session.

        Args:
            session_id: Filter by specific session (optional).

        Returns:
            List of pending approval dicts.
        """
        pending = await self._manager.get_pending(
            source=ApprovalSource.AG_UI,
        )

        # Further filter by session_id if specified
        if session_id is not None:
            pending = [
                p
                for p in pending
                if p.get("metadata", {}).get("session_id") == session_id
            ]

        return pending

    async def get_approval_status(
        self, request_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get status of a specific approval for AG-UI.

        Args:
            request_id: The approval request ID.

        Returns:
            Dict with approval details, or None if not found.
        """
        return await self._manager.get_status(request_id)

    async def cancel_approval(
        self, request_id: str, reason: str = ""
    ) -> bool:
        """
        Cancel a pending AG-UI approval.

        Args:
            request_id: The approval to cancel.
            reason: Cancellation reason.

        Returns:
            True if cancelled, False if not found.
        """
        return await self._manager.cancel_approval(request_id, reason)

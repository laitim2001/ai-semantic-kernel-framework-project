"""
Claude SDK Approval Delegate -- Sprint 111

Bridges Claude SDK hook-based tool approval checks to the UnifiedApprovalManager.

When Claude SDK attempts to execute a tool, the approval hook can delegate
the approval decision to the unified system instead of using its own
standalone approval storage.

Usage:
    from src.integrations.orchestration.hitl.unified_manager import (
        UnifiedApprovalManager,
    )
    from src.integrations.claude_sdk.hooks.approval_delegate import (
        ClaudeApprovalDelegate,
    )

    manager = UnifiedApprovalManager(approval_store=store)
    delegate = ClaudeApprovalDelegate(unified_manager=manager)

    # Check if a tool needs approval and submit request
    needs_approval, request_id = await delegate.check_tool_approval(
        tool_name="execute_command",
        tool_args={"command": "rm -rf /tmp/cache"},
        user_id="user_123",
    )

    # Wait for the approval result
    if needs_approval:
        approved = await delegate.wait_for_approval(request_id, timeout=300)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from src.infrastructure.storage.approval_store import ApprovalStatus
from src.integrations.orchestration.hitl.unified_manager import (
    ApprovalPriority,
    ApprovalRequest,
    ApprovalSource,
    UnifiedApprovalManager,
)

logger = logging.getLogger(__name__)

# Tools that always require approval
DEFAULT_HIGH_RISK_TOOLS: Set[str] = {
    "execute_command",
    "execute_shell",
    "delete_resource",
    "modify_production",
    "deploy_service",
    "database_migrate",
    "firewall_modify",
}

# Tools that never need approval
DEFAULT_SAFE_TOOLS: Set[str] = {
    "get_status",
    "list_resources",
    "read_file",
    "search",
    "get_logs",
    "describe_resource",
}


class ClaudeApprovalDelegate:
    """
    Delegates Claude SDK tool approval checks to UnifiedApprovalManager.

    Intercepts tool calls from Claude SDK hooks and determines whether
    approval is needed based on the tool name and risk level. If approval
    is required, submits a request to the unified system and provides
    a polling mechanism to wait for the result.

    Args:
        unified_manager: The shared UnifiedApprovalManager instance.
        high_risk_tools: Set of tool names that always require approval.
                        Defaults to DEFAULT_HIGH_RISK_TOOLS.
        safe_tools: Set of tool names that never require approval.
                   Defaults to DEFAULT_SAFE_TOOLS.
        default_timeout_minutes: Default timeout for approval requests.
    """

    def __init__(
        self,
        unified_manager: UnifiedApprovalManager,
        high_risk_tools: Optional[Set[str]] = None,
        safe_tools: Optional[Set[str]] = None,
        default_timeout_minutes: int = 15,
    ):
        self._manager = unified_manager
        self._high_risk_tools = (
            high_risk_tools
            if high_risk_tools is not None
            else DEFAULT_HIGH_RISK_TOOLS
        )
        self._safe_tools = (
            safe_tools if safe_tools is not None else DEFAULT_SAFE_TOOLS
        )
        self._default_timeout = default_timeout_minutes

    def _assess_tool_risk(
        self, tool_name: str, tool_args: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, ApprovalPriority]:
        """
        Assess whether a tool call requires approval.

        Args:
            tool_name: Name of the tool being called.
            tool_args: Arguments for the tool call.

        Returns:
            Tuple of (needs_approval, priority).
        """
        # Safe tools never need approval
        if tool_name in self._safe_tools:
            return False, ApprovalPriority.LOW

        # High-risk tools always need approval
        if tool_name in self._high_risk_tools:
            return True, ApprovalPriority.HIGH

        # For unknown tools, default to requiring approval with normal priority
        return True, ApprovalPriority.NORMAL

    async def check_tool_approval(
        self,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        risk_level: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a tool call needs approval and submit if needed.

        Args:
            tool_name: Name of the tool being called.
            tool_args: Arguments for the tool call.
            user_id: User who initiated the Claude SDK session.
            session_id: Associated session ID.
            risk_level: Pre-assessed risk level from the SDK hook chain.

        Returns:
            Tuple of (needs_approval, request_id).
            If needs_approval is False, request_id is None.
        """
        needs_approval, priority = self._assess_tool_risk(tool_name, tool_args)

        if not needs_approval:
            logger.debug(
                f"ClaudeApprovalDelegate: tool {tool_name} is safe, "
                f"no approval needed"
            )
            return False, None

        # Override priority based on external risk assessment
        if risk_level == "critical":
            priority = ApprovalPriority.CRITICAL
        elif risk_level == "high":
            priority = ApprovalPriority.HIGH

        # Build and submit approval request
        request = ApprovalRequest(
            source=ApprovalSource.CLAUDE_SDK,
            priority=priority,
            title=f"Claude SDK Tool Approval: {tool_name}",
            description=(
                f"Claude SDK is requesting to execute tool '{tool_name}' "
                f"with args: {tool_args}"
            ),
            requester_id=user_id,
            session_id=session_id,
            risk_level=risk_level,
            tool_name=tool_name,
            tool_args=tool_args,
            timeout_minutes=self._default_timeout,
        )

        request_id = await self._manager.submit_approval(request)

        logger.info(
            f"ClaudeApprovalDelegate: submitted approval {request_id} "
            f"for tool={tool_name} (priority={priority.value})"
        )
        return True, request_id

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> bool:
        """
        Wait for an approval result by polling with exponential backoff.

        Args:
            request_id: The approval request to wait for.
            timeout: Maximum wait time in seconds.
            poll_interval: Initial polling interval in seconds.

        Returns:
            True if approved, False if rejected/expired/cancelled.

        Raises:
            TimeoutError: If the approval is not resolved within timeout.
        """
        elapsed = 0.0
        current_interval = poll_interval

        while elapsed < timeout:
            status_data = await self._manager.get_status(request_id)

            if status_data is None:
                raise ValueError(
                    f"Approval {request_id} not found"
                )

            status = status_data.get("status", "")
            if status == ApprovalStatus.APPROVED.value:
                logger.info(
                    f"ClaudeApprovalDelegate: {request_id} approved "
                    f"after {elapsed:.1f}s"
                )
                return True
            elif status in (
                ApprovalStatus.REJECTED.value,
                ApprovalStatus.EXPIRED.value,
                ApprovalStatus.CANCELLED.value,
            ):
                logger.info(
                    f"ClaudeApprovalDelegate: {request_id} {status} "
                    f"after {elapsed:.1f}s"
                )
                return False

            # Still pending -- wait and retry
            await asyncio.sleep(current_interval)
            elapsed += current_interval
            # Exponential backoff up to 10 seconds
            current_interval = min(current_interval * 1.5, 10.0)

        # Timeout reached
        logger.warning(
            f"ClaudeApprovalDelegate: {request_id} timed out "
            f"after {timeout}s"
        )
        raise TimeoutError(
            f"Approval {request_id} not resolved within {timeout}s"
        )

    async def get_pending_for_session(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get pending Claude SDK approvals for a session.

        Args:
            session_id: The Claude SDK session to query.

        Returns:
            List of pending approval dicts.
        """
        pending = await self._manager.get_pending(
            source=ApprovalSource.CLAUDE_SDK,
        )
        return [
            p
            for p in pending
            if p.get("metadata", {}).get("session_id") == session_id
        ]

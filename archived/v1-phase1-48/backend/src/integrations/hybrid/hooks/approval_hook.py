# =============================================================================
# IPA Platform - Risk-Driven Approval Hook
# =============================================================================
# Sprint 55: S55-4 - API & ApprovalHook Integration
#
# Approval hook that uses RiskAssessmentEngine to drive approval decisions.
# Integrates with Claude SDK hook system while leveraging multi-dimensional
# risk analysis for intelligent HITL (Human-in-the-Loop) decisions.
#
# Dependencies:
#   - RiskAssessmentEngine (src.integrations.hybrid.risk.engine)
#   - OperationAnalyzer (src.integrations.hybrid.risk.analyzers)
#   - ContextEvaluator (src.integrations.hybrid.risk.analyzers)
#   - PatternDetector (src.integrations.hybrid.risk.analyzers)
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from ..risk.engine import RiskAssessmentEngine, create_engine
from ..risk.models import OperationContext, RiskAssessment, RiskConfig, RiskLevel
from ..risk.analyzers.operation_analyzer import OperationAnalyzer
from ..risk.analyzers.context_evaluator import ContextEvaluator
from ..risk.analyzers.pattern_detector import PatternDetector

logger = logging.getLogger(__name__)


class ApprovalMode(Enum):
    """
    Approval mode determines how decisions are made.

    AUTO: Automatically approve based on risk level
    MANUAL: Always require human approval
    RISK_DRIVEN: Use risk assessment to determine approval requirement
    """
    AUTO = "auto"
    MANUAL = "manual"
    RISK_DRIVEN = "risk_driven"


@dataclass
class ApprovalDecision:
    """
    Result of an approval decision.

    Attributes:
        approved: Whether the operation is approved
        reason: Human-readable reason for the decision
        risk_assessment: The underlying risk assessment (if available)
        required_human_approval: Whether human approval was required
        approval_time: When the decision was made
        approver: Who approved (system or user ID)
        metadata: Additional decision context
    """
    approved: bool
    reason: str
    risk_assessment: Optional[RiskAssessment] = None
    required_human_approval: bool = False
    approval_time: datetime = field(default_factory=datetime.utcnow)
    approver: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)


class RiskDrivenApprovalHook:
    """
    Approval hook driven by multi-dimensional risk assessment.

    Uses RiskAssessmentEngine to analyze operations and determine
    whether human approval is required based on:
    - Tool/operation risk (OperationAnalyzer)
    - User trust level and environment (ContextEvaluator)
    - Behavioral patterns (PatternDetector)

    Args:
        config: Risk configuration (thresholds, weights)
        mode: Approval mode (AUTO, MANUAL, RISK_DRIVEN)
        approval_callback: Async callback for human approval requests
        timeout: Timeout for human approval in seconds
        auto_approve_tools: Tools that bypass risk assessment

    Example:
        >>> async def request_approval(assessment):
        ...     return await ask_user(f"Allow? Risk: {assessment.overall_level}")
        ...
        >>> hook = RiskDrivenApprovalHook(
        ...     mode=ApprovalMode.RISK_DRIVEN,
        ...     approval_callback=request_approval,
        ... )
        >>> decision = await hook.check_approval(context)
        >>> if decision.approved:
        ...     execute_operation()
    """

    name: str = "risk_driven_approval"
    priority: int = 85  # High priority - run early

    def __init__(
        self,
        config: Optional[RiskConfig] = None,
        mode: ApprovalMode = ApprovalMode.RISK_DRIVEN,
        approval_callback: Optional[
            Callable[[RiskAssessment], Awaitable[bool]]
        ] = None,
        timeout: float = 300.0,
        auto_approve_tools: Optional[Set[str]] = None,
    ):
        """Initialize the risk-driven approval hook."""
        self.config = config or RiskConfig()
        self.mode = mode
        self.approval_callback = approval_callback
        self.timeout = timeout
        self.auto_approve_tools = auto_approve_tools or {"Read", "Glob", "Grep"}

        # Create engine with analyzers
        self._engine = create_engine(config=self.config)
        self._operation_analyzer = OperationAnalyzer()
        self._context_evaluator = ContextEvaluator()
        self._pattern_detector = PatternDetector()

        # Register analyzers
        self._engine.register_analyzer(self._operation_analyzer)
        self._engine.register_analyzer(self._context_evaluator)
        self._engine.register_analyzer(self._pattern_detector)

        # Track decisions for session
        self._approved_operations: Set[str] = set()
        self._pending_approvals: Dict[str, RiskAssessment] = {}
        self._decision_history: List[ApprovalDecision] = []

        logger.info(
            f"RiskDrivenApprovalHook initialized with mode={mode.value}"
        )

    async def check_approval(
        self,
        context: OperationContext,
    ) -> ApprovalDecision:
        """
        Check if operation is approved based on risk assessment.

        Main entry point for approval decisions. Analyzes the operation,
        determines risk level, and returns approval decision.

        Args:
            context: Operation context to evaluate

        Returns:
            ApprovalDecision: Whether approved and why
        """
        # Auto-approve read operations
        if context.tool_name in self.auto_approve_tools:
            return ApprovalDecision(
                approved=True,
                reason=f"Auto-approved: {context.tool_name} is read-only",
                approver="system:auto_approve",
            )

        # Handle based on mode
        if self.mode == ApprovalMode.AUTO:
            return self._auto_approve(context)

        if self.mode == ApprovalMode.MANUAL:
            return await self._manual_approve(context)

        # RISK_DRIVEN mode
        return await self._risk_driven_approve(context)

    def _auto_approve(self, context: OperationContext) -> ApprovalDecision:
        """Auto-approve all operations."""
        return ApprovalDecision(
            approved=True,
            reason="Auto-approval mode enabled",
            approver="system:auto_mode",
        )

    async def _manual_approve(
        self,
        context: OperationContext,
    ) -> ApprovalDecision:
        """Require manual approval for all operations."""
        # Perform risk assessment for information
        assessment = self._engine.assess(context)

        if self.approval_callback is None:
            return ApprovalDecision(
                approved=False,
                reason="Manual approval required but no callback configured",
                risk_assessment=assessment,
                required_human_approval=True,
            )

        try:
            approved = await asyncio.wait_for(
                self.approval_callback(assessment),
                timeout=self.timeout,
            )

            return ApprovalDecision(
                approved=approved,
                reason="User approved" if approved else "User rejected",
                risk_assessment=assessment,
                required_human_approval=True,
                approver="user" if approved else "user:rejected",
            )

        except asyncio.TimeoutError:
            return ApprovalDecision(
                approved=False,
                reason=f"Approval timeout after {self.timeout}s",
                risk_assessment=assessment,
                required_human_approval=True,
            )

    async def _risk_driven_approve(
        self,
        context: OperationContext,
    ) -> ApprovalDecision:
        """
        Use risk assessment to determine approval.

        LOW/MEDIUM risk: Auto-approve based on config
        HIGH/CRITICAL risk: Require human approval
        """
        # Check if already approved in this session
        operation_key = self._get_operation_key(context)
        if operation_key in self._approved_operations:
            return ApprovalDecision(
                approved=True,
                reason="Previously approved in session",
                approver="system:cached",
            )

        # Perform risk assessment
        assessment = self._engine.assess(context)

        # Check if auto-approve is possible
        if self._can_auto_approve(assessment):
            decision = ApprovalDecision(
                approved=True,
                reason=f"Auto-approved: {assessment.overall_level.value} risk "
                       f"(score={assessment.overall_score:.3f})",
                risk_assessment=assessment,
                approver="system:risk_engine",
            )
            self._approved_operations.add(operation_key)
            self._decision_history.append(decision)
            return decision

        # Requires human approval
        if self.approval_callback is None:
            return ApprovalDecision(
                approved=False,
                reason=f"Human approval required: {assessment.approval_reason}",
                risk_assessment=assessment,
                required_human_approval=True,
            )

        # Store pending approval
        self._pending_approvals[operation_key] = assessment

        try:
            approved = await asyncio.wait_for(
                self.approval_callback(assessment),
                timeout=self.timeout,
            )

            decision = ApprovalDecision(
                approved=approved,
                reason=f"User {'approved' if approved else 'rejected'}: "
                       f"{assessment.overall_level.value} risk",
                risk_assessment=assessment,
                required_human_approval=True,
                approver="user" if approved else "user:rejected",
            )

            if approved:
                self._approved_operations.add(operation_key)

            # Remove from pending
            self._pending_approvals.pop(operation_key, None)
            self._decision_history.append(decision)

            return decision

        except asyncio.TimeoutError:
            self._pending_approvals.pop(operation_key, None)
            return ApprovalDecision(
                approved=False,
                reason=f"Approval timeout after {self.timeout}s for "
                       f"{assessment.overall_level.value} risk operation",
                risk_assessment=assessment,
                required_human_approval=True,
            )

    def _can_auto_approve(self, assessment: RiskAssessment) -> bool:
        """
        Check if assessment can be auto-approved based on config.

        Args:
            assessment: Risk assessment result

        Returns:
            bool: True if can auto-approve
        """
        return self.config.should_auto_approve(
            assessment.overall_level,
            assessment.overall_score,
        )

    def _get_operation_key(self, context: OperationContext) -> str:
        """Generate unique key for operation deduplication."""
        if context.command:
            cmd_prefix = context.command[:50]
            return f"{context.tool_name}:{cmd_prefix}"

        if context.target_paths:
            paths = ",".join(context.target_paths[:3])
            return f"{context.tool_name}:{paths}"

        return f"{context.tool_name}:{context.session_id}"

    # Session Lifecycle Methods

    async def on_session_start(self, session_id: str) -> None:
        """Clear state when session starts."""
        self._approved_operations.clear()
        self._pending_approvals.clear()
        logger.debug(f"Session started: {session_id}")

    async def on_session_end(self, session_id: str) -> None:
        """Clean up when session ends."""
        self._approved_operations.clear()
        self._pending_approvals.clear()
        self._engine.clear_session_history(session_id)
        self._pattern_detector.clear_session(session_id)
        logger.debug(f"Session ended: {session_id}")

    # Configuration and State Methods

    def set_mode(self, mode: ApprovalMode) -> None:
        """Change approval mode."""
        old_mode = self.mode
        self.mode = mode
        logger.info(f"Approval mode changed: {old_mode.value} -> {mode.value}")

    def add_auto_approve_tool(self, tool_name: str) -> None:
        """Add tool to auto-approve list."""
        self.auto_approve_tools.add(tool_name)

    def remove_auto_approve_tool(self, tool_name: str) -> None:
        """Remove tool from auto-approve list."""
        self.auto_approve_tools.discard(tool_name)

    def clear_approved_operations(self) -> None:
        """Clear cached approvals (require re-approval)."""
        self._approved_operations.clear()

    def get_pending_approvals(self) -> Dict[str, RiskAssessment]:
        """Get currently pending approval requests."""
        return dict(self._pending_approvals)

    def get_decision_history(self) -> List[ApprovalDecision]:
        """Get history of approval decisions."""
        return list(self._decision_history)

    def get_engine_metrics(self) -> Dict[str, Any]:
        """Get risk engine metrics."""
        metrics = self._engine.get_metrics()
        return {
            "total_assessments": metrics.total_assessments,
            "assessments_by_level": metrics.assessments_by_level,
            "average_score": metrics.average_score,
            "approval_rate": metrics.approval_rate,
            "average_latency_ms": metrics.average_latency_ms,
        }

    # Tool Context Conversion (for Claude SDK integration)

    def from_tool_call_context(
        self,
        tool_name: str,
        args: Dict[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        environment: str = "development",
    ) -> OperationContext:
        """
        Convert Claude SDK tool call to OperationContext.

        Helper method for integrating with Claude SDK hook system.

        Args:
            tool_name: Name of the tool being called
            args: Tool arguments
            session_id: Session identifier
            user_id: User identifier
            environment: Execution environment

        Returns:
            OperationContext for risk assessment
        """
        # Extract paths from common argument patterns
        paths = []
        if "file_path" in args:
            paths.append(args["file_path"])
        if "path" in args:
            paths.append(args["path"])
        if "paths" in args and isinstance(args["paths"], list):
            paths.extend(args["paths"])

        return OperationContext(
            tool_name=tool_name,
            operation_type=self._infer_operation_type(tool_name),
            target_paths=paths,
            command=args.get("command"),
            arguments=args,
            session_id=session_id,
            user_id=user_id,
            environment=environment,
        )

    def _infer_operation_type(self, tool_name: str) -> str:
        """Infer operation type from tool name."""
        read_tools = {"Read", "Glob", "Grep", "LSP"}
        write_tools = {"Write", "Edit", "MultiEdit"}
        execute_tools = {"Bash", "Task"}

        if tool_name in read_tools:
            return "read"
        if tool_name in write_tools:
            return "write"
        if tool_name in execute_tools:
            return "execute"
        return "unknown"

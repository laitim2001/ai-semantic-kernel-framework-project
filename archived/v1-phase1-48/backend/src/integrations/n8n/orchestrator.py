"""n8n Bidirectional Orchestrator (Mode 3).

Coordinates the bidirectional collaboration between IPA and n8n:
    1. Receives user request
    2. IPA performs reasoning and decision-making
    3. Translates reasoning result into n8n workflow parameters
    4. Triggers n8n workflow execution
    5. Monitors execution via polling + callback
    6. Returns consolidated result to user

Environment Variables:
    N8N_BASE_URL: n8n instance base URL
    N8N_API_KEY: n8n API key
    N8N_ORCHESTRATOR_TIMEOUT: Overall orchestration timeout (default: 300s)
    N8N_ORCHESTRATOR_MAX_RETRIES: Max retries on transient failures (default: 2)
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.integrations.mcp.servers.n8n.client import (
    N8nApiClient,
    N8nApiError,
    N8nConfig,
    N8nConnectionError,
    N8nNotFoundError,
    ExecutionStatus,
)

from .monitor import ExecutionMonitor, ExecutionProgress, ExecutionState, MonitorConfig

logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Status of an orchestration request."""

    PENDING = "pending"
    REASONING = "reasoning"
    TRANSLATING = "translating"
    EXECUTING = "executing"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class OrchestrationRequest:
    """Request for n8n bidirectional orchestration.

    Attributes:
        request_id: Unique request identifier (auto-generated if not provided)
        user_input: Original user input text
        context: Additional context for IPA reasoning
        workflow_id: Specific n8n workflow to execute (optional, can be auto-selected)
        workflow_params: Additional parameters for the n8n workflow
        timeout: Overall timeout in seconds (default: 300)
        callback_url: Optional callback URL for async notifications
        metadata: Arbitrary metadata attached to the request
    """

    user_input: str
    context: Dict[str, Any] = field(default_factory=dict)
    workflow_id: Optional[str] = None
    workflow_params: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300
    callback_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ReasoningResult:
    """Result from IPA reasoning phase.

    Attributes:
        intent: Detected intent category
        sub_intent: Specific sub-intent
        confidence: Confidence score (0.0-1.0)
        recommended_workflow: Suggested n8n workflow ID
        workflow_input: Translated input for n8n workflow
        risk_level: Assessed risk level
        requires_approval: Whether HITL approval is needed
        reasoning_metadata: Additional reasoning metadata
    """

    intent: str
    sub_intent: str = ""
    confidence: float = 0.0
    recommended_workflow: Optional[str] = None
    workflow_input: Dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    requires_approval: bool = False
    reasoning_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """Result of an orchestration request.

    Attributes:
        request_id: Original request identifier
        status: Final orchestration status
        reasoning: IPA reasoning result
        execution_id: n8n execution ID (if executed)
        execution_result: n8n execution output data
        error: Error message if failed
        started_at: When orchestration started
        completed_at: When orchestration completed
        duration_ms: Total duration in milliseconds
        progress_history: List of progress updates during execution
    """

    request_id: str
    status: OrchestrationStatus
    reasoning: Optional[ReasoningResult] = None
    execution_id: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    progress_history: List[Dict[str, Any]] = field(default_factory=list)


# Type alias for reasoning function
ReasoningFn = Callable[[str, Dict[str, Any]], "asyncio.Future[ReasoningResult]"]


class N8nOrchestrator:
    """Bidirectional orchestrator for IPA + n8n collaboration.

    Manages the full lifecycle of a bidirectional orchestration:
    IPA reasoning → n8n execution → result monitoring → consolidation.

    The orchestrator is designed to be extensible. The reasoning function
    can be injected to support different reasoning backends (e.g., Claude,
    orchestration router, custom logic).

    Example:
        >>> config = N8nConfig.from_env()
        >>> orchestrator = N8nOrchestrator(config)
        >>>
        >>> # Register a custom reasoning function
        >>> orchestrator.set_reasoning_fn(my_reasoning_function)
        >>>
        >>> # Execute orchestration
        >>> request = OrchestrationRequest(user_input="Reset password for user john")
        >>> result = await orchestrator.orchestrate(request)
        >>> print(result.status)  # OrchestrationStatus.COMPLETED
        >>> print(result.execution_result)

    Context Manager:
        >>> async with N8nOrchestrator(config) as orchestrator:
        ...     result = await orchestrator.orchestrate(request)
    """

    def __init__(
        self,
        config: N8nConfig,
        monitor_config: Optional[MonitorConfig] = None,
        reasoning_fn: Optional[ReasoningFn] = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: n8n connection configuration
            monitor_config: Execution monitor configuration (optional)
            reasoning_fn: Custom reasoning function (optional)
        """
        self._config = config
        self._client = N8nApiClient(config)
        self._monitor = ExecutionMonitor(
            client=self._client,
            config=monitor_config or MonitorConfig(),
        )
        self._reasoning_fn = reasoning_fn or self._default_reasoning
        self._active_orchestrations: Dict[str, OrchestrationStatus] = {}
        self._progress_callbacks: Dict[str, List[Callable]] = {}
        self._callback_results: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"N8nOrchestrator initialized: n8n={config.base_url}"
        )

    def set_reasoning_fn(self, fn: ReasoningFn) -> None:
        """Set the reasoning function for intent analysis.

        Args:
            fn: Async function that takes (user_input, context) and returns ReasoningResult
        """
        self._reasoning_fn = fn
        logger.info("Custom reasoning function registered")

    def register_progress_callback(
        self, request_id: str, callback: Callable[[ExecutionProgress], Any]
    ) -> None:
        """Register a progress callback for an orchestration.

        Args:
            request_id: The orchestration request ID
            callback: Function called with ExecutionProgress updates
        """
        if request_id not in self._progress_callbacks:
            self._progress_callbacks[request_id] = []
        self._progress_callbacks[request_id].append(callback)

    async def orchestrate(self, request: OrchestrationRequest) -> OrchestrationResult:
        """Execute the full bidirectional orchestration flow.

        Args:
            request: Orchestration request with user input and context

        Returns:
            OrchestrationResult with status, reasoning, and execution results
        """
        started_at = datetime.utcnow()
        self._active_orchestrations[request.request_id] = OrchestrationStatus.PENDING
        progress_history: List[Dict[str, Any]] = []

        logger.info(
            f"Starting orchestration {request.request_id}: "
            f"input='{request.user_input[:100]}...'"
        )

        try:
            # Phase 1: IPA Reasoning
            self._active_orchestrations[request.request_id] = OrchestrationStatus.REASONING
            progress_history.append({
                "phase": "reasoning",
                "status": "started",
                "timestamp": datetime.utcnow().isoformat(),
            })

            reasoning = await asyncio.wait_for(
                self._reasoning_fn(request.user_input, request.context),
                timeout=min(request.timeout, 60),  # Reasoning capped at 60s
            )

            progress_history.append({
                "phase": "reasoning",
                "status": "completed",
                "intent": reasoning.intent,
                "confidence": reasoning.confidence,
                "timestamp": datetime.utcnow().isoformat(),
            })

            logger.info(
                f"Orchestration {request.request_id} reasoning complete: "
                f"intent={reasoning.intent}, confidence={reasoning.confidence:.2f}"
            )

            # Phase 2: HITL Check
            if reasoning.requires_approval:
                logger.info(
                    f"Orchestration {request.request_id} requires HITL approval "
                    f"(risk_level={reasoning.risk_level})"
                )
                progress_history.append({
                    "phase": "approval",
                    "status": "required",
                    "risk_level": reasoning.risk_level,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                # In production, this would wait for HITL approval
                # For now, auto-approve low/medium risk
                if reasoning.risk_level in ("critical", "high"):
                    return OrchestrationResult(
                        request_id=request.request_id,
                        status=OrchestrationStatus.PENDING,
                        reasoning=reasoning,
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        duration_ms=self._calc_duration(started_at),
                        progress_history=progress_history,
                        error="HITL approval required for high/critical risk operations",
                    )

            # Phase 3: Translate reasoning to n8n workflow params
            self._active_orchestrations[request.request_id] = OrchestrationStatus.TRANSLATING
            workflow_id = request.workflow_id or reasoning.recommended_workflow
            if not workflow_id:
                return OrchestrationResult(
                    request_id=request.request_id,
                    status=OrchestrationStatus.FAILED,
                    reasoning=reasoning,
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    duration_ms=self._calc_duration(started_at),
                    progress_history=progress_history,
                    error="No workflow_id provided and reasoning did not recommend one",
                )

            workflow_input = self._build_workflow_input(request, reasoning)

            progress_history.append({
                "phase": "translation",
                "status": "completed",
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
            })

            # Phase 4: Execute n8n workflow
            self._active_orchestrations[request.request_id] = OrchestrationStatus.EXECUTING
            progress_history.append({
                "phase": "execution",
                "status": "started",
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat(),
            })

            execution_response = await self._client.execute_workflow(
                workflow_id=workflow_id,
                data=workflow_input,
            )

            execution_data = execution_response.get("data", execution_response)
            execution_id = execution_data.get("executionId", "unknown")
            execution_status = execution_data.get("status", "unknown")

            logger.info(
                f"Orchestration {request.request_id} workflow triggered: "
                f"execution_id={execution_id}, status={execution_status}"
            )

            # Phase 5: Monitor execution
            self._active_orchestrations[request.request_id] = OrchestrationStatus.MONITORING

            # If execution completed synchronously
            if execution_status in ("success", "error"):
                execution_result = execution_data.get("data", {})
            else:
                # Monitor async execution
                remaining_timeout = request.timeout - self._calc_duration(started_at) / 1000
                if remaining_timeout <= 0:
                    return OrchestrationResult(
                        request_id=request.request_id,
                        status=OrchestrationStatus.TIMEOUT,
                        reasoning=reasoning,
                        execution_id=execution_id,
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        duration_ms=self._calc_duration(started_at),
                        progress_history=progress_history,
                        error="Orchestration timeout before monitoring could start",
                    )

                # Set up progress callback forwarding
                progress_cb = self._create_progress_forwarder(
                    request.request_id, progress_history
                )

                final_state = await self._monitor.wait_for_completion(
                    execution_id=execution_id,
                    timeout=remaining_timeout,
                    progress_callback=progress_cb,
                )

                if final_state.status == ExecutionState.COMPLETED:
                    execution_result = final_state.output_data or {}
                    execution_status = "success"
                elif final_state.status == ExecutionState.TIMED_OUT:
                    return OrchestrationResult(
                        request_id=request.request_id,
                        status=OrchestrationStatus.TIMEOUT,
                        reasoning=reasoning,
                        execution_id=execution_id,
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        duration_ms=self._calc_duration(started_at),
                        progress_history=progress_history,
                        error=f"n8n execution timed out after {remaining_timeout:.0f}s",
                    )
                else:
                    return OrchestrationResult(
                        request_id=request.request_id,
                        status=OrchestrationStatus.FAILED,
                        reasoning=reasoning,
                        execution_id=execution_id,
                        started_at=started_at,
                        completed_at=datetime.utcnow(),
                        duration_ms=self._calc_duration(started_at),
                        progress_history=progress_history,
                        error=final_state.error or "n8n execution failed",
                    )

            # Phase 6: Consolidate result
            progress_history.append({
                "phase": "execution",
                "status": "completed",
                "execution_id": execution_id,
                "timestamp": datetime.utcnow().isoformat(),
            })

            self._active_orchestrations[request.request_id] = OrchestrationStatus.COMPLETED

            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.COMPLETED,
                reasoning=reasoning,
                execution_id=execution_id,
                execution_result=execution_result if isinstance(execution_result, dict) else {"data": execution_result},
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
            )

        except asyncio.TimeoutError:
            logger.error(f"Orchestration {request.request_id} timed out")
            self._active_orchestrations[request.request_id] = OrchestrationStatus.TIMEOUT
            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.TIMEOUT,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
                error=f"Orchestration timed out after {request.timeout}s",
            )

        except N8nNotFoundError as e:
            logger.error(f"Orchestration {request.request_id} workflow not found: {e}")
            self._active_orchestrations[request.request_id] = OrchestrationStatus.FAILED
            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
                error=f"n8n workflow not found: {e}",
            )

        except N8nConnectionError as e:
            logger.error(f"Orchestration {request.request_id} connection error: {e}")
            self._active_orchestrations[request.request_id] = OrchestrationStatus.FAILED
            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
                error=f"n8n connection error: {e}",
            )

        except N8nApiError as e:
            logger.error(f"Orchestration {request.request_id} API error: {e}")
            self._active_orchestrations[request.request_id] = OrchestrationStatus.FAILED
            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
                error=f"n8n API error: {e}",
            )

        except Exception as e:
            logger.error(
                f"Orchestration {request.request_id} unexpected error: {e}",
                exc_info=True,
            )
            self._active_orchestrations[request.request_id] = OrchestrationStatus.FAILED
            return OrchestrationResult(
                request_id=request.request_id,
                status=OrchestrationStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                duration_ms=self._calc_duration(started_at),
                progress_history=progress_history,
                error=f"Unexpected error: {e}",
            )

        finally:
            # Cleanup
            self._active_orchestrations.pop(request.request_id, None)
            self._progress_callbacks.pop(request.request_id, None)

    def handle_callback(
        self, request_id: str, callback_data: Dict[str, Any]
    ) -> bool:
        """Handle an n8n callback notification.

        Called when n8n sends a callback to the IPA webhook endpoint.
        Stores the callback data for the orchestration to consume.

        Args:
            request_id: The orchestration request ID
            callback_data: Data from n8n callback

        Returns:
            True if callback was accepted, False if request_id unknown
        """
        if request_id not in self._active_orchestrations:
            logger.warning(f"Callback for unknown orchestration: {request_id}")
            return False

        self._callback_results[request_id] = callback_data
        logger.info(
            f"Callback received for orchestration {request_id}: "
            f"status={callback_data.get('status', 'unknown')}"
        )
        return True

    def get_status(self, request_id: str) -> Optional[OrchestrationStatus]:
        """Get the current status of an orchestration.

        Args:
            request_id: The orchestration request ID

        Returns:
            Current status or None if not found
        """
        return self._active_orchestrations.get(request_id)

    def get_active_count(self) -> int:
        """Get the number of active orchestrations."""
        return len(self._active_orchestrations)

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _build_workflow_input(
        self, request: OrchestrationRequest, reasoning: ReasoningResult
    ) -> Dict[str, Any]:
        """Build the input data for n8n workflow execution.

        Combines the reasoning result with request context and params
        into a structured input for the n8n workflow.

        Args:
            request: Original orchestration request
            reasoning: IPA reasoning result

        Returns:
            Dict suitable for n8n workflow input
        """
        workflow_input = {
            "orchestration_id": request.request_id,
            "user_input": request.user_input,
            "intent": reasoning.intent,
            "sub_intent": reasoning.sub_intent,
            "confidence": reasoning.confidence,
            "risk_level": reasoning.risk_level,
            "reasoning_data": reasoning.workflow_input,
            "context": request.context,
            "metadata": {
                **request.metadata,
                "ipa_version": "1.0",
                "orchestration_mode": "bidirectional",
            },
        }

        # Merge explicit workflow params (they take precedence)
        if request.workflow_params:
            workflow_input.update(request.workflow_params)

        # Add callback URL if provided
        if request.callback_url:
            workflow_input["callback_url"] = request.callback_url

        return workflow_input

    def _create_progress_forwarder(
        self, request_id: str, progress_history: List[Dict[str, Any]]
    ) -> Callable[[ExecutionProgress], None]:
        """Create a progress callback that forwards to registered callbacks.

        Args:
            request_id: The orchestration request ID
            progress_history: Mutable list to append progress entries

        Returns:
            Callback function for the execution monitor
        """

        def forwarder(progress: ExecutionProgress) -> None:
            entry = {
                "phase": "monitoring",
                "execution_state": progress.state.value,
                "progress_pct": progress.progress_pct,
                "message": progress.message,
                "timestamp": progress.timestamp.isoformat(),
            }
            progress_history.append(entry)

            # Forward to registered callbacks
            for cb in self._progress_callbacks.get(request_id, []):
                try:
                    cb(progress)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

        return forwarder

    @staticmethod
    def _calc_duration(started_at: datetime) -> int:
        """Calculate duration in milliseconds from start time."""
        delta = datetime.utcnow() - started_at
        return int(delta.total_seconds() * 1000)

    @staticmethod
    async def _default_reasoning(
        user_input: str, context: Dict[str, Any]
    ) -> ReasoningResult:
        """Default reasoning function (placeholder).

        Provides a basic intent classification. In production, this should
        be replaced with the actual IPA orchestration router
        (BusinessIntentRouter from src.integrations.orchestration).

        Args:
            user_input: User input text
            context: Additional context

        Returns:
            Basic ReasoningResult
        """
        input_lower = user_input.lower()

        # Simple keyword-based classification
        if any(w in input_lower for w in ("reset", "password", "account", "access")):
            intent = "REQUEST"
            sub_intent = "account_management"
            risk_level = "medium"
        elif any(w in input_lower for w in ("down", "error", "fail", "crash", "outage")):
            intent = "INCIDENT"
            sub_intent = "system_failure"
            risk_level = "high"
        elif any(w in input_lower for w in ("update", "change", "modify", "config")):
            intent = "CHANGE"
            sub_intent = "configuration_change"
            risk_level = "medium"
        elif any(w in input_lower for w in ("status", "info", "what", "how", "check")):
            intent = "QUERY"
            sub_intent = "information_request"
            risk_level = "low"
        else:
            intent = "UNKNOWN"
            sub_intent = ""
            risk_level = "low"

        requires_approval = risk_level in ("high", "critical")

        return ReasoningResult(
            intent=intent,
            sub_intent=sub_intent,
            confidence=0.75,
            workflow_input={"original_input": user_input, "context": context},
            risk_level=risk_level,
            requires_approval=requires_approval,
            reasoning_metadata={"method": "keyword_default"},
        )

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the orchestrator and release resources."""
        await self._client.close()
        self._active_orchestrations.clear()
        self._progress_callbacks.clear()
        self._callback_results.clear()
        logger.info("N8nOrchestrator closed")

    async def __aenter__(self) -> "N8nOrchestrator":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

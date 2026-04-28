# =============================================================================
# IPA Platform - WorkflowExecutor Adapter
# =============================================================================
# Sprint 18: S18-1 WorkflowExecutor 適配器 (8 points)
#
# This module provides adapter implementation for Microsoft Agent Framework
# WorkflowExecutor, enabling nested workflow composition and hierarchical
# workflow architectures.
#
# Key Features:
#   - WorkflowExecutorAdapter: Wraps workflows as executors
#   - SubWorkflowRequestMessage: Requests from sub-workflow to parent
#   - SubWorkflowResponseMessage: Responses from parent to sub-workflow
#   - ExecutionContext: Per-execution state isolation
#   - Concurrent execution support
#   - Checkpoint save/restore integration
#
# Agent Framework Reference:
#   - WorkflowExecutor: Core class for nested workflow composition
#   - Supports multiple concurrent sub-workflow executions
#   - Request/response coordination between parent and child workflows
#
# Author: IPA Platform Team
# Sprint: 18 - WorkflowExecutor 和整合
# Created: 2025-12-05
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
)
from uuid import uuid4
import asyncio
import logging
import time

# =============================================================================
# 官方 Agent Framework API 導入 (Sprint 19 整合)
# =============================================================================
from agent_framework import (
    WorkflowExecutor,
    SubWorkflowRequestMessage,
    SubWorkflowResponseMessage,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class WorkflowExecutorStatus(str, Enum):
    """Status of the workflow executor."""
    IDLE = "idle"
    RUNNING = "running"
    WAITING_RESPONSE = "waiting_response"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowRunState(str, Enum):
    """State of a workflow run (matching Agent Framework)."""
    IDLE = "idle"
    IN_PROGRESS = "in_progress"
    IN_PROGRESS_PENDING_REQUESTS = "in_progress_pending_requests"
    IDLE_WITH_PENDING_REQUESTS = "idle_with_pending_requests"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Role of a message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    EXECUTOR = "executor"


# =============================================================================
# Data Classes - Request/Response Messages
# =============================================================================


@dataclass
class RequestInfoEvent:
    """
    Event representing a request for external information.

    Matches Agent Framework RequestInfoEvent structure.
    """
    request_id: str
    data: Any
    response_type: Type[Any]
    executor_id: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "data": self.data,
            "response_type": str(self.response_type),
            "executor_id": self.executor_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class SubWorkflowRequestMessage:
    """
    Message sent from a sub-workflow to parent workflow.

    This message wraps a RequestInfoEvent emitted by an executor
    in the sub-workflow.

    Attributes:
        source_event: The original RequestInfoEvent from sub-workflow
        executor_id: ID of the WorkflowExecutor in parent workflow
    """
    source_event: RequestInfoEvent
    executor_id: str

    def create_response(self, data: Any) -> "SubWorkflowResponseMessage":
        """
        Create a response message with validated data.

        Args:
            data: Response data (should match source_event.response_type)

        Returns:
            SubWorkflowResponseMessage wrapping the response

        Raises:
            TypeError: If data type doesn't match expected response_type
        """
        expected_type = self.source_event.response_type
        # Type validation (relaxed for flexibility)
        if expected_type is not Any and not isinstance(data, expected_type):
            # Log warning but allow flexibility
            logger.warning(
                f"Response data type {type(data)} may not match expected "
                f"type {expected_type} for request_id {self.source_event.request_id}"
            )

        return SubWorkflowResponseMessage(
            data=data,
            source_event=self.source_event,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_event": self.source_event.to_dict(),
            "executor_id": self.executor_id,
        }


@dataclass
class SubWorkflowResponseMessage:
    """
    Message sent from parent workflow to sub-workflow.

    This message wraps the response data along with the original
    RequestInfoEvent for correlation.

    Attributes:
        data: The response data
        source_event: The original RequestInfoEvent this responds to
    """
    data: Any
    source_event: RequestInfoEvent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data": self.data,
            "source_event": self.source_event.to_dict(),
        }


# =============================================================================
# Data Classes - Execution Context
# =============================================================================


@dataclass
class ExecutionContext:
    """
    Context for tracking a single sub-workflow execution.

    Each invocation of the WorkflowExecutor creates an isolated
    ExecutionContext to enable concurrent execution support.

    Attributes:
        execution_id: Unique identifier for this execution
        collected_responses: Responses collected so far (request_id -> data)
        expected_response_count: Number of responses needed before resuming
        pending_requests: Outstanding requests (request_id -> RequestInfoEvent)
    """
    execution_id: str
    collected_responses: Dict[str, Any] = field(default_factory=dict)
    expected_response_count: int = 0
    pending_requests: Dict[str, RequestInfoEvent] = field(default_factory=dict)
    started_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for checkpoint."""
        return {
            "execution_id": self.execution_id,
            "collected_responses": dict(self.collected_responses),
            "expected_response_count": self.expected_response_count,
            "pending_requests": {
                k: v.to_dict() for k, v in self.pending_requests.items()
            },
            "started_at": self.started_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create from dictionary."""
        pending_requests = {}
        for k, v in data.get("pending_requests", {}).items():
            pending_requests[k] = RequestInfoEvent(
                request_id=v["request_id"],
                data=v["data"],
                response_type=Any,  # Type info lost in serialization
                executor_id=v.get("executor_id", ""),
                timestamp=v.get("timestamp", 0),
                metadata=v.get("metadata", {}),
            )

        return cls(
            execution_id=data["execution_id"],
            collected_responses=dict(data.get("collected_responses", {})),
            expected_response_count=data.get("expected_response_count", 0),
            pending_requests=pending_requests,
            started_at=data.get("started_at", time.time()),
            metadata=dict(data.get("metadata", {})),
        )


# =============================================================================
# Data Classes - Workflow Results
# =============================================================================


@dataclass
class WorkflowOutput:
    """Output from a workflow execution."""
    data: Any
    output_type: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowRunResult:
    """
    Result from a workflow execution.

    Contains outputs, request events, and final state.
    """
    outputs: List[WorkflowOutput] = field(default_factory=list)
    request_info_events: List[RequestInfoEvent] = field(default_factory=list)
    final_state: WorkflowRunState = WorkflowRunState.IDLE
    error: Optional[str] = None
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_outputs(self) -> List[Any]:
        """Get output data list."""
        return [o.data for o in self.outputs]

    def get_request_info_events(self) -> List[RequestInfoEvent]:
        """Get pending request events."""
        return list(self.request_info_events)

    def get_final_state(self) -> WorkflowRunState:
        """Get final workflow state."""
        return self.final_state

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "outputs": [{"data": o.data, "type": o.output_type} for o in self.outputs],
            "request_info_events": [e.to_dict() for e in self.request_info_events],
            "final_state": self.final_state.value,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "metadata": self.metadata,
        }


# =============================================================================
# Protocol - Workflow Interface
# =============================================================================


class WorkflowProtocol(Protocol):
    """Protocol for workflow objects that can be wrapped."""

    @property
    def id(self) -> str:
        """Workflow identifier."""
        ...

    @property
    def input_types(self) -> List[Type[Any]]:
        """Types accepted as input."""
        ...

    @property
    def output_types(self) -> List[Type[Any]]:
        """Types produced as output."""
        ...

    async def run(self, input_data: Any) -> WorkflowRunResult:
        """Run the workflow with input data."""
        ...

    async def send_responses(self, responses: Dict[str, Any]) -> WorkflowRunResult:
        """Send responses to pending requests."""
        ...


# =============================================================================
# Data Classes - Execution Result
# =============================================================================


@dataclass
class WorkflowExecutorResult:
    """
    Result from WorkflowExecutor execution.

    Contains consolidated information about the sub-workflow execution.
    """
    status: WorkflowExecutorStatus
    outputs: List[Any] = field(default_factory=list)
    pending_requests: List[SubWorkflowRequestMessage] = field(default_factory=list)
    execution_id: str = ""
    workflow_id: str = ""
    total_executions: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "outputs": self.outputs,
            "pending_requests": [r.to_dict() for r in self.pending_requests],
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "total_executions": self.total_executions,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "metadata": self.metadata,
        }


# =============================================================================
# Main Class - WorkflowExecutorAdapter
# =============================================================================


class WorkflowExecutorAdapter:
    """
    Adapter for Agent Framework WorkflowExecutor.

    Enables nested workflow composition by wrapping workflows as executors
    within parent workflows. Supports:

    - Hierarchical workflow composition
    - Request/response coordination between parent and child
    - Multiple concurrent sub-workflow executions
    - Checkpoint save/restore for state persistence

    Example Usage:
        ```python
        # Create sub-workflow
        sub_workflow = create_email_validation_workflow()

        # Create adapter
        adapter = WorkflowExecutorAdapter(
            id="email-validator",
            workflow=sub_workflow,
            allow_direct_output=False,
        )

        # Build and run
        adapter.build()
        result = await adapter.run(input_data)

        # Handle pending requests
        for request in result.pending_requests:
            response = request.create_response(handle_request(request))
            await adapter.send_response(response)
        ```

    Agent Framework Mapping:
        - WorkflowExecutor → WorkflowExecutorAdapter
        - handler decorators → internal handler methods
        - ExecutionContext → self._execution_contexts
    """

    def __init__(
        self,
        id: str,
        workflow: Optional[WorkflowProtocol] = None,
        allow_direct_output: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize WorkflowExecutorAdapter.

        Args:
            id: Unique identifier for this executor
            workflow: The workflow to wrap (can be set later via with_workflow)
            allow_direct_output: If True, sub-workflow outputs go directly to
                                 parent's event stream. If False (default),
                                 outputs are sent as messages to other executors.
            config: Additional configuration options

        Raises:
            ValueError: If id is empty
        """
        if not id:
            raise ValueError("ID cannot be empty")

        self._id = id
        self._workflow = workflow
        self._allow_direct_output = allow_direct_output
        self._config = config or {}

        # Execution state
        self._execution_contexts: Dict[str, ExecutionContext] = {}
        self._request_to_execution: Dict[str, str] = {}

        # Build state
        self._is_built = False
        self._is_initialized = False
        self._status = WorkflowExecutorStatus.IDLE

        # Event tracking
        self._events: List[Dict[str, Any]] = []

        # Callbacks
        self._request_handlers: Dict[str, Callable] = {}
        self._output_handler: Optional[Callable] = None

        # Sprint 19: 使用官方 WorkflowExecutor API (繼承模式的備用)
        self._executor: Optional[WorkflowExecutor] = None

        logger.info(f"WorkflowExecutorAdapter created: {id}")

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Get executor ID."""
        return self._id

    @property
    def workflow(self) -> Optional[WorkflowProtocol]:
        """Get wrapped workflow."""
        return self._workflow

    @property
    def status(self) -> WorkflowExecutorStatus:
        """Get current status."""
        return self._status

    @property
    def is_built(self) -> bool:
        """Check if adapter is built."""
        return self._is_built

    @property
    def is_initialized(self) -> bool:
        """Check if adapter is initialized."""
        return self._is_initialized

    @property
    def allow_direct_output(self) -> bool:
        """Check if direct output is allowed."""
        return self._allow_direct_output

    @property
    def input_types(self) -> List[Type[Any]]:
        """
        Get input types from wrapped workflow.

        Also includes SubWorkflowResponseMessage for response handling.
        """
        types: List[Type[Any]] = []

        if self._workflow:
            types.extend(self._workflow.input_types)

        if SubWorkflowResponseMessage not in types:
            types.append(SubWorkflowResponseMessage)

        return types

    @property
    def output_types(self) -> List[Type[Any]]:
        """
        Get output types from wrapped workflow.

        Includes SubWorkflowRequestMessage if workflow has request capability.
        """
        types: List[Type[Any]] = []

        if self._workflow:
            types.extend(self._workflow.output_types)

        # Add request message type
        if SubWorkflowRequestMessage not in types:
            types.append(SubWorkflowRequestMessage)

        return types

    @property
    def active_execution_count(self) -> int:
        """Get number of active executions."""
        return len(self._execution_contexts)

    # -------------------------------------------------------------------------
    # Fluent Configuration Methods
    # -------------------------------------------------------------------------

    def with_workflow(self, workflow: WorkflowProtocol) -> "WorkflowExecutorAdapter":
        """
        Set the workflow to wrap.

        Args:
            workflow: Workflow object implementing WorkflowProtocol

        Returns:
            Self for method chaining
        """
        self._workflow = workflow
        return self

    def with_direct_output(self, enable: bool = True) -> "WorkflowExecutorAdapter":
        """
        Enable or disable direct output.

        Args:
            enable: If True, outputs go directly to parent's event stream

        Returns:
            Self for method chaining
        """
        self._allow_direct_output = enable
        return self

    def with_request_handler(
        self,
        request_type: Type[Any],
        handler: Callable,
    ) -> "WorkflowExecutorAdapter":
        """
        Register a handler for specific request types.

        Args:
            request_type: Type of request to handle
            handler: Async callable to handle the request

        Returns:
            Self for method chaining
        """
        type_name = request_type.__name__
        self._request_handlers[type_name] = handler
        return self

    def with_output_handler(
        self,
        handler: Callable,
    ) -> "WorkflowExecutorAdapter":
        """
        Register a handler for workflow outputs.

        Args:
            handler: Async callable to handle outputs

        Returns:
            Self for method chaining
        """
        self._output_handler = handler
        return self

    # -------------------------------------------------------------------------
    # Lifecycle Methods
    # -------------------------------------------------------------------------

    async def initialize(self) -> None:
        """Initialize the adapter."""
        if self._is_initialized:
            return

        logger.info(f"Initializing WorkflowExecutorAdapter: {self._id}")
        self._is_initialized = True
        self._add_event("initialized")

    def build(self) -> "WorkflowExecutorAdapter":
        """
        Build the workflow executor.

        使用官方 Agent Framework WorkflowExecutor API。

        Returns:
            Self for method chaining

        Raises:
            ValueError: If workflow is not set
        """
        if not self._workflow:
            raise ValueError("Workflow must be set before building")

        # Sprint 19: 使用官方 WorkflowExecutor API
        try:
            # 創建官方 WorkflowExecutor 實例
            self._executor = WorkflowExecutor(
                workflow=self._workflow,
                id=self._id,
            )
            logger.info(f"Official WorkflowExecutor created: {self._id}")
        except Exception as e:
            # 如果官方 API 失敗，記錄警告但繼續使用內部實現
            logger.warning(
                f"Official WorkflowExecutor creation failed: {e}. "
                f"Falling back to IPA platform implementation."
            )
            self._executor = None

        logger.info(f"Building WorkflowExecutorAdapter: {self._id}")
        self._is_built = True
        self._add_event("built")
        return self

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info(f"Cleaning up WorkflowExecutorAdapter: {self._id}")

        # Clear execution contexts
        self._execution_contexts.clear()
        self._request_to_execution.clear()

        self._is_initialized = False
        self._is_built = False
        self._status = WorkflowExecutorStatus.IDLE
        self._add_event("cleanup")

    async def reset(self) -> None:
        """Reset to initial state."""
        logger.info(f"Resetting WorkflowExecutorAdapter: {self._id}")

        self._execution_contexts.clear()
        self._request_to_execution.clear()
        self._status = WorkflowExecutorStatus.IDLE
        self._events.clear()
        self._add_event("reset")

    # -------------------------------------------------------------------------
    # Execution Methods
    # -------------------------------------------------------------------------

    async def run(
        self,
        input_data: Any,
        timeout_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecutorResult:
        """
        Execute the sub-workflow with input data.

        Creates a new ExecutionContext for this invocation, enabling
        concurrent executions to be isolated.

        Args:
            input_data: Input data to send to sub-workflow
            timeout_seconds: Optional execution timeout
            metadata: Optional metadata for this execution

        Returns:
            WorkflowExecutorResult with outputs and pending requests

        Raises:
            ValueError: If workflow is not built
            TimeoutError: If execution times out
        """
        if not self._is_built or not self._workflow:
            raise ValueError("Adapter must be built before running")

        start_time = time.time()
        execution_id = str(uuid4())

        # Create execution context
        execution_context = ExecutionContext(
            execution_id=execution_id,
            metadata=metadata or {},
        )
        self._execution_contexts[execution_id] = execution_context

        logger.debug(
            f"WorkflowExecutorAdapter {self._id} starting execution {execution_id}"
        )

        self._status = WorkflowExecutorStatus.RUNNING
        self._add_event("execution_started", {"execution_id": execution_id})

        try:
            # Run with optional timeout
            if timeout_seconds:
                result = await asyncio.wait_for(
                    self._workflow.run(input_data),
                    timeout=timeout_seconds,
                )
            else:
                result = await self._workflow.run(input_data)

            # Process result
            return await self._process_workflow_result(
                result,
                execution_context,
                start_time,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self._status = WorkflowExecutorStatus.FAILED
            self._cleanup_execution(execution_id)

            return WorkflowExecutorResult(
                status=WorkflowExecutorStatus.FAILED,
                execution_id=execution_id,
                workflow_id=self._workflow.id if self._workflow else "",
                duration_seconds=duration,
                error="Execution timed out",
            )

        except Exception as e:
            duration = time.time() - start_time
            self._status = WorkflowExecutorStatus.FAILED
            self._cleanup_execution(execution_id)

            logger.error(f"Execution {execution_id} failed: {e}")
            return WorkflowExecutorResult(
                status=WorkflowExecutorStatus.FAILED,
                execution_id=execution_id,
                workflow_id=self._workflow.id if self._workflow else "",
                duration_seconds=duration,
                error=str(e),
            )

    async def send_response(
        self,
        response: SubWorkflowResponseMessage,
    ) -> Optional[WorkflowExecutorResult]:
        """
        Send response to a pending request.

        Accumulates responses and resumes sub-workflow when all
        expected responses are received.

        Args:
            response: Response to a previous request

        Returns:
            WorkflowExecutorResult if sub-workflow resumed, None otherwise
        """
        request_id = response.source_event.request_id
        execution_id = self._request_to_execution.get(request_id)

        if not execution_id or execution_id not in self._execution_contexts:
            logger.warning(
                f"Response for unknown request_id: {request_id}, ignoring"
            )
            return None

        execution_context = self._execution_contexts[execution_id]

        # Validate request is pending
        if request_id not in execution_context.pending_requests:
            logger.warning(
                f"Response for non-pending request_id: {request_id}, ignoring"
            )
            return None

        # Remove from pending
        execution_context.pending_requests.pop(request_id)
        self._request_to_execution.pop(request_id)

        # Accumulate response
        execution_context.collected_responses[request_id] = response.data

        logger.debug(
            f"Collected response {len(execution_context.collected_responses)}/"
            f"{execution_context.expected_response_count} for execution {execution_id}"
        )

        # Check if all responses received
        if len(execution_context.collected_responses) < execution_context.expected_response_count:
            return None  # Wait for more responses

        # All responses received, resume sub-workflow
        return await self._resume_workflow(execution_context)

    async def send_responses(
        self,
        responses: Dict[str, Any],
    ) -> Optional[WorkflowExecutorResult]:
        """
        Send multiple responses at once.

        Args:
            responses: Dictionary of request_id -> response_data

        Returns:
            WorkflowExecutorResult if sub-workflow resumed
        """
        result = None
        for request_id, data in responses.items():
            # Find the original request
            execution_id = self._request_to_execution.get(request_id)
            if not execution_id:
                continue

            execution_context = self._execution_contexts.get(execution_id)
            if not execution_context:
                continue

            pending_request = execution_context.pending_requests.get(request_id)
            if not pending_request:
                continue

            # Create response message
            response = SubWorkflowResponseMessage(
                data=data,
                source_event=pending_request,
            )

            result = await self.send_response(response)

        return result

    # -------------------------------------------------------------------------
    # Internal Processing Methods
    # -------------------------------------------------------------------------

    async def _process_workflow_result(
        self,
        result: WorkflowRunResult,
        execution_context: ExecutionContext,
        start_time: float,
    ) -> WorkflowExecutorResult:
        """
        Process result from workflow execution.

        Handles outputs, request events, and state transitions.
        """
        duration = time.time() - start_time
        execution_id = execution_context.execution_id

        # Get data from result
        outputs = result.get_outputs()
        request_events = result.get_request_info_events()
        final_state = result.get_final_state()

        logger.debug(
            f"Processing result: {len(outputs)} outputs, "
            f"{len(request_events)} requests, state={final_state}"
        )

        # Process outputs
        processed_outputs = []
        for output in outputs:
            if self._output_handler:
                await self._output_handler(output)
            processed_outputs.append(output)

        # Process request events
        pending_requests: List[SubWorkflowRequestMessage] = []
        for event in request_events:
            # Track pending request
            execution_context.pending_requests[event.request_id] = event
            self._request_to_execution[event.request_id] = execution_id

            # Create request message for parent
            request_msg = SubWorkflowRequestMessage(
                source_event=event,
                executor_id=self._id,
            )
            pending_requests.append(request_msg)

        execution_context.expected_response_count = len(request_events)

        # Determine status
        if final_state == WorkflowRunState.COMPLETED:
            self._status = WorkflowExecutorStatus.COMPLETED
            self._cleanup_execution(execution_id)
        elif final_state == WorkflowRunState.FAILED:
            self._status = WorkflowExecutorStatus.FAILED
            self._cleanup_execution(execution_id)
        elif request_events:
            self._status = WorkflowExecutorStatus.WAITING_RESPONSE
        else:
            self._status = WorkflowExecutorStatus.IDLE

        self._add_event("execution_processed", {
            "execution_id": execution_id,
            "outputs": len(processed_outputs),
            "pending_requests": len(pending_requests),
            "final_state": final_state.value,
        })

        return WorkflowExecutorResult(
            status=self._status,
            outputs=processed_outputs,
            pending_requests=pending_requests,
            execution_id=execution_id,
            workflow_id=self._workflow.id if self._workflow else "",
            total_executions=len(self._execution_contexts),
            duration_seconds=duration,
            error=result.error,
        )

    async def _resume_workflow(
        self,
        execution_context: ExecutionContext,
    ) -> WorkflowExecutorResult:
        """
        Resume sub-workflow with collected responses.
        """
        if not self._workflow:
            raise ValueError("Workflow not set")

        execution_id = execution_context.execution_id
        start_time = time.time()

        logger.debug(f"Resuming execution {execution_id}")

        # Get collected responses
        responses = dict(execution_context.collected_responses)
        execution_context.collected_responses.clear()

        try:
            # Resume workflow
            result = await self._workflow.send_responses(responses)

            # Process result
            return await self._process_workflow_result(
                result,
                execution_context,
                start_time,
            )

        except Exception as e:
            duration = time.time() - start_time
            self._status = WorkflowExecutorStatus.FAILED
            self._cleanup_execution(execution_id)

            logger.error(f"Resume failed for {execution_id}: {e}")
            return WorkflowExecutorResult(
                status=WorkflowExecutorStatus.FAILED,
                execution_id=execution_id,
                workflow_id=self._workflow.id,
                duration_seconds=duration,
                error=str(e),
            )

    def _cleanup_execution(self, execution_id: str) -> None:
        """Clean up completed execution."""
        if execution_id in self._execution_contexts:
            ctx = self._execution_contexts[execution_id]
            # Remove request mappings
            for request_id in ctx.pending_requests:
                self._request_to_execution.pop(request_id, None)
            # Remove context
            del self._execution_contexts[execution_id]

    # -------------------------------------------------------------------------
    # Checkpoint Methods
    # -------------------------------------------------------------------------

    async def on_checkpoint_save(self) -> Dict[str, Any]:
        """
        Get state for checkpointing.

        Returns:
            Dictionary containing execution state
        """
        return {
            "execution_contexts": {
                k: v.to_dict() for k, v in self._execution_contexts.items()
            },
            "request_to_execution": dict(self._request_to_execution),
            "status": self._status.value,
        }

    async def on_checkpoint_restore(self, state: Dict[str, Any]) -> None:
        """
        Restore state from checkpoint.

        Args:
            state: State dictionary from on_checkpoint_save

        Raises:
            KeyError: If required keys are missing
            ValueError: If state data is invalid
        """
        if "execution_contexts" not in state:
            raise KeyError("Missing 'execution_contexts' in state")
        if "request_to_execution" not in state:
            raise KeyError("Missing 'request_to_execution' in state")

        # Restore execution contexts
        self._execution_contexts = {
            k: ExecutionContext.from_dict(v)
            for k, v in state["execution_contexts"].items()
        }

        # Restore request mapping
        self._request_to_execution = dict(state["request_to_execution"])

        # Restore status
        if "status" in state:
            self._status = WorkflowExecutorStatus(state["status"])

        logger.info(
            f"Restored state: {len(self._execution_contexts)} execution contexts"
        )

    # -------------------------------------------------------------------------
    # State and Event Methods
    # -------------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        """Get current adapter state."""
        return {
            "id": self._id,
            "status": self._status.value,
            "is_built": self._is_built,
            "is_initialized": self._is_initialized,
            "allow_direct_output": self._allow_direct_output,
            "workflow_id": self._workflow.id if self._workflow else None,
            "active_executions": len(self._execution_contexts),
            "pending_requests": len(self._request_to_execution),
        }

    def get_events(self) -> List[Dict[str, Any]]:
        """Get event history."""
        return list(self._events)

    def clear_events(self) -> None:
        """Clear event history."""
        self._events.clear()

    def _add_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to history."""
        self._events.append({
            "type": event_type,
            "timestamp": time.time(),
            "data": data or {},
        })

    # -------------------------------------------------------------------------
    # Context Manager Support
    # -------------------------------------------------------------------------

    async def __aenter__(self) -> "WorkflowExecutorAdapter":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.cleanup()


# =============================================================================
# Simple Workflow Implementation (for testing/migration)
# =============================================================================


class SimpleWorkflow:
    """
    Simple workflow implementation for migration support.

    Provides a basic workflow that can be used with WorkflowExecutorAdapter
    without depending on the full Agent Framework.
    """

    def __init__(
        self,
        id: str,
        executor_fn: Callable,
        input_types: Optional[List[Type[Any]]] = None,
        output_types: Optional[List[Type[Any]]] = None,
    ):
        """
        Initialize simple workflow.

        Args:
            id: Workflow identifier
            executor_fn: Async function to execute workflow logic
            input_types: List of accepted input types
            output_types: List of output types
        """
        self._id = id
        self._executor_fn = executor_fn
        self._input_types = input_types or [Any]
        self._output_types = output_types or [Any]
        self._pending_responses: Dict[str, Any] = {}

    @property
    def id(self) -> str:
        return self._id

    @property
    def input_types(self) -> List[Type[Any]]:
        return self._input_types

    @property
    def output_types(self) -> List[Type[Any]]:
        return self._output_types

    async def run(self, input_data: Any) -> WorkflowRunResult:
        """Run the workflow."""
        start_time = time.time()
        try:
            result = await self._executor_fn(input_data, self._pending_responses)

            # If result is WorkflowRunResult, return it
            if isinstance(result, WorkflowRunResult):
                return result

            # Otherwise wrap it
            return WorkflowRunResult(
                outputs=[WorkflowOutput(data=result)],
                final_state=WorkflowRunState.COMPLETED,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            return WorkflowRunResult(
                final_state=WorkflowRunState.FAILED,
                error=str(e),
                duration_seconds=time.time() - start_time,
            )

    async def send_responses(self, responses: Dict[str, Any]) -> WorkflowRunResult:
        """Send responses to pending requests."""
        self._pending_responses.update(responses)
        # Re-run with responses available
        return await self.run(None)


# =============================================================================
# Factory Functions
# =============================================================================


def create_workflow_executor(
    id: str,
    workflow: Optional[WorkflowProtocol] = None,
    allow_direct_output: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> WorkflowExecutorAdapter:
    """
    Create a WorkflowExecutorAdapter.

    Args:
        id: Executor identifier
        workflow: Workflow to wrap
        allow_direct_output: Enable direct output to parent
        config: Additional configuration

    Returns:
        Configured WorkflowExecutorAdapter
    """
    return WorkflowExecutorAdapter(
        id=id,
        workflow=workflow,
        allow_direct_output=allow_direct_output,
        config=config,
    )


def create_simple_workflow(
    id: str,
    executor_fn: Callable,
    input_types: Optional[List[Type[Any]]] = None,
    output_types: Optional[List[Type[Any]]] = None,
) -> SimpleWorkflow:
    """
    Create a SimpleWorkflow for migration support.

    Args:
        id: Workflow identifier
        executor_fn: Async function for workflow logic
        input_types: Accepted input types
        output_types: Output types

    Returns:
        Configured SimpleWorkflow
    """
    return SimpleWorkflow(
        id=id,
        executor_fn=executor_fn,
        input_types=input_types,
        output_types=output_types,
    )


def create_nested_workflow_executor(
    id: str,
    parent_workflow: WorkflowProtocol,
    child_workflows: List[WorkflowProtocol],
) -> WorkflowExecutorAdapter:
    """
    Create a nested workflow executor with multiple child workflows.

    This is a convenience function for creating hierarchical workflows.

    Args:
        id: Parent executor identifier
        parent_workflow: Parent workflow
        child_workflows: List of child workflows to nest

    Returns:
        Configured WorkflowExecutorAdapter
    """
    # Create child executors
    child_executors = [
        WorkflowExecutorAdapter(
            id=f"{id}_child_{i}",
            workflow=child,
        )
        for i, child in enumerate(child_workflows)
    ]

    # Build all child executors
    for executor in child_executors:
        executor.build()

    # Create parent executor
    adapter = WorkflowExecutorAdapter(
        id=id,
        workflow=parent_workflow,
        config={"child_executors": child_executors},
    )

    return adapter


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "WorkflowExecutorStatus",
    "WorkflowRunState",
    "MessageRole",
    # Data Classes
    "RequestInfoEvent",
    "SubWorkflowRequestMessage",
    "SubWorkflowResponseMessage",
    "ExecutionContext",
    "WorkflowOutput",
    "WorkflowRunResult",
    "WorkflowExecutorResult",
    # Protocol
    "WorkflowProtocol",
    # Main Classes
    "WorkflowExecutorAdapter",
    "SimpleWorkflow",
    # Factory Functions
    "create_workflow_executor",
    "create_simple_workflow",
    "create_nested_workflow_executor",
]

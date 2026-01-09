# =============================================================================
# IPA Platform - AG-UI Hybrid Event Bridge
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-2: HybridEventBridge
# Sprint 67: S67-BF-1 - Add heartbeat mechanism for Rate Limit handling
#
# Bridge component that connects HybridOrchestratorV2 to AG-UI protocol.
# Transforms execution results into AG-UI standard SSE event streams.
#
# Key Features:
#   - Wraps HybridOrchestratorV2 execution
#   - Generates AG-UI compliant event streams
#   - Supports SSE (Server-Sent Events) formatting
#   - Handles tool call events from execution results
#   - Heartbeat mechanism for long-running operations (Rate Limit retry)
#
# Dependencies:
#   - EventConverters (src.integrations.ag_ui.converters)
#   - HybridOrchestratorV2 (src.integrations.hybrid.orchestrator_v2)
#   - AG-UI Events (src.integrations.ag_ui.events)
# =============================================================================

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, TYPE_CHECKING

from src.integrations.ag_ui.converters import EventConverters, create_converters
from src.integrations.ag_ui.events import (
    BaseAGUIEvent,
    CustomEvent,
    RunStartedEvent,
    RunFinishedEvent,
    RunFinishReason,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
)

if TYPE_CHECKING:
    from src.integrations.hybrid.orchestrator_v2 import HybridOrchestratorV2, HybridResultV2
    from src.integrations.hybrid.intent import ExecutionMode

logger = logging.getLogger(__name__)


@dataclass
class RunAgentInput:
    """
    Input for running an agent through the bridge.

    Attributes:
        prompt: User prompt/message
        thread_id: Thread ID for conversation context
        run_id: Unique run ID (generated if not provided)
        session_id: Optional session ID
        force_mode: Force specific execution mode
        tools: Available tools for execution
        max_tokens: Maximum tokens for response
        timeout: Execution timeout in seconds
        metadata: Additional metadata
        file_ids: List of file IDs to include as attachments (Sprint 75)
    """

    prompt: str
    thread_id: str
    run_id: Optional[str] = None
    session_id: Optional[str] = None
    force_mode: Optional["ExecutionMode"] = None
    tools: Optional[List[Dict[str, Any]]] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_ids: Optional[List[str]] = None  # Sprint 75: File attachments

    def __post_init__(self):
        """Generate run_id if not provided."""
        if not self.run_id:
            self.run_id = f"run-{uuid.uuid4().hex[:12]}"


@dataclass
class BridgeConfig:
    """
    Configuration for HybridEventBridge.

    Attributes:
        chunk_size: Size of text chunks for streaming
        include_metadata: Whether to include metadata in events
        emit_state_events: Whether to emit state events
        emit_custom_events: Whether to emit custom events
        heartbeat_interval: Interval in seconds for heartbeat events (0 = disabled)
    """

    chunk_size: int = 100
    include_metadata: bool = True
    emit_state_events: bool = True
    emit_custom_events: bool = True
    heartbeat_interval: float = 10.0  # S67-BF-1: Send heartbeat every 10 seconds


class HybridEventBridge:
    """
    AG-UI Event Bridge for HybridOrchestratorV2.

    Bridges the HybridOrchestratorV2 execution model to AG-UI protocol,
    converting execution results into standardized SSE event streams.

    The bridge:
    1. Accepts RunAgentInput with prompt and thread context
    2. Executes via HybridOrchestratorV2
    3. Generates AG-UI events from the execution result
    4. Yields events as SSE-formatted strings

    Example:
        >>> orchestrator = HybridOrchestratorV2()
        >>> bridge = HybridEventBridge(orchestrator=orchestrator)
        >>> input = RunAgentInput(prompt="Hello", thread_id="thread-123")
        >>> async for event_sse in bridge.stream_events(input):
        ...     print(event_sse)
    """

    def __init__(
        self,
        *,
        orchestrator: Optional["HybridOrchestratorV2"] = None,
        converters: Optional[EventConverters] = None,
        config: Optional[BridgeConfig] = None,
    ):
        """
        Initialize HybridEventBridge.

        Args:
            orchestrator: HybridOrchestratorV2 instance for execution
            converters: EventConverters for event transformation
            config: Bridge configuration
        """
        self._orchestrator = orchestrator
        self._config = config or BridgeConfig()
        self._converters = converters or create_converters(
            chunk_size=self._config.chunk_size,
            include_metadata=self._config.include_metadata,
        )

        logger.info(
            f"HybridEventBridge initialized: "
            f"orchestrator={orchestrator is not None}, "
            f"chunk_size={self._config.chunk_size}"
        )

    @property
    def orchestrator(self) -> Optional["HybridOrchestratorV2"]:
        """Get the orchestrator instance."""
        return self._orchestrator

    @property
    def converters(self) -> EventConverters:
        """Get the converters instance."""
        return self._converters

    @property
    def config(self) -> BridgeConfig:
        """Get the bridge configuration."""
        return self._config

    def set_orchestrator(self, orchestrator: "HybridOrchestratorV2") -> None:
        """
        Set the orchestrator instance.

        Args:
            orchestrator: HybridOrchestratorV2 instance
        """
        self._orchestrator = orchestrator
        logger.info("Orchestrator updated in bridge")

    async def _generate_simulation_events(
        self,
        run_input: RunAgentInput,
    ) -> AsyncGenerator[BaseAGUIEvent, None]:
        """
        Generate simulation events when orchestrator is not configured.

        This is used for UAT testing and development without a real LLM.

        Args:
            run_input: RunAgentInput with execution parameters

        Yields:
            Simulated AG-UI events
        """
        thread_id = run_input.thread_id
        run_id = run_input.run_id or f"run-{uuid.uuid4().hex[:12]}"
        message_id = f"msg-{uuid.uuid4().hex[:8]}"

        logger.info(f"Generating simulation events for thread={thread_id}, run={run_id}")

        # 1. RUN_STARTED
        yield self._converters.to_run_started(thread_id, run_id)

        # 2. TEXT_MESSAGE_START
        yield TextMessageStartEvent(
            type="TEXT_MESSAGE_START",
            message_id=message_id,
            role="assistant",
        )

        # 3. Simulate response content
        simulation_content = (
            f"[Simulation Mode] Received your message: '{run_input.prompt[:50]}...'. "
            f"The AG-UI API is working correctly. "
            f"Configure HybridOrchestratorV2 for real LLM responses."
        )

        # Yield content in chunks
        for i in range(0, len(simulation_content), self._config.chunk_size):
            chunk = simulation_content[i : i + self._config.chunk_size]
            yield TextMessageContentEvent(
                type="TEXT_MESSAGE_CONTENT",
                message_id=message_id,
                delta=chunk,
            )

        # 4. TEXT_MESSAGE_END
        yield TextMessageEndEvent(
            type="TEXT_MESSAGE_END",
            message_id=message_id,
        )

        # 5. RUN_FINISHED
        yield self._converters.to_run_finished(
            thread_id=thread_id,
            run_id=run_id,
            success=True,
            error=None,
            usage={
                "simulation": True,
                "tokens_used": len(simulation_content.split()),
            } if self._config.include_metadata else None,
        )

    async def stream_events(
        self,
        run_input: RunAgentInput,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AG-UI events as SSE-formatted strings.

        This is the main entry point for streaming execution results.
        The method:
        1. Emits RUN_STARTED event
        2. Executes via orchestrator with heartbeat during wait
        3. Converts result to AG-UI events
        4. Yields each event as SSE string
        5. Emits RUN_FINISHED event

        S67-BF-1: Added heartbeat mechanism to keep SSE connection alive
        during long-running operations (e.g., Rate Limit retry waits).

        Args:
            run_input: RunAgentInput with execution parameters

        Yields:
            SSE-formatted event strings ("data: {...}\\n\\n")

        """
        # Simulation mode when orchestrator not configured
        if not self._orchestrator:
            async for event in self._generate_simulation_events(run_input):
                yield self._format_sse(event)
            return

        thread_id = run_input.thread_id
        run_id = run_input.run_id or f"run-{uuid.uuid4().hex[:12]}"

        # 1. Emit RUN_STARTED
        run_started = self._converters.to_run_started(thread_id, run_id)
        yield self._format_sse(run_started)

        try:
            # S67-BF-1: Execute with heartbeat mechanism
            # Use asyncio.Queue to collect events from both heartbeat and execution
            event_queue: asyncio.Queue[BaseAGUIEvent | None] = asyncio.Queue()
            execution_done = asyncio.Event()
            execution_result: Dict[str, Any] = {"result": None, "error": None}

            async def execute_task():
                """Execute orchestrator and signal completion."""
                try:
                    result = await self._orchestrator.execute(
                        prompt=run_input.prompt,
                        session_id=run_input.session_id,
                        force_mode=run_input.force_mode,
                        tools=run_input.tools,
                        max_tokens=run_input.max_tokens,
                        timeout=run_input.timeout,
                        metadata=run_input.metadata,
                    )
                    execution_result["result"] = result
                except Exception as e:
                    execution_result["error"] = e
                finally:
                    execution_done.set()
                    await event_queue.put(None)  # Signal end

            async def heartbeat_task():
                """Send heartbeat events while execution is in progress."""
                heartbeat_count = 0
                start_time = time.time()
                while not execution_done.is_set():
                    try:
                        # Wait for heartbeat interval or until execution completes
                        await asyncio.wait_for(
                            execution_done.wait(),
                            timeout=self._config.heartbeat_interval,
                        )
                        break  # Execution completed
                    except asyncio.TimeoutError:
                        # Execution still in progress, send heartbeat
                        heartbeat_count += 1
                        elapsed = time.time() - start_time
                        heartbeat_event = CustomEvent(
                            event_name="heartbeat",
                            payload={
                                "count": heartbeat_count,
                                "elapsed_seconds": round(elapsed, 1),
                                "message": "Processing request... (API may be rate limited)",
                                "status": "processing",
                            },
                        )
                        await event_queue.put(heartbeat_event)
                        logger.debug(
                            f"Heartbeat #{heartbeat_count}: "
                            f"elapsed={elapsed:.1f}s, thread={thread_id}"
                        )

            # Start both tasks concurrently
            exec_task = asyncio.create_task(execute_task())
            hb_task = asyncio.create_task(heartbeat_task())

            # Yield events from queue (heartbeats) until execution completes
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    if event is None:
                        break  # Execution completed
                    yield self._format_sse(event)
                except asyncio.TimeoutError:
                    # Check if execution is done
                    if execution_done.is_set():
                        break

            # Ensure tasks are cleaned up
            await exec_task
            hb_task.cancel()
            try:
                await hb_task
            except asyncio.CancelledError:
                pass

            # Check for execution error
            if execution_result["error"]:
                raise execution_result["error"]

            result = execution_result["result"]

            # 3. Convert result to events and yield (excluding RUN_STARTED and RUN_FINISHED)
            message_id = f"msg-{uuid.uuid4().hex[:8]}"
            events = self._converters.from_result(
                result,
                thread_id=thread_id,
                run_id=run_id,
                message_id=message_id,
            )

            # Yield all events except the last one (RUN_FINISHED)
            # because we'll emit it separately below
            for event in events[:-1]:
                yield self._format_sse(event)

            # 4. Emit RUN_FINISHED with result status
            run_finished = self._converters.to_run_finished(
                thread_id=thread_id,
                run_id=run_id,
                success=result.success,
                error=result.error,
                usage={
                    "tokens_used": result.tokens_used,
                    "duration_ms": result.duration * 1000,
                    "framework": result.framework_used,
                    "mode": result.execution_mode.value if result.execution_mode else None,
                } if self._config.include_metadata else None,
            )
            yield self._format_sse(run_finished)

        except Exception as e:
            logger.error(f"Bridge execution error: {e}", exc_info=True)

            # Emit error RUN_FINISHED
            run_finished = self._converters.to_run_finished(
                thread_id=thread_id,
                run_id=run_id,
                success=False,
                error=str(e),
            )
            yield self._format_sse(run_finished)

    async def stream_events_raw(
        self,
        run_input: RunAgentInput,
    ) -> AsyncGenerator[BaseAGUIEvent, None]:
        """
        Stream AG-UI events as raw event objects.

        Similar to stream_events but yields BaseAGUIEvent objects
        instead of SSE-formatted strings.

        If orchestrator is not configured, operates in simulation mode
        and returns a mock response.

        Args:
            run_input: RunAgentInput with execution parameters

        Yields:
            BaseAGUIEvent instances
        """
        # Simulation mode when orchestrator not configured
        if not self._orchestrator:
            async for event in self._generate_simulation_events(run_input):
                yield event
            return

        thread_id = run_input.thread_id
        run_id = run_input.run_id or f"run-{uuid.uuid4().hex[:12]}"

        # 1. Emit RUN_STARTED
        yield self._converters.to_run_started(thread_id, run_id)

        try:
            # 2. Execute via orchestrator
            result = await self._orchestrator.execute(
                prompt=run_input.prompt,
                session_id=run_input.session_id,
                force_mode=run_input.force_mode,
                tools=run_input.tools,
                max_tokens=run_input.max_tokens,
                timeout=run_input.timeout,
                metadata=run_input.metadata,
            )

            # 3. Convert result to events and yield
            message_id = f"msg-{uuid.uuid4().hex[:8]}"
            events = self._converters.from_result(
                result,
                thread_id=thread_id,
                run_id=run_id,
                message_id=message_id,
            )

            for event in events[:-1]:
                yield event

            # 4. Emit RUN_FINISHED
            yield self._converters.to_run_finished(
                thread_id=thread_id,
                run_id=run_id,
                success=result.success,
                error=result.error,
                usage={
                    "tokens_used": result.tokens_used,
                    "duration_ms": result.duration * 1000,
                    "framework": result.framework_used,
                } if self._config.include_metadata else None,
            )

        except Exception as e:
            logger.error(f"Bridge execution error: {e}", exc_info=True)
            yield self._converters.to_run_finished(
                thread_id=thread_id,
                run_id=run_id,
                success=False,
                error=str(e),
            )

    async def execute_and_collect(
        self,
        run_input: RunAgentInput,
    ) -> List[BaseAGUIEvent]:
        """
        Execute and collect all events without streaming.

        Useful for testing or when streaming is not needed.

        Args:
            run_input: RunAgentInput with execution parameters

        Returns:
            List of all generated AG-UI events
        """
        events: List[BaseAGUIEvent] = []
        async for event in self.stream_events_raw(run_input):
            events.append(event)
        return events

    def _format_sse(self, event: BaseAGUIEvent) -> str:
        """
        Format an event as SSE string.

        Args:
            event: AG-UI event to format

        Returns:
            SSE-formatted string: "data: {json}\\n\\n"
        """
        return event.to_sse()

    # =========================================================================
    # Direct Event Methods (for manual event generation)
    # =========================================================================

    def create_run_started(
        self,
        thread_id: str,
        run_id: str,
    ) -> RunStartedEvent:
        """Create a RUN_STARTED event."""
        return self._converters.to_run_started(thread_id, run_id)

    def create_run_finished(
        self,
        thread_id: str,
        run_id: str,
        *,
        success: bool = True,
        error: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
    ) -> RunFinishedEvent:
        """Create a RUN_FINISHED event."""
        return self._converters.to_run_finished(
            thread_id, run_id, success=success, error=error, usage=usage
        )

    def format_event(self, event: BaseAGUIEvent) -> str:
        """Format any event as SSE string."""
        return self._format_sse(event)


def create_bridge(
    *,
    orchestrator: Optional["HybridOrchestratorV2"] = None,
    chunk_size: int = 100,
    include_metadata: bool = True,
) -> HybridEventBridge:
    """
    Factory function to create HybridEventBridge.

    Args:
        orchestrator: HybridOrchestratorV2 instance
        chunk_size: Size of text chunks for streaming
        include_metadata: Whether to include metadata in events

    Returns:
        Configured HybridEventBridge instance
    """
    config = BridgeConfig(
        chunk_size=chunk_size,
        include_metadata=include_metadata,
    )
    converters = create_converters(
        chunk_size=chunk_size,
        include_metadata=include_metadata,
    )
    return HybridEventBridge(
        orchestrator=orchestrator,
        converters=converters,
        config=config,
    )

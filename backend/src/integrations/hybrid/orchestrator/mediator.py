# =============================================================================
# IPA Platform - Orchestrator Mediator
# =============================================================================
# Sprint 132: Central coordinator replacing HybridOrchestratorV2 God Object.
#
# Mediator Pattern: Coordinates Handler chain execution, managing the flow
# between routing, dialog, approval, execution, context, and observability.
# =============================================================================

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis, SessionContext
from src.integrations.hybrid.context import ContextBridge, HybridContext, SyncResult
from src.integrations.hybrid.execution import (
    ToolExecutionResult,
    ToolSource,
    UnifiedToolExecutor,
)
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
    OrchestratorResponse,
)
from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler
from src.integrations.hybrid.orchestrator.handlers.routing import RoutingHandler
from src.integrations.hybrid.orchestrator.handlers.dialog import DialogHandler
from src.integrations.hybrid.orchestrator.handlers.approval import ApprovalHandler
from src.integrations.hybrid.orchestrator.handlers.execution import ExecutionHandler
from src.integrations.hybrid.orchestrator.handlers.context import ContextHandler
from src.integrations.hybrid.orchestrator.handlers.observability import (
    ObservabilityHandler,
)

logger = logging.getLogger(__name__)


class OrchestratorMediator:
    """Central coordinator for the orchestration pipeline.

    Replaces HybridOrchestratorV2's God Object pattern with a Mediator
    that coordinates loosely-coupled handlers. Each handler encapsulates
    a single responsibility.

    Pipeline:
    1. ContextHandler   — Prepare hybrid context
    2. RoutingHandler   — Route request and determine execution mode
    3. DialogHandler    — Gather missing information (conditional)
    4. ApprovalHandler  — Risk assessment and HITL approval (conditional)
    5. AgentHandler     — LLM-powered response generation (may short-circuit)
    6. ExecutionHandler  — Dispatch to MAF/Claude/Swarm
    7. ObservabilityHandler — Record metrics
    """

    def __init__(
        self,
        *,
        routing_handler: Optional[RoutingHandler] = None,
        dialog_handler: Optional[DialogHandler] = None,
        approval_handler: Optional[ApprovalHandler] = None,
        agent_handler: Optional[AgentHandler] = None,
        execution_handler: Optional[ExecutionHandler] = None,
        context_handler: Optional[ContextHandler] = None,
        observability_handler: Optional[ObservabilityHandler] = None,
    ):
        self._handlers: Dict[HandlerType, Handler] = {}

        # Register handlers
        if routing_handler:
            self._handlers[HandlerType.ROUTING] = routing_handler
        if dialog_handler:
            self._handlers[HandlerType.DIALOG] = dialog_handler
        if approval_handler:
            self._handlers[HandlerType.APPROVAL] = approval_handler
        if agent_handler:
            self._handlers[HandlerType.AGENT] = agent_handler
        if execution_handler:
            self._handlers[HandlerType.EXECUTION] = execution_handler
        if context_handler:
            self._handlers[HandlerType.CONTEXT] = context_handler
        if observability_handler:
            self._handlers[HandlerType.OBSERVABILITY] = observability_handler

        # Sprint 147: Session state — use ConversationStateStore when available
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._conversation_store: Optional[Any] = None
        try:
            from src.infrastructure.storage.conversation_state import ConversationStateStore
            self._conversation_store = ConversationStateStore()
            logger.info("Mediator: ConversationStateStore wired for session persistence")
        except Exception as e:
            logger.warning("Mediator: ConversationStateStore unavailable, using in-memory: %s", e)

        # Sprint 147: Checkpoint storage — use Redis/Postgres when available
        self._checkpoint_storage: Optional[Any] = None
        try:
            from src.integrations.hybrid.checkpoint.backends.redis import RedisCheckpointStorage
            self._checkpoint_storage = RedisCheckpointStorage()
            logger.info("Mediator: RedisCheckpointStorage wired")
        except Exception:
            try:
                from src.integrations.hybrid.checkpoint.backends.memory import MemoryCheckpointStorage
                self._checkpoint_storage = MemoryCheckpointStorage()
                logger.info("Mediator: MemoryCheckpointStorage fallback")
            except Exception:
                pass

        # Sprint 146: HITL approval state
        self._pending_approvals: Dict[str, Any] = {}  # approval_id -> asyncio.Event
        self._approval_results: Dict[str, str] = {}  # approval_id -> "approve"/"reject"

        logger.info(
            f"OrchestratorMediator initialized with handlers: "
            f"{[h.value for h in self._handlers.keys()]}"
        )

    # =========================================================================
    # Handler Management
    # =========================================================================

    def register_handler(self, handler: Handler) -> None:
        """Register a handler with the mediator."""
        self._handlers[handler.handler_type] = handler

    def get_handler(self, handler_type: HandlerType) -> Optional[Handler]:
        """Get a registered handler by type."""
        return self._handlers.get(handler_type)

    @property
    def registered_handlers(self) -> List[HandlerType]:
        """List registered handler types."""
        return list(self._handlers.keys())

    # =========================================================================
    # Session Management
    # =========================================================================

    def create_session(
        self,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new session."""
        sid = session_id or str(uuid.uuid4())
        self._sessions[sid] = {
            "session_id": sid,
            "conversation_history": [],
            "current_mode": ExecutionMode.CHAT_MODE,
            "metadata": metadata or {},
            "created_at": time.time(),
            "last_activity": time.time(),
        }
        return sid

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID."""
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        """Close and remove a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    @property
    def session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._sessions)

    # =========================================================================
    # Sprint 146: HITL Approval
    # =========================================================================

    def resolve_approval(self, approval_id: str, action: str) -> bool:
        """Resolve a pending HITL approval.

        Called by the approval endpoint when user approves/rejects.
        Sets the event to unblock the waiting pipeline.
        """
        event = self._pending_approvals.get(approval_id)
        if not event:
            return False
        self._approval_results[approval_id] = action
        event.set()
        return True

    # =========================================================================
    # Core Execution
    # =========================================================================

    async def execute(
        self,
        request: OrchestratorRequest,
        event_emitter: Optional[Any] = None,
    ) -> OrchestratorResponse:
        """Execute the full mediator pipeline.

        Coordinates all registered handlers in sequence, handling
        short-circuit responses from dialog and approval handlers.

        Args:
            request: The orchestrator request.
            event_emitter: Optional PipelineEventEmitter for SSE streaming.
                When provided, events are emitted at each pipeline step.
        """
        start_time = time.time()

        # Get or create session
        session = self._get_or_create_session(request)
        session["last_activity"] = time.time()

        # Pipeline context shared across handlers
        pipeline_context: Dict[str, Any] = {
            "session_id": session["session_id"],
            "conversation_history": session.get("conversation_history", []),
            "current_mode": session.get("current_mode", ExecutionMode.CHAT_MODE),
            "metadata": {**(request.metadata or {}), **(session.get("metadata", {}))},
        }

        handler_results: Dict[str, HandlerResult] = {}

        # Sprint 145: Helper to emit SSE events when emitter is available
        def _enum_val(v: Any) -> Any:
            """Convert enum to its .value string."""
            return v.value if hasattr(v, "value") else str(v) if v else None

        async def _emit(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
            if event_emitter and hasattr(event_emitter, "emit"):
                import asyncio as _aio
                from src.integrations.hybrid.orchestrator.sse_events import SSEEventType
                try:
                    et = SSEEventType(event_type)
                    await event_emitter.emit(et, data or {})
                    # Yield control so SSE stream can send this event
                    # before the next pipeline step starts
                    await _aio.sleep(0)
                except (ValueError, Exception):
                    pass

        try:
            # Sprint 147: Helper to save checkpoint after each handler
            async def _save_checkpoint(step_name: str, step_index: int) -> None:
                if self._checkpoint_storage and hasattr(self._checkpoint_storage, "save"):
                    try:
                        from src.integrations.hybrid.checkpoint.models import HybridCheckpoint
                        cp = HybridCheckpoint(
                            session_id=session["session_id"],
                            step_name=step_name,
                            step_index=step_index,
                            state={
                                "execution_mode": str(pipeline_context.get("execution_mode", "")),
                                "handler_results_keys": list(handler_results.keys()),
                            },
                        )
                        await self._checkpoint_storage.save(cp)
                    except Exception as cp_err:
                        logger.debug("Checkpoint save failed for step '%s': %s", step_name, cp_err)

            # Sprint 147: Check for existing checkpoint to resume from
            resume_step = -1
            if self._checkpoint_storage and hasattr(self._checkpoint_storage, "load_latest"):
                try:
                    latest_cp = await self._checkpoint_storage.load_latest(
                        session_id=session["session_id"]
                    )
                    if latest_cp:
                        resume_step = getattr(latest_cp, "step_index", -1)
                        logger.info(
                            "Mediator: found checkpoint at step %d (%s), resuming",
                            resume_step,
                            getattr(latest_cp, "step_name", "unknown"),
                        )
                        await _emit("CHECKPOINT_RESTORED", {
                            "step_name": getattr(latest_cp, "step_name", ""),
                            "step_index": resume_step,
                        })
                except Exception as cp_err:
                    logger.debug("Mediator: checkpoint load failed: %s", cp_err)

            # Sprint 145: Emit pipeline start
            await _emit("PIPELINE_START", {
                "session_id": session["session_id"],
                "mode": _enum_val(request.force_mode) or "auto",
            })

            # Step 1: Context preparation
            context_result = await self._run_handler(
                HandlerType.CONTEXT, request, pipeline_context
            )
            if context_result:
                handler_results["context"] = context_result

            # Step 2: Routing
            routing_result = await self._run_handler(
                HandlerType.ROUTING, request, pipeline_context
            )
            if routing_result:
                handler_results["routing"] = routing_result
                if not routing_result.success:
                    await _emit("PIPELINE_ERROR", {"error": routing_result.error or "routing failed"})
                    return self._build_error_response(
                        routing_result, session, start_time, handler_results
                    )

                # Sprint 145: Emit routing complete
                rd = routing_result.data or {}
                routing_decision = rd.get("routing_decision")
                await _emit("ROUTING_COMPLETE", {
                    "intent": _enum_val(getattr(routing_decision, "intent_category", None)) if routing_decision else None,
                    "risk_level": _enum_val(getattr(routing_decision, "risk_level", None)) if routing_decision else None,
                    "mode": _enum_val(pipeline_context.get("execution_mode")),
                    "confidence": getattr(routing_decision, "confidence", None) if routing_decision else None,
                    "routing_layer": getattr(routing_decision, "routing_layer", None) if routing_decision else None,
                    "suggested_mode": rd.get("suggested_mode"),
                })

            await _save_checkpoint("routing", 2)

            # Step 3: Dialog (conditional)
            dialog_result = await self._run_handler(
                HandlerType.DIALOG, request, pipeline_context
            )
            if dialog_result:
                handler_results["dialog"] = dialog_result
                if dialog_result.should_short_circuit:
                    return self._build_short_circuit_response(
                        dialog_result, session, start_time, handler_results,
                        framework="guided_dialog",
                        mode=ExecutionMode.CHAT_MODE,
                        pipeline_context=pipeline_context,
                    )

            # Step 4: Approval (conditional)
            approval_result = await self._run_handler(
                HandlerType.APPROVAL, request, pipeline_context
            )
            if approval_result:
                handler_results["approval"] = approval_result
                if approval_result.should_short_circuit:
                    return self._build_short_circuit_response(
                        approval_result, session, start_time, handler_results,
                        framework="hitl_controller",
                        mode=ExecutionMode.WORKFLOW_MODE,
                        pipeline_context=pipeline_context,
                    )

            # Sprint 146: HITL approval via SSE for high-risk operations
            routing_decision = pipeline_context.get("routing_decision")
            if routing_decision and event_emitter:
                rd_risk = str(getattr(routing_decision, "risk_level", "")).lower()
                if "high" in rd_risk or "critical" in rd_risk:
                    import asyncio as _aio
                    approval_id = str(uuid.uuid4())
                    approval_event = _aio.Event()
                    self._pending_approvals[approval_id] = approval_event

                    await _emit("APPROVAL_REQUIRED", {
                        "approval_id": approval_id,
                        "action": "pipeline_execution",
                        "risk_level": rd_risk,
                        "description": f"高風險操作需要審批 (risk={rd_risk})",
                        "details": {
                            "intent": str(getattr(routing_decision, "intent_category", "")),
                            "content_preview": request.content[:100],
                        },
                    })

                    # Wait for approval (timeout 120s)
                    try:
                        await _aio.wait_for(approval_event.wait(), timeout=120)
                        result = self._approval_results.pop(approval_id, "approve")
                        self._pending_approvals.pop(approval_id, None)
                        if result == "reject":
                            await _emit("PIPELINE_COMPLETE", {
                                "content": "操作已被拒絕。",
                                "mode": _enum_val(pipeline_context.get("execution_mode")),
                            })
                            return self._build_short_circuit_response(
                                HandlerResult(
                                    success=True,
                                    handler_type=HandlerType.APPROVAL,
                                    data={"content": "操作已被用戶拒絕。"},
                                    should_short_circuit=True,
                                    short_circuit_response={"content": "操作已被用戶拒絕。"},
                                ),
                                session, start_time, handler_results,
                                framework="hitl_approval",
                                mode=pipeline_context.get("execution_mode", ExecutionMode.CHAT_MODE),
                                pipeline_context=pipeline_context,
                            )
                        logger.info("HITL: approval granted for %s", approval_id)
                    except _aio.TimeoutError:
                        self._pending_approvals.pop(approval_id, None)
                        logger.warning("HITL: approval timeout for %s", approval_id)

            # Step 5: Agent (LLM response generation)
            await _emit("AGENT_THINKING", {"status": "thinking"})
            agent_result = await self._run_handler(
                HandlerType.AGENT, request, pipeline_context
            )
            if agent_result:
                handler_results["agent"] = agent_result
                pipeline_context["agent_response"] = agent_result.data

                # Sprint 145: Emit tool calls if any
                agent_data = agent_result.data or {}
                tool_calls = agent_data.get("tool_calls", [])
                for tc in tool_calls:
                    await _emit("TOOL_CALL_END", {
                        "tool_name": tc.get("tool_name", ""),
                        "result": tc.get("result"),
                        "iteration": tc.get("iteration", 0),
                    })

                if agent_result.should_short_circuit:
                    # Phase 41: Write conversation to memory before short-circuit return
                    try:
                        memory_mgr = pipeline_context.get("memory_manager")
                        response_content = agent_result.data.get("content", "") if agent_result.data else ""
                        if memory_mgr and hasattr(memory_mgr, "_write_to_longterm") and response_content and request.content:
                            conversation = f"User: {request.content}\nAssistant: {response_content[:500]}"
                            await memory_mgr._write_to_longterm(
                                content=conversation,
                                user_id=request.user_id or session.get("user_id", "system"),
                                metadata={
                                    "session_id": session.get("session_id", ""),
                                    "source": "auto_conversation",
                                    "intent": pipeline_context.get("intent_category", ""),
                                },
                            )
                    except Exception as mem_err:
                        logger.warning(f"Memory write failed (non-critical): {mem_err}")

                    # Phase 41: Update session conversation history for short-circuit path
                    response_content = agent_result.data.get("content", "") if agent_result.data else ""
                    history = session.setdefault("conversation_history", [])
                    history.append({"role": "user", "content": request.content, "timestamp": time.time()})
                    if response_content:
                        history.append({"role": "assistant", "content": response_content, "timestamp": time.time()})

                    # Sprint 145: Emit complete before short-circuit return
                    sc_content = agent_result.data.get("content", "") if agent_result.data else ""
                    await _emit("TEXT_DELTA", {"delta": sc_content})
                    await _emit("PIPELINE_COMPLETE", {
                        "content": sc_content,
                        "mode": _enum_val(pipeline_context.get("execution_mode")),
                        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
                    })

                    # Agent produced a direct response — skip execution dispatch
                    return self._build_short_circuit_response(
                        agent_result, session, start_time, handler_results,
                        framework=agent_result.data.get(
                            "framework_used",
                            agent_result.short_circuit_response.get(
                                "framework_used", "orchestrator_agent"
                            ) if agent_result.short_circuit_response else "orchestrator_agent",
                        ),
                        mode=pipeline_context.get(
                            "execution_mode", ExecutionMode.CHAT_MODE
                        ),
                        pipeline_context=pipeline_context,
                    )

            await _save_checkpoint("agent", 5)

            # Step 6: Execution
            await _emit("TASK_DISPATCHED", {
                "mode": _enum_val(pipeline_context.get("execution_mode")),
                "description": request.content[:100],
            })
            exec_result = await self._run_handler(
                HandlerType.EXECUTION, request, pipeline_context
            )
            if exec_result:
                handler_results["execution"] = exec_result

                # Update pipeline context for observability
                exec_data = exec_result.data or {}
                pipeline_context["framework_used"] = exec_data.get(
                    "framework_used", ""
                )
                pipeline_context["execution_success"] = exec_result.success
                pipeline_context["execution_duration"] = time.time() - start_time

            # Step 7: Context sync after execution
            context_handler = self._handlers.get(HandlerType.CONTEXT)
            if context_handler and hasattr(context_handler, "sync_after_execution"):
                hybrid_ctx = pipeline_context.get("hybrid_context")
                if exec_result and hybrid_ctx:
                    # Build a temporary result for sync
                    sync_result = await context_handler.sync_after_execution(
                        exec_result, hybrid_ctx
                    )
                    pipeline_context["sync_result"] = sync_result

            # Step 8: Observability
            obs_result = await self._run_handler(
                HandlerType.OBSERVABILITY, request, pipeline_context
            )
            if obs_result:
                handler_results["observability"] = obs_result

            # Step 9: Write conversation to memory (Phase 41)
            try:
                memory_mgr = pipeline_context.get("memory_manager")
                if memory_mgr and hasattr(memory_mgr, "_write_to_longterm"):
                    # Get response content
                    response_content = ""
                    if exec_result and exec_result.data:
                        response_content = exec_result.data.get("content", "")
                    elif agent_result and agent_result.data:
                        response_content = agent_result.data.get("content", "")

                    if response_content and request.content:
                        conversation = (
                            f"User: {request.content}\n"
                            f"Assistant: {response_content[:500]}"
                        )
                        await memory_mgr._write_to_longterm(
                            content=conversation,
                            user_id=request.user_id or session.get("user_id", "system"),
                            metadata={
                                "session_id": session.get("session_id", ""),
                                "source": "auto_conversation",
                                "intent": pipeline_context.get("intent_category", ""),
                            },
                        )
                        logger.info("Memory: conversation written to long-term memory")
            except Exception as mem_err:
                logger.warning(f"Memory write failed (non-critical): {mem_err}")

            # Update session
            self._update_session_after_execution(
                session, request, exec_result, pipeline_context
            )

            # Sprint 145: Emit final response
            final_resp = self._build_response(
                exec_result, session, pipeline_context, start_time, handler_results
            )
            await _emit("TEXT_DELTA", {"delta": final_resp.content})
            await _emit("PIPELINE_COMPLETE", {
                "content": final_resp.content,
                "mode": str(pipeline_context.get("execution_mode", "")),
                "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            })

            return final_resp

        except Exception as e:
            logger.error(f"Mediator pipeline error: {e}", exc_info=True)
            return OrchestratorResponse(
                success=False,
                error=str(e),
                session_id=session["session_id"],
                execution_mode=pipeline_context.get(
                    "execution_mode", ExecutionMode.CHAT_MODE
                ),
                duration=time.time() - start_time,
                handler_results=handler_results,
            )

    # =========================================================================
    # Metrics Delegation
    # =========================================================================

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from observability handler."""
        obs = self._handlers.get(HandlerType.OBSERVABILITY)
        if obs and hasattr(obs, "get_metrics"):
            return obs.get_metrics()
        return {}

    def reset_metrics(self) -> None:
        """Reset metrics via observability handler."""
        obs = self._handlers.get(HandlerType.OBSERVABILITY)
        if obs and hasattr(obs, "reset_metrics"):
            obs.reset_metrics()

    # =========================================================================
    # Tool Execution
    # =========================================================================

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        source: ToolSource = ToolSource.HYBRID,
        session_id: Optional[str] = None,
        approval_required: bool = False,
        unified_executor: Optional[UnifiedToolExecutor] = None,
    ) -> ToolExecutionResult:
        """Execute a tool through unified executor."""
        if not unified_executor:
            return ToolExecutionResult(
                success=False,
                error="UnifiedToolExecutor not configured",
                tool_name=tool_name,
                source=source,
            )

        context = None
        if session_id:
            session = self._sessions.get(session_id)
            if session:
                context = session.get("hybrid_context")

        return await unified_executor.execute(
            tool_name=tool_name,
            arguments=arguments,
            source=source,
            context=context,
            approval_required=approval_required,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _run_handler(
        self,
        handler_type: HandlerType,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> Optional[HandlerResult]:
        """Run a handler if registered and applicable."""
        handler = self._handlers.get(handler_type)
        if not handler:
            return None
        if not handler.can_handle(request, context):
            return None
        return await handler.handle(request, context)

    def _get_or_create_session(
        self, request: OrchestratorRequest
    ) -> Dict[str, Any]:
        """Get existing session or create new one.

        Sprint 147: Tries ConversationStateStore first for persistence,
        falls back to in-memory dict.
        """
        sid = request.session_id

        # Check in-memory cache first
        if sid and sid in self._sessions:
            return self._sessions[sid]

        # Sprint 147: Try loading from persistent store
        if sid and self._conversation_store:
            try:
                stored = self._conversation_store.load(sid)
                if stored:
                    session = {
                        "session_id": sid,
                        "conversation_history": getattr(stored, "messages", []),
                        "current_mode": ExecutionMode.CHAT_MODE,
                        "metadata": getattr(stored, "context", {}),
                        "last_activity": time.time(),
                    }
                    self._sessions[sid] = session
                    logger.info("Mediator: restored session '%s' from store", sid)
                    return session
            except Exception as e:
                logger.debug("Mediator: store load failed for '%s': %s", sid, e)

        new_sid = self.create_session(sid, request.metadata)
        return self._sessions[new_sid]

    def _update_session_after_execution(
        self,
        session: Dict[str, Any],
        request: OrchestratorRequest,
        exec_result: Optional[HandlerResult],
        context: Dict[str, Any],
    ) -> None:
        """Update session state after execution.

        Sprint 147: Persists to ConversationStateStore after each execution.
        """
        intent = context.get("intent_analysis")
        if intent:
            session["current_mode"] = intent.mode

        history = session.setdefault("conversation_history", [])
        history.append({
            "role": "user",
            "content": request.content,
            "timestamp": time.time(),
        })

        response_content = ""
        if exec_result and exec_result.data:
            response_content = exec_result.data.get("content", "")
            history.append({
                "role": "assistant",
                "content": response_content,
                "mode": str(context.get("execution_mode", "")),
                "framework": exec_result.data.get("framework_used", ""),
                "timestamp": time.time(),
            })

        # Sprint 147: Persist to store
        if self._conversation_store:
            try:
                self._conversation_store.save(
                    session_id=session["session_id"],
                    messages=history,
                    routing_decision=context.get("routing_decision"),
                    context=session.get("metadata", {}),
                )
            except Exception as e:
                logger.debug("Mediator: session persist failed: %s", e)

    def _build_response(
        self,
        exec_result: Optional[HandlerResult],
        session: Dict[str, Any],
        context: Dict[str, Any],
        start_time: float,
        handler_results: Dict[str, HandlerResult],
    ) -> OrchestratorResponse:
        """Build final response from execution result."""
        exec_data = (exec_result.data if exec_result else {}) or {}

        # Sprint 144: Use pipeline_context execution_mode (set by RoutingHandler)
        mode = context.get("execution_mode", ExecutionMode.CHAT_MODE)
        if isinstance(mode, str):
            try:
                mode = ExecutionMode(mode) if mode else ExecutionMode.CHAT_MODE
            except ValueError:
                mode = ExecutionMode.CHAT_MODE

        # Sprint 144: If ExecutionHandler returned empty content, fall back to
        # AgentHandler response (common when WORKFLOW/SWARM dispatch is not
        # yet fully connected).
        content = exec_data.get("content", "")
        if not content:
            agent_resp = context.get("agent_response") or {}
            if isinstance(agent_resp, dict):
                content = agent_resp.get("content", "")

        # Sprint 144: Collect tool_calls from agent_response
        agent_resp = context.get("agent_response") or {}
        agent_tool_calls = (
            agent_resp.get("tool_calls") if isinstance(agent_resp, dict) else None
        )

        return OrchestratorResponse(
            success=exec_result.success if exec_result else (bool(content)),
            content=content,
            error=exec_data.get("error"),
            framework_used=exec_data.get("framework_used", ""),
            execution_mode=mode,
            session_id=session["session_id"],
            intent_analysis=context.get("intent_analysis"),
            tool_results=exec_data.get("tool_results", []),
            sync_result=context.get("sync_result"),
            duration=time.time() - start_time,
            tokens_used=exec_data.get("tokens_used", 0),
            metadata={
                **exec_data.get("metadata", {}),
                "execution_mode": mode,
                "suggested_mode": context.get("suggested_mode"),
                "agent_response": {"tool_calls": agent_tool_calls}
                if agent_tool_calls
                else {},
                "routing_decision": (
                    context["routing_decision"].to_dict()
                    if context.get("routing_decision")
                    and hasattr(context.get("routing_decision"), "to_dict")
                    else None
                ),
                "risk_assessment": (
                    context["risk_assessment"].to_dict()
                    if context.get("risk_assessment")
                    and hasattr(context.get("risk_assessment"), "to_dict")
                    else None
                ),
                "phase_28_flow": bool(context.get("routing_decision")),
            },
            handler_results=handler_results,
        )

    def _build_short_circuit_response(
        self,
        result: HandlerResult,
        session: Dict[str, Any],
        start_time: float,
        handler_results: Dict[str, HandlerResult],
        framework: str,
        mode: ExecutionMode,
        pipeline_context: Optional[Dict[str, Any]] = None,
    ) -> OrchestratorResponse:
        """Build response for short-circuit (dialog/approval pending)."""
        sc = result.short_circuit_response or {}
        ctx = pipeline_context or {}

        # Include routing/risk metadata from pipeline context
        meta = {k: v for k, v in sc.items() if k not in ("content", "error")}
        rd = ctx.get("routing_decision")
        if rd and hasattr(rd, "to_dict"):
            meta["routing_decision"] = rd.to_dict()
        elif rd and isinstance(rd, dict):
            meta["routing_decision"] = rd
        ra = ctx.get("risk_assessment")
        if ra and hasattr(ra, "to_dict"):
            meta["risk_assessment"] = ra.to_dict()

        return OrchestratorResponse(
            success=result.success,
            content=sc.get("content", ""),
            error=sc.get("error"),
            framework_used=framework,
            execution_mode=mode,
            session_id=session["session_id"],
            duration=time.time() - start_time,
            metadata=meta,
            handler_results=handler_results,
        )

    def _build_error_response(
        self,
        result: HandlerResult,
        session: Dict[str, Any],
        start_time: float,
        handler_results: Dict[str, HandlerResult],
    ) -> OrchestratorResponse:
        """Build error response."""
        return OrchestratorResponse(
            success=False,
            error=result.error or "Handler failed",
            session_id=session["session_id"],
            duration=time.time() - start_time,
            handler_results=handler_results,
        )

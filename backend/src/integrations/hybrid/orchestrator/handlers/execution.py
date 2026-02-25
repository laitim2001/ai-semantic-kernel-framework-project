# =============================================================================
# IPA Platform - Execution Handler
# =============================================================================
# Sprint 132: Encapsulates MAF/Claude/Swarm execution logic extracted from
#   HybridOrchestratorV2._execute_workflow_mode(), _execute_chat_mode(),
#   _execute_hybrid_mode().
# =============================================================================

import asyncio
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from src.integrations.hybrid.intent import ExecutionMode, IntentAnalysis
from src.integrations.hybrid.execution import (
    MAFToolCallback,
    ToolExecutionResult,
    ToolSource,
)
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 300.0


class ExecutionHandler(Handler):
    """Handles framework execution dispatch.

    Encapsulates:
    - MAF-led execution (WORKFLOW_MODE)
    - Claude-led execution (CHAT_MODE)
    - Hybrid dynamic switching (HYBRID_MODE)
    - Swarm multi-agent execution (SWARM_MODE)
    """

    def __init__(
        self,
        *,
        claude_executor: Optional[Callable] = None,
        maf_executor: Optional[Callable] = None,
        maf_callback: Optional[MAFToolCallback] = None,
        swarm_handler: Optional[Any] = None,
        default_timeout: float = DEFAULT_TIMEOUT,
    ):
        self._claude_executor = claude_executor
        self._maf_executor = maf_executor
        self._maf_callback = maf_callback
        self._swarm_handler = swarm_handler
        self._default_timeout = default_timeout

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.EXECUTION

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Dispatch execution to the appropriate framework."""
        try:
            # Check for swarm mode first
            swarm_decomposition = context.get("swarm_decomposition")
            if swarm_decomposition and self._swarm_handler:
                return await self._execute_swarm(request, context, swarm_decomposition)

            intent = context.get("intent_analysis")
            mode = context.get("execution_mode", ExecutionMode.CHAT_MODE)
            if isinstance(mode, str):
                mode = ExecutionMode(mode)

            if mode == ExecutionMode.WORKFLOW_MODE:
                return await self._execute_workflow(request, context, intent)
            elif mode == ExecutionMode.HYBRID_MODE:
                return await self._execute_hybrid(request, context, intent)
            else:
                return await self._execute_chat(request, context, intent)

        except asyncio.TimeoutError:
            timeout = request.timeout or self._default_timeout
            return HandlerResult(
                success=False,
                handler_type=HandlerType.EXECUTION,
                error=f"Execution timed out after {timeout}s",
                data={"execution_mode": context.get("execution_mode", "unknown")},
            )
        except Exception as e:
            logger.error(f"ExecutionHandler error: {e}", exc_info=True)
            return HandlerResult(
                success=False,
                handler_type=HandlerType.EXECUTION,
                error=str(e),
            )

    async def _execute_workflow(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
        intent: Optional[IntentAnalysis],
    ) -> HandlerResult:
        """Execute in WORKFLOW_MODE (MAF-led with Claude fallback)."""
        logger.info(f"ExecutionHandler: WORKFLOW_MODE — {request.content[:50]}...")
        timeout = request.timeout or self._default_timeout
        history = context.get("conversation_history", [])

        if self._maf_executor:
            raw_result = await asyncio.wait_for(
                self._maf_executor(
                    prompt=request.content,
                    history=history,
                    tools=request.tools,
                    max_tokens=request.max_tokens,
                    tool_callback=self._maf_callback,
                ),
                timeout=timeout,
            )
            return self._build_result(
                raw_result, "microsoft_agent_framework", ExecutionMode.WORKFLOW_MODE
            )

        if self._claude_executor:
            logger.info("MAF not available, using Claude fallback for workflow")
            raw_result = await asyncio.wait_for(
                self._claude_executor(
                    prompt=request.content,
                    history=history,
                    tools=request.tools,
                    max_tokens=request.max_tokens,
                ),
                timeout=timeout,
            )
            return self._build_result(
                raw_result, "claude_sdk", ExecutionMode.WORKFLOW_MODE
            )

        # Simulated response
        return HandlerResult(
            success=True,
            handler_type=HandlerType.EXECUTION,
            data={
                "content": f"[WORKFLOW_MODE] Processed: {request.content[:100]}...",
                "framework_used": "microsoft_agent_framework",
                "execution_mode": ExecutionMode.WORKFLOW_MODE,
            },
        )

    async def _execute_chat(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
        intent: Optional[IntentAnalysis],
    ) -> HandlerResult:
        """Execute in CHAT_MODE (Claude-led)."""
        logger.info(f"ExecutionHandler: CHAT_MODE — {request.content[:50]}...")
        timeout = request.timeout or self._default_timeout
        history = context.get("conversation_history", [])

        if self._claude_executor:
            executor_kwargs: Dict[str, Any] = {
                "prompt": request.content,
                "history": history,
                "tools": request.tools,
                "max_tokens": request.max_tokens,
            }
            # S75-5: multimodal support
            multimodal_content = (context.get("metadata") or {}).get("multimodal_content")
            if multimodal_content:
                executor_kwargs["multimodal_content"] = multimodal_content

            raw_result = await asyncio.wait_for(
                self._claude_executor(**executor_kwargs),
                timeout=timeout,
            )
            return self._build_result(
                raw_result, "claude_sdk", ExecutionMode.CHAT_MODE
            )

        # Simulated response
        return HandlerResult(
            success=True,
            handler_type=HandlerType.EXECUTION,
            data={
                "content": f"[CHAT_MODE] Processed: {request.content[:100]}...",
                "framework_used": "claude_sdk",
                "execution_mode": ExecutionMode.CHAT_MODE,
            },
        )

    async def _execute_hybrid(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
        intent: Optional[IntentAnalysis],
    ) -> HandlerResult:
        """Execute in HYBRID_MODE (dynamic dispatch)."""
        logger.info(f"ExecutionHandler: HYBRID_MODE — {request.content[:50]}...")

        use_maf = False
        if intent and intent.suggested_framework:
            use_maf = intent.suggested_framework.maf_confidence > 0.7

        if use_maf:
            result = await self._execute_workflow(request, context, intent)
        else:
            result = await self._execute_chat(request, context, intent)

        # Override mode to HYBRID
        if result.data.get("execution_mode"):
            result.data["execution_mode"] = ExecutionMode.HYBRID_MODE
        return result

    async def _execute_swarm(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
        decomposition: Any,
    ) -> HandlerResult:
        """Execute in SWARM_MODE (multi-agent)."""
        logger.info(
            f"ExecutionHandler: SWARM_MODE — {len(decomposition.subtasks)} subtasks"
        )
        routing_decision = context.get("routing_decision")

        swarm_result = await self._swarm_handler.execute_swarm(
            intent=request.content,
            decomposition=decomposition,
            routing_decision=routing_decision,
            session_id=request.session_id or "",
            timeout=request.timeout,
        )

        return HandlerResult(
            success=swarm_result.success,
            handler_type=HandlerType.EXECUTION,
            data={
                "content": swarm_result.content,
                "error": swarm_result.error,
                "framework_used": "swarm",
                "execution_mode": ExecutionMode.SWARM_MODE,
                "swarm_id": swarm_result.swarm_id,
                "swarm_mode": decomposition.swarm_mode,
                "worker_count": len(decomposition.subtasks),
                "worker_results": swarm_result.worker_results,
            },
        )

    def _build_result(
        self,
        raw_result: Any,
        framework: str,
        mode: ExecutionMode,
    ) -> HandlerResult:
        """Convert raw executor result to HandlerResult."""
        if isinstance(raw_result, dict):
            tool_results = self._extract_tool_results(raw_result, framework)
            return HandlerResult(
                success=raw_result.get("success", True),
                handler_type=HandlerType.EXECUTION,
                data={
                    "content": raw_result.get("content", ""),
                    "error": raw_result.get("error"),
                    "framework_used": framework,
                    "execution_mode": mode,
                    "tokens_used": raw_result.get("tokens_used", 0),
                    "metadata": raw_result.get("metadata", {}),
                    "tool_results": tool_results,
                },
            )

        return HandlerResult(
            success=True,
            handler_type=HandlerType.EXECUTION,
            data={
                "content": str(raw_result),
                "framework_used": framework,
                "execution_mode": mode,
            },
        )

    @staticmethod
    def _extract_tool_results(
        raw_result: dict, framework: str
    ) -> List[ToolExecutionResult]:
        """Extract tool results from raw executor output."""
        tool_results: List[ToolExecutionResult] = []
        source = ToolSource.CLAUDE if framework == "claude_sdk" else ToolSource.MAF

        for tc in raw_result.get("tool_calls", []):
            if isinstance(tc, dict):
                tool_results.append(
                    ToolExecutionResult(
                        success=True,
                        content="",
                        tool_name=tc.get("name", ""),
                        execution_id=tc.get("id", str(uuid.uuid4())),
                        source=source,
                        metadata={"args": tc.get("args", {})},
                    )
                )
            elif hasattr(tc, "name"):
                tool_results.append(
                    ToolExecutionResult(
                        success=True,
                        content="",
                        tool_name=getattr(tc, "name", ""),
                        execution_id=getattr(tc, "id", str(uuid.uuid4())),
                        source=source,
                        metadata={"args": getattr(tc, "args", {})},
                    )
                )
        return tool_results

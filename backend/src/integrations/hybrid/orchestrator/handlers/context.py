# =============================================================================
# IPA Platform - Context Handler
# =============================================================================
# Sprint 132: Encapsulates ContextBridge sync logic extracted from
#   HybridOrchestratorV2._prepare_hybrid_context() and post-execution sync.
# =============================================================================

import logging
from typing import Any, Dict, Optional

from src.integrations.hybrid.context import ContextBridge, HybridContext, SyncResult
from src.integrations.hybrid.orchestrator.contracts import (
    Handler,
    HandlerResult,
    HandlerType,
    OrchestratorRequest,
)

logger = logging.getLogger(__name__)


class ContextHandler(Handler):
    """Handles cross-framework context synchronization.

    Encapsulates ContextBridge for:
    - Pre-execution: Prepare hybrid context
    - Post-execution: Sync context after execution
    """

    def __init__(
        self,
        *,
        context_bridge: Optional[ContextBridge] = None,
        memory_manager: Optional[Any] = None,
    ):
        self._context_bridge = context_bridge or ContextBridge()
        self._memory_manager = memory_manager  # Sprint 135: auto-memory injection

    @property
    def handler_type(self) -> HandlerType:
        return HandlerType.CONTEXT

    @property
    def context_bridge(self) -> ContextBridge:
        """Get the underlying ContextBridge instance."""
        return self._context_bridge

    async def handle(
        self,
        request: OrchestratorRequest,
        context: Dict[str, Any],
    ) -> HandlerResult:
        """Prepare hybrid context before execution.

        Sprint 135: Also retrieves relevant memories and injects them
        into the pipeline context for the AgentHandler to use.
        """
        try:
            hybrid_context = await self._prepare_context(request.session_id or "")
            context["hybrid_context"] = hybrid_context

            # Sprint 135: Auto-inject relevant memories
            if self._memory_manager:
                try:
                    memories = await self._memory_manager.retrieve_relevant_memories(
                        query=request.content,
                        user_id=request.metadata.get("user_id") if request.metadata else None,
                        limit=5,
                    )
                    if memories:
                        memory_context = self._memory_manager.build_memory_context(memories)
                        context["memory_context"] = memory_context
                        context["retrieved_memories"] = memories
                        logger.info(
                            "ContextHandler: injected %d memories into context",
                            len(memories),
                        )
                except Exception as e:
                    logger.warning("ContextHandler: memory injection failed: %s", e)

            return HandlerResult(
                success=True,
                handler_type=HandlerType.CONTEXT,
                data={"hybrid_context": hybrid_context},
            )
        except Exception as e:
            logger.warning(f"ContextHandler: Failed to prepare context: {e}")
            return HandlerResult(
                success=True,
                handler_type=HandlerType.CONTEXT,
                data={"hybrid_context": None, "warning": str(e)},
            )

    async def sync_after_execution(
        self,
        result: Any,
        hybrid_context: Optional[HybridContext],
    ) -> Optional[SyncResult]:
        """Sync context after execution completes."""
        if not hybrid_context:
            return None

        try:
            return await self._context_bridge.sync_after_execution(
                result, hybrid_context
            )
        except Exception as e:
            logger.warning(f"ContextHandler: Post-execution sync failed: {e}")
            return None

    async def _prepare_context(self, session_id: str) -> Optional[HybridContext]:
        """Create or retrieve hybrid context."""
        try:
            return await self._context_bridge.get_or_create_hybrid(
                session_id=session_id,
            )
        except Exception as e:
            logger.warning(f"ContextHandler: Context preparation failed: {e}")
            return None

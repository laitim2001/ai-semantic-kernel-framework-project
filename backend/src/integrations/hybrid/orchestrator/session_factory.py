"""
Per-Session Orchestrator Factory — creates independent Orchestrator instances per session.

Each session gets its own fully-wired OrchestratorMediator via OrchestratorBootstrap,
sharing the global LLM Pool and Tool Registry.

Sprint 112 — Phase 36 Orchestrator completeness.
Phase 41 — Refactored to use OrchestratorBootstrap for full 7-handler wiring.
"""

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
from src.integrations.llm.protocol import LLMServiceProtocol

logger = logging.getLogger(__name__)


class OrchestratorSessionFactory:
    """Creates and manages per-session Orchestrator instances.

    Every session receives a fully-wired ``OrchestratorMediator`` via
    ``OrchestratorBootstrap.build()`` with all 7 handlers:
    1. ContextHandler (memory read/write)
    2. RoutingHandler (3-tier intent routing + framework selection)
    3. DialogHandler (guided dialog)
    4. ApprovalHandler (risk assessment + HITL)
    5. AgentHandler (LLM response)
    6. ExecutionHandler (MAF/Claude/Swarm dispatch)
    7. ObservabilityHandler (metrics)

    An LRU eviction policy prevents unbounded memory growth.
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        max_sessions: int = 100,
    ) -> None:
        self._llm_service = llm_service
        self._max_sessions = max_sessions
        self._sessions: OrderedDict[str, OrchestratorMediator] = OrderedDict()
        self._created_at: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create(self, session_id: str) -> OrchestratorMediator:
        """Get existing or create new orchestrator for *session_id*."""
        if session_id in self._sessions:
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]

        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()

        mediator = self._create_orchestrator(session_id)
        self._sessions[session_id] = mediator
        self._created_at[session_id] = time.time()
        logger.info(
            "OrchestratorSessionFactory: created fully-wired orchestrator for "
            "session '%s' (active: %d/%d)",
            session_id,
            len(self._sessions),
            self._max_sessions,
        )
        return mediator

    def remove_session(self, session_id: str) -> bool:
        """Remove an orchestrator instance for the given session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._created_at.pop(session_id, None)
            logger.info(
                "OrchestratorSessionFactory: removed session '%s' (active: %d)",
                session_id,
                len(self._sessions),
            )
            return True
        return False

    @property
    def active_count(self) -> int:
        """Return the number of active orchestrator sessions."""
        return len(self._sessions)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_orchestrator(self, session_id: str) -> OrchestratorMediator:
        """Create a fully-wired OrchestratorMediator via OrchestratorBootstrap.

        Uses Bootstrap.build() to wire all 7 handlers with real dependencies:
        ContextHandler, RoutingHandler, DialogHandler, ApprovalHandler,
        AgentHandler, ExecutionHandler, ObservabilityHandler.

        Falls back to minimal AgentHandler-only mediator if Bootstrap fails.
        """
        try:
            from src.integrations.hybrid.orchestrator.bootstrap import (
                OrchestratorBootstrap,
            )

            bootstrap = OrchestratorBootstrap(llm_service=self._llm_service)
            mediator = bootstrap.build()
            logger.info(
                "SessionFactory: full pipeline assembled via Bootstrap for '%s'",
                session_id,
            )
            return mediator

        except Exception as e:
            logger.error(
                "SessionFactory: Bootstrap failed, falling back to minimal "
                "mediator for '%s': %s",
                session_id,
                e,
                exc_info=True,
            )
            # Fallback: minimal mediator with just AgentHandler
            from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler

            agent_handler = AgentHandler(llm_service=self._llm_service)
            return OrchestratorMediator(agent_handler=agent_handler)

    def _evict_oldest(self) -> None:
        """Evict the least-recently-used session to make room."""
        if not self._sessions:
            return
        oldest_id, _ = self._sessions.popitem(last=False)
        self._created_at.pop(oldest_id, None)
        logger.info(
            "OrchestratorSessionFactory: evicted oldest session '%s' "
            "(capacity: %d)",
            oldest_id,
            self._max_sessions,
        )

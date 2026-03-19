"""
Per-Session Orchestrator Factory — creates independent Orchestrator instances per session.

Each session gets its own OrchestratorMediator + AgentHandler instance,
sharing the global LLM Pool and Tool Registry.

Sprint 112 — Phase 36 Orchestrator completeness.
"""

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

from src.integrations.hybrid.orchestrator.agent_handler import AgentHandler
from src.integrations.hybrid.orchestrator.mediator import OrchestratorMediator
from src.integrations.hybrid.orchestrator.tools import OrchestratorToolRegistry
from src.integrations.llm.protocol import LLMServiceProtocol

logger = logging.getLogger(__name__)


class OrchestratorSessionFactory:
    """Creates and manages per-session Orchestrator instances.

    Every session receives its own ``OrchestratorMediator`` (and therefore its
    own ``AgentHandler``), while sharing the global LLM service and tool
    registry.  An LRU eviction policy prevents unbounded memory growth.

    Usage::

        factory = OrchestratorSessionFactory(
            llm_service=llm,
            tool_registry=registry,
        )
        orchestrator = factory.get_or_create("session_123")
        response = await orchestrator.execute(request)
    """

    def __init__(
        self,
        llm_service: Optional[LLMServiceProtocol] = None,
        tool_registry: Optional[OrchestratorToolRegistry] = None,
        max_sessions: int = 100,
    ) -> None:
        self._llm_service = llm_service
        self._tool_registry = tool_registry
        self._max_sessions = max_sessions
        # OrderedDict for LRU eviction: most-recently-used items are moved
        # to the end via ``move_to_end()``.
        self._sessions: OrderedDict[str, OrchestratorMediator] = OrderedDict()
        # Track creation timestamps for diagnostics
        self._created_at: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_or_create(self, session_id: str) -> OrchestratorMediator:
        """Get existing or create new orchestrator for *session_id*.

        Accessing an existing session marks it as recently used so that
        LRU eviction targets stale sessions first.
        """
        if session_id in self._sessions:
            # Mark as recently used
            self._sessions.move_to_end(session_id)
            return self._sessions[session_id]

        if len(self._sessions) >= self._max_sessions:
            self._evict_oldest()

        mediator = self._create_orchestrator(session_id)
        self._sessions[session_id] = mediator
        self._created_at[session_id] = time.time()
        logger.info(
            "OrchestratorSessionFactory: created new orchestrator for session '%s' "
            "(active: %d/%d)",
            session_id,
            len(self._sessions),
            self._max_sessions,
        )
        return mediator

    def remove_session(self, session_id: str) -> bool:
        """Remove an orchestrator instance for the given session.

        Returns ``True`` if the session existed and was removed.
        """
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
        """Create a fresh OrchestratorMediator with AgentHandler."""
        agent_handler = AgentHandler(
            llm_service=self._llm_service,
            tool_registry=self._tool_registry,
        )
        mediator = OrchestratorMediator(agent_handler=agent_handler)
        return mediator

    def _evict_oldest(self) -> None:
        """Evict the least-recently-used session to make room."""
        if not self._sessions:
            return
        # OrderedDict.popitem(last=False) removes the oldest entry
        oldest_id, _ = self._sessions.popitem(last=False)
        self._created_at.pop(oldest_id, None)
        logger.info(
            "OrchestratorSessionFactory: evicted oldest session '%s' "
            "(capacity: %d)",
            oldest_id,
            self._max_sessions,
        )

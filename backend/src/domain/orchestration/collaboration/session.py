# =============================================================================
# IPA Platform - Collaboration Session Manager
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Manages collaboration sessions between multiple agents.
# Supports session lifecycle:
#   - DISCOVERY: Finding participants
#   - NEGOTIATION: Agreeing on terms
#   - ACTIVE: Active collaboration
#   - COMPLETED: Successfully finished
#   - FAILED: Session failed
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class SessionPhase(str, Enum):
    """
    Phases of a collaboration session.

    Phases:
        DISCOVERY: Finding and inviting participants
        NEGOTIATION: Negotiating collaboration terms
        ACTIVE: Actively collaborating
        COMPLETING: Wrapping up collaboration
        COMPLETED: Session completed successfully
        FAILED: Session failed
        CANCELLED: Session was cancelled
    """
    DISCOVERY = "discovery"
    NEGOTIATION = "negotiation"
    ACTIVE = "active"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SessionStatus(str, Enum):
    """
    Status of a collaboration session.

    States:
        PENDING: Session created but not started
        OPEN: Session is open and active
        CLOSED: Session is closed
        EXPIRED: Session expired due to timeout
    """
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"


@dataclass
class SessionParticipant:
    """
    Participant in a collaboration session.

    Attributes:
        agent_id: Agent identifier
        role: Role in the session (initiator, participant, observer)
        joined_at: When agent joined
        left_at: When agent left (if left)
        capabilities: Agent capabilities
        is_active: Whether participant is currently active
    """
    agent_id: UUID
    role: str = "participant"
    joined_at: datetime = field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    capabilities: List[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class CollaborationSession:
    """
    Represents a collaboration session between agents.

    Attributes:
        id: Unique session identifier
        initiator_id: ID of agent that started the session
        name: Human-readable session name
        description: Session description
        phase: Current session phase
        status: Session status
        participants: List of participants
        context: Shared session context
        messages: History of messages in session
        max_participants: Maximum allowed participants
        timeout_minutes: Session timeout in minutes
        created_at: When session was created
        started_at: When session started
        completed_at: When session completed
        metadata: Additional session metadata
    """
    id: UUID = field(default_factory=uuid4)
    initiator_id: Optional[UUID] = None
    name: str = ""
    description: str = ""
    phase: SessionPhase = SessionPhase.DISCOVERY
    status: SessionStatus = SessionStatus.PENDING
    participants: List[SessionParticipant] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    max_participants: int = 10
    timeout_minutes: int = 60
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def participant_ids(self) -> List[UUID]:
        """Get list of participant IDs."""
        return [p.agent_id for p in self.participants]

    @property
    def active_participants(self) -> List[SessionParticipant]:
        """Get list of active participants."""
        return [p for p in self.participants if p.is_active]

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.timeout_minutes <= 0:
            return False
        expiry = self.created_at + timedelta(minutes=self.timeout_minutes)
        return datetime.utcnow() > expiry

    @property
    def is_active(self) -> bool:
        """Check if session is currently active."""
        return (
            self.status == SessionStatus.OPEN and
            self.phase in [SessionPhase.DISCOVERY, SessionPhase.NEGOTIATION, SessionPhase.ACTIVE]
        )

    def get_participant(self, agent_id: UUID) -> Optional[SessionParticipant]:
        """Get a participant by agent ID."""
        for p in self.participants:
            if p.agent_id == agent_id:
                return p
        return None


class SessionManager:
    """
    Manages collaboration sessions.

    Provides functionality for:
        - Creating and closing sessions
        - Adding and removing participants
        - Session phase transitions
        - Session context management
        - Session lifecycle events

    Usage:
        manager = SessionManager()

        # Create a session
        session = await manager.create_session(
            initiator_id=agent_id,
            name="Analysis Session",
        )

        # Add participants
        await manager.join_session(session.id, other_agent_id)

        # Start collaboration
        await manager.start_session(session.id)

        # Close when done
        await manager.close_session(session.id, "completed")
    """

    def __init__(self, session_store: Any = None):
        """
        Initialize SessionManager.

        Args:
            session_store: Optional storage for session persistence
        """
        self._session_store = session_store
        self._sessions: Dict[UUID, CollaborationSession] = {}

        # Event handlers
        self._on_session_created: List[Callable] = []
        self._on_session_started: List[Callable] = []
        self._on_session_closed: List[Callable] = []
        self._on_participant_joined: List[Callable] = []
        self._on_participant_left: List[Callable] = []

        logger.info("SessionManager initialized")

    # =========================================================================
    # Session Lifecycle
    # =========================================================================

    async def create_session(
        self,
        initiator_id: UUID,
        name: str = "",
        description: str = "",
        max_participants: int = 10,
        timeout_minutes: int = 60,
        context: Dict[str, Any] = None,
    ) -> CollaborationSession:
        """
        Create a new collaboration session.

        Args:
            initiator_id: ID of initiating agent
            name: Session name
            description: Session description
            max_participants: Maximum participants
            timeout_minutes: Session timeout
            context: Initial session context

        Returns:
            Created session
        """
        session = CollaborationSession(
            initiator_id=initiator_id,
            name=name or f"Session-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            description=description,
            max_participants=max_participants,
            timeout_minutes=timeout_minutes,
            context=context or {},
        )

        # Add initiator as first participant
        initiator_participant = SessionParticipant(
            agent_id=initiator_id,
            role="initiator",
        )
        session.participants.append(initiator_participant)

        self._sessions[session.id] = session

        # Persist if storage available
        if self._session_store:
            await self._session_store.save(session)

        # Notify handlers
        await self._notify_handlers(self._on_session_created, session)

        logger.info(f"Session {session.id} created by agent {initiator_id}")

        return session

    async def start_session(self, session_id: UUID) -> bool:
        """
        Start a collaboration session.

        Args:
            session_id: Session to start

        Returns:
            True if session was started
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot start: session {session_id} not found")
            return False

        if session.status != SessionStatus.PENDING:
            logger.warning(f"Cannot start: session {session_id} not pending")
            return False

        session.status = SessionStatus.OPEN
        session.phase = SessionPhase.ACTIVE
        session.started_at = datetime.utcnow()

        # Notify handlers
        await self._notify_handlers(self._on_session_started, session)

        logger.info(f"Session {session_id} started")
        return True

    async def close_session(
        self,
        session_id: UUID,
        outcome: str = "completed",
        result: Dict[str, Any] = None,
    ) -> bool:
        """
        Close a collaboration session.

        Args:
            session_id: Session to close
            outcome: Outcome reason (completed, failed, cancelled)
            result: Final result data

        Returns:
            True if session was closed
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot close: session {session_id} not found")
            return False

        if session.status == SessionStatus.CLOSED:
            logger.warning(f"Session {session_id} already closed")
            return False

        # Update session
        session.status = SessionStatus.CLOSED
        session.completed_at = datetime.utcnow()

        if outcome == "completed":
            session.phase = SessionPhase.COMPLETED
        elif outcome == "failed":
            session.phase = SessionPhase.FAILED
        else:
            session.phase = SessionPhase.CANCELLED

        session.context["outcome"] = outcome
        if result:
            session.context["result"] = result

        # Mark all participants as inactive
        for participant in session.participants:
            if participant.is_active:
                participant.is_active = False
                participant.left_at = datetime.utcnow()

        # Notify handlers
        await self._notify_handlers(self._on_session_closed, session)

        logger.info(f"Session {session_id} closed with outcome: {outcome}")
        return True

    # =========================================================================
    # Participant Management
    # =========================================================================

    async def join_session(
        self,
        session_id: UUID,
        agent_id: UUID,
        role: str = "participant",
        capabilities: List[str] = None,
    ) -> bool:
        """
        Add an agent to a session.

        Args:
            session_id: Session to join
            agent_id: Agent joining
            role: Role in session
            capabilities: Agent capabilities

        Returns:
            True if agent joined successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot join: session {session_id} not found")
            return False

        if not session.is_active:
            logger.warning(f"Cannot join: session {session_id} not active")
            return False

        if len(session.active_participants) >= session.max_participants:
            logger.warning(f"Cannot join: session {session_id} is full")
            return False

        # Check if already participating
        if session.get_participant(agent_id):
            logger.warning(f"Agent {agent_id} already in session {session_id}")
            return False

        participant = SessionParticipant(
            agent_id=agent_id,
            role=role,
            capabilities=capabilities or [],
        )
        session.participants.append(participant)

        # Notify handlers
        await self._notify_handlers(
            self._on_participant_joined,
            session,
            participant,
        )

        logger.info(f"Agent {agent_id} joined session {session_id}")
        return True

    async def leave_session(
        self,
        session_id: UUID,
        agent_id: UUID,
        reason: str = "",
    ) -> bool:
        """
        Remove an agent from a session.

        Args:
            session_id: Session to leave
            agent_id: Agent leaving
            reason: Reason for leaving

        Returns:
            True if agent left successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Cannot leave: session {session_id} not found")
            return False

        participant = session.get_participant(agent_id)
        if not participant:
            logger.warning(f"Agent {agent_id} not in session {session_id}")
            return False

        if not participant.is_active:
            logger.warning(f"Agent {agent_id} already left session {session_id}")
            return False

        participant.is_active = False
        participant.left_at = datetime.utcnow()

        # Notify handlers
        await self._notify_handlers(
            self._on_participant_left,
            session,
            participant,
            reason,
        )

        logger.info(f"Agent {agent_id} left session {session_id}: {reason}")
        return True

    def get_participants(
        self,
        session_id: UUID,
        active_only: bool = True,
    ) -> List[SessionParticipant]:
        """
        Get participants of a session.

        Args:
            session_id: Session to get participants for
            active_only: Only return active participants

        Returns:
            List of participants
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        if active_only:
            return session.active_participants
        return session.participants.copy()

    # =========================================================================
    # Session Access
    # =========================================================================

    def get_session(self, session_id: UUID) -> Optional[CollaborationSession]:
        """
        Get a session by ID.

        Args:
            session_id: Session to retrieve

        Returns:
            Session if found, None otherwise
        """
        return self._sessions.get(session_id)

    def get_agent_sessions(
        self,
        agent_id: UUID,
        active_only: bool = True,
    ) -> List[CollaborationSession]:
        """
        Get all sessions an agent is participating in.

        Args:
            agent_id: Agent to find sessions for
            active_only: Only return active sessions

        Returns:
            List of sessions
        """
        sessions = []
        for session in self._sessions.values():
            participant = session.get_participant(agent_id)
            if participant:
                if not active_only or (participant.is_active and session.is_active):
                    sessions.append(session)
        return sessions

    def get_active_sessions(self) -> List[CollaborationSession]:
        """Get all active sessions."""
        return [s for s in self._sessions.values() if s.is_active]

    # =========================================================================
    # Context Management
    # =========================================================================

    async def update_context(
        self,
        session_id: UUID,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update session context.

        Args:
            session_id: Session to update
            updates: Context updates to apply

        Returns:
            True if context was updated
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.context.update(updates)
        return True

    async def set_context_value(
        self,
        session_id: UUID,
        key: str,
        value: Any,
    ) -> bool:
        """
        Set a specific context value.

        Args:
            session_id: Session to update
            key: Context key
            value: Value to set

        Returns:
            True if value was set
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        session.context[key] = value
        return True

    def get_context(
        self,
        session_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get session context.

        Args:
            session_id: Session to get context for

        Returns:
            Session context or empty dict
        """
        session = self._sessions.get(session_id)
        return session.context.copy() if session else {}

    # =========================================================================
    # Phase Management
    # =========================================================================

    async def transition_phase(
        self,
        session_id: UUID,
        new_phase: SessionPhase,
    ) -> bool:
        """
        Transition session to a new phase.

        Args:
            session_id: Session to transition
            new_phase: New phase

        Returns:
            True if transition was successful
        """
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Validate transition
        valid_transitions = {
            SessionPhase.DISCOVERY: [SessionPhase.NEGOTIATION, SessionPhase.ACTIVE, SessionPhase.CANCELLED],
            SessionPhase.NEGOTIATION: [SessionPhase.ACTIVE, SessionPhase.CANCELLED, SessionPhase.FAILED],
            SessionPhase.ACTIVE: [SessionPhase.COMPLETING, SessionPhase.COMPLETED, SessionPhase.FAILED, SessionPhase.CANCELLED],
            SessionPhase.COMPLETING: [SessionPhase.COMPLETED, SessionPhase.FAILED],
        }

        allowed = valid_transitions.get(session.phase, [])
        if new_phase not in allowed:
            logger.warning(
                f"Invalid phase transition: {session.phase.value} -> {new_phase.value}"
            )
            return False

        old_phase = session.phase
        session.phase = new_phase

        logger.info(
            f"Session {session_id} phase transition: "
            f"{old_phase.value} -> {new_phase.value}"
        )
        return True

    # =========================================================================
    # Cleanup
    # =========================================================================

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        expired = []
        for session_id, session in self._sessions.items():
            if session.is_expired and session.status != SessionStatus.CLOSED:
                expired.append(session_id)

        for session_id in expired:
            await self.close_session(session_id, "expired")
            self._sessions[session_id].status = SessionStatus.EXPIRED

        logger.info(f"Cleaned up {len(expired)} expired sessions")
        return len(expired)

    def remove_session(self, session_id: UUID) -> bool:
        """
        Remove a session from memory.

        Args:
            session_id: Session to remove

        Returns:
            True if session was removed
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    @property
    def session_count(self) -> int:
        """Get total number of sessions."""
        return len(self._sessions)

    @property
    def active_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self.get_active_sessions())

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on_session_created(self, handler: Callable) -> None:
        """Register handler for session created event."""
        self._on_session_created.append(handler)

    def on_session_started(self, handler: Callable) -> None:
        """Register handler for session started event."""
        self._on_session_started.append(handler)

    def on_session_closed(self, handler: Callable) -> None:
        """Register handler for session closed event."""
        self._on_session_closed.append(handler)

    def on_participant_joined(self, handler: Callable) -> None:
        """Register handler for participant joined event."""
        self._on_participant_joined.append(handler)

    def on_participant_left(self, handler: Callable) -> None:
        """Register handler for participant left event."""
        self._on_participant_left.append(handler)

    async def _notify_handlers(
        self,
        handlers: List[Callable],
        *args,
    ) -> None:
        """Notify all registered handlers."""
        import asyncio
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args)
                else:
                    handler(*args)
            except Exception as e:
                logger.error(f"Handler error: {e}", exc_info=True)

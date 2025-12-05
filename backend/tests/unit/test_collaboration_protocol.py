# =============================================================================
# IPA Platform - Collaboration Protocol Unit Tests
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Tests for collaboration protocol including:
#   - MessageType enumeration
#   - CollaborationMessage data structure
#   - CollaborationProtocol messaging
#   - SessionPhase enumeration
#   - CollaborationSession data structure
#   - SessionManager lifecycle
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.domain.orchestration.collaboration.protocol import (
    CollaborationMessage,
    CollaborationProtocol,
    MessagePriority,
    MessageStatus,
    MessageType,
)
from src.domain.orchestration.collaboration.session import (
    CollaborationSession,
    SessionManager,
    SessionParticipant,
    SessionPhase,
    SessionStatus,
)


# =============================================================================
# MessageType Tests
# =============================================================================


class TestMessageType:
    """Tests for MessageType enum."""

    def test_type_values(self):
        """Test all type enum values."""
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.BROADCAST.value == "broadcast"
        assert MessageType.NEGOTIATE.value == "negotiate"
        assert MessageType.ACKNOWLEDGE.value == "acknowledge"
        assert MessageType.REJECT.value == "reject"

    def test_type_from_string(self):
        """Test creating type from string."""
        assert MessageType("request") == MessageType.REQUEST
        assert MessageType("broadcast") == MessageType.BROADCAST


# =============================================================================
# CollaborationMessage Tests
# =============================================================================


class TestCollaborationMessage:
    """Tests for CollaborationMessage dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        message = CollaborationMessage()

        assert message.id is not None
        assert message.message_type == MessageType.REQUEST
        assert message.status == MessageStatus.PENDING
        assert message.priority == MessagePriority.NORMAL.value
        assert message.ttl == 60
        assert isinstance(message.created_at, datetime)

    def test_initialization_with_fields(self):
        """Test initialization with all fields."""
        sender = uuid4()
        recipient = uuid4()

        message = CollaborationMessage(
            message_type=MessageType.BROADCAST,
            sender_id=sender,
            recipient_id=recipient,
            content={"action": "notify"},
            priority=MessagePriority.HIGH.value,
        )

        assert message.sender_id == sender
        assert message.recipient_id == recipient
        assert message.content == {"action": "notify"}
        assert message.priority == MessagePriority.HIGH.value

    def test_is_broadcast(self):
        """Test broadcast detection."""
        broadcast = CollaborationMessage(recipient_id=None)
        direct = CollaborationMessage(recipient_id=uuid4())

        assert broadcast.is_broadcast is True
        assert direct.is_broadcast is False

    def test_is_expired(self):
        """Test expiration detection."""
        # Not expired
        fresh = CollaborationMessage(ttl=60)
        assert fresh.is_expired is False

        # Expired
        old_time = datetime.utcnow() - timedelta(seconds=120)
        expired = CollaborationMessage(ttl=60, created_at=old_time)
        assert expired.is_expired is True

        # Never expires
        never = CollaborationMessage(ttl=0)
        assert never.is_expired is False


# =============================================================================
# CollaborationProtocol Tests
# =============================================================================


class TestCollaborationProtocol:
    """Tests for CollaborationProtocol class."""

    @pytest.fixture
    def protocol(self):
        """Create protocol instance."""
        return CollaborationProtocol()

    @pytest.fixture
    def agents(self, protocol):
        """Register test agents."""
        agent1 = uuid4()
        agent2 = uuid4()
        agent3 = uuid4()
        protocol.register_agent(agent1)
        protocol.register_agent(agent2)
        protocol.register_agent(agent3)
        return agent1, agent2, agent3

    # -------------------------------------------------------------------------
    # Agent Registration Tests
    # -------------------------------------------------------------------------

    def test_register_agent(self, protocol):
        """Test agent registration."""
        agent_id = uuid4()
        protocol.register_agent(agent_id)

        assert protocol.is_agent_registered(agent_id)
        assert agent_id in protocol.registered_agents

    def test_unregister_agent(self, protocol, agents):
        """Test agent unregistration."""
        agent1, agent2, _ = agents
        protocol.unregister_agent(agent1)

        assert not protocol.is_agent_registered(agent1)
        assert protocol.is_agent_registered(agent2)

    # -------------------------------------------------------------------------
    # Message Sending Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_message_success(self, protocol, agents):
        """Test sending message successfully."""
        agent1, agent2, _ = agents

        message = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=agent1,
            recipient_id=agent2,
            content={"action": "help"},
        )

        result = await protocol.send_message(message)

        assert result is True
        assert message.status == MessageStatus.SENT
        assert message.sent_at is not None

    @pytest.mark.asyncio
    async def test_send_message_to_unregistered(self, protocol, agents):
        """Test sending to unregistered agent fails."""
        agent1, _, _ = agents
        unregistered = uuid4()

        message = CollaborationMessage(
            sender_id=agent1,
            recipient_id=unregistered,
        )

        result = await protocol.send_message(message)

        assert result is False
        assert message.status == MessageStatus.FAILED

    @pytest.mark.asyncio
    async def test_broadcast_message(self, protocol, agents):
        """Test broadcasting message."""
        agent1, agent2, agent3 = agents

        message = await protocol.broadcast(
            sender_id=agent1,
            content={"announcement": "test"},
        )

        assert message.message_type == MessageType.BROADCAST
        assert message.is_broadcast is True
        assert message.status == MessageStatus.SENT

        # Check queues
        assert protocol.get_queue_size(agent2) == 1
        assert protocol.get_queue_size(agent3) == 1
        assert protocol.get_queue_size(agent1) == 0  # Sender doesn't get it

    # -------------------------------------------------------------------------
    # Request-Response Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_request_timeout(self, protocol, agents):
        """Test request timeout."""
        agent1, agent2, _ = agents

        result = await protocol.send_request(
            sender_id=agent1,
            recipient_id=agent2,
            content={"question": "are you there?"},
            timeout=0.1,
        )

        assert result is None  # Timed out

    @pytest.mark.asyncio
    async def test_send_response(self, protocol, agents):
        """Test sending response to request."""
        agent1, agent2, _ = agents

        request = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=agent1,
            recipient_id=agent2,
            content={"question": "help?"},
        )
        await protocol.send_message(request)

        response = await protocol.send_response(
            request=request,
            content={"answer": "yes"},
            accepted=True,
        )

        assert response.message_type == MessageType.RESPONSE
        assert response.correlation_id == request.id
        assert response.sender_id == agent2
        assert response.recipient_id == agent1

    @pytest.mark.asyncio
    async def test_send_response_rejected(self, protocol, agents):
        """Test sending rejection response."""
        agent1, agent2, _ = agents

        request = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=agent1,
            recipient_id=agent2,
        )
        await protocol.send_message(request)

        response = await protocol.send_response(
            request=request,
            content={"reason": "busy"},
            accepted=False,
        )

        assert response.message_type == MessageType.REJECT

    # -------------------------------------------------------------------------
    # Negotiation Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_negotiate(self, protocol, agents):
        """Test sending negotiation message."""
        agent1, agent2, _ = agents

        message = await protocol.negotiate(
            sender_id=agent1,
            recipient_id=agent2,
            proposal={"terms": "50/50 split"},
        )

        assert message.message_type == MessageType.NEGOTIATE
        assert message.priority == MessagePriority.HIGH.value
        assert "proposal" in message.content

    @pytest.mark.asyncio
    async def test_counter_propose(self, protocol, agents):
        """Test counter-proposal in negotiation."""
        agent1, agent2, _ = agents

        original = await protocol.negotiate(
            sender_id=agent1,
            recipient_id=agent2,
            proposal={"terms": "50/50"},
        )

        counter = await protocol.counter_propose(
            original=original,
            counter_proposal={"terms": "60/40"},
        )

        assert counter.correlation_id == original.id
        assert "counter_proposal" in counter.content

    # -------------------------------------------------------------------------
    # Message Receiving Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_receive_messages(self, protocol, agents):
        """Test receiving messages."""
        agent1, agent2, _ = agents

        # Send multiple messages
        for i in range(3):
            await protocol.send_message(CollaborationMessage(
                sender_id=agent1,
                recipient_id=agent2,
                content={"index": i},
            ))

        messages = await protocol.receive_messages(agent2, count=10)

        assert len(messages) == 3

    @pytest.mark.asyncio
    async def test_receive_marks_delivered(self, protocol, agents):
        """Test that receiving marks messages as delivered."""
        agent1, agent2, _ = agents

        await protocol.send_message(CollaborationMessage(
            sender_id=agent1,
            recipient_id=agent2,
        ))

        messages = await protocol.receive_messages(agent2, mark_delivered=True)

        assert messages[0].status == MessageStatus.DELIVERED
        assert messages[0].delivered_at is not None

    @pytest.mark.asyncio
    async def test_receive_filters_expired(self, protocol, agents):
        """Test that expired messages are filtered."""
        agent1, agent2, _ = agents

        # Create expired message directly in queue
        expired = CollaborationMessage(
            sender_id=agent1,
            recipient_id=agent2,
            ttl=1,
            created_at=datetime.utcnow() - timedelta(seconds=10),
        )
        protocol._queues[agent2].append(expired)

        messages = await protocol.receive_messages(agent2)

        assert len(messages) == 0

    # -------------------------------------------------------------------------
    # Acknowledgment Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_acknowledge_message(self, protocol, agents):
        """Test acknowledging a message."""
        agent1, agent2, _ = agents

        original = CollaborationMessage(
            sender_id=agent1,
            recipient_id=agent2,
        )
        await protocol.send_message(original)

        ack = await protocol.acknowledge(original)

        assert ack.message_type == MessageType.ACKNOWLEDGE
        assert ack.correlation_id == original.id
        assert original.status == MessageStatus.READ

    # -------------------------------------------------------------------------
    # Queue Management Tests
    # -------------------------------------------------------------------------

    def test_get_queue_size(self, protocol, agents):
        """Test getting queue size."""
        agent1, _, _ = agents
        assert protocol.get_queue_size(agent1) == 0

    @pytest.mark.asyncio
    async def test_clear_queue(self, protocol, agents):
        """Test clearing queue."""
        agent1, agent2, _ = agents

        await protocol.send_message(CollaborationMessage(
            sender_id=agent1,
            recipient_id=agent2,
        ))

        count = protocol.clear_queue(agent2)

        assert count == 1
        assert protocol.get_queue_size(agent2) == 0

    @pytest.mark.asyncio
    async def test_clear_expired(self, protocol, agents):
        """Test clearing expired messages."""
        agent1, agent2, _ = agents

        # Add expired message
        expired = CollaborationMessage(
            sender_id=agent1,
            recipient_id=agent2,
            ttl=1,
            created_at=datetime.utcnow() - timedelta(seconds=10),
        )
        protocol._queues[agent2].append(expired)

        count = protocol.clear_expired()

        assert count == 1

    # -------------------------------------------------------------------------
    # Handler Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_register_handler(self, protocol, agents):
        """Test registering message handler."""
        agent1, agent2, _ = agents
        handled = []

        def handler(msg):
            handled.append(msg)

        protocol.register_handler(MessageType.REQUEST, handler)

        await protocol.send_message(CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=agent1,
            recipient_id=agent2,
        ))

        assert len(handled) == 1

    def test_unregister_handler(self, protocol):
        """Test unregistering handler."""
        handler = lambda msg: None

        protocol.register_handler(MessageType.REQUEST, handler)
        result = protocol.unregister_handler(MessageType.REQUEST, handler)

        assert result is True

    @pytest.mark.asyncio
    async def test_handler_error_handling(self, protocol, agents):
        """Test that handler errors don't break protocol."""
        agent1, agent2, _ = agents

        def bad_handler(msg):
            raise Exception("Handler error")

        protocol.register_handler(MessageType.REQUEST, bad_handler)

        # Should not raise
        await protocol.send_message(CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=agent1,
            recipient_id=agent2,
        ))


# =============================================================================
# SessionPhase Tests
# =============================================================================


class TestSessionPhase:
    """Tests for SessionPhase enum."""

    def test_phase_values(self):
        """Test all phase enum values."""
        assert SessionPhase.DISCOVERY.value == "discovery"
        assert SessionPhase.NEGOTIATION.value == "negotiation"
        assert SessionPhase.ACTIVE.value == "active"
        assert SessionPhase.COMPLETED.value == "completed"
        assert SessionPhase.FAILED.value == "failed"


# =============================================================================
# SessionParticipant Tests
# =============================================================================


class TestSessionParticipant:
    """Tests for SessionParticipant dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        agent_id = uuid4()
        participant = SessionParticipant(agent_id=agent_id)

        assert participant.agent_id == agent_id
        assert participant.role == "participant"
        assert participant.is_active is True
        assert participant.left_at is None


# =============================================================================
# CollaborationSession Tests
# =============================================================================


class TestCollaborationSession:
    """Tests for CollaborationSession dataclass."""

    def test_basic_initialization(self):
        """Test basic initialization."""
        session = CollaborationSession()

        assert session.id is not None
        assert session.phase == SessionPhase.DISCOVERY
        assert session.status == SessionStatus.PENDING
        assert session.participants == []
        assert session.max_participants == 10

    def test_participant_ids(self):
        """Test getting participant IDs."""
        session = CollaborationSession()
        agent1, agent2 = uuid4(), uuid4()

        session.participants = [
            SessionParticipant(agent_id=agent1),
            SessionParticipant(agent_id=agent2),
        ]

        assert agent1 in session.participant_ids
        assert agent2 in session.participant_ids

    def test_active_participants(self):
        """Test getting active participants."""
        session = CollaborationSession()
        agent1, agent2 = uuid4(), uuid4()

        session.participants = [
            SessionParticipant(agent_id=agent1, is_active=True),
            SessionParticipant(agent_id=agent2, is_active=False),
        ]

        active = session.active_participants
        assert len(active) == 1
        assert active[0].agent_id == agent1

    def test_is_expired(self):
        """Test expiration detection."""
        # Not expired
        session = CollaborationSession(timeout_minutes=60)
        assert session.is_expired is False

        # Expired
        old_time = datetime.utcnow() - timedelta(minutes=120)
        expired_session = CollaborationSession(
            timeout_minutes=60,
            created_at=old_time,
        )
        assert expired_session.is_expired is True

    def test_is_active(self):
        """Test active status."""
        session = CollaborationSession(
            status=SessionStatus.OPEN,
            phase=SessionPhase.ACTIVE,
        )
        assert session.is_active is True

        closed = CollaborationSession(status=SessionStatus.CLOSED)
        assert closed.is_active is False


# =============================================================================
# SessionManager Tests
# =============================================================================


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.fixture
    def manager(self):
        """Create manager instance."""
        return SessionManager()

    # -------------------------------------------------------------------------
    # Session Lifecycle Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        """Test creating a session."""
        initiator = uuid4()

        session = await manager.create_session(
            initiator_id=initiator,
            name="Test Session",
            description="A test session",
        )

        assert session.id is not None
        assert session.initiator_id == initiator
        assert session.name == "Test Session"
        assert len(session.participants) == 1  # Initiator
        assert session.participants[0].role == "initiator"

    @pytest.mark.asyncio
    async def test_start_session(self, manager):
        """Test starting a session."""
        session = await manager.create_session(initiator_id=uuid4())

        result = await manager.start_session(session.id)

        assert result is True
        assert session.status == SessionStatus.OPEN
        assert session.phase == SessionPhase.ACTIVE
        assert session.started_at is not None

    @pytest.mark.asyncio
    async def test_start_already_started(self, manager):
        """Test starting already started session fails."""
        session = await manager.create_session(initiator_id=uuid4())
        await manager.start_session(session.id)

        result = await manager.start_session(session.id)

        assert result is False

    @pytest.mark.asyncio
    async def test_close_session(self, manager):
        """Test closing a session."""
        session = await manager.create_session(initiator_id=uuid4())
        await manager.start_session(session.id)

        result = await manager.close_session(session.id, "completed")

        assert result is True
        assert session.status == SessionStatus.CLOSED
        assert session.phase == SessionPhase.COMPLETED
        assert session.completed_at is not None

    @pytest.mark.asyncio
    async def test_close_with_result(self, manager):
        """Test closing session with result."""
        session = await manager.create_session(initiator_id=uuid4())
        await manager.start_session(session.id)

        await manager.close_session(
            session.id,
            "completed",
            result={"output": "success"},
        )

        assert session.context["result"] == {"output": "success"}

    # -------------------------------------------------------------------------
    # Participant Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_join_session(self, manager):
        """Test joining a session."""
        initiator = uuid4()
        joiner = uuid4()

        session = await manager.create_session(initiator_id=initiator)
        await manager.start_session(session.id)

        result = await manager.join_session(
            session.id,
            joiner,
            role="helper",
        )

        assert result is True
        assert len(session.participants) == 2

    @pytest.mark.asyncio
    async def test_join_full_session(self, manager):
        """Test joining full session fails."""
        session = await manager.create_session(
            initiator_id=uuid4(),
            max_participants=1,
        )
        await manager.start_session(session.id)

        result = await manager.join_session(session.id, uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_leave_session(self, manager):
        """Test leaving a session."""
        initiator = uuid4()
        joiner = uuid4()

        session = await manager.create_session(initiator_id=initiator)
        await manager.start_session(session.id)
        await manager.join_session(session.id, joiner)

        result = await manager.leave_session(session.id, joiner, "done")

        assert result is True
        participant = session.get_participant(joiner)
        assert participant.is_active is False
        assert participant.left_at is not None

    @pytest.mark.asyncio
    async def test_get_participants(self, manager):
        """Test getting participants."""
        session = await manager.create_session(initiator_id=uuid4())
        await manager.start_session(session.id)

        for _ in range(3):
            await manager.join_session(session.id, uuid4())

        participants = manager.get_participants(session.id)
        assert len(participants) == 4  # Initiator + 3

    # -------------------------------------------------------------------------
    # Session Access Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_session(self, manager):
        """Test getting a session."""
        session = await manager.create_session(initiator_id=uuid4())

        retrieved = manager.get_session(session.id)

        assert retrieved == session

    @pytest.mark.asyncio
    async def test_get_agent_sessions(self, manager):
        """Test getting sessions for an agent."""
        agent = uuid4()

        await manager.create_session(initiator_id=agent)
        await manager.create_session(initiator_id=agent)

        sessions = manager.get_agent_sessions(agent, active_only=False)

        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, manager):
        """Test getting active sessions."""
        session1 = await manager.create_session(initiator_id=uuid4())
        session2 = await manager.create_session(initiator_id=uuid4())

        await manager.start_session(session1.id)

        active = manager.get_active_sessions()

        assert len(active) == 1
        assert active[0].id == session1.id

    # -------------------------------------------------------------------------
    # Context Management Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_update_context(self, manager):
        """Test updating session context."""
        session = await manager.create_session(initiator_id=uuid4())

        await manager.update_context(session.id, {"key": "value"})

        assert session.context["key"] == "value"

    @pytest.mark.asyncio
    async def test_set_context_value(self, manager):
        """Test setting specific context value."""
        session = await manager.create_session(initiator_id=uuid4())

        await manager.set_context_value(session.id, "count", 42)

        assert session.context["count"] == 42

    @pytest.mark.asyncio
    async def test_get_context(self, manager):
        """Test getting session context."""
        session = await manager.create_session(
            initiator_id=uuid4(),
            context={"initial": "data"},
        )

        context = manager.get_context(session.id)

        assert context["initial"] == "data"

    # -------------------------------------------------------------------------
    # Phase Transition Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_transition_phase(self, manager):
        """Test phase transition."""
        session = await manager.create_session(initiator_id=uuid4())

        result = await manager.transition_phase(
            session.id,
            SessionPhase.NEGOTIATION,
        )

        assert result is True
        assert session.phase == SessionPhase.NEGOTIATION

    @pytest.mark.asyncio
    async def test_invalid_phase_transition(self, manager):
        """Test invalid phase transition fails."""
        session = await manager.create_session(initiator_id=uuid4())
        session.phase = SessionPhase.COMPLETED

        result = await manager.transition_phase(
            session.id,
            SessionPhase.ACTIVE,
        )

        assert result is False

    # -------------------------------------------------------------------------
    # Cleanup Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, manager):
        """Test cleaning up expired sessions."""
        old_time = datetime.utcnow() - timedelta(minutes=120)
        session = await manager.create_session(
            initiator_id=uuid4(),
            timeout_minutes=60,
        )
        session.created_at = old_time
        await manager.start_session(session.id)

        count = await manager.cleanup_expired()

        assert count == 1
        assert session.status == SessionStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_remove_session(self, manager):
        """Test removing a session."""
        session = await manager.create_session(initiator_id=uuid4())

        result = manager.remove_session(session.id)

        assert result is True
        assert manager.session_count == 0

    # -------------------------------------------------------------------------
    # Event Handler Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_on_session_created_handler(self, manager):
        """Test session created handler."""
        events = []
        manager.on_session_created(lambda s: events.append(("created", s)))

        await manager.create_session(initiator_id=uuid4())

        assert len(events) == 1
        assert events[0][0] == "created"

    @pytest.mark.asyncio
    async def test_on_participant_joined_handler(self, manager):
        """Test participant joined handler."""
        events = []
        manager.on_participant_joined(
            lambda s, p: events.append(("joined", s, p))
        )

        session = await manager.create_session(initiator_id=uuid4())
        await manager.start_session(session.id)
        await manager.join_session(session.id, uuid4())

        assert len(events) == 1

    # -------------------------------------------------------------------------
    # Properties Tests
    # -------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_session_count(self, manager):
        """Test session count property."""
        await manager.create_session(initiator_id=uuid4())
        await manager.create_session(initiator_id=uuid4())

        assert manager.session_count == 2

    @pytest.mark.asyncio
    async def test_active_session_count(self, manager):
        """Test active session count."""
        session1 = await manager.create_session(initiator_id=uuid4())
        await manager.create_session(initiator_id=uuid4())

        await manager.start_session(session1.id)

        assert manager.active_session_count == 1

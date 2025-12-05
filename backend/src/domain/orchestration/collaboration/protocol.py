# =============================================================================
# IPA Platform - Collaboration Protocol
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Defines the communication protocol for Agent collaboration.
# Supports message types:
#   - REQUEST: Request for action or information
#   - RESPONSE: Response to a request
#   - BROADCAST: Message to all participants
#   - NEGOTIATE: Negotiation message for agreements
#
# References:
#   - Sprint 8 Plan: docs/03-implementation/sprint-planning/phase-2/sprint-8-plan.md
# =============================================================================

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """
    Types of collaboration messages.

    Types:
        REQUEST: Request for action or information from another agent
        RESPONSE: Response to a previous request
        BROADCAST: Message sent to all participants
        NEGOTIATE: Negotiation message for reaching agreements
        ACKNOWLEDGE: Acknowledgment of message receipt
        REJECT: Rejection of a request
        CANCEL: Cancellation of a previous message/request
        HEARTBEAT: Keep-alive message
    """
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    NEGOTIATE = "negotiate"
    ACKNOWLEDGE = "acknowledge"
    REJECT = "reject"
    CANCEL = "cancel"
    HEARTBEAT = "heartbeat"


class MessagePriority(int, Enum):
    """
    Message priority levels.

    Higher priority messages are processed first.
    """
    LOW = 0
    NORMAL = 50
    HIGH = 100
    URGENT = 200


class MessageStatus(str, Enum):
    """
    Status of a message.

    States:
        PENDING: Message created but not yet sent
        SENT: Message sent to recipient
        DELIVERED: Message delivered to recipient
        READ: Message has been read/processed
        FAILED: Message delivery failed
        EXPIRED: Message TTL expired
    """
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class CollaborationMessage:
    """
    Message exchanged between collaborating agents.

    Attributes:
        id: Unique message identifier
        message_type: Type of message
        sender_id: ID of sending agent
        recipient_id: ID of recipient agent (None for broadcast)
        session_id: ID of collaboration session (optional)
        correlation_id: ID of related message (for response/ack)
        content: Message content/payload
        priority: Message priority
        status: Current status
        ttl: Time-to-live in seconds
        created_at: When message was created
        sent_at: When message was sent
        delivered_at: When message was delivered
        metadata: Additional message metadata
    """
    id: UUID = field(default_factory=uuid4)
    message_type: MessageType = MessageType.REQUEST
    sender_id: Optional[UUID] = None
    recipient_id: Optional[UUID] = None  # None for broadcast
    session_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    content: Dict[str, Any] = field(default_factory=dict)
    priority: int = MessagePriority.NORMAL.value
    status: MessageStatus = MessageStatus.PENDING
    ttl: int = 60  # seconds
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_broadcast(self) -> bool:
        """Check if this is a broadcast message."""
        return self.recipient_id is None

    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl <= 0:
            return False  # Never expires
        expiry = self.created_at + timedelta(seconds=self.ttl)
        return datetime.utcnow() > expiry


class CollaborationProtocol:
    """
    Protocol for Agent collaboration messaging.

    Provides functionality for:
        - Sending and receiving messages between agents
        - Broadcasting to multiple agents
        - Request-response patterns
        - Message routing and delivery
        - Message handlers registration

    Usage:
        protocol = CollaborationProtocol()

        # Register message handler
        protocol.register_handler(MessageType.REQUEST, handle_request)

        # Send a message
        await protocol.send_message(message)

        # Broadcast to all
        await protocol.broadcast(sender_id, content)
    """

    def __init__(self, message_store: Any = None):
        """
        Initialize CollaborationProtocol.

        Args:
            message_store: Optional storage for message persistence
        """
        self._message_store = message_store

        # Message handlers by type
        self._handlers: Dict[MessageType, List[Callable]] = {
            t: [] for t in MessageType
        }

        # Registered agents
        self._agents: Set[UUID] = set()

        # Message queue per agent
        self._queues: Dict[UUID, List[CollaborationMessage]] = {}

        # Pending responses (correlation_id -> Future)
        self._pending_responses: Dict[UUID, asyncio.Future] = {}

        logger.info("CollaborationProtocol initialized")

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent(self, agent_id: UUID) -> None:
        """
        Register an agent for collaboration.

        Args:
            agent_id: Agent ID to register
        """
        self._agents.add(agent_id)
        self._queues[agent_id] = []
        logger.debug(f"Agent {agent_id} registered for collaboration")

    def unregister_agent(self, agent_id: UUID) -> None:
        """
        Unregister an agent from collaboration.

        Args:
            agent_id: Agent ID to unregister
        """
        self._agents.discard(agent_id)
        self._queues.pop(agent_id, None)
        logger.debug(f"Agent {agent_id} unregistered from collaboration")

    def is_agent_registered(self, agent_id: UUID) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents

    @property
    def registered_agents(self) -> Set[UUID]:
        """Get set of registered agent IDs."""
        return self._agents.copy()

    # =========================================================================
    # Message Handlers
    # =========================================================================

    def register_handler(
        self,
        message_type: MessageType,
        handler: Callable,
    ) -> None:
        """
        Register a handler for a message type.

        Args:
            message_type: Type of messages to handle
            handler: Async function (message) -> None/response
        """
        self._handlers[message_type].append(handler)
        logger.debug(f"Registered handler for {message_type.value}")

    def unregister_handler(
        self,
        message_type: MessageType,
        handler: Callable,
    ) -> bool:
        """
        Unregister a message handler.

        Args:
            message_type: Type of messages
            handler: Handler to remove

        Returns:
            True if handler was removed
        """
        if handler in self._handlers[message_type]:
            self._handlers[message_type].remove(handler)
            return True
        return False

    # =========================================================================
    # Message Sending
    # =========================================================================

    async def send_message(
        self,
        message: CollaborationMessage,
    ) -> bool:
        """
        Send a message to recipient.

        Args:
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        if message.is_broadcast:
            return await self._broadcast_message(message)

        if not self.is_agent_registered(message.recipient_id):
            logger.warning(
                f"Cannot send message: recipient {message.recipient_id} not registered"
            )
            message.status = MessageStatus.FAILED
            return False

        # Update status
        message.status = MessageStatus.SENT
        message.sent_at = datetime.utcnow()

        # Add to recipient queue
        self._queues[message.recipient_id].append(message)

        # Persist if storage available
        if self._message_store:
            await self._message_store.save(message)

        # Process handlers
        await self._invoke_handlers(message)

        logger.debug(
            f"Message {message.id} sent from {message.sender_id} "
            f"to {message.recipient_id}"
        )

        return True

    async def _broadcast_message(
        self,
        message: CollaborationMessage,
    ) -> bool:
        """
        Broadcast message to all registered agents.

        Args:
            message: Message to broadcast

        Returns:
            True if message was broadcast
        """
        message.status = MessageStatus.SENT
        message.sent_at = datetime.utcnow()

        # Add to all agent queues except sender
        for agent_id in self._agents:
            if agent_id != message.sender_id:
                self._queues[agent_id].append(message)

        # Process handlers
        await self._invoke_handlers(message)

        logger.debug(
            f"Message {message.id} broadcast from {message.sender_id} "
            f"to {len(self._agents) - 1} agents"
        )

        return True

    async def broadcast(
        self,
        sender_id: UUID,
        content: Dict[str, Any],
        session_id: UUID = None,
        priority: int = MessagePriority.NORMAL.value,
    ) -> CollaborationMessage:
        """
        Create and send a broadcast message.

        Args:
            sender_id: Sender agent ID
            content: Message content
            session_id: Optional session ID
            priority: Message priority

        Returns:
            Created message
        """
        message = CollaborationMessage(
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            recipient_id=None,  # Broadcast
            session_id=session_id,
            content=content,
            priority=priority,
        )

        await self.send_message(message)
        return message

    # =========================================================================
    # Request-Response Pattern
    # =========================================================================

    async def send_request(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        content: Dict[str, Any],
        session_id: UUID = None,
        timeout: float = 30.0,
    ) -> Optional[CollaborationMessage]:
        """
        Send a request and wait for response.

        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            content: Request content
            session_id: Optional session ID
            timeout: Timeout in seconds

        Returns:
            Response message or None if timed out
        """
        message = CollaborationMessage(
            message_type=MessageType.REQUEST,
            sender_id=sender_id,
            recipient_id=recipient_id,
            session_id=session_id,
            content=content,
        )

        # Create future for response
        response_future = asyncio.get_event_loop().create_future()
        self._pending_responses[message.id] = response_future

        try:
            await self.send_message(message)

            # Wait for response
            response = await asyncio.wait_for(
                response_future,
                timeout=timeout,
            )
            return response

        except asyncio.TimeoutError:
            logger.warning(f"Request {message.id} timed out after {timeout}s")
            return None

        finally:
            self._pending_responses.pop(message.id, None)

    async def send_response(
        self,
        request: CollaborationMessage,
        content: Dict[str, Any],
        accepted: bool = True,
    ) -> CollaborationMessage:
        """
        Send a response to a request.

        Args:
            request: Original request message
            content: Response content
            accepted: Whether request was accepted

        Returns:
            Response message
        """
        message_type = (
            MessageType.RESPONSE if accepted
            else MessageType.REJECT
        )

        response = CollaborationMessage(
            message_type=message_type,
            sender_id=request.recipient_id,
            recipient_id=request.sender_id,
            session_id=request.session_id,
            correlation_id=request.id,
            content=content,
        )

        await self.send_message(response)

        # Resolve pending future if exists
        if request.id in self._pending_responses:
            future = self._pending_responses.pop(request.id)
            if not future.done():
                future.set_result(response)

        return response

    # =========================================================================
    # Negotiation Pattern
    # =========================================================================

    async def negotiate(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        proposal: Dict[str, Any],
        session_id: UUID = None,
    ) -> CollaborationMessage:
        """
        Send a negotiation message.

        Args:
            sender_id: Sender agent ID
            recipient_id: Recipient agent ID
            proposal: Negotiation proposal
            session_id: Optional session ID

        Returns:
            Negotiation message
        """
        message = CollaborationMessage(
            message_type=MessageType.NEGOTIATE,
            sender_id=sender_id,
            recipient_id=recipient_id,
            session_id=session_id,
            content={"proposal": proposal},
            priority=MessagePriority.HIGH.value,
        )

        await self.send_message(message)
        return message

    async def counter_propose(
        self,
        original: CollaborationMessage,
        counter_proposal: Dict[str, Any],
    ) -> CollaborationMessage:
        """
        Send a counter-proposal in negotiation.

        Args:
            original: Original negotiation message
            counter_proposal: Counter-proposal content

        Returns:
            Counter-proposal message
        """
        message = CollaborationMessage(
            message_type=MessageType.NEGOTIATE,
            sender_id=original.recipient_id,
            recipient_id=original.sender_id,
            session_id=original.session_id,
            correlation_id=original.id,
            content={"counter_proposal": counter_proposal},
            priority=MessagePriority.HIGH.value,
        )

        await self.send_message(message)
        return message

    # =========================================================================
    # Message Receiving
    # =========================================================================

    async def receive_messages(
        self,
        agent_id: UUID,
        count: int = 10,
        mark_delivered: bool = True,
    ) -> List[CollaborationMessage]:
        """
        Receive messages for an agent.

        Args:
            agent_id: Agent to receive messages for
            count: Maximum messages to return
            mark_delivered: Whether to mark as delivered

        Returns:
            List of messages
        """
        if agent_id not in self._queues:
            return []

        # Filter out expired messages
        queue = self._queues[agent_id]
        valid_messages = [m for m in queue if not m.is_expired]
        self._queues[agent_id] = valid_messages

        # Get messages (sorted by priority)
        messages = sorted(
            valid_messages[:count],
            key=lambda m: m.priority,
            reverse=True,
        )

        if mark_delivered:
            for msg in messages:
                msg.status = MessageStatus.DELIVERED
                msg.delivered_at = datetime.utcnow()

        return messages

    async def acknowledge(
        self,
        message: CollaborationMessage,
    ) -> CollaborationMessage:
        """
        Acknowledge receipt of a message.

        Args:
            message: Message to acknowledge

        Returns:
            Acknowledgment message
        """
        ack = CollaborationMessage(
            message_type=MessageType.ACKNOWLEDGE,
            sender_id=message.recipient_id,
            recipient_id=message.sender_id,
            session_id=message.session_id,
            correlation_id=message.id,
            content={"acknowledged": True},
        )

        message.status = MessageStatus.READ
        await self.send_message(ack)
        return ack

    # =========================================================================
    # Queue Management
    # =========================================================================

    def get_queue_size(self, agent_id: UUID) -> int:
        """Get number of messages in agent's queue."""
        return len(self._queues.get(agent_id, []))

    def clear_queue(self, agent_id: UUID) -> int:
        """
        Clear all messages in agent's queue.

        Args:
            agent_id: Agent to clear queue for

        Returns:
            Number of messages cleared
        """
        if agent_id in self._queues:
            count = len(self._queues[agent_id])
            self._queues[agent_id] = []
            return count
        return 0

    def clear_expired(self) -> int:
        """
        Clear all expired messages from all queues.

        Returns:
            Number of messages cleared
        """
        count = 0
        for agent_id in self._queues:
            before = len(self._queues[agent_id])
            self._queues[agent_id] = [
                m for m in self._queues[agent_id]
                if not m.is_expired
            ]
            count += before - len(self._queues[agent_id])
        return count

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _invoke_handlers(
        self,
        message: CollaborationMessage,
    ) -> None:
        """
        Invoke registered handlers for a message.

        Args:
            message: Message to handle
        """
        handlers = self._handlers.get(message.message_type, [])

        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(
                    f"Handler error for message {message.id}: {e}",
                    exc_info=True,
                )

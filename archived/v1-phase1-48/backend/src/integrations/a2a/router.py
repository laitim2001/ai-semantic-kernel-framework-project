# =============================================================================
# IPA Platform - A2A Message Router
# =============================================================================
# Sprint 81: S81-2 - A2A 通信協議完善 (8 pts)
#
# This module handles message routing and tracking between agents.
# =============================================================================

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from .protocol import (
    A2AMessage,
    MessagePriority,
    MessageStatus,
    MessageType,
)


logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes messages between agents and tracks delivery status.

    Responsibilities:
    - Route messages to target agents
    - Track message delivery status
    - Handle retries and failures
    - Support message priority queuing
    """

    def __init__(
        self,
        max_queue_size: int = 1000,
        default_timeout_seconds: int = 30,
    ):
        self.max_queue_size = max_queue_size
        self.default_timeout_seconds = default_timeout_seconds
        self._queues: Dict[str, List[A2AMessage]] = {}
        self._messages: Dict[str, A2AMessage] = {}
        self._handlers: Dict[str, Callable[[A2AMessage], Any]] = {}
        self._on_delivery_callbacks: List[Callable[[A2AMessage], None]] = []
        self._on_failure_callbacks: List[Callable[[A2AMessage, str], None]] = []

    def register_handler(self, agent_id: str, handler: Callable[[A2AMessage], Any]) -> None:
        self._handlers[agent_id] = handler
        logger.info(f"Registered handler for agent: {agent_id}")

    def unregister_handler(self, agent_id: str) -> bool:
        if agent_id in self._handlers:
            del self._handlers[agent_id]
            return True
        return False

    async def route_message(self, message: A2AMessage, timeout_seconds: Optional[int] = None) -> bool:
        self._messages[message.message_id] = message
        message.status = MessageStatus.PENDING
        if message.is_expired:
            message.status = MessageStatus.EXPIRED
            return False
        handler = self._handlers.get(message.to_agent)
        if not handler:
            return self._queue_message(message)
        timeout = timeout_seconds or self.default_timeout_seconds
        try:
            message.status = MessageStatus.SENT
            if asyncio.iscoroutinefunction(handler):
                await asyncio.wait_for(handler(message), timeout=timeout)
            else:
                handler(message)
            message.status = MessageStatus.DELIVERED
            self._notify_delivery(message)
            return True
        except asyncio.TimeoutError:
            return await self._handle_failure(message, "Delivery timeout")
        except Exception as e:
            return await self._handle_failure(message, str(e))

    def _queue_message(self, message: A2AMessage) -> bool:
        if message.to_agent not in self._queues:
            self._queues[message.to_agent] = []
        queue = self._queues[message.to_agent]
        if len(queue) >= self.max_queue_size:
            message.status = MessageStatus.FAILED
            return False
        queue.append(message)
        message.status = MessageStatus.PENDING
        return True

    async def _handle_failure(self, message: A2AMessage, error: str) -> bool:
        message.retry_count += 1
        if message.can_retry:
            return self._queue_message(message)
        message.status = MessageStatus.FAILED
        self._notify_failure(message, error)
        return False

    async def process_queue(self, agent_id: str) -> int:
        if agent_id not in self._handlers:
            return 0
        queue = self._queues.get(agent_id, [])
        processed = 0
        while queue:
            message = queue.pop(0)
            if message.is_expired:
                message.status = MessageStatus.EXPIRED
                continue
            if await self.route_message(message):
                processed += 1
        return processed

    def track_message(self, message_id: str) -> Optional[A2AMessage]:
        return self._messages.get(message_id)

    def get_message_status(self, message_id: str) -> Optional[MessageStatus]:
        message = self._messages.get(message_id)
        return message.status if message else None

    def get_pending_messages(self, agent_id: Optional[str] = None) -> List[A2AMessage]:
        if agent_id:
            return list(self._queues.get(agent_id, []))
        all_pending = []
        for queue in self._queues.values():
            all_pending.extend(queue)
        return all_pending

    def get_conversation_messages(self, correlation_id: str) -> List[A2AMessage]:
        return [m for m in self._messages.values() if m.correlation_id == correlation_id]

    def on_delivery(self, callback: Callable[[A2AMessage], None]) -> None:
        self._on_delivery_callbacks.append(callback)

    def on_failure(self, callback: Callable[[A2AMessage, str], None]) -> None:
        self._on_failure_callbacks.append(callback)

    def _notify_delivery(self, message: A2AMessage) -> None:
        for callback in self._on_delivery_callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.warning(f"Delivery callback failed: {e}")

    def _notify_failure(self, message: A2AMessage, error: str) -> None:
        for callback in self._on_failure_callbacks:
            try:
                callback(message, error)
            except Exception as e:
                logger.warning(f"Failure callback failed: {e}")

    def cleanup_expired(self) -> int:
        expired_ids = [msg_id for msg_id, msg in self._messages.items() if msg.is_expired]
        for msg_id in expired_ids:
            del self._messages[msg_id]
        for queue in self._queues.values():
            queue[:] = [m for m in queue if not m.is_expired]
        return len(expired_ids)

    def get_statistics(self) -> Dict[str, Any]:
        from collections import defaultdict
        total_messages = len(self._messages)
        by_status = defaultdict(int)
        by_type = defaultdict(int)
        for msg in self._messages.values():
            by_status[msg.status.value] += 1
            by_type[msg.type.value] += 1
        total_queued = sum(len(q) for q in self._queues.values())
        return {
            "total_messages": total_messages,
            "total_queued": total_queued,
            "registered_handlers": len(self._handlers),
            "by_status": dict(by_status),
            "by_type": dict(by_type),
        }

    def clear(self) -> None:
        self._messages.clear()
        self._queues.clear()

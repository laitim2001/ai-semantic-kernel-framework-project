# =============================================================================
# IPA Platform - A2A Communication Module
# =============================================================================
# Sprint 81: S81-2 - A2A 通信協議完善 (8 pts)
#
# This module provides Agent-to-Agent communication capabilities.
#
# Architecture:
#   - protocol.py: Message formats and agent capabilities
#   - discovery.py: Agent registration and discovery
#   - router.py: Message routing and tracking
#
# Usage:
#   from src.integrations.a2a import (
#       A2AMessage, MessageType, AgentCapability,
#       AgentDiscoveryService, MessageRouter,
#   )
#
#   # Create discovery service
#   discovery = AgentDiscoveryService()
#   discovery.register_agent(AgentCapability(...))
#
#   # Create message router
#   router = MessageRouter()
#   await router.route_message(A2AMessage.create(...))
# =============================================================================

from .protocol import (
    # Enums
    MessageType,
    MessagePriority,
    MessageStatus,
    A2AAgentStatus,
    # Data classes
    A2AMessage,
    AgentCapability,
    DiscoveryQuery,
    DiscoveryResult,
)

from .discovery import AgentDiscoveryService

from .router import MessageRouter


__all__ = [
    # Protocol - Enums
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    "A2AAgentStatus",
    # Protocol - Data classes
    "A2AMessage",
    "AgentCapability",
    "DiscoveryQuery",
    "DiscoveryResult",
    # Discovery
    "AgentDiscoveryService",
    # Router
    "MessageRouter",
]

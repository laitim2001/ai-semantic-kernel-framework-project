# =============================================================================
# IPA Platform - Collaboration Module
# =============================================================================
# Sprint 8: Agent Handoff & Collaboration (Phase 2)
#
# Agent collaboration capabilities including:
#   - CollaborationProtocol: Message-based communication protocol
#   - CollaborationSession: Session management for multi-agent collaboration
#   - Message routing and delivery
# =============================================================================

from src.domain.orchestration.collaboration.protocol import (
    CollaborationMessage,
    CollaborationProtocol,
    MessageType,
    MessagePriority,
    MessageStatus,
)
from src.domain.orchestration.collaboration.session import (
    CollaborationSession,
    SessionManager,
    SessionPhase,
    SessionStatus,
)

__all__ = [
    # Protocol
    "CollaborationMessage",
    "CollaborationProtocol",
    "MessageType",
    "MessagePriority",
    "MessageStatus",
    # Session
    "CollaborationSession",
    "SessionManager",
    "SessionPhase",
    "SessionStatus",
]

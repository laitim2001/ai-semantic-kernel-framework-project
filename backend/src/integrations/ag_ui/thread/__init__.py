# =============================================================================
# IPA Platform - AG-UI Thread Package
# =============================================================================
# Sprint 58: AG-UI Core Infrastructure
# S58-3: Thread Manager
#
# Thread management for AG-UI Protocol.
# Handles conversation thread lifecycle, message storage, and state persistence.
#
# Usage:
#   from src.integrations.ag_ui.thread import (
#       ThreadManager,
#       AGUIThread,
#       AGUIMessage,
#       ThreadStatus,
#       MessageRole,
#   )
# =============================================================================

from .manager import ThreadManager
from .models import (
    AGUIMessage,
    AGUIMessageSchema,
    AGUIThread,
    AGUIThreadSchema,
    MessageRole,
    ThreadStatus,
)
from .storage import (
    CacheProtocol,
    InMemoryCache,
    InMemoryThreadRepository,
    ThreadCache,
    ThreadRepository,
)

__all__ = [
    # Manager
    "ThreadManager",
    # Models
    "AGUIThread",
    "AGUIMessage",
    "ThreadStatus",
    "MessageRole",
    # Schemas (Pydantic)
    "AGUIThreadSchema",
    "AGUIMessageSchema",
    # Storage
    "ThreadCache",
    "ThreadRepository",
    "InMemoryThreadRepository",
    "InMemoryCache",
    "CacheProtocol",
]

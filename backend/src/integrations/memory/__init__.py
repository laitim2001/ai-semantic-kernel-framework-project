# =============================================================================
# IPA Platform - Unified Memory System
# =============================================================================
# Sprint 79: S79-2 - mem0 長期記憶整合 (10 pts)
#
# This module provides a unified memory system with three layers:
#   Layer 1: Working Memory (Redis) - Short-term, TTL 30 min
#   Layer 2: Session Memory (PostgreSQL) - Medium-term, TTL 7 days
#   Layer 3: Long-term Memory (mem0 + Qdrant) - Permanent
#
# Usage:
#   from src.integrations.memory import (
#       UnifiedMemoryManager,
#       Mem0Client,
#       EmbeddingService,
#       MemoryRecord,
#       MemoryType,
#   )
#
#   # Initialize memory manager
#   manager = UnifiedMemoryManager()
#   await manager.initialize()
#
#   # Add memory
#   await manager.add(content="User prefers dark mode", user_id="user123")
#
#   # Search memories
#   results = await manager.search("user preferences", user_id="user123")
# =============================================================================

from .types import (
    # Enums
    MemoryType,
    MemoryLayer,
    # Data classes
    MemoryMetadata,
    MemoryRecord,
    MemorySearchResult,
    MemorySearchQuery,
    MemoryConfig,
    # Constants
    DEFAULT_MEMORY_CONFIG,
)

from .mem0_client import Mem0Client
from .unified_memory import UnifiedMemoryManager
from .embeddings import EmbeddingService


__all__ = [
    # Enums
    "MemoryType",
    "MemoryLayer",
    # Data classes
    "MemoryMetadata",
    "MemoryRecord",
    "MemorySearchResult",
    "MemorySearchQuery",
    "MemoryConfig",
    # Constants
    "DEFAULT_MEMORY_CONFIG",
    # Core components
    "Mem0Client",
    "UnifiedMemoryManager",
    "EmbeddingService",
]

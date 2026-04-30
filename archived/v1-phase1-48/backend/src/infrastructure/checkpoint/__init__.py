"""Unified Checkpoint Infrastructure.

Sprint 120 -- Provides a unified interface for the platform's 4 checkpoint systems.

Usage:
    from src.infrastructure.checkpoint import (
        CheckpointProvider,
        CheckpointEntry,
        UnifiedCheckpointRegistry,
    )

    registry = UnifiedCheckpointRegistry()
    registry.register_provider(my_provider)
    await registry.save("my_provider", "cp-001", {"state": "data"})
"""

from src.infrastructure.checkpoint.protocol import (
    CheckpointEntry,
    CheckpointProvider,
)
from src.infrastructure.checkpoint.unified_registry import UnifiedCheckpointRegistry

__all__ = [
    "CheckpointEntry",
    "CheckpointProvider",
    "UnifiedCheckpointRegistry",
]

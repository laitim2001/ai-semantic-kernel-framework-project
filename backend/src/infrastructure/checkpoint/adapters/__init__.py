"""Checkpoint provider adapters.

Each adapter wraps an existing checkpoint system to implement CheckpointProvider.
"""

from src.infrastructure.checkpoint.adapters.hybrid_adapter import HybridCheckpointAdapter

__all__ = [
    "HybridCheckpointAdapter",
]

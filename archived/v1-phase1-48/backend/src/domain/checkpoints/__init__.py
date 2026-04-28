# =============================================================================
# IPA Platform - Checkpoints Domain Module
# =============================================================================
# Sprint 2: Workflow & Checkpoints - Human-in-the-Loop
#
# Checkpoint domain module providing:
#   - CheckpointStatus: Status enumeration for checkpoint lifecycle
#   - CheckpointData: Data structure for checkpoint information
#   - CheckpointService: Business logic for checkpoint operations
#   - CheckpointStorage: Abstract storage interface
#   - DatabaseCheckpointStorage: PostgreSQL storage implementation
#
# Usage:
#   from src.domain.checkpoints import CheckpointService, CheckpointStatus
#
#   service = CheckpointService(repository)
#   pending = await service.get_pending_approvals()
#   await service.approve_checkpoint(checkpoint_id, user_id, response)
# =============================================================================

from src.domain.checkpoints.service import (
    CheckpointService,
    CheckpointStatus,
    CheckpointData,
)
from src.domain.checkpoints.storage import (
    CheckpointStorage,
    DatabaseCheckpointStorage,
)

__all__ = [
    # Enums
    "CheckpointStatus",
    # Data structures
    "CheckpointData",
    # Services
    "CheckpointService",
    # Storage adapters
    "CheckpointStorage",
    "DatabaseCheckpointStorage",
]

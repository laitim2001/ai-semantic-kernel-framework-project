# =============================================================================
# IPA Platform - Unified Checkpoint Module
# =============================================================================
# Phase 14: Human-in-the-Loop & Approval
# Sprint 57: Unified Checkpoint & Polish
#
# Unified checkpoint system for hybrid MAF + Claude SDK architecture.
# Supports saving and restoring execution state across framework boundaries.
#
# Key Components:
#   - HybridCheckpoint: Unified checkpoint structure
#   - MAFCheckpointState: MAF workflow state snapshot
#   - ClaudeCheckpointState: Claude session state snapshot
#   - UnifiedCheckpointStorage: Multi-backend storage abstraction
#
# Dependencies:
#   - HybridContext (src.integrations.hybrid.context.models)
#   - RiskProfile (src.integrations.hybrid.risk.models)
#   - ModeTransition (src.integrations.hybrid.switching.models)
# =============================================================================

from .models import (
    CheckpointStatus,
    CheckpointType,
    ClaudeCheckpointState,
    CompressionAlgorithm,
    HybridCheckpoint,
    MAFCheckpointState,
    RestoreResult,
    RestoreStatus,
    RiskSnapshot,
)
from .serialization import (
    CheckpointSerializer,
    DeserializationResult,
    SerializationConfig,
    SerializationResult,
)
from .storage import (
    CheckpointQuery,
    CheckpointStorageProtocol,
    StorageBackend,
    StorageConfig,
    StorageError,
    StorageStats,
    UnifiedCheckpointStorage,
)
from .version import (
    CheckpointVersion,
    CheckpointVersionMigrator,
    MigrationResult,
)

# Backend implementations (lazy import to avoid circular dependencies)
# from .backends import (
#     FilesystemCheckpointStorage,
#     MemoryCheckpointStorage,
#     PostgresCheckpointStorage,
#     RedisCheckpointStorage,
# )

__all__ = [
    # Enums
    "CheckpointStatus",
    "CheckpointType",
    "CompressionAlgorithm",
    "RestoreStatus",
    "CheckpointVersion",
    # Models
    "MAFCheckpointState",
    "ClaudeCheckpointState",
    "HybridCheckpoint",
    "RiskSnapshot",
    "RestoreResult",
    # Serialization
    "CheckpointSerializer",
    "SerializationConfig",
    "SerializationResult",
    "DeserializationResult",
    # Version Migration
    "CheckpointVersionMigrator",
    "MigrationResult",
    # Storage
    "UnifiedCheckpointStorage",
    "CheckpointStorageProtocol",
    "StorageBackend",
    "StorageConfig",
    "StorageStats",
    "CheckpointQuery",
    "StorageError",
]

# =============================================================================
# IPA Platform - Hybrid Mode Switching Module
# =============================================================================
# Sprint 56: Mode Switcher & HITL
#
# 動態模式切換模組，支援 Workflow (MAF) 與 Chat (Claude SDK) 模式之間的切換。
# 包含觸發檢測、狀態遷移、Checkpoint 與 Rollback 機制。
#
# Components:
#   - ModeSwitcher: 核心切換器，協調觸發檢測與狀態遷移
#   - SwitchTrigger: 觸發資訊，記錄切換原因與信心度
#   - SwitchResult: 切換結果，包含狀態與 rollback 支援
#   - ModeTransition: 完整切換記錄，用於審計追蹤
#
# Dependencies:
#   - ExecutionMode (src.integrations.hybrid.intent.models)
#   - HybridContext (src.integrations.hybrid.context.models)
# =============================================================================

from src.integrations.hybrid.switching.models import (
    ExecutionState,
    MigrationDirection,
    MigratedState,
    ModeTransition,
    SwitchCheckpoint,
    SwitchConfig,
    SwitchResult,
    SwitchStatus,
    SwitchTrigger,
    SwitchTriggerType,
)
from src.integrations.hybrid.switching.switcher import (
    CheckpointStorageProtocol,
    ContextBridgeProtocol,
    InMemoryCheckpointStorage,
    ModeSwitcher,
    StateMigratorProtocol,
    TriggerDetectorProtocol,
)
from src.integrations.hybrid.switching.migration import (
    MigrationConfig,
    MigrationError,
    MigrationValidator,
    StateMigrator,
)
from src.integrations.hybrid.switching.migration.state_migrator import (
    MigrationContext,
    MigrationStatus,
)

__all__ = [
    # Enums
    "SwitchTriggerType",
    "SwitchStatus",
    "MigrationDirection",
    "MigrationStatus",
    # Config
    "SwitchConfig",
    "MigrationConfig",
    # Data Models
    "SwitchTrigger",
    "SwitchResult",
    "ModeTransition",
    "MigratedState",
    "ExecutionState",
    "SwitchCheckpoint",
    "MigrationContext",
    # Exceptions
    "MigrationError",
    # Protocols
    "TriggerDetectorProtocol",
    "StateMigratorProtocol",
    "CheckpointStorageProtocol",
    "ContextBridgeProtocol",
    # Implementations
    "ModeSwitcher",
    "InMemoryCheckpointStorage",
    "StateMigrator",
    "MigrationValidator",
]

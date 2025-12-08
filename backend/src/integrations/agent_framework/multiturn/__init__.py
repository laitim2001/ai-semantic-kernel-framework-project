# =============================================================================
# IPA Platform - Multi-turn Integration Module
# =============================================================================
# Sprint 24: S24-3 Multi-turn 遷移到 Checkpoint (8 points)
#
# 多輪對話適配器模組，整合官方 CheckpointStorage 與 Phase 2 會話管理。
# =============================================================================

from .adapter import (
    MultiTurnAdapter,
    TurnResult,
    SessionState,
    SessionInfo,
    MultiTurnConfig,
    Message,
    MessageRole,
    ContextScope,
    ContextManager,
    TurnTracker,
    create_multiturn_adapter,
    create_redis_multiturn_adapter,
)
from .checkpoint_storage import (
    BaseCheckpointStorage,
    RedisCheckpointStorage,
    PostgresCheckpointStorage,
    FileCheckpointStorage,
)

__all__ = [
    # 適配器
    "MultiTurnAdapter",
    "TurnResult",
    "SessionState",
    "SessionInfo",
    "MultiTurnConfig",
    # 消息和上下文
    "Message",
    "MessageRole",
    "ContextScope",
    "ContextManager",
    "TurnTracker",
    # 工廠函數
    "create_multiturn_adapter",
    "create_redis_multiturn_adapter",
    # Checkpoint 存儲
    "BaseCheckpointStorage",
    "RedisCheckpointStorage",
    "PostgresCheckpointStorage",
    "FileCheckpointStorage",
]

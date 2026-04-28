# =============================================================================
# IPA Platform - Multi-Turn Session Module
# =============================================================================
# Sprint 9: S9-3 MultiTurnSessionManager (8 points)
# Sprint 30: 棄用警告 - 請使用適配器層
#
# DEPRECATED: 此模組已棄用，請使用適配器層
#
# 推薦使用:
#   from src.integrations.agent_framework.multiturn import (
#       MultiTurnAdapter,
#       CheckpointStorageAdapter,
#   )
#
# 或使用 API 服務:
#   from src.api.v1.groupchat.routes import multiturn_* endpoints
#
# 此模組將在未來版本中移除
# =============================================================================

import warnings

warnings.warn(
    "domain.orchestration.multiturn 模組已棄用。"
    "請使用 integrations.agent_framework.multiturn 中的適配器。",
    DeprecationWarning,
    stacklevel=2,
)

from src.domain.orchestration.multiturn.session_manager import (
    MultiTurnSession,
    MultiTurnSessionManager,
    SessionStatus,
)
from src.domain.orchestration.multiturn.turn_tracker import (
    Turn,
    TurnStatus,
    TurnTracker,
)
from src.domain.orchestration.multiturn.context_manager import (
    ContextScope,
    SessionContextManager,
)

__all__ = [
    # Session Manager
    "MultiTurnSessionManager",
    "MultiTurnSession",
    "SessionStatus",
    # Turn Tracker
    "TurnTracker",
    "Turn",
    "TurnStatus",
    # Context Manager
    "SessionContextManager",
    "ContextScope",
]

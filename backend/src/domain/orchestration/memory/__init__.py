# =============================================================================
# IPA Platform - Conversation Memory Module
# =============================================================================
# Sprint 9: S9-4 ConversationMemoryStore (8 points)
# Sprint 30: 棄用警告 - 請使用適配器層
#
# DEPRECATED: 此模組已棄用，請使用適配器層
#
# 推薦使用:
#   from src.integrations.agent_framework.memory import (
#       MemoryStorageAdapter,
#       InMemoryStorageAdapter,
#       RedisStorageAdapter,
#   )
#
# 或使用 API 服務:
#   from src.api.v1.groupchat.routes import memory_* endpoints
#
# 此模組將在未來版本中移除
# =============================================================================

import warnings

warnings.warn(
    "domain.orchestration.memory 模組已棄用。"
    "請使用 integrations.agent_framework.memory 中的適配器。",
    DeprecationWarning,
    stacklevel=2,
)

from src.domain.orchestration.memory.models import (
    ConversationSession,
    ConversationTurn,
    MessageRecord,
    SessionStatus,
)
from src.domain.orchestration.memory.base import ConversationMemoryStore
from src.domain.orchestration.memory.in_memory import InMemoryConversationMemoryStore
from src.domain.orchestration.memory.redis_store import RedisConversationMemoryStore
from src.domain.orchestration.memory.postgres_store import PostgresConversationMemoryStore

__all__ = [
    # Models
    "ConversationSession",
    "ConversationTurn",
    "MessageRecord",
    "SessionStatus",
    # Base class
    "ConversationMemoryStore",
    # Implementations
    "InMemoryConversationMemoryStore",
    "RedisConversationMemoryStore",
    "PostgresConversationMemoryStore",
]

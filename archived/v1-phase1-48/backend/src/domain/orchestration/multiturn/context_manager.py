# =============================================================================
# IPA Platform - Session Context Manager
# =============================================================================
# Sprint 9: S9-3 MultiTurnSessionManager (8 points)
#
# Manages conversation context across turns within a session.
# Supports context scoping, merging, and retrieval.
# =============================================================================

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ContextScope(str, Enum):
    """Scope of context variables.

    上下文作用域:
    - SESSION: 整個會話期間有效
    - TURN: 只在當前輪次有效
    - TEMPORARY: 臨時上下文，使用後清除
    - PERSISTENT: 持久化上下文，跨會話有效
    """
    SESSION = "session"
    TURN = "turn"
    TEMPORARY = "temporary"
    PERSISTENT = "persistent"


@dataclass
class ContextEntry:
    """An entry in the context.

    上下文條目。

    Attributes:
        key: 鍵
        value: 值
        scope: 作用域
        created_at: 創建時間
        updated_at: 更新時間
        expires_at: 過期時間
        metadata: 額外元數據
    """
    key: str
    value: Any
    scope: ContextScope = ContextScope.SESSION
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "key": self.key,
            "value": self.value,
            "scope": self.scope.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
        }

    def is_expired(self) -> bool:
        """Check if the entry is expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


class SessionContextManager:
    """Manages conversation context for a multi-turn session.

    會話上下文管理器，管理多輪對話中的上下文信息。

    主要功能:
    - 設置和獲取上下文變量
    - 支持不同作用域的上下文
    - 上下文合併和覆蓋
    - 上下文過期處理
    - 上下文序列化和反序列化

    Example:
        ```python
        manager = SessionContextManager(session_id="session-123")

        # 設置上下文
        manager.set("user_name", "Alice", scope=ContextScope.SESSION)
        manager.set("current_topic", "Planning", scope=ContextScope.TURN)

        # 獲取上下文
        name = manager.get("user_name")
        topic = manager.get("current_topic")

        # 構建 Agent 上下文
        context = manager.build_agent_context()
        ```
    """

    def __init__(
        self,
        session_id: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize the SessionContextManager.

        Args:
            session_id: 會話 ID
            initial_context: 初始上下文
        """
        self._session_id = session_id
        self._entries: Dict[str, ContextEntry] = {}
        self._current_turn: int = 0
        self._context_transformers: List[Callable] = []

        # Initialize with provided context
        if initial_context:
            for key, value in initial_context.items():
                self.set(key, value, scope=ContextScope.SESSION)

        logger.debug(f"SessionContextManager initialized for session {session_id}")

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def current_turn(self) -> int:
        """Get the current turn number."""
        return self._current_turn

    # =========================================================================
    # Context Operations
    # =========================================================================

    def set(
        self,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.SESSION,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set a context value.

        設置上下文值。

        Args:
            key: 鍵
            value: 值
            scope: 作用域
            expires_at: 過期時間
            metadata: 額外元數據
        """
        if key in self._entries:
            entry = self._entries[key]
            entry.value = value
            entry.scope = scope
            entry.updated_at = datetime.utcnow()
            if expires_at:
                entry.expires_at = expires_at
            if metadata:
                entry.metadata.update(metadata)
        else:
            self._entries[key] = ContextEntry(
                key=key,
                value=value,
                scope=scope,
                expires_at=expires_at,
                metadata=metadata or {},
            )

        logger.debug(f"Set context '{key}' with scope {scope.value}")

    def get(
        self,
        key: str,
        default: Any = None,
        check_expiry: bool = True,
    ) -> Any:
        """Get a context value.

        獲取上下文值。

        Args:
            key: 鍵
            default: 默認值
            check_expiry: 是否檢查過期

        Returns:
            值
        """
        entry = self._entries.get(key)
        if not entry:
            return default

        if check_expiry and entry.is_expired():
            self.remove(key)
            return default

        return entry.value

    def remove(self, key: str) -> bool:
        """Remove a context entry.

        移除上下文條目。

        Args:
            key: 鍵

        Returns:
            是否成功移除
        """
        if key in self._entries:
            del self._entries[key]
            logger.debug(f"Removed context '{key}'")
            return True
        return False

    def has(self, key: str) -> bool:
        """Check if a context key exists.

        檢查上下文鍵是否存在。

        Args:
            key: 鍵

        Returns:
            是否存在
        """
        entry = self._entries.get(key)
        if not entry:
            return False
        if entry.is_expired():
            self.remove(key)
            return False
        return True

    def keys(self, scope: Optional[ContextScope] = None) -> List[str]:
        """Get all context keys.

        獲取所有上下文鍵。

        Args:
            scope: 過濾的作用域

        Returns:
            鍵列表
        """
        keys = []
        for key, entry in self._entries.items():
            if entry.is_expired():
                continue
            if scope and entry.scope != scope:
                continue
            keys.append(key)
        return keys

    # =========================================================================
    # Context Management
    # =========================================================================

    def get_context(
        self,
        scopes: Optional[Set[ContextScope]] = None,
    ) -> Dict[str, Any]:
        """Get the full context as a dictionary.

        獲取完整上下文字典。

        Args:
            scopes: 要包含的作用域集合

        Returns:
            上下文字典
        """
        context = {}
        for key, entry in self._entries.items():
            if entry.is_expired():
                continue
            if scopes and entry.scope not in scopes:
                continue
            context[key] = entry.value
        return context

    def update_context(
        self,
        updates: Dict[str, Any],
        scope: ContextScope = ContextScope.SESSION,
    ) -> None:
        """Update multiple context values.

        批量更新上下文值。

        Args:
            updates: 要更新的鍵值對
            scope: 作用域
        """
        for key, value in updates.items():
            self.set(key, value, scope=scope)

    def merge_context(
        self,
        other: Dict[str, Any],
        override: bool = False,
        scope: ContextScope = ContextScope.SESSION,
    ) -> None:
        """Merge another context into this one.

        合併另一個上下文。

        Args:
            other: 要合併的上下文
            override: 是否覆蓋現有值
            scope: 作用域
        """
        for key, value in other.items():
            if override or not self.has(key):
                self.set(key, value, scope=scope)

    def clear_context(
        self,
        scope: Optional[ContextScope] = None,
    ) -> int:
        """Clear context entries.

        清除上下文條目。

        Args:
            scope: 只清除指定作用域的條目

        Returns:
            清除的條目數
        """
        if scope is None:
            count = len(self._entries)
            self._entries.clear()
            logger.debug(f"Cleared all {count} context entries")
            return count

        keys_to_remove = [
            key for key, entry in self._entries.items()
            if entry.scope == scope
        ]
        for key in keys_to_remove:
            del self._entries[key]

        logger.debug(f"Cleared {len(keys_to_remove)} context entries with scope {scope.value}")
        return len(keys_to_remove)

    # =========================================================================
    # Turn Management
    # =========================================================================

    def start_turn(self, turn_number: int) -> None:
        """Start a new turn.

        開始新的輪次。

        Args:
            turn_number: 輪次編號
        """
        self._current_turn = turn_number
        logger.debug(f"Started turn {turn_number} in context")

    def end_turn(self) -> None:
        """End the current turn and clear turn-scoped context."""
        cleared = self.clear_context(scope=ContextScope.TURN)
        self.clear_context(scope=ContextScope.TEMPORARY)
        logger.debug(f"Ended turn {self._current_turn}, cleared {cleared} turn entries")

    # =========================================================================
    # Agent Context Building
    # =========================================================================

    def build_agent_context(
        self,
        include_turn: bool = True,
        max_history_items: int = 10,
        custom_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build context for an agent.

        構建 Agent 上下文。

        Args:
            include_turn: 是否包含輪次上下文
            max_history_items: 最大歷史項數
            custom_fields: 自定義字段

        Returns:
            Agent 上下文字典
        """
        scopes = {ContextScope.SESSION, ContextScope.PERSISTENT}
        if include_turn:
            scopes.add(ContextScope.TURN)

        context = self.get_context(scopes=scopes)

        # Apply transformers
        for transformer in self._context_transformers:
            try:
                context = transformer(context)
            except Exception as e:
                logger.error(f"Context transformer error: {e}")

        # Add custom fields
        if custom_fields:
            context.update(custom_fields)

        # Add metadata
        context["_session_id"] = self._session_id
        context["_current_turn"] = self._current_turn

        return context

    def register_transformer(
        self,
        transformer: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Register a context transformer.

        註冊上下文轉換器。

        Args:
            transformer: 轉換函數
        """
        self._context_transformers.append(transformer)

    # =========================================================================
    # Serialization
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the context manager state.

        序列化上下文管理器狀態。

        Returns:
            狀態字典
        """
        return {
            "session_id": self._session_id,
            "current_turn": self._current_turn,
            "entries": {k: v.to_dict() for k, v in self._entries.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionContextManager":
        """Deserialize a context manager.

        反序列化上下文管理器。

        Args:
            data: 狀態字典

        Returns:
            SessionContextManager 實例
        """
        manager = cls(session_id=data["session_id"])
        manager._current_turn = data.get("current_turn", 0)

        for key, entry_data in data.get("entries", {}).items():
            manager._entries[key] = ContextEntry(
                key=entry_data["key"],
                value=entry_data["value"],
                scope=ContextScope(entry_data["scope"]),
                created_at=datetime.fromisoformat(entry_data["created_at"]),
                updated_at=datetime.fromisoformat(entry_data["updated_at"]),
                expires_at=datetime.fromisoformat(entry_data["expires_at"]) if entry_data.get("expires_at") else None,
                metadata=entry_data.get("metadata", {}),
            )

        return manager

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def clone(self) -> "SessionContextManager":
        """Create a deep copy of this context manager.

        創建此上下文管理器的深拷貝。

        Returns:
            新的 SessionContextManager 實例
        """
        new_manager = SessionContextManager(session_id=self._session_id)
        new_manager._current_turn = self._current_turn
        new_manager._entries = copy.deepcopy(self._entries)
        return new_manager

    def get_statistics(self) -> Dict[str, Any]:
        """Get context statistics.

        獲取上下文統計信息。

        Returns:
            統計字典
        """
        by_scope: Dict[str, int] = {}
        expired_count = 0

        for entry in self._entries.values():
            if entry.is_expired():
                expired_count += 1
            else:
                scope = entry.scope.value
                by_scope[scope] = by_scope.get(scope, 0) + 1

        return {
            "session_id": self._session_id,
            "total_entries": len(self._entries),
            "expired_entries": expired_count,
            "by_scope": by_scope,
            "current_turn": self._current_turn,
        }

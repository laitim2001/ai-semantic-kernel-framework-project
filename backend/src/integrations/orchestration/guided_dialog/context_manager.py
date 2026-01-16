"""
Conversation Context Manager Implementation

Manages conversation context with incremental update support.
Key principle: Update sub_intent based on rules, never re-classify via LLM.

Sprint 94: Story 94-2 - Implement ConversationContextManager (Phase 28)
Sprint 97: Story 97-5 - Enhanced State Management with Redis Persistence (Phase 28)
"""

import copy
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol, Tuple

from ..intent_router.completeness import CompletenessChecker
from ..intent_router.completeness.rules import CompletenessRules, get_default_rules
from ..intent_router.models import CompletenessInfo, ITIntentCategory, RoutingDecision
from .refinement_rules import RefinementRules, get_default_refinement_rules

logger = logging.getLogger(__name__)


# =============================================================================
# Dialog Session Configuration
# =============================================================================


@dataclass
class DialogSessionConfig:
    """
    Configuration for dialog sessions.

    Attributes:
        timeout_minutes: Session timeout in minutes (default: 30)
        max_turns: Maximum dialog turns allowed (default: 10)
        persist_history: Whether to persist dialog history
        auto_expire: Whether to automatically expire sessions
    """

    timeout_minutes: int = 30
    max_turns: int = 10
    persist_history: bool = True
    auto_expire: bool = True


# =============================================================================
# Dialog Session Storage Protocol
# =============================================================================


class DialogSessionStorage(Protocol):
    """Protocol for dialog session storage backends."""

    async def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """Save session state."""
        ...

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state by ID."""
        ...

    async def delete_session(self, session_id: str) -> None:
        """Delete session."""
        ...

    async def touch_session(self, session_id: str) -> None:
        """Update session last activity timestamp."""
        ...


@dataclass
class DialogTurn:
    """
    Single turn in dialog history.

    Attributes:
        role: "user" or "assistant"
        content: Message content
        timestamp: When the turn occurred
        extracted: Fields extracted from this turn
        context_snapshot: Snapshot of context at this point
    """
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    extracted: Dict[str, Any] = field(default_factory=dict)
    context_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "extracted": self.extracted,
            "context_snapshot": self.context_snapshot,
        }


@dataclass
class ContextState:
    """
    Current state of conversation context.

    Attributes:
        routing_decision: Current routing decision
        collected_info: All collected information across turns
        turn_count: Number of dialog turns
        last_updated: Timestamp of last update
    """
    routing_decision: Optional[RoutingDecision] = None
    collected_info: Dict[str, Any] = field(default_factory=dict)
    turn_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "routing_decision": (
                self.routing_decision.to_dict()
                if self.routing_decision else None
            ),
            "collected_info": self.collected_info,
            "turn_count": self.turn_count,
            "last_updated": self.last_updated.isoformat(),
        }


class ConversationContextManager:
    """
    Conversation context manager with incremental update support.

    Key Improvement: Updates sub_intent via rules, never re-classifies via LLM.
    This ensures low latency and zero additional API cost during dialog.

    Attributes:
        routing_decision: Current routing decision (mutable)
        collected_info: Information collected across dialog turns
        dialog_history: Complete dialog history
        refinement_rules: Rules for sub_intent refinement
        completeness_rules: Rules for completeness checking

    Example:
        >>> manager = ConversationContextManager()
        >>> manager.initialize(initial_routing_decision)
        >>> updated_decision = manager.update_with_user_response(
        ...     "是 ETL 系統，跑批次時報錯"
        ... )
        >>> print(updated_decision.sub_intent)  # "etl_failure" (refined)
        >>> print(updated_decision.completeness.completeness_score)  # 0.7 (recalculated)
    """

    def __init__(
        self,
        refinement_rules: Optional[RefinementRules] = None,
        completeness_rules: Optional[CompletenessRules] = None,
    ):
        """
        Initialize the context manager.

        Args:
            refinement_rules: Rules for sub_intent refinement (optional)
            completeness_rules: Rules for completeness checking (optional)
        """
        self.refinement_rules = refinement_rules or get_default_refinement_rules()
        self.completeness_rules = completeness_rules or get_default_rules()
        self._completeness_checker = CompletenessChecker(rules=self.completeness_rules)

        # State
        self._routing_decision: Optional[RoutingDecision] = None
        self._collected_info: Dict[str, Any] = {}
        self._dialog_history: List[DialogTurn] = []
        self._initialized: bool = False

    @property
    def routing_decision(self) -> Optional[RoutingDecision]:
        """Get current routing decision."""
        return self._routing_decision

    @property
    def collected_info(self) -> Dict[str, Any]:
        """Get all collected information."""
        return self._collected_info.copy()

    @property
    def dialog_history(self) -> List[DialogTurn]:
        """Get dialog history."""
        return self._dialog_history.copy()

    @property
    def is_initialized(self) -> bool:
        """Check if context is initialized."""
        return self._initialized

    def initialize(self, routing_decision: RoutingDecision) -> None:
        """
        Initialize context with initial routing decision.

        Args:
            routing_decision: Initial routing decision from BusinessIntentRouter
        """
        # Deep copy to avoid mutation issues
        self._routing_decision = copy.deepcopy(routing_decision)
        self._collected_info = {}
        self._dialog_history = []
        self._initialized = True

        # Extract initial fields from routing decision metadata
        if routing_decision.metadata:
            initial_extracted = routing_decision.metadata.get("extracted_fields", {})
            self._collected_info.update(initial_extracted)

        logger.info(
            f"Context initialized: category={routing_decision.intent_category.value}, "
            f"sub_intent={routing_decision.sub_intent}, "
            f"completeness={routing_decision.completeness.completeness_score:.2f}"
        )

    def update_with_user_response(
        self,
        user_response: str,
    ) -> RoutingDecision:
        """
        Update context with user response (incremental update).

        This method:
        1. Extracts fields from user response
        2. Updates collected information
        3. Refines sub_intent based on rules (NO LLM re-classification)
        4. Recalculates completeness score

        Args:
            user_response: User's response text

        Returns:
            Updated RoutingDecision

        Raises:
            RuntimeError: If context not initialized
        """
        if not self._initialized or not self._routing_decision:
            raise RuntimeError("Context not initialized. Call initialize() first.")

        # 1. Extract fields from user response
        extracted = self._extract_fields(user_response)

        # 2. Update collected information
        self._collected_info.update(extracted)

        # 3. Record dialog turn
        context_snapshot = {
            "intent_category": self._routing_decision.intent_category.value,
            "sub_intent": self._routing_decision.sub_intent,
            "completeness_score": self._routing_decision.completeness.completeness_score,
        }
        turn = DialogTurn(
            role="user",
            content=user_response,
            extracted=extracted,
            context_snapshot=context_snapshot,
        )
        self._dialog_history.append(turn)

        # 4. Refine sub_intent based on rules (NOT LLM)
        new_sub_intent = self._refine_sub_intent(extracted)
        if new_sub_intent:
            old_sub = self._routing_decision.sub_intent
            self._routing_decision.sub_intent = new_sub_intent
            logger.info(
                f"Sub-intent refined: {old_sub} → {new_sub_intent}"
            )

        # 5. Recalculate completeness
        new_completeness = self._calculate_completeness()
        self._routing_decision.completeness = new_completeness

        logger.debug(
            f"Context updated: extracted={list(extracted.keys())}, "
            f"completeness={new_completeness.completeness_score:.2f}, "
            f"is_complete={new_completeness.is_complete}"
        )

        return self._routing_decision

    def add_assistant_turn(self, content: str) -> None:
        """
        Add assistant response to dialog history.

        Args:
            content: Assistant's response content
        """
        turn = DialogTurn(
            role="assistant",
            content=content,
            context_snapshot={
                "intent_category": (
                    self._routing_decision.intent_category.value
                    if self._routing_decision else None
                ),
                "sub_intent": (
                    self._routing_decision.sub_intent
                    if self._routing_decision else None
                ),
            },
        )
        self._dialog_history.append(turn)

    def _extract_fields(self, user_response: str) -> Dict[str, Any]:
        """
        Extract field values from user response.

        Uses pattern matching for common IT fields.
        This is a rule-based extraction, NOT LLM-based.

        Args:
            user_response: User's response text

        Returns:
            Dictionary of extracted field values
        """
        extracted: Dict[str, Any] = {}

        # System name patterns
        system_patterns = [
            (r"ETL|etl|Pipeline|pipeline|批次|排程", "ETL"),
            (r"網路|network|網絡|VPN", "網路"),
            (r"ERP|erp|SAP|sap", "ERP"),
            (r"郵件|email|mail|Exchange|Outlook", "郵件系統"),
            (r"API|api|Gateway|gateway|服務|service", "API"),
            (r"資料庫|database|DB|db|SQL|sql|Oracle|oracle", "資料庫"),
            (r"CRM|crm|客戶關係", "CRM"),
            (r"訂單|order|交易|trading", "訂單系統"),
            (r"網站|website|portal|入口", "網站"),
            (r"後台|backend|管理系統|admin", "後台系統"),
        ]
        for pattern, system in system_patterns:
            if re.search(pattern, user_response, re.IGNORECASE):
                extracted["affected_system"] = system
                break

        # Symptom patterns
        symptom_patterns = [
            (r"報錯|error|錯誤|失敗|fail", "報錯"),
            (r"慢|slow|延遲|lag|卡", "效能問題"),
            (r"當機|down|掛|停止|unavailable", "系統當機"),
            (r"斷線|disconnect|連不上|無法連接", "連線問題"),
            (r"超時|timeout|逾時", "超時"),
            (r"登入|login|登錄|認證", "登入問題"),
            (r"異常|abnormal|不正常", "異常"),
        ]
        for pattern, symptom in symptom_patterns:
            if re.search(pattern, user_response, re.IGNORECASE):
                extracted["symptom_type"] = symptom
                break

        # Urgency patterns
        urgency_patterns = [
            (r"緊急|urgent|馬上|立刻|asap|critical", "緊急"),
            (r"嚴重|影響業務|影響生產|客戶影響", "嚴重"),
            (r"一般|正常|普通", "一般"),
        ]
        for pattern, urgency in urgency_patterns:
            if re.search(pattern, user_response, re.IGNORECASE):
                extracted["urgency"] = urgency
                break

        # Request type patterns
        request_patterns = [
            (r"帳號|account|用戶", "帳號"),
            (r"權限|access|permission|存取", "權限"),
            (r"軟體|software|安裝|install", "軟體"),
            (r"設備|hardware|電腦|laptop", "設備"),
            (r"密碼|password|重設|reset", "密碼重設"),
            (r"VPN", "VPN"),
        ]
        for pattern, req_type in request_patterns:
            if re.search(pattern, user_response, re.IGNORECASE):
                extracted["request_type"] = req_type
                break

        # Change type patterns
        change_patterns = [
            (r"部署|deploy|發布|release", "部署"),
            (r"配置|config|設定", "配置"),
            (r"升級|upgrade|更新|update", "升級"),
            (r"遷移|migration|搬遷", "遷移"),
        ]
        for pattern, change_type in change_patterns:
            if re.search(pattern, user_response, re.IGNORECASE):
                extracted["change_type"] = change_type
                break

        # Extract error message (quoted text or specific patterns)
        error_match = re.search(
            r'[「「"\'](.*?)[」」"\']|error[：:]\s*(.+?)(?:[。,，]|$)',
            user_response,
            re.IGNORECASE,
        )
        if error_match:
            error_msg = error_match.group(1) or error_match.group(2)
            if error_msg:
                extracted["error_message"] = error_msg.strip()

        # Extract requester (name patterns)
        requester_match = re.search(
            r'(?:申請人|用戶|使用者|員工)[：:]\s*([^\s,，。]+)|'
            r'(?:幫|為|給)\s*([^\s,，。]+)\s*(?:申請|開)',
            user_response,
        )
        if requester_match:
            requester = requester_match.group(1) or requester_match.group(2)
            if requester:
                extracted["requester"] = requester.strip()

        # Extract justification
        justification_match = re.search(
            r'(?:因為|由於|為了|原因)[：:]?\s*(.+?)(?:[。,，]|$)',
            user_response,
        )
        if justification_match:
            extracted["justification"] = justification_match.group(1).strip()

        # Extract target system for changes
        target_match = re.search(
            r'(?:目標|對象|在)\s*([^\s,，。]+)\s*(?:上|中|系統)?',
            user_response,
        )
        if target_match and "target_system" not in extracted:
            extracted["target_system"] = target_match.group(1).strip()

        return extracted

    def _refine_sub_intent(self, extracted: Dict[str, Any]) -> Optional[str]:
        """
        Refine sub_intent based on extracted information.

        Uses rule-based refinement, NOT LLM re-classification.

        Args:
            extracted: Newly extracted information

        Returns:
            New sub_intent if a rule matches, None otherwise
        """
        if not self._routing_decision:
            return None

        category = self._routing_decision.intent_category
        current_sub = self._routing_decision.sub_intent or "general"

        # Merge with all collected info for rule matching
        all_info = {**self._collected_info, **extracted}

        # Find matching rule
        rule = self.refinement_rules.find_rule(
            category=category,
            current_sub_intent=current_sub,
            extracted_info=all_info,
        )

        return rule.to_sub_intent if rule else None

    def _calculate_completeness(self) -> CompletenessInfo:
        """
        Recalculate completeness based on all collected information.

        Returns:
            Updated CompletenessInfo
        """
        if not self._routing_decision:
            return CompletenessInfo()

        # Use completeness checker with collected info
        return self._completeness_checker.check(
            intent_category=self._routing_decision.intent_category,
            user_input="",  # Not used when collected_info is provided
            collected_info=self._collected_info,
        )

    def get_missing_fields(self) -> List[str]:
        """
        Get list of missing required fields.

        Returns:
            List of missing field names
        """
        if not self._routing_decision:
            return []

        completeness = self._calculate_completeness()
        return completeness.missing_fields

    def get_collected_fields(self) -> List[str]:
        """
        Get list of fields already collected.

        Returns:
            List of collected field names
        """
        return list(self._collected_info.keys())

    def is_complete(self) -> bool:
        """
        Check if information collection is complete.

        Returns:
            True if completeness threshold is met
        """
        if not self._routing_decision:
            return False

        # If we have collected info, recalculate completeness
        # Otherwise, use the routing decision's initial completeness
        if self._collected_info:
            completeness = self._calculate_completeness()
            return completeness.is_complete
        else:
            return self._routing_decision.completeness.is_complete

    def get_state(self) -> ContextState:
        """
        Get current context state.

        Returns:
            ContextState with current information
        """
        return ContextState(
            routing_decision=self._routing_decision,
            collected_info=self._collected_info.copy(),
            turn_count=len(self._dialog_history),
        )

    def reset(self) -> None:
        """Reset context to initial state."""
        self._routing_decision = None
        self._collected_info = {}
        self._dialog_history = []
        self._initialized = False


class MockConversationContextManager(ConversationContextManager):
    """
    Mock context manager for testing.

    Provides deterministic behavior based on input length.
    """

    def __init__(self, **kwargs):
        """Initialize mock context manager."""
        super().__init__(**kwargs)
        self._mock_completeness_score = 0.5

    def update_with_user_response(
        self,
        user_response: str,
    ) -> RoutingDecision:
        """
        Mock update with deterministic behavior.

        Args:
            user_response: User's response text

        Returns:
            Updated RoutingDecision with mock values
        """
        if not self._initialized or not self._routing_decision:
            raise RuntimeError("Context not initialized")

        # Simple heuristic based on response length
        response_length = len(user_response)

        if response_length >= 30:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.3)
        elif response_length >= 15:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.2)
        else:
            self._mock_completeness_score = min(1.0, self._mock_completeness_score + 0.1)

        # Update completeness
        self._routing_decision.completeness = CompletenessInfo(
            is_complete=self._mock_completeness_score >= 0.6,
            completeness_score=self._mock_completeness_score,
            missing_fields=[] if self._mock_completeness_score >= 0.6 else ["details"],
        )

        # Mock sub_intent refinement
        if "ETL" in user_response.upper() or "etl" in user_response:
            self._routing_decision.sub_intent = "etl_failure"
        elif "網路" in user_response or "network" in user_response.lower():
            self._routing_decision.sub_intent = "network_failure"

        return self._routing_decision


# =============================================================================
# Factory Functions
# =============================================================================

def create_context_manager(
    refinement_rules: Optional[RefinementRules] = None,
    completeness_rules: Optional[CompletenessRules] = None,
) -> ConversationContextManager:
    """
    Factory function to create a ConversationContextManager.

    Args:
        refinement_rules: Custom refinement rules (optional)
        completeness_rules: Custom completeness rules (optional)

    Returns:
        ConversationContextManager instance
    """
    return ConversationContextManager(
        refinement_rules=refinement_rules,
        completeness_rules=completeness_rules,
    )


def create_mock_context_manager() -> MockConversationContextManager:
    """
    Factory function to create a mock context manager for testing.

    Returns:
        MockConversationContextManager instance
    """
    return MockConversationContextManager()


# =============================================================================
# Redis Session Storage
# =============================================================================


class RedisDialogSessionStorage:
    """
    Redis-based storage for dialog sessions.

    Provides persistent storage with TTL-based expiration.

    Key Format:
        - dialog_session:{session_id} -> Session state JSON

    TTL:
        - Default: 30 minutes (configurable)
    """

    DEFAULT_TTL = 30 * 60  # 30 minutes

    def __init__(
        self,
        redis_client: Any,
        key_prefix: str = "dialog_session",
        ttl_seconds: int = DEFAULT_TTL,
    ):
        """
        Initialize Redis storage.

        Args:
            redis_client: Redis client instance
            key_prefix: Prefix for all keys
            ttl_seconds: TTL for sessions
        """
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.ttl_seconds = ttl_seconds

    def _session_key(self, session_id: str) -> str:
        """Generate key for session."""
        return f"{self.key_prefix}:{session_id}"

    async def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        Save session state to Redis.

        Args:
            session_id: Session identifier
            state: Session state dictionary
        """
        key = self._session_key(session_id)
        data = json.dumps(state, default=str)
        await self.redis.setex(key, self.ttl_seconds, data)
        logger.debug(f"Saved dialog session: {session_id}")

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session state from Redis.

        Args:
            session_id: Session identifier

        Returns:
            Session state or None if not found
        """
        key = self._session_key(session_id)
        data = await self.redis.get(key)

        if not data:
            return None

        try:
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize session: {e}")
            return None

    async def delete_session(self, session_id: str) -> None:
        """
        Delete session from Redis.

        Args:
            session_id: Session identifier
        """
        key = self._session_key(session_id)
        await self.redis.delete(key)
        logger.debug(f"Deleted dialog session: {session_id}")

    async def touch_session(self, session_id: str) -> None:
        """
        Update session TTL (keep alive).

        Args:
            session_id: Session identifier
        """
        key = self._session_key(session_id)
        await self.redis.expire(key, self.ttl_seconds)
        logger.debug(f"Touched dialog session: {session_id}")

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists
        """
        key = self._session_key(session_id)
        return await self.redis.exists(key) > 0


# =============================================================================
# In-Memory Session Storage
# =============================================================================


class InMemoryDialogSessionStorage:
    """
    In-memory storage for dialog sessions.

    Suitable for testing and development. Not persistent across restarts.
    """

    def __init__(self, ttl_seconds: int = 30 * 60):
        """Initialize in-memory storage."""
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}
        self.ttl_seconds = ttl_seconds

    async def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """Save session state."""
        self._sessions[session_id] = state
        self._expiry[session_id] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state by ID."""
        # Check expiry
        if session_id in self._expiry:
            if datetime.utcnow() > self._expiry[session_id]:
                await self.delete_session(session_id)
                return None
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> None:
        """Delete session."""
        self._sessions.pop(session_id, None)
        self._expiry.pop(session_id, None)

    async def touch_session(self, session_id: str) -> None:
        """Update session expiry."""
        if session_id in self._sessions:
            self._expiry[session_id] = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

    def clear(self) -> None:
        """Clear all sessions."""
        self._sessions.clear()
        self._expiry.clear()


# =============================================================================
# Enhanced Context Manager with Persistence
# =============================================================================


class PersistentConversationContextManager(ConversationContextManager):
    """
    Enhanced ConversationContextManager with Redis persistence support.

    Features:
    - Session persistence with Redis
    - Automatic timeout handling
    - Session recovery
    - Maximum turn limit enforcement

    Example:
        >>> storage = RedisDialogSessionStorage(redis_client)
        >>> manager = PersistentConversationContextManager(storage=storage)
        >>> session_id = await manager.create_session(routing_decision)
        >>> # ... later, recover session ...
        >>> await manager.resume_session(session_id)
        >>> decision = manager.update_with_user_response("ETL 系統報錯")
    """

    def __init__(
        self,
        storage: Optional[DialogSessionStorage] = None,
        config: Optional[DialogSessionConfig] = None,
        refinement_rules: Optional[RefinementRules] = None,
        completeness_rules: Optional[CompletenessRules] = None,
    ):
        """
        Initialize persistent context manager.

        Args:
            storage: Session storage backend (uses in-memory if None)
            config: Session configuration
            refinement_rules: Rules for sub_intent refinement
            completeness_rules: Rules for completeness checking
        """
        super().__init__(
            refinement_rules=refinement_rules,
            completeness_rules=completeness_rules,
        )
        self.storage = storage or InMemoryDialogSessionStorage()
        self.config = config or DialogSessionConfig()

        # Session state
        self._session_id: Optional[str] = None
        self._session_created_at: Optional[datetime] = None
        self._last_activity: Optional[datetime] = None

    @property
    def session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self._session_id

    @property
    def turn_count(self) -> int:
        """Get current turn count."""
        return len(self._dialog_history)

    @property
    def is_max_turns_reached(self) -> bool:
        """Check if maximum turns reached."""
        return self.turn_count >= self.config.max_turns

    @property
    def is_session_expired(self) -> bool:
        """Check if session has expired due to inactivity."""
        if not self._last_activity:
            return False
        timeout = timedelta(minutes=self.config.timeout_minutes)
        return datetime.utcnow() > self._last_activity + timeout

    async def create_session(
        self,
        routing_decision: RoutingDecision,
        session_id: Optional[str] = None,
    ) -> str:
        """
        Create a new dialog session.

        Args:
            routing_decision: Initial routing decision
            session_id: Optional custom session ID

        Returns:
            Session ID
        """
        # Generate or use provided session ID
        self._session_id = session_id or str(uuid.uuid4())
        self._session_created_at = datetime.utcnow()
        self._last_activity = datetime.utcnow()

        # Initialize parent context
        self.initialize(routing_decision)

        # Persist session
        await self._save_session()

        logger.info(f"Created dialog session: {self._session_id}")
        return self._session_id

    async def resume_session(self, session_id: str) -> bool:
        """
        Resume an existing dialog session.

        Args:
            session_id: Session ID to resume

        Returns:
            True if session resumed successfully, False if not found or expired
        """
        state = await self.storage.get_session(session_id)
        if not state:
            logger.warning(f"Session not found: {session_id}")
            return False

        # Check expiration
        last_activity_str = state.get("last_activity")
        if last_activity_str:
            last_activity = datetime.fromisoformat(last_activity_str)
            timeout = timedelta(minutes=self.config.timeout_minutes)
            if self.config.auto_expire and datetime.utcnow() > last_activity + timeout:
                logger.warning(f"Session expired: {session_id}")
                await self.storage.delete_session(session_id)
                return False

        # Restore state
        self._session_id = session_id
        self._restore_from_state(state)
        self._last_activity = datetime.utcnow()

        # Touch session to extend TTL
        await self.storage.touch_session(session_id)

        logger.info(f"Resumed dialog session: {session_id}")
        return True

    def update_with_user_response(self, user_response: str) -> RoutingDecision:
        """
        Update context with user response.

        Overrides parent to add turn limit check and auto-persist.

        Args:
            user_response: User's response text

        Returns:
            Updated RoutingDecision

        Raises:
            RuntimeError: If context not initialized or max turns reached
        """
        if self.is_max_turns_reached:
            raise RuntimeError(
                f"Maximum turns ({self.config.max_turns}) reached. "
                "Session should be concluded."
            )

        if self.is_session_expired:
            raise RuntimeError(
                f"Session expired (timeout: {self.config.timeout_minutes} minutes). "
                "Please start a new session."
            )

        # Update last activity
        self._last_activity = datetime.utcnow()

        # Call parent method
        result = super().update_with_user_response(user_response)

        return result

    async def update_with_user_response_async(
        self,
        user_response: str,
    ) -> RoutingDecision:
        """
        Update context with user response and persist.

        Args:
            user_response: User's response text

        Returns:
            Updated RoutingDecision
        """
        result = self.update_with_user_response(user_response)

        # Persist updated state
        if self.config.persist_history:
            await self._save_session()

        return result

    async def end_session(self, reason: str = "completed") -> None:
        """
        End the current session.

        Args:
            reason: Reason for ending session
        """
        if self._session_id:
            logger.info(f"Ending dialog session: {self._session_id} (reason: {reason})")

            # Add final event to history
            self._dialog_history.append(
                DialogTurn(
                    role="system",
                    content=f"Session ended: {reason}",
                    context_snapshot={
                        "turn_count": self.turn_count,
                        "is_complete": self.is_complete(),
                    },
                )
            )

            # Final save before deletion (for audit)
            await self._save_session()

            # Delete session
            if self.config.auto_expire:
                await self.storage.delete_session(self._session_id)

            self._session_id = None

    async def _save_session(self) -> None:
        """Save current session state."""
        if not self._session_id:
            return

        state = self._to_state_dict()
        await self.storage.save_session(self._session_id, state)

    def _to_state_dict(self) -> Dict[str, Any]:
        """Convert current state to dictionary for persistence."""
        return {
            "session_id": self._session_id,
            "created_at": self._session_created_at.isoformat() if self._session_created_at else None,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "routing_decision": self._routing_decision.to_dict() if self._routing_decision else None,
            "collected_info": self._collected_info,
            "dialog_history": [turn.to_dict() for turn in self._dialog_history],
            "initialized": self._initialized,
        }

    def _restore_from_state(self, state: Dict[str, Any]) -> None:
        """Restore state from dictionary."""
        self._session_created_at = (
            datetime.fromisoformat(state["created_at"])
            if state.get("created_at") else None
        )
        self._last_activity = (
            datetime.fromisoformat(state["last_activity"])
            if state.get("last_activity") else None
        )

        # Restore routing decision
        if state.get("routing_decision"):
            self._routing_decision = RoutingDecision.from_dict(state["routing_decision"])

        # Restore collected info
        self._collected_info = state.get("collected_info", {})

        # Restore dialog history
        self._dialog_history = [
            DialogTurn(
                role=turn["role"],
                content=turn["content"],
                timestamp=datetime.fromisoformat(turn["timestamp"]),
                extracted=turn.get("extracted", {}),
                context_snapshot=turn.get("context_snapshot", {}),
            )
            for turn in state.get("dialog_history", [])
        ]

        self._initialized = state.get("initialized", False)

    def get_session_info(self) -> Dict[str, Any]:
        """Get session information and statistics."""
        return {
            "session_id": self._session_id,
            "created_at": self._session_created_at.isoformat() if self._session_created_at else None,
            "last_activity": self._last_activity.isoformat() if self._last_activity else None,
            "turn_count": self.turn_count,
            "max_turns": self.config.max_turns,
            "turns_remaining": max(0, self.config.max_turns - self.turn_count),
            "is_complete": self.is_complete(),
            "is_expired": self.is_session_expired,
            "is_max_turns_reached": self.is_max_turns_reached,
            "collected_fields": list(self._collected_info.keys()),
            "missing_fields": self.get_missing_fields(),
        }


# =============================================================================
# Factory Functions (Extended)
# =============================================================================


def create_persistent_context_manager(
    storage: Optional[DialogSessionStorage] = None,
    config: Optional[DialogSessionConfig] = None,
) -> PersistentConversationContextManager:
    """
    Factory function to create a persistent context manager.

    Args:
        storage: Session storage backend
        config: Session configuration

    Returns:
        PersistentConversationContextManager instance
    """
    return PersistentConversationContextManager(
        storage=storage,
        config=config,
    )


def create_redis_dialog_storage(
    redis_client: Any,
    key_prefix: str = "dialog_session",
    ttl_seconds: int = 30 * 60,
) -> RedisDialogSessionStorage:
    """
    Factory function to create Redis dialog storage.

    Args:
        redis_client: Redis client instance
        key_prefix: Key prefix for storage
        ttl_seconds: TTL for sessions

    Returns:
        RedisDialogSessionStorage instance
    """
    return RedisDialogSessionStorage(
        redis_client=redis_client,
        key_prefix=key_prefix,
        ttl_seconds=ttl_seconds,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Config
    "DialogSessionConfig",
    # Data classes
    "DialogTurn",
    "ContextState",
    # Protocols
    "DialogSessionStorage",
    # Storage implementations
    "RedisDialogSessionStorage",
    "InMemoryDialogSessionStorage",
    # Context managers
    "ConversationContextManager",
    "MockConversationContextManager",
    "PersistentConversationContextManager",
    # Factory functions
    "create_context_manager",
    "create_mock_context_manager",
    "create_persistent_context_manager",
    "create_redis_dialog_storage",
]

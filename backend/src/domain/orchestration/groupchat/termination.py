# =============================================================================
# IPA Platform - GroupChat Termination Checker
# =============================================================================
# Sprint 9: S9-1 GroupChatManager (8 points)
#
# Termination condition management for group chat conversations.
# Supports multiple termination types and custom conditions.
# =============================================================================

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Pattern, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.orchestration.groupchat.manager import GroupChatState

logger = logging.getLogger(__name__)


class TerminationType(str, Enum):
    """Types of termination conditions.

    終止條件類型:
    - MAX_ROUNDS: 達到最大輪次
    - MAX_MESSAGES: 達到最大訊息數
    - TIMEOUT: 超時
    - KEYWORD: 關鍵字觸發
    - PATTERN: 正則表達式匹配
    - CONSENSUS: 達成共識
    - CUSTOM: 自定義條件
    - EXPLICIT: 顯式終止命令
    - NO_PROGRESS: 無進展（相同回應重複）
    """
    MAX_ROUNDS = "max_rounds"
    MAX_MESSAGES = "max_messages"
    TIMEOUT = "timeout"
    KEYWORD = "keyword"
    PATTERN = "pattern"
    CONSENSUS = "consensus"
    CUSTOM = "custom"
    EXPLICIT = "explicit"
    NO_PROGRESS = "no_progress"


@dataclass
class TerminationCondition:
    """Represents a termination condition.

    終止條件數據類。

    Attributes:
        condition_id: 條件唯一標識符
        condition_type: 條件類型
        parameters: 條件參數
        priority: 優先級（數值越小優先級越高）
        description: 條件描述
        is_enabled: 是否啟用
    """
    condition_id: str
    condition_type: TerminationType
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    description: str = ""
    is_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "condition_id": self.condition_id,
            "condition_type": self.condition_type.value,
            "parameters": self.parameters,
            "priority": self.priority,
            "description": self.description,
            "is_enabled": self.is_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TerminationCondition":
        """Create from dictionary."""
        return cls(
            condition_id=data["condition_id"],
            condition_type=TerminationType(data["condition_type"]),
            parameters=data.get("parameters", {}),
            priority=data.get("priority", 0),
            description=data.get("description", ""),
            is_enabled=data.get("is_enabled", True),
        )


@dataclass
class TerminationResult:
    """Result of termination check.

    終止檢查結果。

    Attributes:
        should_terminate: 是否應該終止
        reason: 終止原因
        condition_id: 觸發的條件 ID
        condition_type: 觸發的條件類型
        details: 詳細信息
    """
    should_terminate: bool
    reason: str = ""
    condition_id: Optional[str] = None
    condition_type: Optional[TerminationType] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "should_terminate": self.should_terminate,
            "reason": self.reason,
            "condition_id": self.condition_id,
            "condition_type": self.condition_type.value if self.condition_type else None,
            "details": self.details,
        }


class TerminationChecker:
    """Manages and evaluates termination conditions for group chats.

    終止條件管理器，負責評估群組聊天是否應該終止。

    支援多種終止條件:
    - 輪次限制
    - 訊息數限制
    - 超時
    - 關鍵字觸發
    - 正則表達式匹配
    - 共識達成
    - 自定義條件
    - 無進展檢測

    Example:
        ```python
        checker = TerminationChecker()

        # 添加終止條件
        checker.add_condition(TerminationCondition(
            condition_id="keyword-1",
            condition_type=TerminationType.KEYWORD,
            parameters={"keywords": ["DONE", "TERMINATE", "END"]}
        ))

        # 檢查是否應該終止
        result = await checker.should_terminate(group_state)
        if result.should_terminate:
            print(f"Terminating: {result.reason}")
        ```
    """

    # Default termination keywords
    DEFAULT_KEYWORDS = [
        "TERMINATE",
        "DONE",
        "END CONVERSATION",
        "TASK COMPLETE",
        "完成",
        "結束",
    ]

    def __init__(self):
        """Initialize the TerminationChecker."""
        self._conditions: Dict[str, TerminationCondition] = {}
        self._custom_checkers: Dict[str, Callable] = {}
        self._compiled_patterns: Dict[str, Pattern] = {}

        logger.info("TerminationChecker initialized")

    # =========================================================================
    # Condition Management
    # =========================================================================

    def add_condition(self, condition: TerminationCondition) -> None:
        """Add a termination condition.

        Args:
            condition: 終止條件
        """
        self._conditions[condition.condition_id] = condition

        # Pre-compile patterns for efficiency
        if condition.condition_type == TerminationType.PATTERN:
            pattern = condition.parameters.get("pattern", "")
            if pattern:
                flags = 0
                if condition.parameters.get("case_insensitive", True):
                    flags = re.IGNORECASE
                self._compiled_patterns[condition.condition_id] = re.compile(pattern, flags)

        logger.debug(f"Added termination condition: {condition.condition_id}")

    def remove_condition(self, condition_id: str) -> bool:
        """Remove a termination condition.

        Args:
            condition_id: 條件 ID

        Returns:
            是否成功移除
        """
        if condition_id in self._conditions:
            del self._conditions[condition_id]
            self._compiled_patterns.pop(condition_id, None)
            self._custom_checkers.pop(condition_id, None)
            logger.debug(f"Removed termination condition: {condition_id}")
            return True
        return False

    def get_condition(self, condition_id: str) -> Optional[TerminationCondition]:
        """Get a termination condition by ID.

        Args:
            condition_id: 條件 ID

        Returns:
            終止條件
        """
        return self._conditions.get(condition_id)

    def list_conditions(
        self,
        enabled_only: bool = False,
    ) -> List[TerminationCondition]:
        """List all termination conditions.

        Args:
            enabled_only: 只列出啟用的條件

        Returns:
            條件列表
        """
        conditions = list(self._conditions.values())
        if enabled_only:
            conditions = [c for c in conditions if c.is_enabled]
        return sorted(conditions, key=lambda c: c.priority)

    def enable_condition(self, condition_id: str) -> bool:
        """Enable a termination condition.

        Args:
            condition_id: 條件 ID

        Returns:
            是否成功啟用
        """
        condition = self._conditions.get(condition_id)
        if condition:
            condition.is_enabled = True
            return True
        return False

    def disable_condition(self, condition_id: str) -> bool:
        """Disable a termination condition.

        Args:
            condition_id: 條件 ID

        Returns:
            是否成功禁用
        """
        condition = self._conditions.get(condition_id)
        if condition:
            condition.is_enabled = False
            return True
        return False

    def register_custom_checker(
        self,
        condition_id: str,
        checker: Callable[["GroupChatState"], bool],
    ) -> None:
        """Register a custom termination checker.

        Args:
            condition_id: 條件 ID
            checker: 自定義檢查函數
        """
        self._custom_checkers[condition_id] = checker

    # =========================================================================
    # Termination Evaluation
    # =========================================================================

    async def should_terminate(
        self,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check if the conversation should terminate.

        檢查對話是否應該終止。

        Args:
            state: 群組聊天狀態

        Returns:
            終止檢查結果
        """
        # Get enabled conditions sorted by priority
        conditions = self.list_conditions(enabled_only=True)

        for condition in conditions:
            result = await self._evaluate_condition(condition, state)
            if result.should_terminate:
                logger.info(
                    f"Termination triggered by {condition.condition_id}: {result.reason}"
                )
                return result

        return TerminationResult(should_terminate=False)

    async def _evaluate_condition(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Evaluate a single termination condition.

        評估單個終止條件。
        """
        evaluators = {
            TerminationType.MAX_ROUNDS: self._check_max_rounds,
            TerminationType.MAX_MESSAGES: self._check_max_messages,
            TerminationType.TIMEOUT: self._check_timeout,
            TerminationType.KEYWORD: self._check_keyword,
            TerminationType.PATTERN: self._check_pattern,
            TerminationType.CONSENSUS: self._check_consensus,
            TerminationType.CUSTOM: self._check_custom,
            TerminationType.EXPLICIT: self._check_explicit,
            TerminationType.NO_PROGRESS: self._check_no_progress,
        }

        evaluator = evaluators.get(condition.condition_type)
        if evaluator:
            return await evaluator(condition, state)

        return TerminationResult(should_terminate=False)

    # =========================================================================
    # Individual Condition Checkers
    # =========================================================================

    async def _check_max_rounds(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check max rounds condition."""
        max_rounds = condition.parameters.get("max_rounds", state.config.max_rounds)

        if state.current_round > max_rounds:
            return TerminationResult(
                should_terminate=True,
                reason=f"Maximum rounds ({max_rounds}) reached",
                condition_id=condition.condition_id,
                condition_type=TerminationType.MAX_ROUNDS,
                details={"max_rounds": max_rounds, "current_round": state.current_round},
            )

        return TerminationResult(should_terminate=False)

    async def _check_max_messages(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check max messages condition."""
        max_messages = condition.parameters.get("max_messages", 100)
        current_count = state.message_count

        if current_count >= max_messages:
            return TerminationResult(
                should_terminate=True,
                reason=f"Maximum messages ({max_messages}) reached",
                condition_id=condition.condition_id,
                condition_type=TerminationType.MAX_MESSAGES,
                details={"max_messages": max_messages, "current_count": current_count},
            )

        return TerminationResult(should_terminate=False)

    async def _check_timeout(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check timeout condition."""
        timeout_seconds = condition.parameters.get(
            "timeout_seconds",
            state.config.timeout_seconds,
        )

        if state.started_at:
            elapsed = (datetime.utcnow() - state.started_at).total_seconds()
            if elapsed > timeout_seconds:
                return TerminationResult(
                    should_terminate=True,
                    reason=f"Conversation timeout ({timeout_seconds}s) exceeded",
                    condition_id=condition.condition_id,
                    condition_type=TerminationType.TIMEOUT,
                    details={"timeout_seconds": timeout_seconds, "elapsed": elapsed},
                )

        return TerminationResult(should_terminate=False)

    async def _check_keyword(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check keyword termination condition."""
        keywords = condition.parameters.get("keywords", self.DEFAULT_KEYWORDS)
        case_sensitive = condition.parameters.get("case_sensitive", False)
        check_last_n = condition.parameters.get("check_last_n", 1)

        # Get last N messages
        messages_to_check = state.messages[-check_last_n:] if state.messages else []

        for message in messages_to_check:
            content = message.content
            if not case_sensitive:
                content = content.lower()

            for keyword in keywords:
                check_keyword = keyword if case_sensitive else keyword.lower()
                if check_keyword in content:
                    return TerminationResult(
                        should_terminate=True,
                        reason=f"Termination keyword '{keyword}' found",
                        condition_id=condition.condition_id,
                        condition_type=TerminationType.KEYWORD,
                        details={
                            "keyword": keyword,
                            "message_id": message.id,
                            "sender": message.sender_name,
                        },
                    )

        return TerminationResult(should_terminate=False)

    async def _check_pattern(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check regex pattern termination condition."""
        pattern = self._compiled_patterns.get(condition.condition_id)
        if not pattern:
            return TerminationResult(should_terminate=False)

        check_last_n = condition.parameters.get("check_last_n", 1)
        messages_to_check = state.messages[-check_last_n:] if state.messages else []

        for message in messages_to_check:
            match = pattern.search(message.content)
            if match:
                return TerminationResult(
                    should_terminate=True,
                    reason=f"Termination pattern matched: {match.group()}",
                    condition_id=condition.condition_id,
                    condition_type=TerminationType.PATTERN,
                    details={
                        "pattern": condition.parameters.get("pattern"),
                        "matched": match.group(),
                        "message_id": message.id,
                    },
                )

        return TerminationResult(should_terminate=False)

    async def _check_consensus(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check consensus termination condition."""
        threshold = condition.parameters.get("threshold", state.config.consensus_threshold)
        agreement_keyword = condition.parameters.get("agreement_keyword", "agree")
        check_last_n = condition.parameters.get("check_last_n", 5)

        if not state.agents:
            return TerminationResult(should_terminate=False)

        # Get last N messages from agents
        agent_messages = [
            m for m in state.messages[-check_last_n:]
            if m.sender_id in [a.agent_id for a in state.agents]
        ]

        if not agent_messages:
            return TerminationResult(should_terminate=False)

        # Count agreements
        agreement_count = sum(
            1 for m in agent_messages
            if agreement_keyword.lower() in m.content.lower()
        )

        agreement_ratio = agreement_count / len(state.agents)

        if agreement_ratio >= threshold:
            return TerminationResult(
                should_terminate=True,
                reason=f"Consensus reached ({agreement_ratio:.1%} >= {threshold:.1%})",
                condition_id=condition.condition_id,
                condition_type=TerminationType.CONSENSUS,
                details={
                    "threshold": threshold,
                    "agreement_ratio": agreement_ratio,
                    "agreement_count": agreement_count,
                    "total_agents": len(state.agents),
                },
            )

        return TerminationResult(should_terminate=False)

    async def _check_custom(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check custom termination condition."""
        checker = self._custom_checkers.get(condition.condition_id)
        if not checker:
            return TerminationResult(should_terminate=False)

        try:
            should_terminate = checker(state)
            if should_terminate:
                return TerminationResult(
                    should_terminate=True,
                    reason="Custom termination condition met",
                    condition_id=condition.condition_id,
                    condition_type=TerminationType.CUSTOM,
                )
        except Exception as e:
            logger.error(f"Custom checker error for {condition.condition_id}: {e}")

        return TerminationResult(should_terminate=False)

    async def _check_explicit(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check explicit termination command."""
        commands = condition.parameters.get("commands", ["/terminate", "/end", "/stop"])
        check_last_n = condition.parameters.get("check_last_n", 1)

        messages_to_check = state.messages[-check_last_n:] if state.messages else []

        for message in messages_to_check:
            content = message.content.strip().lower()
            for command in commands:
                if content == command.lower() or content.startswith(f"{command.lower()} "):
                    return TerminationResult(
                        should_terminate=True,
                        reason=f"Explicit termination command: {command}",
                        condition_id=condition.condition_id,
                        condition_type=TerminationType.EXPLICIT,
                        details={
                            "command": command,
                            "message_id": message.id,
                            "sender": message.sender_name,
                        },
                    )

        return TerminationResult(should_terminate=False)

    async def _check_no_progress(
        self,
        condition: TerminationCondition,
        state: "GroupChatState",
    ) -> TerminationResult:
        """Check for no progress (repeated similar responses)."""
        threshold = condition.parameters.get("similarity_threshold", 0.9)
        check_last_n = condition.parameters.get("check_last_n", 3)
        min_repeats = condition.parameters.get("min_repeats", 3)

        if len(state.messages) < min_repeats:
            return TerminationResult(should_terminate=False)

        # Get last N agent messages
        agent_messages = [
            m for m in state.messages[-check_last_n:]
            if m.sender_id in [a.agent_id for a in state.agents]
        ]

        if len(agent_messages) < min_repeats:
            return TerminationResult(should_terminate=False)

        # Simple check: exact content matching
        contents = [m.content.strip().lower() for m in agent_messages]
        unique_contents = set(contents)

        if len(unique_contents) == 1 and len(contents) >= min_repeats:
            return TerminationResult(
                should_terminate=True,
                reason=f"No progress detected: {min_repeats} similar messages",
                condition_id=condition.condition_id,
                condition_type=TerminationType.NO_PROGRESS,
                details={
                    "repeated_content": contents[0][:50] + "..." if len(contents[0]) > 50 else contents[0],
                    "repeat_count": len(contents),
                },
            )

        return TerminationResult(should_terminate=False)

    # =========================================================================
    # Factory Methods
    # =========================================================================

    @classmethod
    def create_default(cls) -> "TerminationChecker":
        """Create a TerminationChecker with default conditions.

        創建帶有預設條件的終止檢查器。

        Returns:
            TerminationChecker 實例
        """
        checker = cls()

        # Add default conditions
        checker.add_condition(TerminationCondition(
            condition_id="default-max-rounds",
            condition_type=TerminationType.MAX_ROUNDS,
            parameters={"max_rounds": 10},
            priority=10,
            description="Maximum 10 rounds",
        ))

        checker.add_condition(TerminationCondition(
            condition_id="default-timeout",
            condition_type=TerminationType.TIMEOUT,
            parameters={"timeout_seconds": 300},
            priority=5,
            description="5 minute timeout",
        ))

        checker.add_condition(TerminationCondition(
            condition_id="default-keyword",
            condition_type=TerminationType.KEYWORD,
            parameters={"keywords": cls.DEFAULT_KEYWORDS},
            priority=1,
            description="Default termination keywords",
        ))

        checker.add_condition(TerminationCondition(
            condition_id="default-explicit",
            condition_type=TerminationType.EXPLICIT,
            parameters={"commands": ["/terminate", "/end", "/stop"]},
            priority=0,
            description="Explicit termination commands",
        ))

        return checker

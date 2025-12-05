# =============================================================================
# IPA Platform - Speaker Selector
# =============================================================================
# Sprint 9: S9-2 SpeakerSelector (5 points)
#
# Manages speaker selection strategies for group chat conversations.
# Supports 6 selection methods: AUTO, ROUND_ROBIN, RANDOM, MANUAL, PRIORITY, EXPERTISE
# =============================================================================

from __future__ import annotations

import logging
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.orchestration.groupchat.manager import (
        AgentInfo,
        GroupChatState,
        GroupMessage,
    )

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Available speaker selection strategies.

    發言者選擇策略:
    - AUTO: LLM 自動選擇最適合回應的 Agent
    - ROUND_ROBIN: 按順序輪流發言
    - RANDOM: 隨機選擇發言者
    - MANUAL: 用戶手動指定發言者
    - PRIORITY: 按優先級選擇（優先級數值小的先發言）
    - EXPERTISE: 按專業能力匹配選擇（根據訊息內容匹配最相關的 Agent）
    """
    AUTO = "auto"
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    MANUAL = "manual"
    PRIORITY = "priority"
    EXPERTISE = "expertise"


@dataclass
class SelectionContext:
    """Context for speaker selection.

    發言者選擇上下文，提供選擇所需的信息。

    Attributes:
        state: 群組聊天狀態
        candidates: 可選擇的 Agent 列表
        last_speaker_id: 上一位發言者 ID
        last_message: 最後一條訊息
        allow_repeat: 是否允許連續發言
        manual_selection: 手動指定的 Agent ID（MANUAL 模式用）
    """
    state: "GroupChatState"
    candidates: List["AgentInfo"]
    last_speaker_id: Optional[str] = None
    last_message: Optional["GroupMessage"] = None
    allow_repeat: bool = False
    manual_selection: Optional[str] = None


@dataclass
class SelectionResult:
    """Result of speaker selection.

    發言者選擇結果。

    Attributes:
        selected_agent: 選中的 Agent
        strategy_used: 使用的選擇策略
        confidence: 選擇信心度（0-1）
        reason: 選擇原因
        alternatives: 備選 Agent 列表
    """
    selected_agent: Optional["AgentInfo"]
    strategy_used: SelectionStrategy
    confidence: float = 1.0
    reason: str = ""
    alternatives: List["AgentInfo"] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if selection was successful."""
        return self.selected_agent is not None


class BaseSpeakerStrategy(ABC):
    """Base class for speaker selection strategies.

    發言者選擇策略的基類。
    """

    @property
    @abstractmethod
    def strategy_type(self) -> SelectionStrategy:
        """Get the strategy type."""
        pass

    @abstractmethod
    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select the next speaker.

        Args:
            context: 選擇上下文

        Returns:
            選擇結果
        """
        pass


class RoundRobinStrategy(BaseSpeakerStrategy):
    """Round-robin speaker selection strategy.

    輪流發言策略：按順序輪流選擇發言者。
    """

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.ROUND_ROBIN

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select next speaker in round-robin order."""
        if not context.candidates:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No candidates available",
            )

        if not context.last_speaker_id:
            return SelectionResult(
                selected_agent=context.candidates[0],
                strategy_used=self.strategy_type,
                confidence=1.0,
                reason="First speaker in rotation",
            )

        # Use full agent list for proper ordering
        all_agents = context.state.agents
        candidate_ids = {a.agent_id for a in context.candidates}

        # Find current speaker's position
        try:
            current_idx = next(
                i for i, a in enumerate(all_agents)
                if a.agent_id == context.last_speaker_id
            )
        except StopIteration:
            return SelectionResult(
                selected_agent=context.candidates[0],
                strategy_used=self.strategy_type,
                reason="Previous speaker not found, starting from first",
            )

        # Find next available candidate
        for offset in range(1, len(all_agents) + 1):
            next_idx = (current_idx + offset) % len(all_agents)
            next_agent = all_agents[next_idx]
            if next_agent.agent_id in candidate_ids:
                selected = next(
                    a for a in context.candidates
                    if a.agent_id == next_agent.agent_id
                )
                return SelectionResult(
                    selected_agent=selected,
                    strategy_used=self.strategy_type,
                    confidence=1.0,
                    reason=f"Next in rotation after {context.last_speaker_id}",
                )

        # Fallback
        return SelectionResult(
            selected_agent=context.candidates[0],
            strategy_used=self.strategy_type,
            reason="Fallback to first candidate",
        )


class RandomStrategy(BaseSpeakerStrategy):
    """Random speaker selection strategy.

    隨機選擇策略：隨機選擇一位發言者。
    """

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.RANDOM

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select a random speaker."""
        if not context.candidates:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No candidates available",
            )

        selected = random.choice(context.candidates)
        return SelectionResult(
            selected_agent=selected,
            strategy_used=self.strategy_type,
            confidence=1.0,
            reason="Randomly selected",
            alternatives=[a for a in context.candidates if a != selected],
        )


class PriorityStrategy(BaseSpeakerStrategy):
    """Priority-based speaker selection strategy.

    優先級策略：選擇優先級最高（數值最小）的發言者。
    """

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.PRIORITY

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select speaker with highest priority (lowest number)."""
        if not context.candidates:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No candidates available",
            )

        # Sort by priority (lower number = higher priority)
        sorted_candidates = sorted(context.candidates, key=lambda a: a.priority)
        selected = sorted_candidates[0]

        return SelectionResult(
            selected_agent=selected,
            strategy_used=self.strategy_type,
            confidence=1.0,
            reason=f"Highest priority (level {selected.priority})",
            alternatives=sorted_candidates[1:3],  # Top 3 alternatives
        )


class ManualStrategy(BaseSpeakerStrategy):
    """Manual speaker selection strategy.

    手動選擇策略：使用用戶指定的發言者。
    """

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.MANUAL

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select the manually specified speaker."""
        if not context.manual_selection:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No manual selection provided",
            )

        # Find the specified agent
        selected = next(
            (a for a in context.candidates if a.agent_id == context.manual_selection),
            None,
        )

        if selected:
            return SelectionResult(
                selected_agent=selected,
                strategy_used=self.strategy_type,
                confidence=1.0,
                reason=f"Manually selected: {selected.name}",
            )

        return SelectionResult(
            selected_agent=None,
            strategy_used=self.strategy_type,
            reason=f"Specified agent {context.manual_selection} not available",
        )


class ExpertiseStrategy(BaseSpeakerStrategy):
    """Expertise-based speaker selection strategy.

    專業能力策略：根據訊息內容選擇最相關的專業 Agent。
    """

    def __init__(self, expertise_matcher: Optional["ExpertiseMatcher"] = None):
        self._matcher = expertise_matcher or ExpertiseMatcher()

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.EXPERTISE

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select speaker based on expertise matching."""
        if not context.candidates:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No candidates available",
            )

        if not context.last_message:
            return SelectionResult(
                selected_agent=context.candidates[0],
                strategy_used=self.strategy_type,
                reason="No message context for expertise matching",
            )

        # Match expertise
        match_result = await self._matcher.match_expertise(
            message_content=context.last_message.content,
            candidates=context.candidates,
        )

        if match_result:
            return SelectionResult(
                selected_agent=match_result.best_agent,
                strategy_used=self.strategy_type,
                confidence=match_result.score,
                reason=f"Best expertise match (score: {match_result.score:.2f})",
                alternatives=match_result.alternatives[:3],
            )

        return SelectionResult(
            selected_agent=context.candidates[0],
            strategy_used=self.strategy_type,
            reason="No expertise match found, using first candidate",
        )


class AutoStrategy(BaseSpeakerStrategy):
    """LLM-based automatic speaker selection strategy.

    自動選擇策略：使用 LLM 分析對話上下文，智能選擇最適合回應的 Agent。
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        fallback_strategy: Optional[BaseSpeakerStrategy] = None,
    ):
        self._llm_client = llm_client
        self._fallback = fallback_strategy or RoundRobinStrategy()

    @property
    def strategy_type(self) -> SelectionStrategy:
        return SelectionStrategy.AUTO

    async def select(self, context: SelectionContext) -> SelectionResult:
        """Select speaker using LLM analysis."""
        if not context.candidates:
            return SelectionResult(
                selected_agent=None,
                strategy_used=self.strategy_type,
                reason="No candidates available",
            )

        # If no LLM client, fallback to round-robin
        if not self._llm_client:
            result = await self._fallback.select(context)
            result.reason = f"LLM unavailable, fallback: {result.reason}"
            return result

        try:
            # Build selection prompt
            prompt = self._build_selection_prompt(context)

            # Get LLM response
            response = await self._llm_client.complete(prompt)

            # Parse response
            selected_id = self._parse_selection_response(response, context.candidates)

            selected = next(
                (a for a in context.candidates if a.agent_id == selected_id),
                None,
            )

            if selected:
                return SelectionResult(
                    selected_agent=selected,
                    strategy_used=self.strategy_type,
                    confidence=0.9,  # LLM selection has some uncertainty
                    reason=f"LLM selected: {selected.name}",
                    alternatives=[a for a in context.candidates if a != selected][:2],
                )

        except Exception as e:
            logger.error(f"LLM selection failed: {e}")

        # Fallback on error
        result = await self._fallback.select(context)
        result.reason = f"LLM error, fallback: {result.reason}"
        return result

    def _build_selection_prompt(self, context: SelectionContext) -> str:
        """Build the LLM prompt for speaker selection."""
        agents_desc = "\n".join([
            f"- {a.name} (ID: {a.agent_id}): {a.description}"
            + (f" [Capabilities: {', '.join(a.capabilities)}]" if a.capabilities else "")
            for a in context.candidates
        ])

        recent_messages = ""
        if context.state.messages:
            msg_list = context.state.messages[-5:]
            recent_messages = "\n".join([
                f"{m.sender_name}: {m.content[:100]}{'...' if len(m.content) > 100 else ''}"
                for m in msg_list
            ])

        return f"""Based on the conversation context, select the most appropriate agent to speak next.

Available agents:
{agents_desc}

Recent conversation:
{recent_messages}

Consider:
1. Which agent has the most relevant expertise for the current topic?
2. Which agent can best continue or advance the discussion?
3. Has this agent spoken recently? (Avoid selecting the same agent repeatedly)

Respond with ONLY the agent ID of the selected agent, nothing else."""

    def _parse_selection_response(
        self,
        response: str,
        candidates: List["AgentInfo"],
    ) -> str:
        """Parse LLM response to extract agent ID."""
        response = response.strip()

        # Direct ID match
        for agent in candidates:
            if agent.agent_id in response:
                return agent.agent_id

        # Name match (case insensitive)
        response_lower = response.lower()
        for agent in candidates:
            if agent.name.lower() in response_lower:
                return agent.agent_id

        # First candidate as fallback
        return candidates[0].agent_id if candidates else ""


# =============================================================================
# Expertise Matcher
# =============================================================================

@dataclass
class ExpertiseMatchResult:
    """Result of expertise matching.

    專業能力匹配結果。

    Attributes:
        best_agent: 最佳匹配的 Agent
        score: 匹配分數 (0-1)
        matched_capabilities: 匹配的能力列表
        alternatives: 備選 Agent 列表
    """
    best_agent: "AgentInfo"
    score: float
    matched_capabilities: List[str] = field(default_factory=list)
    alternatives: List["AgentInfo"] = field(default_factory=list)


class ExpertiseMatcher:
    """Matches agents based on expertise and message relevance.

    專業能力匹配器，根據訊息內容匹配最相關的 Agent。

    支援的匹配方法:
    - 關鍵字匹配：比對 Agent 能力與訊息內容
    - 同義詞擴展：使用預定義的同義詞表擴展匹配
    - 加權計算：根據能力相關性計算匹配分數

    Example:
        ```python
        matcher = ExpertiseMatcher()

        result = await matcher.match_expertise(
            message_content="We need to debug the authentication issue",
            candidates=agents,
        )

        if result:
            print(f"Best match: {result.best_agent.name} (score: {result.score})")
        ```
    """

    # Capability synonyms for enhanced matching
    CAPABILITY_SYNONYMS = {
        "coding": ["programming", "development", "code", "implement", "build"],
        "debugging": ["debug", "fix", "troubleshoot", "investigate", "diagnose"],
        "testing": ["test", "qa", "quality", "verify", "validate"],
        "planning": ["plan", "schedule", "organize", "coordinate", "project"],
        "review": ["review", "feedback", "assess", "evaluate", "check"],
        "design": ["design", "architect", "structure", "blueprint", "model"],
        "documentation": ["document", "doc", "write", "describe", "explain"],
        "analysis": ["analyze", "analyse", "research", "study", "investigate"],
        "security": ["secure", "security", "protect", "auth", "permission"],
        "performance": ["optimize", "performance", "speed", "efficiency", "tune"],
    }

    def __init__(
        self,
        synonym_map: Optional[Dict[str, List[str]]] = None,
        min_score_threshold: float = 0.1,
    ):
        """Initialize the ExpertiseMatcher.

        Args:
            synonym_map: 自定義同義詞映射
            min_score_threshold: 最小分數閾值
        """
        self._synonyms = {**self.CAPABILITY_SYNONYMS, **(synonym_map or {})}
        self._min_threshold = min_score_threshold

    async def match_expertise(
        self,
        message_content: str,
        candidates: List["AgentInfo"],
    ) -> Optional[ExpertiseMatchResult]:
        """Match agents based on expertise relevance to message.

        根據訊息內容匹配專業能力。

        Args:
            message_content: 訊息內容
            candidates: 候選 Agent 列表

        Returns:
            匹配結果，如果無匹配則返回 None
        """
        if not candidates:
            return None

        scores: List[tuple] = []  # (agent, score, matched_caps)

        content_lower = message_content.lower()
        content_words = set(re.findall(r'\w+', content_lower))

        for agent in candidates:
            score, matched = self._calculate_relevance(
                agent.capabilities,
                content_lower,
                content_words,
            )
            scores.append((agent, score, matched))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        if scores[0][1] >= self._min_threshold:
            return ExpertiseMatchResult(
                best_agent=scores[0][0],
                score=scores[0][1],
                matched_capabilities=scores[0][2],
                alternatives=[s[0] for s in scores[1:] if s[1] > 0],
            )

        return None

    def _calculate_relevance(
        self,
        capabilities: List[str],
        content_lower: str,
        content_words: Set[str],
    ) -> tuple[float, List[str]]:
        """Calculate relevance score for capabilities.

        計算能力與內容的相關性分數。

        Args:
            capabilities: Agent 能力列表
            content_lower: 小寫訊息內容
            content_words: 內容詞彙集合

        Returns:
            (分數, 匹配的能力列表)
        """
        if not capabilities:
            return 0.0, []

        matched = []
        total_score = 0.0

        for cap in capabilities:
            cap_lower = cap.lower()
            cap_score = 0.0

            # Direct match (highest weight)
            if cap_lower in content_lower:
                cap_score = 1.0
                matched.append(cap)
            else:
                # Synonym matching
                synonyms = self._synonyms.get(cap_lower, [cap_lower])
                for syn in synonyms:
                    if syn in content_lower or syn in content_words:
                        cap_score = 0.7  # Synonym match has lower weight
                        matched.append(cap)
                        break

            total_score += cap_score

        # Normalize by capability count
        normalized_score = total_score / len(capabilities) if capabilities else 0

        return min(1.0, normalized_score), matched

    def get_best_agent(
        self,
        message_content: str,
        candidates: List["AgentInfo"],
    ) -> Optional["AgentInfo"]:
        """Synchronous wrapper to get best agent.

        同步方法獲取最佳匹配 Agent。

        Args:
            message_content: 訊息內容
            candidates: 候選 Agent 列表

        Returns:
            最佳匹配的 Agent，如果無匹配則返回 None
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, create a future
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self.match_expertise(message_content, candidates)
                    )
                    result = future.result()
            else:
                result = loop.run_until_complete(
                    self.match_expertise(message_content, candidates)
                )
        except RuntimeError:
            result = asyncio.run(self.match_expertise(message_content, candidates))

        return result.best_agent if result else None


# =============================================================================
# Main Speaker Selector
# =============================================================================

class SpeakerSelector:
    """Manages speaker selection for group chat conversations.

    發言者選擇器，管理群組聊天中的發言者選擇。

    支援 6 種選擇策略:
    - AUTO: LLM 智能選擇
    - ROUND_ROBIN: 輪流發言
    - RANDOM: 隨機選擇
    - MANUAL: 手動指定
    - PRIORITY: 優先級選擇
    - EXPERTISE: 專業能力匹配

    Example:
        ```python
        selector = SpeakerSelector()

        result = await selector.select_next(
            state=group_state,
            strategy=SelectionStrategy.EXPERTISE,
        )

        if result.success:
            print(f"Selected: {result.selected_agent.name}")
        ```
    """

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        custom_strategies: Optional[Dict[SelectionStrategy, BaseSpeakerStrategy]] = None,
    ):
        """Initialize the SpeakerSelector.

        Args:
            llm_client: LLM 客戶端（用於 AUTO 模式）
            custom_strategies: 自定義策略映射
        """
        self._llm_client = llm_client
        self._expertise_matcher = ExpertiseMatcher()

        # Initialize strategies
        self._strategies: Dict[SelectionStrategy, BaseSpeakerStrategy] = {
            SelectionStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            SelectionStrategy.RANDOM: RandomStrategy(),
            SelectionStrategy.PRIORITY: PriorityStrategy(),
            SelectionStrategy.MANUAL: ManualStrategy(),
            SelectionStrategy.EXPERTISE: ExpertiseStrategy(self._expertise_matcher),
            SelectionStrategy.AUTO: AutoStrategy(llm_client),
        }

        # Apply custom strategies
        if custom_strategies:
            self._strategies.update(custom_strategies)

        logger.info("SpeakerSelector initialized with %d strategies", len(self._strategies))

    async def select_next(
        self,
        state: "GroupChatState",
        strategy: Optional[SelectionStrategy] = None,
        manual_selection: Optional[str] = None,
        exclude_agents: Optional[Set[str]] = None,
    ) -> SelectionResult:
        """Select the next speaker.

        選擇下一位發言者。

        Args:
            state: 群組聊天狀態
            strategy: 選擇策略（可選，默認使用配置中的策略）
            manual_selection: 手動指定的 Agent ID（MANUAL 模式用）
            exclude_agents: 要排除的 Agent ID 集合

        Returns:
            選擇結果
        """
        # Use configured strategy if not specified
        if strategy is None:
            strategy = SelectionStrategy(state.config.speaker_selection_method.value)

        # Build candidates list
        candidates = self._build_candidates(
            state=state,
            exclude_agents=exclude_agents or set(),
        )

        # Get last message for context
        last_message = state.messages[-1] if state.messages else None

        # Build selection context
        context = SelectionContext(
            state=state,
            candidates=candidates,
            last_speaker_id=state.current_speaker_id,
            last_message=last_message,
            allow_repeat=state.config.allow_repeat_speaker,
            manual_selection=manual_selection,
        )

        # Get the strategy implementation
        strategy_impl = self._strategies.get(strategy)
        if not strategy_impl:
            logger.warning(f"Unknown strategy {strategy}, using ROUND_ROBIN")
            strategy_impl = self._strategies[SelectionStrategy.ROUND_ROBIN]

        # Execute selection
        result = await strategy_impl.select(context)

        logger.debug(
            f"Speaker selection: strategy={strategy.value}, "
            f"selected={result.selected_agent.name if result.selected_agent else 'None'}, "
            f"reason={result.reason}"
        )

        return result

    def _build_candidates(
        self,
        state: "GroupChatState",
        exclude_agents: Set[str],
    ) -> List["AgentInfo"]:
        """Build the list of candidate speakers.

        構建候選發言者列表。

        Args:
            state: 群組聊天狀態
            exclude_agents: 要排除的 Agent ID 集合

        Returns:
            候選 Agent 列表
        """
        candidates = []

        for agent in state.agents:
            # Skip inactive agents
            if not agent.is_active:
                continue

            # Skip excluded agents
            if agent.agent_id in exclude_agents:
                continue

            # Skip last speaker if repeat not allowed
            if not state.config.allow_repeat_speaker:
                if agent.agent_id == state.current_speaker_id:
                    continue

            candidates.append(agent)

        # If all agents filtered (only one agent and repeat not allowed), include all active
        if not candidates:
            candidates = [a for a in state.agents if a.is_active]

        return candidates

    def register_strategy(
        self,
        strategy_type: SelectionStrategy,
        strategy: BaseSpeakerStrategy,
    ) -> None:
        """Register a custom selection strategy.

        註冊自定義選擇策略。

        Args:
            strategy_type: 策略類型
            strategy: 策略實現
        """
        self._strategies[strategy_type] = strategy
        logger.info(f"Registered custom strategy: {strategy_type.value}")

    def get_available_strategies(self) -> List[SelectionStrategy]:
        """Get list of available selection strategies.

        獲取可用的選擇策略列表。

        Returns:
            策略類型列表
        """
        return list(self._strategies.keys())

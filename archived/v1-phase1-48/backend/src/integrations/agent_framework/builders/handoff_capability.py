# =============================================================================
# Agent Framework Handoff Capability Adapter
# =============================================================================
# Sprint 21: Handoff 完整遷移
# Phase 4 Feature: S21-2 (CapabilityMatcher 整合)
#
# 此模組提供 Phase 2 CapabilityMatcher 到官方 Agent Framework API 的整合。
# 在適配器層保留能力匹配功能，支持智能 Agent 選擇和路由。
#
# 設計原則:
#   - 複製關鍵枚舉和資料類以避免循環依賴
#   - 提供統一的能力匹配接口
#   - 支持與 HandoffBuilderAdapter 整合
#
# 核心功能:
#   - MatchStrategy: 4 種匹配策略 (BEST_FIT, FIRST_FIT, ROUND_ROBIN, LEAST_LOADED)
#   - CapabilityMatcherAdapter: 能力匹配適配器
#   - 能力評分與選擇算法
#
# 使用方式:
#   from integrations.agent_framework.builders.handoff_capability import (
#       CapabilityMatcherAdapter,
#       MatchStrategy,
#       AgentCapabilityInfo,
#   )
#
#   # 創建適配器
#   matcher = CapabilityMatcherAdapter()
#
#   # 註冊 Agent 能力
#   matcher.register_agent(agent_id, [
#       AgentCapabilityInfo(name="code_generation", proficiency=0.9),
#       AgentCapabilityInfo(name="data_analysis", proficiency=0.7),
#   ])
#
#   # 查找匹配的 Agent
#   matches = matcher.find_capable_agents(
#       requirements=[CapabilityRequirementInfo(name="code_generation", min_proficiency=0.7)],
#       strategy=MatchStrategy.BEST_FIT,
#   )
#
# References:
#   - Phase 2 CapabilityMatcher: src/domain/orchestration/handoff/capability_matcher.py
#   - Phase 2 Capabilities: src/domain/orchestration/handoff/capabilities.py
#   - HandoffBuilderAdapter: src/integrations/agent_framework/builders/handoff.py
# =============================================================================

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


# =============================================================================
# Capability Enums (從 domain 層複製以避免循環依賴)
# =============================================================================


class CapabilityCategory(str, Enum):
    """
    Agent 能力類別。

    Categories:
        LANGUAGE: 自然語言處理能力
        REASONING: 邏輯推理與分析
        KNOWLEDGE: 領域知識與專業
        ACTION: 執行任務能力
        INTEGRATION: 外部系統整合
        COMMUNICATION: Agent 間通信
    """
    LANGUAGE = "language"
    REASONING = "reasoning"
    KNOWLEDGE = "knowledge"
    ACTION = "action"
    INTEGRATION = "integration"
    COMMUNICATION = "communication"


class AgentStatus(str, Enum):
    """
    Agent 可用性狀態。

    States:
        AVAILABLE: 可接受任務
        BUSY: 處理中但可排隊
        OVERLOADED: 已達容量上限
        OFFLINE: 離線
        MAINTENANCE: 維護中
    """
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class MatchStrategy(str, Enum):
    """
    Agent 匹配選擇策略。

    Strategies:
        BEST_FIT: 選擇得分最高的 Agent
        FIRST_FIT: 選擇第一個符合要求的 Agent
        ROUND_ROBIN: 在符合條件的 Agent 之間輪詢
        LEAST_LOADED: 選擇負載最低的 Agent
    """
    BEST_FIT = "best_fit"
    FIRST_FIT = "first_fit"
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"


# =============================================================================
# Capability Data Classes
# =============================================================================


@dataclass
class AgentCapabilityInfo:
    """
    Agent 能力資訊。

    Attributes:
        name: 能力名稱
        proficiency: 熟練度 (0.0 到 1.0)
        category: 能力類別
        description: 能力描述
        metadata: 額外元數據
    """
    name: str
    proficiency: float = 0.5
    category: CapabilityCategory = CapabilityCategory.ACTION
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """驗證熟練度範圍。"""
        self.proficiency = max(0.0, min(1.0, self.proficiency))


@dataclass
class CapabilityRequirementInfo:
    """
    能力需求資訊。

    Attributes:
        name: 能力名稱
        min_proficiency: 最低熟練度要求
        category: 類別限制 (可選)
        required: 是否為必需 (vs 偏好)
        weight: 重要性權重
    """
    name: str
    min_proficiency: float = 0.0
    category: Optional[CapabilityCategory] = None
    required: bool = True
    weight: float = 1.0

    def __post_init__(self):
        """驗證值範圍。"""
        self.min_proficiency = max(0.0, min(1.0, self.min_proficiency))
        self.weight = max(0.0, min(1.0, self.weight))


@dataclass
class AgentAvailabilityInfo:
    """
    Agent 可用性資訊。

    Attributes:
        agent_id: Agent 識別碼
        status: 當前狀態
        current_load: 當前負載 (0.0 到 1.0)
        max_concurrent: 最大並行任務數
        active_tasks: 活動任務數
        last_updated: 最後更新時間
    """
    agent_id: str
    status: AgentStatus = AgentStatus.AVAILABLE
    current_load: float = 0.0
    max_concurrent: int = 5
    active_tasks: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_available(self) -> bool:
        """檢查 Agent 是否可接受新任務。"""
        return (
            self.status in (AgentStatus.AVAILABLE, AgentStatus.BUSY)
            and self.active_tasks < self.max_concurrent
        )

    @property
    def remaining_capacity(self) -> int:
        """獲取剩餘任務容量。"""
        return max(0, self.max_concurrent - self.active_tasks)


@dataclass
class CapabilityMatchResult:
    """
    能力匹配結果。

    Attributes:
        agent_id: 匹配的 Agent ID
        score: 整體匹配分數 (0.0 到 1.0)
        capability_scores: 各能力的匹配分數
        missing_capabilities: 缺少的必需能力
        availability: Agent 可用性資訊
        metadata: 額外元數據
    """
    agent_id: str
    score: float = 0.0
    capability_scores: Dict[str, float] = field(default_factory=dict)
    missing_capabilities: List[str] = field(default_factory=list)
    availability: Optional[AgentAvailabilityInfo] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete_match(self) -> bool:
        """檢查是否滿足所有必需能力。"""
        return len(self.missing_capabilities) == 0

    @property
    def is_available(self) -> bool:
        """檢查 Agent 是否可用。"""
        return self.availability is not None and self.availability.is_available


# =============================================================================
# Built-in Capabilities
# =============================================================================


# 預設內建能力列表
BUILTIN_CAPABILITIES: Dict[str, AgentCapabilityInfo] = {
    "text_generation": AgentCapabilityInfo(
        name="text_generation",
        proficiency=0.8,
        category=CapabilityCategory.LANGUAGE,
        description="生成自然語言文字回應",
    ),
    "text_summarization": AgentCapabilityInfo(
        name="text_summarization",
        proficiency=0.7,
        category=CapabilityCategory.LANGUAGE,
        description="將長文摘要為簡潔形式",
    ),
    "translation": AgentCapabilityInfo(
        name="translation",
        proficiency=0.7,
        category=CapabilityCategory.LANGUAGE,
        description="在不同語言之間翻譯文字",
    ),
    "sentiment_analysis": AgentCapabilityInfo(
        name="sentiment_analysis",
        proficiency=0.6,
        category=CapabilityCategory.LANGUAGE,
        description="分析文字的情感傾向",
    ),
    "logical_reasoning": AgentCapabilityInfo(
        name="logical_reasoning",
        proficiency=0.7,
        category=CapabilityCategory.REASONING,
        description="執行邏輯推演和分析",
    ),
    "data_analysis": AgentCapabilityInfo(
        name="data_analysis",
        proficiency=0.7,
        category=CapabilityCategory.REASONING,
        description="分析和解釋數據",
    ),
    "problem_solving": AgentCapabilityInfo(
        name="problem_solving",
        proficiency=0.6,
        category=CapabilityCategory.REASONING,
        description="分解並解決複雜問題",
    ),
    "code_generation": AgentCapabilityInfo(
        name="code_generation",
        proficiency=0.7,
        category=CapabilityCategory.ACTION,
        description="生成程式代碼",
    ),
    "code_review": AgentCapabilityInfo(
        name="code_review",
        proficiency=0.6,
        category=CapabilityCategory.ACTION,
        description="審查和分析代碼質量",
    ),
    "api_integration": AgentCapabilityInfo(
        name="api_integration",
        proficiency=0.8,
        category=CapabilityCategory.INTEGRATION,
        description="與外部 API 整合",
    ),
    "database_operations": AgentCapabilityInfo(
        name="database_operations",
        proficiency=0.7,
        category=CapabilityCategory.INTEGRATION,
        description="執行資料庫查詢和操作",
    ),
    "file_operations": AgentCapabilityInfo(
        name="file_operations",
        proficiency=0.8,
        category=CapabilityCategory.INTEGRATION,
        description="讀取、寫入和操作檔案",
    ),
    "domain_knowledge_general": AgentCapabilityInfo(
        name="domain_knowledge_general",
        proficiency=0.6,
        category=CapabilityCategory.KNOWLEDGE,
        description="一般領域知識",
    ),
    "domain_knowledge_technical": AgentCapabilityInfo(
        name="domain_knowledge_technical",
        proficiency=0.7,
        category=CapabilityCategory.KNOWLEDGE,
        description="技術領域專業知識",
    ),
    "multi_agent_coordination": AgentCapabilityInfo(
        name="multi_agent_coordination",
        proficiency=0.6,
        category=CapabilityCategory.COMMUNICATION,
        description="與其他 Agent 協調",
    ),
}


# =============================================================================
# Capability Matcher Adapter
# =============================================================================


class CapabilityMatcherAdapter:
    """
    能力匹配適配器。

    將 Phase 2 的 CapabilityMatcher 功能封裝為適配器，
    可與 HandoffBuilderAdapter 整合使用。

    功能:
        - 註冊和管理 Agent 能力
        - 根據需求查找匹配的 Agent
        - 支持多種選擇策略
        - 追蹤 Agent 可用性

    Usage:
        matcher = CapabilityMatcherAdapter()

        # 註冊 Agent
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])

        # 查找匹配
        matches = matcher.find_capable_agents(
            requirements=[CapabilityRequirementInfo(name="code_generation")],
        )

        # 獲取最佳匹配
        best = matcher.get_best_match(requirements, strategy=MatchStrategy.BEST_FIT)
    """

    def __init__(
        self,
        availability_checker: Optional[Callable[[str], AgentAvailabilityInfo]] = None,
    ):
        """
        初始化能力匹配適配器。

        Args:
            availability_checker: 可選的可用性檢查回調
        """
        # Agent 能力存儲: agent_id -> List[AgentCapabilityInfo]
        self._agent_capabilities: Dict[str, List[AgentCapabilityInfo]] = {}

        # 能力反向索引: capability_name -> Set[agent_id]
        self._capability_agents: Dict[str, Set[str]] = {}

        # Agent 可用性緩存
        self._availability_cache: Dict[str, AgentAvailabilityInfo] = {}

        # 外部可用性檢查器
        self._availability_checker = availability_checker

        # Round-robin 狀態
        self._round_robin_index: Dict[str, int] = {}

        logger.info("CapabilityMatcherAdapter initialized")

    # =========================================================================
    # Agent Registration
    # =========================================================================

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[AgentCapabilityInfo],
    ) -> None:
        """
        註冊 Agent 能力。

        Args:
            agent_id: Agent 識別碼
            capabilities: 能力列表
        """
        self._agent_capabilities[agent_id] = capabilities.copy()

        # 更新反向索引
        for cap in capabilities:
            cap_name = cap.name.lower()
            if cap_name not in self._capability_agents:
                self._capability_agents[cap_name] = set()
            self._capability_agents[cap_name].add(agent_id)

        logger.debug(f"Registered {len(capabilities)} capabilities for agent {agent_id}")

    def unregister_agent(self, agent_id: str) -> bool:
        """
        移除 Agent 註冊。

        Args:
            agent_id: Agent 識別碼

        Returns:
            是否成功移除
        """
        if agent_id not in self._agent_capabilities:
            return False

        caps = self._agent_capabilities.pop(agent_id)

        # 更新反向索引
        for cap in caps:
            cap_name = cap.name.lower()
            if cap_name in self._capability_agents:
                self._capability_agents[cap_name].discard(agent_id)

        # 清除可用性緩存
        self._availability_cache.pop(agent_id, None)

        logger.debug(f"Unregistered agent {agent_id}")
        return True

    def update_availability(
        self,
        agent_id: str,
        availability: AgentAvailabilityInfo,
    ) -> None:
        """
        更新 Agent 可用性資訊。

        Args:
            agent_id: Agent 識別碼
            availability: 可用性資訊
        """
        self._availability_cache[agent_id] = availability
        logger.debug(f"Updated availability for agent {agent_id}: {availability.status}")

    # =========================================================================
    # Capability Queries
    # =========================================================================

    def get_agent_capabilities(self, agent_id: str) -> List[AgentCapabilityInfo]:
        """
        獲取 Agent 的所有能力。

        Args:
            agent_id: Agent 識別碼

        Returns:
            能力列表
        """
        return self._agent_capabilities.get(agent_id, []).copy()

    def has_capability(
        self,
        agent_id: str,
        capability_name: str,
        min_proficiency: float = 0.0,
    ) -> bool:
        """
        檢查 Agent 是否具有特定能力。

        Args:
            agent_id: Agent 識別碼
            capability_name: 能力名稱
            min_proficiency: 最低熟練度要求

        Returns:
            是否具有能力
        """
        caps = self._agent_capabilities.get(agent_id, [])
        for cap in caps:
            if cap.name.lower() == capability_name.lower():
                return cap.proficiency >= min_proficiency
        return False

    def get_capability(
        self,
        agent_id: str,
        capability_name: str,
    ) -> Optional[AgentCapabilityInfo]:
        """
        獲取 Agent 的特定能力。

        Args:
            agent_id: Agent 識別碼
            capability_name: 能力名稱

        Returns:
            能力資訊或 None
        """
        caps = self._agent_capabilities.get(agent_id, [])
        for cap in caps:
            if cap.name.lower() == capability_name.lower():
                return cap
        return None

    # =========================================================================
    # Capability Matching
    # =========================================================================

    def find_capable_agents(
        self,
        requirements: List[CapabilityRequirementInfo],
        check_availability: bool = True,
        include_partial: bool = False,
    ) -> List[CapabilityMatchResult]:
        """
        查找符合能力需求的 Agent。

        Args:
            requirements: 能力需求列表
            check_availability: 是否檢查可用性
            include_partial: 是否包含部分匹配

        Returns:
            匹配結果列表 (按分數降序排列)
        """
        if not requirements:
            return []

        # 獲取候選 Agent
        candidates = self._get_candidate_agents(requirements)

        if not candidates:
            logger.debug("No candidate agents found for requirements")
            return []

        # 計算每個候選的匹配分數
        results = []
        for agent_id in candidates:
            result = self._calculate_match(agent_id, requirements)

            # 檢查是否符合要求
            if not include_partial and not result.is_complete_match:
                continue

            # 檢查可用性
            if check_availability:
                result.availability = self._check_availability(agent_id)
                if not result.is_available:
                    continue

            results.append(result)

        # 按分數降序排列
        results.sort(key=lambda r: r.score, reverse=True)

        logger.debug(f"Found {len(results)} matching agents for requirements")
        return results

    def get_best_match(
        self,
        requirements: List[CapabilityRequirementInfo],
        strategy: MatchStrategy = MatchStrategy.BEST_FIT,
        exclude_agents: Optional[Set[str]] = None,
    ) -> Optional[CapabilityMatchResult]:
        """
        獲取最佳匹配的 Agent。

        Args:
            requirements: 能力需求列表
            strategy: 選擇策略
            exclude_agents: 要排除的 Agent ID 集合

        Returns:
            最佳匹配結果或 None
        """
        matches = self.find_capable_agents(
            requirements,
            check_availability=True,
            include_partial=False,
        )

        if not matches:
            return None

        # 過濾排除的 Agent
        if exclude_agents:
            matches = [m for m in matches if m.agent_id not in exclude_agents]

        if not matches:
            return None

        # 應用選擇策略
        if strategy == MatchStrategy.BEST_FIT:
            return matches[0]  # 已按分數排序

        elif strategy == MatchStrategy.FIRST_FIT:
            # 返回第一個達到最低閾值的
            for match in matches:
                if match.score >= 0.5:
                    return match
            return matches[0]

        elif strategy == MatchStrategy.ROUND_ROBIN:
            return self._select_round_robin(matches, requirements)

        elif strategy == MatchStrategy.LEAST_LOADED:
            return self._select_least_loaded(matches)

        return matches[0]

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _get_candidate_agents(
        self,
        requirements: List[CapabilityRequirementInfo],
    ) -> Set[str]:
        """
        獲取候選 Agent 集合。

        Args:
            requirements: 能力需求

        Returns:
            候選 Agent ID 集合
        """
        candidates: Optional[Set[str]] = None

        for req in requirements:
            if not req.required:
                continue

            cap_name = req.name.lower()
            agents = self._capability_agents.get(cap_name, set())

            if candidates is None:
                candidates = agents.copy()
            else:
                candidates &= agents  # 交集

        return candidates or set()

    def _calculate_match(
        self,
        agent_id: str,
        requirements: List[CapabilityRequirementInfo],
    ) -> CapabilityMatchResult:
        """
        計算 Agent 的匹配分數。

        Args:
            agent_id: Agent 識別碼
            requirements: 能力需求

        Returns:
            匹配結果
        """
        result = CapabilityMatchResult(agent_id=agent_id)
        total_weight = 0.0
        weighted_score = 0.0

        for req in requirements:
            cap = self.get_capability(agent_id, req.name)

            if cap is None:
                if req.required:
                    result.missing_capabilities.append(req.name)
                    result.capability_scores[req.name] = 0.0
                continue

            # 計算能力分數
            score = self._calculate_capability_score(cap, req)
            result.capability_scores[req.name] = score

            # 檢查最低熟練度
            if cap.proficiency < req.min_proficiency:
                if req.required:
                    result.missing_capabilities.append(req.name)

            # 累加加權分數
            weighted_score += score * req.weight
            total_weight += req.weight

        # 計算整體分數
        if total_weight > 0:
            result.score = weighted_score / total_weight

        return result

    def _calculate_capability_score(
        self,
        capability: AgentCapabilityInfo,
        requirement: CapabilityRequirementInfo,
    ) -> float:
        """
        計算單一能力的匹配分數。

        Args:
            capability: Agent 的能力
            requirement: 能力需求

        Returns:
            匹配分數 (0.0 到 1.0)
        """
        proficiency = capability.proficiency

        # 超過最低要求的獎勵
        if proficiency >= requirement.min_proficiency:
            excess = proficiency - requirement.min_proficiency
            bonus = min(0.2, excess * 0.5)
            score = min(1.0, proficiency + bonus)
        else:
            # 未達最低要求的懲罰
            deficit = requirement.min_proficiency - proficiency
            score = max(0.0, proficiency - deficit * 0.5)

        # 類別匹配獎勵
        if requirement.category and capability.category == requirement.category:
            score = min(1.0, score + 0.1)

        return score

    def _check_availability(self, agent_id: str) -> AgentAvailabilityInfo:
        """
        檢查 Agent 可用性。

        Args:
            agent_id: Agent 識別碼

        Returns:
            可用性資訊
        """
        # 先嘗試外部檢查器
        if self._availability_checker:
            try:
                return self._availability_checker(agent_id)
            except Exception as e:
                logger.warning(f"Availability check failed for {agent_id}: {e}")

        # 回退到緩存
        if agent_id in self._availability_cache:
            return self._availability_cache[agent_id]

        # 預設為可用
        return AgentAvailabilityInfo(agent_id=agent_id)

    def _select_round_robin(
        self,
        matches: List[CapabilityMatchResult],
        requirements: List[CapabilityRequirementInfo],
    ) -> CapabilityMatchResult:
        """
        使用 Round-robin 策略選擇 Agent。

        Args:
            matches: 匹配結果列表
            requirements: 需求 (用於分組)

        Returns:
            選擇的匹配結果
        """
        # 從需求創建 key
        key = "_".join(sorted(r.name for r in requirements))

        # 獲取當前索引
        index = self._round_robin_index.get(key, 0)

        # 選擇並更新索引
        result = matches[index % len(matches)]
        self._round_robin_index[key] = (index + 1) % len(matches)

        return result

    def _select_least_loaded(
        self,
        matches: List[CapabilityMatchResult],
    ) -> CapabilityMatchResult:
        """
        選擇負載最低的 Agent。

        Args:
            matches: 匹配結果列表

        Returns:
            負載最低的匹配結果
        """
        return min(
            matches,
            key=lambda m: (
                m.availability.current_load if m.availability else 0.0,
                -m.score,  # 分數作為次要排序
            ),
        )

    # =========================================================================
    # Handoff Integration
    # =========================================================================

    def calculate_handoff_score(
        self,
        source_agent_id: str,
        target_agent_id: str,
        requirements: List[CapabilityRequirementInfo],
    ) -> float:
        """
        計算 Handoff 適合度分數。

        考慮目標能力匹配度和相對於來源的改進。

        Args:
            source_agent_id: 當前 Agent
            target_agent_id: 目標 Handoff Agent
            requirements: 任務需求

        Returns:
            Handoff 分數 (0.0 到 1.0)
        """
        # 獲取匹配分數
        source_match = self._calculate_match(source_agent_id, requirements)
        target_match = self._calculate_match(target_agent_id, requirements)

        # 基礎分數為目標的匹配分數
        score = target_match.score

        # 如果目標比來源更好則有獎勵
        improvement = target_match.score - source_match.score
        if improvement > 0:
            score = min(1.0, score + improvement * 0.2)

        # 如果來源實際上更好則有懲罰
        if improvement < 0:
            score = max(0.0, score + improvement * 0.5)

        # 檢查可用性
        target_avail = self._check_availability(target_agent_id)
        if not target_avail.is_available:
            score *= 0.5

        return score

    def suggest_handoff_target(
        self,
        source_agent_id: str,
        requirements: List[CapabilityRequirementInfo],
        strategy: MatchStrategy = MatchStrategy.BEST_FIT,
    ) -> Optional[CapabilityMatchResult]:
        """
        建議 Handoff 目標 Agent。

        Args:
            source_agent_id: 當前 Agent
            requirements: 任務需求
            strategy: 選擇策略

        Returns:
            建議的目標或 None
        """
        return self.get_best_match(
            requirements=requirements,
            strategy=strategy,
            exclude_agents={source_agent_id},
        )

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_agents_by_category(
        self,
        category: CapabilityCategory,
        check_availability: bool = True,
    ) -> List[str]:
        """
        獲取具有特定類別能力的 Agent。

        Args:
            category: 能力類別
            check_availability: 是否過濾可用性

        Returns:
            Agent ID 列表
        """
        agents = set()
        for agent_id, caps in self._agent_capabilities.items():
            for cap in caps:
                if cap.category == category:
                    agents.add(agent_id)
                    break

        if check_availability:
            agents = {
                a for a in agents
                if self._check_availability(a).is_available
            }

        return list(agents)

    def get_builtin_capability(self, name: str) -> Optional[AgentCapabilityInfo]:
        """
        獲取內建能力定義。

        Args:
            name: 能力名稱

        Returns:
            內建能力或 None
        """
        return BUILTIN_CAPABILITIES.get(name)

    def list_builtin_capabilities(self) -> List[str]:
        """
        列出所有內建能力名稱。

        Returns:
            能力名稱列表
        """
        return list(BUILTIN_CAPABILITIES.keys())

    @property
    def agent_count(self) -> int:
        """已註冊的 Agent 數量。"""
        return len(self._agent_capabilities)

    @property
    def capability_count(self) -> int:
        """已註冊的能力總數。"""
        return sum(len(caps) for caps in self._agent_capabilities.values())


# =============================================================================
# Factory Functions
# =============================================================================


def create_capability_matcher(
    availability_checker: Optional[Callable[[str], AgentAvailabilityInfo]] = None,
) -> CapabilityMatcherAdapter:
    """
    創建能力匹配適配器。

    Args:
        availability_checker: 可選的可用性檢查回調

    Returns:
        CapabilityMatcherAdapter 實例
    """
    return CapabilityMatcherAdapter(availability_checker=availability_checker)


def create_capability_requirement(
    name: str,
    min_proficiency: float = 0.0,
    required: bool = True,
    weight: float = 1.0,
    category: Optional[CapabilityCategory] = None,
) -> CapabilityRequirementInfo:
    """
    便捷函數：創建能力需求。

    Args:
        name: 能力名稱
        min_proficiency: 最低熟練度
        required: 是否為必需
        weight: 重要性權重
        category: 類別限制

    Returns:
        CapabilityRequirementInfo 實例
    """
    return CapabilityRequirementInfo(
        name=name,
        min_proficiency=min_proficiency,
        required=required,
        weight=weight,
        category=category,
    )


def create_agent_capability(
    name: str,
    proficiency: float = 0.5,
    category: CapabilityCategory = CapabilityCategory.ACTION,
    description: str = "",
) -> AgentCapabilityInfo:
    """
    便捷函數：創建 Agent 能力。

    Args:
        name: 能力名稱
        proficiency: 熟練度
        category: 能力類別
        description: 描述

    Returns:
        AgentCapabilityInfo 實例
    """
    return AgentCapabilityInfo(
        name=name,
        proficiency=proficiency,
        category=category,
        description=description,
    )


# =============================================================================
# 模組導出
# =============================================================================

__all__ = [
    # Enums
    "CapabilityCategory",
    "AgentStatus",
    "MatchStrategy",
    # Data Classes
    "AgentCapabilityInfo",
    "CapabilityRequirementInfo",
    "AgentAvailabilityInfo",
    "CapabilityMatchResult",
    # Constants
    "BUILTIN_CAPABILITIES",
    # Main Adapter
    "CapabilityMatcherAdapter",
    # Factory Functions
    "create_capability_matcher",
    "create_capability_requirement",
    "create_agent_capability",
]

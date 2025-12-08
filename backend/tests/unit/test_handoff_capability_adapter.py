# =============================================================================
# Test: Handoff Capability Adapter
# =============================================================================
# Sprint 21: S21-2 單元測試
# Phase 4 Feature: CapabilityMatcher 整合驗證
#
# 測試涵蓋:
#   - CapabilityCategory, AgentStatus, MatchStrategy 枚舉
#   - AgentCapabilityInfo, CapabilityRequirementInfo 資料類
#   - CapabilityMatcherAdapter 核心功能
#   - 匹配策略 (BEST_FIT, FIRST_FIT, ROUND_ROBIN, LEAST_LOADED)
#   - Handoff 整合功能
#
# 驗收標準:
#   - 所有匹配策略正確運作
#   - Agent 註冊和查詢正常
#   - 可用性檢查功能正確
# =============================================================================

import pytest
from datetime import datetime
from typing import Dict, List

from src.integrations.agent_framework.builders.handoff_capability import (
    # Enums
    CapabilityCategory,
    AgentStatus,
    MatchStrategy,
    # Data Classes
    AgentCapabilityInfo,
    CapabilityRequirementInfo,
    AgentAvailabilityInfo,
    CapabilityMatchResult,
    # Constants
    BUILTIN_CAPABILITIES,
    # Main Adapter
    CapabilityMatcherAdapter,
    # Factory Functions
    create_capability_matcher,
    create_capability_requirement,
    create_agent_capability,
)


# =============================================================================
# Test: Enums
# =============================================================================


class TestCapabilityCategory:
    """測試 CapabilityCategory 枚舉。"""

    def test_all_categories_exist(self):
        """驗證所有類別存在。"""
        assert CapabilityCategory.LANGUAGE == "language"
        assert CapabilityCategory.REASONING == "reasoning"
        assert CapabilityCategory.KNOWLEDGE == "knowledge"
        assert CapabilityCategory.ACTION == "action"
        assert CapabilityCategory.INTEGRATION == "integration"
        assert CapabilityCategory.COMMUNICATION == "communication"

    def test_category_count(self):
        """驗證類別數量。"""
        assert len(CapabilityCategory) == 6


class TestAgentStatus:
    """測試 AgentStatus 枚舉。"""

    def test_all_statuses_exist(self):
        """驗證所有狀態存在。"""
        assert AgentStatus.AVAILABLE == "available"
        assert AgentStatus.BUSY == "busy"
        assert AgentStatus.OVERLOADED == "overloaded"
        assert AgentStatus.OFFLINE == "offline"
        assert AgentStatus.MAINTENANCE == "maintenance"


class TestMatchStrategy:
    """測試 MatchStrategy 枚舉。"""

    def test_all_strategies_exist(self):
        """驗證所有策略存在。"""
        assert MatchStrategy.BEST_FIT == "best_fit"
        assert MatchStrategy.FIRST_FIT == "first_fit"
        assert MatchStrategy.ROUND_ROBIN == "round_robin"
        assert MatchStrategy.LEAST_LOADED == "least_loaded"


# =============================================================================
# Test: Data Classes
# =============================================================================


class TestAgentCapabilityInfo:
    """測試 AgentCapabilityInfo 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        cap = AgentCapabilityInfo(name="test")
        assert cap.name == "test"
        assert cap.proficiency == 0.5
        assert cap.category == CapabilityCategory.ACTION
        assert cap.description == ""
        assert cap.metadata == {}

    def test_proficiency_validation(self):
        """驗證熟練度範圍限制。"""
        cap = AgentCapabilityInfo(name="test", proficiency=1.5)
        assert cap.proficiency == 1.0

        cap = AgentCapabilityInfo(name="test", proficiency=-0.5)
        assert cap.proficiency == 0.0


class TestCapabilityRequirementInfo:
    """測試 CapabilityRequirementInfo 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        req = CapabilityRequirementInfo(name="test")
        assert req.name == "test"
        assert req.min_proficiency == 0.0
        assert req.category is None
        assert req.required is True
        assert req.weight == 1.0

    def test_proficiency_validation(self):
        """驗證熟練度範圍限制。"""
        req = CapabilityRequirementInfo(name="test", min_proficiency=1.5)
        assert req.min_proficiency == 1.0

    def test_weight_validation(self):
        """驗證權重範圍限制。"""
        req = CapabilityRequirementInfo(name="test", weight=2.0)
        assert req.weight == 1.0


class TestAgentAvailabilityInfo:
    """測試 AgentAvailabilityInfo 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        avail = AgentAvailabilityInfo(agent_id="agent-1")
        assert avail.status == AgentStatus.AVAILABLE
        assert avail.current_load == 0.0
        assert avail.max_concurrent == 5
        assert avail.active_tasks == 0

    def test_is_available_when_available(self):
        """驗證 AVAILABLE 狀態下可用。"""
        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.AVAILABLE,
            active_tasks=2,
            max_concurrent=5,
        )
        assert avail.is_available is True

    def test_is_available_when_busy(self):
        """驗證 BUSY 狀態下仍可用。"""
        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.BUSY,
            active_tasks=2,
            max_concurrent=5,
        )
        assert avail.is_available is True

    def test_not_available_when_overloaded(self):
        """驗證 OVERLOADED 狀態下不可用。"""
        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.OVERLOADED,
        )
        assert avail.is_available is False

    def test_not_available_at_capacity(self):
        """驗證達到容量上限時不可用。"""
        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.AVAILABLE,
            active_tasks=5,
            max_concurrent=5,
        )
        assert avail.is_available is False

    def test_remaining_capacity(self):
        """驗證剩餘容量計算。"""
        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            active_tasks=3,
            max_concurrent=5,
        )
        assert avail.remaining_capacity == 2


class TestCapabilityMatchResult:
    """測試 CapabilityMatchResult 資料類。"""

    def test_default_values(self):
        """驗證預設值。"""
        result = CapabilityMatchResult(agent_id="agent-1")
        assert result.score == 0.0
        assert result.capability_scores == {}
        assert result.missing_capabilities == []
        assert result.availability is None

    def test_is_complete_match(self):
        """驗證完整匹配判斷。"""
        result = CapabilityMatchResult(agent_id="agent-1")
        assert result.is_complete_match is True

        result.missing_capabilities = ["code_generation"]
        assert result.is_complete_match is False


# =============================================================================
# Test: Built-in Capabilities
# =============================================================================


class TestBuiltinCapabilities:
    """測試內建能力定義。"""

    def test_builtin_count(self):
        """驗證內建能力數量。"""
        assert len(BUILTIN_CAPABILITIES) == 15

    def test_code_generation_exists(self):
        """驗證 code_generation 存在。"""
        cap = BUILTIN_CAPABILITIES.get("code_generation")
        assert cap is not None
        assert cap.proficiency == 0.7
        assert cap.category == CapabilityCategory.ACTION

    def test_data_analysis_exists(self):
        """驗證 data_analysis 存在。"""
        cap = BUILTIN_CAPABILITIES.get("data_analysis")
        assert cap is not None
        assert cap.category == CapabilityCategory.REASONING


# =============================================================================
# Test: CapabilityMatcherAdapter - Agent Registration
# =============================================================================


class TestCapabilityMatcherAdapterRegistration:
    """測試 Agent 註冊功能。"""

    def test_register_agent(self):
        """驗證 Agent 註冊。"""
        matcher = CapabilityMatcherAdapter()
        caps = [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
            AgentCapabilityInfo(name="data_analysis", proficiency=0.7),
        ]
        matcher.register_agent("agent-1", caps)

        assert matcher.agent_count == 1
        assert matcher.capability_count == 2

    def test_unregister_agent(self):
        """驗證 Agent 取消註冊。"""
        matcher = CapabilityMatcherAdapter()
        caps = [AgentCapabilityInfo(name="code_generation", proficiency=0.9)]
        matcher.register_agent("agent-1", caps)

        result = matcher.unregister_agent("agent-1")
        assert result is True
        assert matcher.agent_count == 0

    def test_unregister_nonexistent_agent(self):
        """驗證取消註冊不存在的 Agent。"""
        matcher = CapabilityMatcherAdapter()
        result = matcher.unregister_agent("nonexistent")
        assert result is False


# =============================================================================
# Test: CapabilityMatcherAdapter - Capability Queries
# =============================================================================


class TestCapabilityMatcherAdapterQueries:
    """測試能力查詢功能。"""

    @pytest.fixture
    def matcher_with_agents(self):
        """創建帶有註冊 Agent 的 matcher。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
            AgentCapabilityInfo(name="data_analysis", proficiency=0.7),
        ])
        matcher.register_agent("agent-2", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.6),
            AgentCapabilityInfo(name="text_generation", proficiency=0.8),
        ])
        return matcher

    def test_get_agent_capabilities(self, matcher_with_agents):
        """驗證獲取 Agent 能力。"""
        caps = matcher_with_agents.get_agent_capabilities("agent-1")
        assert len(caps) == 2
        cap_names = [c.name for c in caps]
        assert "code_generation" in cap_names
        assert "data_analysis" in cap_names

    def test_has_capability(self, matcher_with_agents):
        """驗證能力存在檢查。"""
        assert matcher_with_agents.has_capability("agent-1", "code_generation") is True
        assert matcher_with_agents.has_capability("agent-1", "text_generation") is False

    def test_has_capability_with_proficiency(self, matcher_with_agents):
        """驗證帶熟練度的能力檢查。"""
        assert matcher_with_agents.has_capability(
            "agent-1", "code_generation", min_proficiency=0.8
        ) is True
        assert matcher_with_agents.has_capability(
            "agent-1", "code_generation", min_proficiency=0.95
        ) is False

    def test_get_capability(self, matcher_with_agents):
        """驗證獲取特定能力。"""
        cap = matcher_with_agents.get_capability("agent-1", "code_generation")
        assert cap is not None
        assert cap.proficiency == 0.9

    def test_get_nonexistent_capability(self, matcher_with_agents):
        """驗證獲取不存在的能力。"""
        cap = matcher_with_agents.get_capability("agent-1", "nonexistent")
        assert cap is None


# =============================================================================
# Test: CapabilityMatcherAdapter - Capability Matching
# =============================================================================


class TestCapabilityMatcherAdapterMatching:
    """測試能力匹配功能。"""

    @pytest.fixture
    def matcher_with_agents(self):
        """創建帶有註冊 Agent 的 matcher。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
            AgentCapabilityInfo(name="data_analysis", proficiency=0.7),
        ])
        matcher.register_agent("agent-2", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.6),
            AgentCapabilityInfo(name="text_generation", proficiency=0.8),
        ])
        matcher.register_agent("agent-3", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.5),
        ])
        return matcher

    def test_find_capable_agents_single_requirement(self, matcher_with_agents):
        """驗證單一需求匹配。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        matches = matcher_with_agents.find_capable_agents(
            requirements, check_availability=False
        )

        assert len(matches) == 3  # 所有 Agent 都有 code_generation
        # 應該按分數排序
        assert matches[0].agent_id == "agent-1"  # 最高分

    def test_find_capable_agents_with_proficiency(self, matcher_with_agents):
        """驗證帶熟練度要求的匹配。"""
        requirements = [
            CapabilityRequirementInfo(name="code_generation", min_proficiency=0.7)
        ]
        matches = matcher_with_agents.find_capable_agents(
            requirements, check_availability=False
        )

        assert len(matches) == 1  # 只有 agent-1 滿足 0.7
        assert matches[0].agent_id == "agent-1"

    def test_find_capable_agents_multiple_requirements(self, matcher_with_agents):
        """驗證多重需求匹配。"""
        requirements = [
            CapabilityRequirementInfo(name="code_generation"),
            CapabilityRequirementInfo(name="data_analysis"),
        ]
        matches = matcher_with_agents.find_capable_agents(
            requirements, check_availability=False
        )

        assert len(matches) == 1  # 只有 agent-1 同時具有兩個能力
        assert matches[0].agent_id == "agent-1"

    def test_find_capable_agents_include_partial(self, matcher_with_agents):
        """驗證包含部分匹配。"""
        requirements = [
            CapabilityRequirementInfo(name="code_generation"),
            CapabilityRequirementInfo(name="data_analysis"),
        ]
        matches = matcher_with_agents.find_capable_agents(
            requirements, check_availability=False, include_partial=True
        )

        assert len(matches) >= 1


# =============================================================================
# Test: CapabilityMatcherAdapter - Match Strategies
# =============================================================================


class TestCapabilityMatcherAdapterStrategies:
    """測試匹配策略。"""

    @pytest.fixture
    def matcher_with_agents(self):
        """創建帶有註冊 Agent 的 matcher。"""
        matcher = CapabilityMatcherAdapter()

        # Agent 1: 高分
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])
        matcher.update_availability("agent-1", AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.AVAILABLE,
            current_load=0.3,
        ))

        # Agent 2: 中等分數，低負載
        matcher.register_agent("agent-2", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.7),
        ])
        matcher.update_availability("agent-2", AgentAvailabilityInfo(
            agent_id="agent-2",
            status=AgentStatus.AVAILABLE,
            current_load=0.1,
        ))

        # Agent 3: 中等分數，高負載
        matcher.register_agent("agent-3", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.7),
        ])
        matcher.update_availability("agent-3", AgentAvailabilityInfo(
            agent_id="agent-3",
            status=AgentStatus.AVAILABLE,
            current_load=0.8,
        ))

        return matcher

    def test_best_fit_strategy(self, matcher_with_agents):
        """驗證 BEST_FIT 策略 - 選擇分數最高。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        result = matcher_with_agents.get_best_match(
            requirements, strategy=MatchStrategy.BEST_FIT
        )

        assert result is not None
        assert result.agent_id == "agent-1"  # 最高分

    def test_first_fit_strategy(self, matcher_with_agents):
        """驗證 FIRST_FIT 策略 - 選擇第一個達標。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        result = matcher_with_agents.get_best_match(
            requirements, strategy=MatchStrategy.FIRST_FIT
        )

        # 應該返回第一個達到 0.5 閾值的
        assert result is not None
        assert result.score >= 0.5

    def test_least_loaded_strategy(self, matcher_with_agents):
        """驗證 LEAST_LOADED 策略 - 選擇負載最低。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        result = matcher_with_agents.get_best_match(
            requirements, strategy=MatchStrategy.LEAST_LOADED
        )

        assert result is not None
        assert result.agent_id == "agent-2"  # 負載最低 (0.1)

    def test_round_robin_strategy(self, matcher_with_agents):
        """驗證 ROUND_ROBIN 策略 - 輪詢選擇。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]

        # 多次調用應該輪詢不同的 Agent
        results = []
        for _ in range(6):  # 至少調用兩輪
            result = matcher_with_agents.get_best_match(
                requirements, strategy=MatchStrategy.ROUND_ROBIN
            )
            results.append(result.agent_id)

        # 應該有多個不同的 Agent
        unique_agents = set(results)
        assert len(unique_agents) >= 2


# =============================================================================
# Test: CapabilityMatcherAdapter - Availability
# =============================================================================


class TestCapabilityMatcherAdapterAvailability:
    """測試可用性檢查。"""

    def test_update_availability(self):
        """驗證更新可用性。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])

        avail = AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.BUSY,
            current_load=0.7,
        )
        matcher.update_availability("agent-1", avail)

        # 驗證可以找到
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        matches = matcher.find_capable_agents(requirements)
        assert len(matches) == 1
        assert matches[0].availability.status == AgentStatus.BUSY

    def test_filter_unavailable_agents(self):
        """驗證過濾不可用 Agent。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])
        matcher.update_availability("agent-1", AgentAvailabilityInfo(
            agent_id="agent-1",
            status=AgentStatus.OFFLINE,
        ))

        requirements = [CapabilityRequirementInfo(name="code_generation")]
        matches = matcher.find_capable_agents(requirements, check_availability=True)
        assert len(matches) == 0

    def test_external_availability_checker(self):
        """驗證外部可用性檢查器。"""
        def checker(agent_id: str) -> AgentAvailabilityInfo:
            return AgentAvailabilityInfo(
                agent_id=agent_id,
                status=AgentStatus.AVAILABLE,
                current_load=0.5,
            )

        matcher = CapabilityMatcherAdapter(availability_checker=checker)
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])

        requirements = [CapabilityRequirementInfo(name="code_generation")]
        matches = matcher.find_capable_agents(requirements)

        assert len(matches) == 1
        assert matches[0].availability.current_load == 0.5


# =============================================================================
# Test: CapabilityMatcherAdapter - Handoff Integration
# =============================================================================


class TestCapabilityMatcherAdapterHandoff:
    """測試 Handoff 整合功能。"""

    @pytest.fixture
    def matcher_with_agents(self):
        """創建帶有註冊 Agent 的 matcher。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("source", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.5),
        ])
        matcher.register_agent("target-good", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])
        matcher.register_agent("target-worse", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.3),
        ])
        return matcher

    def test_calculate_handoff_score_improvement(self, matcher_with_agents):
        """驗證 Handoff 分數 - 有改進時。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        score = matcher_with_agents.calculate_handoff_score(
            source_agent_id="source",
            target_agent_id="target-good",
            requirements=requirements,
        )

        assert score > 0.7  # 應該有較高分數

    def test_calculate_handoff_score_worse(self, matcher_with_agents):
        """驗證 Handoff 分數 - 無改進時。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        score = matcher_with_agents.calculate_handoff_score(
            source_agent_id="source",
            target_agent_id="target-worse",
            requirements=requirements,
        )

        # 目標比來源差，分數應該較低
        assert score < 0.5

    def test_suggest_handoff_target(self, matcher_with_agents):
        """驗證建議 Handoff 目標。"""
        requirements = [CapabilityRequirementInfo(name="code_generation")]
        result = matcher_with_agents.suggest_handoff_target(
            source_agent_id="source",
            requirements=requirements,
        )

        assert result is not None
        assert result.agent_id == "target-good"  # 應該建議最好的


# =============================================================================
# Test: Factory Functions
# =============================================================================


class TestFactoryFunctions:
    """測試工廠函數。"""

    def test_create_capability_matcher(self):
        """驗證創建 matcher。"""
        matcher = create_capability_matcher()
        assert isinstance(matcher, CapabilityMatcherAdapter)

    def test_create_capability_requirement(self):
        """驗證創建需求。"""
        req = create_capability_requirement(
            name="code_generation",
            min_proficiency=0.7,
            required=True,
            weight=0.8,
        )
        assert req.name == "code_generation"
        assert req.min_proficiency == 0.7
        assert req.required is True
        assert req.weight == 0.8

    def test_create_agent_capability(self):
        """驗證創建能力。"""
        cap = create_agent_capability(
            name="code_generation",
            proficiency=0.9,
            category=CapabilityCategory.ACTION,
            description="Generate code",
        )
        assert cap.name == "code_generation"
        assert cap.proficiency == 0.9
        assert cap.category == CapabilityCategory.ACTION


# =============================================================================
# Test: Utility Methods
# =============================================================================


class TestCapabilityMatcherAdapterUtilities:
    """測試工具方法。"""

    def test_get_agents_by_category(self):
        """驗證按類別獲取 Agent。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(
                name="code_generation",
                category=CapabilityCategory.ACTION
            ),
        ])
        matcher.register_agent("agent-2", [
            AgentCapabilityInfo(
                name="data_analysis",
                category=CapabilityCategory.REASONING
            ),
        ])

        action_agents = matcher.get_agents_by_category(
            CapabilityCategory.ACTION, check_availability=False
        )
        assert len(action_agents) == 1
        assert "agent-1" in action_agents

    def test_get_builtin_capability(self):
        """驗證獲取內建能力。"""
        matcher = CapabilityMatcherAdapter()
        cap = matcher.get_builtin_capability("code_generation")
        assert cap is not None
        assert cap.name == "code_generation"

    def test_list_builtin_capabilities(self):
        """驗證列出內建能力。"""
        matcher = CapabilityMatcherAdapter()
        builtins = matcher.list_builtin_capabilities()
        assert len(builtins) == 15
        assert "code_generation" in builtins
        assert "data_analysis" in builtins


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """測試邊界情況。"""

    def test_empty_requirements(self):
        """驗證空需求處理。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation"),
        ])

        matches = matcher.find_capable_agents([])
        assert len(matches) == 0

    def test_no_matching_agents(self):
        """驗證無匹配 Agent。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation"),
        ])

        requirements = [CapabilityRequirementInfo(name="unknown_capability")]
        matches = matcher.find_capable_agents(requirements)
        assert len(matches) == 0

    def test_exclude_agents_in_get_best_match(self):
        """驗證排除 Agent 功能。"""
        matcher = CapabilityMatcherAdapter()
        matcher.register_agent("agent-1", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.9),
        ])
        matcher.register_agent("agent-2", [
            AgentCapabilityInfo(name="code_generation", proficiency=0.7),
        ])

        requirements = [CapabilityRequirementInfo(name="code_generation")]
        result = matcher.get_best_match(
            requirements,
            exclude_agents={"agent-1"},
        )

        assert result is not None
        assert result.agent_id == "agent-2"

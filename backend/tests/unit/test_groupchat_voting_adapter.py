"""
GroupChatVotingAdapter Unit Tests - Sprint 20 (S20-5)

測試 groupchat_voting.py 模組的所有組件。

測試覆蓋:
    - VotingMethod 枚舉
    - VotingStatus 枚舉
    - VotingConfig 數據類
    - Vote 數據類
    - VotingResult 數據類
    - Voting Selectors (majority, unanimous, ranked, weighted, approval)
    - GroupChatVotingAdapter 類
    - Factory functions (create_voting_chat, etc.)

Author: IPA Platform Team
Sprint: 20 - S20-5 測試遷移
Created: 2025-12-06
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, List

# Import modules under test
from src.integrations.agent_framework.builders.groupchat_voting import (
    # Enums
    VotingMethod,
    VotingStatus,
    # Data classes
    VotingConfig,
    Vote,
    VotingResult,
    # Selectors
    create_voting_selector,
    create_majority_selector,
    create_unanimous_selector,
    create_ranked_selector,
    create_weighted_selector,
    create_approval_selector,
    # Main class
    GroupChatVotingAdapter,
    # Factory functions
    create_voting_chat,
    create_majority_voting_chat,
    create_unanimous_voting_chat,
    create_ranked_voting_chat,
)

from src.integrations.agent_framework.builders.groupchat import (
    GroupChatParticipant,
    GroupChatStatus,
    SpeakerSelectionMethod,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestVotingMethod:
    """測試 VotingMethod 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert VotingMethod.MAJORITY == "majority"
        assert VotingMethod.UNANIMOUS == "unanimous"
        assert VotingMethod.RANKED == "ranked"
        assert VotingMethod.WEIGHTED == "weighted"
        assert VotingMethod.APPROVAL == "approval"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        method = VotingMethod("majority")
        assert method == VotingMethod.MAJORITY

    def test_all_values_exist(self):
        """測試所有預期值都存在。"""
        expected = ["majority", "unanimous", "ranked", "weighted", "approval"]
        actual = [v.value for v in VotingMethod]
        for e in expected:
            assert e in actual


class TestVotingStatus:
    """測試 VotingStatus 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert VotingStatus.PENDING == "pending"
        assert VotingStatus.IN_PROGRESS == "in_progress"
        assert VotingStatus.COMPLETED == "completed"
        assert VotingStatus.CANCELLED == "cancelled"


# =============================================================================
# Data Class Tests
# =============================================================================


class TestVotingConfig:
    """測試 VotingConfig 數據類。"""

    def test_default_values(self):
        """測試預設值。"""
        config = VotingConfig()
        assert config.method == VotingMethod.MAJORITY
        assert config.threshold == 0.5
        assert config.require_all is False
        assert config.timeout_seconds is None
        assert config.allow_abstain is True

    def test_custom_values(self):
        """測試自定義值。"""
        config = VotingConfig(
            method=VotingMethod.UNANIMOUS,
            threshold=1.0,
            require_all=True,
            timeout_seconds=60.0,
            allow_abstain=False,
        )
        assert config.method == VotingMethod.UNANIMOUS
        assert config.threshold == 1.0
        assert config.require_all is True
        assert config.timeout_seconds == 60.0
        assert config.allow_abstain is False


class TestVote:
    """測試 Vote 數據類。"""

    def test_basic_creation(self):
        """測試基本創建。"""
        vote = Vote(
            voter_name="agent1",
            choice="agent2",
        )
        assert vote.voter_name == "agent1"
        assert vote.choice == "agent2"
        assert vote.weight == 1.0
        assert vote.reason is None

    def test_full_creation(self):
        """測試完整創建。"""
        vote = Vote(
            voter_name="agent1",
            choice="agent2",
            weight=2.5,
            reason="Best candidate",
        )
        assert vote.weight == 2.5
        assert vote.reason == "Best candidate"

    def test_to_dict(self):
        """測試轉換為字典。"""
        vote = Vote(
            voter_name="agent1",
            choice="agent2",
            weight=1.5,
            reason="Good choice",
        )
        data = vote.to_dict()
        assert data["voter_name"] == "agent1"
        assert data["choice"] == "agent2"
        assert data["weight"] == 1.5
        assert data["reason"] == "Good choice"


class TestVotingResult:
    """測試 VotingResult 數據類。"""

    def test_default_values(self):
        """測試預設值。"""
        result = VotingResult()
        assert result.winner is None
        assert result.status == VotingStatus.PENDING
        assert result.votes == []
        assert result.tallies == {}
        assert result.participation_rate == 0.0

    def test_full_creation(self):
        """測試完整創建。"""
        votes = [
            Vote(voter_name="a", choice="b"),
            Vote(voter_name="c", choice="b"),
        ]
        result = VotingResult(
            winner="b",
            status=VotingStatus.COMPLETED,
            votes=votes,
            tallies={"b": 2.0},
            participation_rate=1.0,
        )
        assert result.winner == "b"
        assert result.status == VotingStatus.COMPLETED
        assert len(result.votes) == 2
        assert result.tallies["b"] == 2.0

    def test_to_dict(self):
        """測試轉換為字典。"""
        result = VotingResult(
            winner="agent1",
            status=VotingStatus.COMPLETED,
            tallies={"agent1": 3.0, "agent2": 1.0},
            participation_rate=0.8,
        )
        data = result.to_dict()
        assert data["winner"] == "agent1"
        assert data["status"] == "completed"
        assert data["participation_rate"] == 0.8


# =============================================================================
# Voting Selector Tests
# =============================================================================


class TestMajoritySelector:
    """測試多數投票選擇器。"""

    @pytest.fixture
    def participants(self):
        """創建參與者。"""
        return {
            "agent1": GroupChatParticipant(name="agent1", description="Agent 1"),
            "agent2": GroupChatParticipant(name="agent2", description="Agent 2"),
            "agent3": GroupChatParticipant(name="agent3", description="Agent 3"),
        }

    def test_selects_majority_winner(self, participants):
        """測試選擇多數贏家。"""
        selector = create_majority_selector(participants, threshold=0.5)
        state = {
            "conversation": [
                {"content": "I vote for agent2", "author_name": "agent1"},
                {"content": "I also prefer agent2", "author_name": "agent3"},
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "agent2"

    def test_fallback_when_no_votes(self, participants):
        """測試無投票時的回退。"""
        selector = create_majority_selector(participants, threshold=0.5)
        state = {"conversation": [], "history": []}
        result = selector(state)
        # Returns first participant
        assert result in participants.keys()

    def test_empty_participants(self):
        """測試空參與者列表。"""
        selector = create_majority_selector({})
        result = selector({"conversation": []})
        assert result is None


class TestUnanimousSelector:
    """測試一致通過選擇器。"""

    @pytest.fixture
    def participants(self):
        """創建參與者。"""
        return {
            "agent1": GroupChatParticipant(name="agent1", description="Agent 1"),
            "agent2": GroupChatParticipant(name="agent2", description="Agent 2"),
        }

    def test_unanimous_selection(self, participants):
        """測試一致通過選擇。"""
        selector = create_unanimous_selector(participants)
        state = {
            "conversation": [
                {"content": "I support agent1", "author_name": "agent2"},
            ],
            "history": [],
        }
        result = selector(state)
        # agent2 supports agent1
        assert result == "agent1"

    def test_no_unanimous_support(self, participants):
        """測試無一致支持。"""
        selector = create_unanimous_selector(participants)
        state = {
            "conversation": [
                {"content": "I don't know", "author_name": "agent2"},
            ],
            "history": [],
        }
        result = selector(state)
        # No unanimous support, returns first
        assert result in participants.keys()

    def test_empty_participants(self):
        """測試空參與者列表。"""
        selector = create_unanimous_selector({})
        result = selector({"conversation": []})
        assert result is None


class TestRankedSelector:
    """測試排序投票選擇器。"""

    @pytest.fixture
    def participants(self):
        """創建參與者。"""
        return {
            "agent1": GroupChatParticipant(name="agent1", description="Agent 1"),
            "agent2": GroupChatParticipant(name="agent2", description="Agent 2"),
            "agent3": GroupChatParticipant(name="agent3", description="Agent 3"),
        }

    def test_ranked_selection(self, participants):
        """測試排序選擇。"""
        selector = create_ranked_selector(participants)
        state = {
            "conversation": [
                # agent1 is mentioned first by agent2
                {"content": "I prefer agent1, then agent3", "author_name": "agent2"},
            ],
            "history": [],
        }
        result = selector(state)
        # agent1 should get higher score (mentioned first)
        assert result in participants.keys()

    def test_fallback_no_mentions(self, participants):
        """測試無提及時的回退。"""
        selector = create_ranked_selector(participants)
        state = {
            "conversation": [
                {"content": "Hello everyone", "author_name": "agent1"},
            ],
            "history": [],
        }
        result = selector(state)
        assert result in participants.keys()

    def test_empty_participants(self):
        """測試空參與者列表。"""
        selector = create_ranked_selector({})
        result = selector({"conversation": []})
        assert result is None


class TestWeightedSelector:
    """測試加權投票選擇器。"""

    @pytest.fixture
    def weighted_participants(self):
        """創建帶權重的參與者。"""
        return {
            "leader": GroupChatParticipant(
                name="leader",
                description="Team Leader",
                metadata={"weight": 3.0},
            ),
            "member": GroupChatParticipant(
                name="member",
                description="Team Member",
                metadata={"weight": 1.0},
            ),
        }

    def test_weighted_selection(self, weighted_participants):
        """測試加權選擇。"""
        selector = create_weighted_selector(weighted_participants)
        state = {
            "conversation": [
                {"content": "I vote for member", "author_name": "leader"},
            ],
            "history": [],
        }
        result = selector(state)
        # leader's vote has weight 3.0
        assert result == "member"

    def test_fallback_no_votes(self, weighted_participants):
        """測試無投票時的回退。"""
        selector = create_weighted_selector(weighted_participants)
        state = {"conversation": [], "history": []}
        result = selector(state)
        assert result in weighted_participants.keys()


class TestApprovalSelector:
    """測試贊成票選擇器。"""

    @pytest.fixture
    def participants(self):
        """創建參與者。"""
        return {
            "agent1": GroupChatParticipant(name="agent1", description="Agent 1"),
            "agent2": GroupChatParticipant(name="agent2", description="Agent 2"),
            "agent3": GroupChatParticipant(name="agent3", description="Agent 3"),
        }

    def test_approval_selection(self, participants):
        """測試贊成票選擇。"""
        selector = create_approval_selector(participants)
        state = {
            "conversation": [
                {"content": "I agree with agent2", "author_name": "agent1"},
                {"content": "I also support agent2", "author_name": "agent3"},
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "agent2"

    def test_approval_keywords_chinese(self, participants):
        """測試中文贊成關鍵字。"""
        selector = create_approval_selector(participants)
        state = {
            "conversation": [
                {"content": "我同意 agent1 的方案", "author_name": "agent2"},
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "agent1"

    def test_no_approval_fallback(self, participants):
        """測試無贊成時的回退。"""
        selector = create_approval_selector(participants)
        state = {
            "conversation": [
                {"content": "Let me think about it", "author_name": "agent1"},
            ],
            "history": [],
        }
        result = selector(state)
        assert result in participants.keys()


class TestCreateVotingSelector:
    """測試 create_voting_selector 工廠函數。"""

    @pytest.fixture
    def participants(self):
        """創建參與者。"""
        return {
            "agent1": GroupChatParticipant(name="agent1", description="Agent 1"),
            "agent2": GroupChatParticipant(name="agent2", description="Agent 2"),
        }

    def test_creates_majority_selector(self, participants):
        """測試創建多數選擇器。"""
        config = VotingConfig(method=VotingMethod.MAJORITY)
        selector = create_voting_selector(participants, config)
        assert callable(selector)

    def test_creates_unanimous_selector(self, participants):
        """測試創建一致通過選擇器。"""
        config = VotingConfig(method=VotingMethod.UNANIMOUS)
        selector = create_voting_selector(participants, config)
        assert callable(selector)

    def test_creates_ranked_selector(self, participants):
        """測試創建排序選擇器。"""
        config = VotingConfig(method=VotingMethod.RANKED)
        selector = create_voting_selector(participants, config)
        assert callable(selector)

    def test_creates_weighted_selector(self, participants):
        """測試創建加權選擇器。"""
        config = VotingConfig(method=VotingMethod.WEIGHTED)
        selector = create_voting_selector(participants, config)
        assert callable(selector)

    def test_creates_approval_selector(self, participants):
        """測試創建贊成票選擇器。"""
        config = VotingConfig(method=VotingMethod.APPROVAL)
        selector = create_voting_selector(participants, config)
        assert callable(selector)


# =============================================================================
# GroupChatVotingAdapter Tests
# =============================================================================


class TestGroupChatVotingAdapter:
    """測試 GroupChatVotingAdapter 類。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(name="agent1", description="Agent 1"),
            GroupChatParticipant(name="agent2", description="Agent 2"),
            GroupChatParticipant(name="agent3", description="Agent 3"),
        ]

    def test_creation_default(self, sample_participants):
        """測試預設創建。"""
        adapter = GroupChatVotingAdapter(
            id="voting-test",
            participants=sample_participants,
        )
        assert adapter.id == "voting-test"
        assert adapter.voting_config.method == VotingMethod.MAJORITY
        assert adapter.voting_config.threshold == 0.5

    def test_creation_with_method(self, sample_participants):
        """測試指定投票方法創建。"""
        adapter = GroupChatVotingAdapter(
            id="voting-test",
            participants=sample_participants,
            voting_method=VotingMethod.UNANIMOUS,
        )
        assert adapter.voting_config.method == VotingMethod.UNANIMOUS

    def test_creation_with_threshold(self, sample_participants):
        """測試指定投票門檻創建。"""
        adapter = GroupChatVotingAdapter(
            id="voting-test",
            participants=sample_participants,
            voting_threshold=0.7,
        )
        assert adapter.voting_config.threshold == 0.7

    def test_creation_with_config(self, sample_participants):
        """測試使用 VotingConfig 創建。"""
        config = VotingConfig(
            method=VotingMethod.RANKED,
            threshold=0.8,
            require_all=True,
        )
        adapter = GroupChatVotingAdapter(
            id="voting-test",
            participants=sample_participants,
            voting_config=config,
        )
        assert adapter.voting_config.method == VotingMethod.RANKED
        assert adapter.voting_config.require_all is True

    def test_inherits_from_groupchat_adapter(self, sample_participants):
        """測試繼承自 GroupChatBuilderAdapter。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        # Should have base adapter methods
        assert hasattr(adapter, "build")
        assert hasattr(adapter, "run")
        assert hasattr(adapter, "participants")

    def test_uses_custom_selection_method(self, sample_participants):
        """測試使用 CUSTOM 選擇方法。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        # Internally uses CUSTOM with voting selector
        assert adapter.selection_method == SpeakerSelectionMethod.CUSTOM

    def test_with_voting_updates_config(self, sample_participants):
        """測試 with_voting 更新配置。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
            voting_method=VotingMethod.MAJORITY,
        )
        adapter.with_voting(
            method=VotingMethod.UNANIMOUS,
            threshold=1.0,
        )
        assert adapter.voting_config.method == VotingMethod.UNANIMOUS
        assert adapter.voting_config.threshold == 1.0

    def test_with_voting_returns_self(self, sample_participants):
        """測試 with_voting 返回 self。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        result = adapter.with_voting(method=VotingMethod.RANKED)
        assert result is adapter

    def test_with_voting_chain(self, sample_participants):
        """測試 with_voting 鏈式調用。"""
        adapter = (
            GroupChatVotingAdapter(
                id="test",
                participants=sample_participants,
            )
            .with_voting(method=VotingMethod.WEIGHTED)
            .with_voting(threshold=0.9)
        )
        assert adapter.voting_config.method == VotingMethod.WEIGHTED
        assert adapter.voting_config.threshold == 0.9

    def test_voting_results_property(self, sample_participants):
        """測試 voting_results 屬性。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        results = adapter.voting_results
        assert isinstance(results, list)

    def test_clear_voting_history(self, sample_participants):
        """測試清除投票歷史。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        # Add some fake results
        adapter._voting_results.append(VotingResult(winner="agent1"))
        assert len(adapter.voting_results) == 1

        adapter.clear_voting_history()
        assert len(adapter.voting_results) == 0

    @pytest.mark.asyncio
    async def test_initialize(self, sample_participants):
        """測試初始化。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        assert adapter.is_initialized is True
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_run(self, sample_participants):
        """測試執行。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
            max_rounds=2,
        )
        await adapter.initialize()
        result = await adapter.run("Test voting task")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_build(self, sample_participants):
        """測試構建。"""
        adapter = GroupChatVotingAdapter(
            id="test",
            participants=sample_participants,
        )
        await adapter.initialize()
        workflow = adapter.build()
        assert workflow is not None
        await adapter.cleanup()


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestVotingFactoryFunctions:
    """測試投票工廠函數。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(name="agent1", description="Agent 1"),
            GroupChatParticipant(name="agent2", description="Agent 2"),
        ]

    def test_create_voting_chat(self, sample_participants):
        """測試 create_voting_chat。"""
        adapter = create_voting_chat(
            id="factory-test",
            participants=sample_participants,
            voting_method=VotingMethod.MAJORITY,
            voting_threshold=0.6,
            max_rounds=5,
        )
        assert adapter.id == "factory-test"
        assert adapter.voting_config.method == VotingMethod.MAJORITY
        assert adapter.voting_config.threshold == 0.6
        assert adapter._max_rounds == 5

    def test_create_majority_voting_chat(self, sample_participants):
        """測試 create_majority_voting_chat。"""
        adapter = create_majority_voting_chat(
            id="majority-test",
            participants=sample_participants,
            threshold=0.7,
        )
        assert adapter.voting_config.method == VotingMethod.MAJORITY
        assert adapter.voting_config.threshold == 0.7

    def test_create_unanimous_voting_chat(self, sample_participants):
        """測試 create_unanimous_voting_chat。"""
        adapter = create_unanimous_voting_chat(
            id="unanimous-test",
            participants=sample_participants,
        )
        assert adapter.voting_config.method == VotingMethod.UNANIMOUS
        assert adapter.voting_config.threshold == 1.0

    def test_create_ranked_voting_chat(self, sample_participants):
        """測試 create_ranked_voting_chat。"""
        adapter = create_ranked_voting_chat(
            id="ranked-test",
            participants=sample_participants,
        )
        assert adapter.voting_config.method == VotingMethod.RANKED

    def test_default_max_rounds(self, sample_participants):
        """測試預設最大輪數。"""
        adapter = create_voting_chat(
            id="test",
            participants=sample_participants,
        )
        assert adapter._max_rounds == 10

    def test_unanimous_default_max_rounds(self, sample_participants):
        """測試一致通過的預設最大輪數。"""
        adapter = create_unanimous_voting_chat(
            id="test",
            participants=sample_participants,
        )
        assert adapter._max_rounds == 15


# =============================================================================
# Integration Tests
# =============================================================================


class TestVotingIntegration:
    """投票整合測試。"""

    @pytest.fixture
    def sample_participants(self):
        """創建示例參與者。"""
        return [
            GroupChatParticipant(
                name="agent1",
                description="Agent 1",
                metadata={"weight": 2.0},
            ),
            GroupChatParticipant(
                name="agent2",
                description="Agent 2",
                metadata={"weight": 1.0},
            ),
            GroupChatParticipant(
                name="agent3",
                description="Agent 3",
                metadata={"weight": 1.0},
            ),
        ]

    @pytest.mark.asyncio
    async def test_full_voting_flow(self, sample_participants):
        """測試完整投票流程。"""
        adapter = GroupChatVotingAdapter(
            id="integration-test",
            participants=sample_participants,
            voting_method=VotingMethod.MAJORITY,
            max_rounds=3,
        )

        await adapter.initialize()
        assert adapter.is_initialized

        result = await adapter.run("Discuss and vote on the best approach")

        assert result.status == GroupChatStatus.COMPLETED
        assert result.total_rounds >= 0
        assert result.duration > 0

        await adapter.cleanup()
        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_context_manager(self, sample_participants):
        """測試上下文管理器。"""
        adapter = GroupChatVotingAdapter(
            id="context-test",
            participants=sample_participants,
            max_rounds=2,
        )

        async with adapter:
            assert adapter.is_initialized
            result = await adapter.run("Test")
            assert result is not None

        assert not adapter.is_initialized

    @pytest.mark.asyncio
    async def test_weighted_voting_flow(self, sample_participants):
        """測試加權投票流程。"""
        adapter = GroupChatVotingAdapter(
            id="weighted-test",
            participants=sample_participants,
            voting_method=VotingMethod.WEIGHTED,
            max_rounds=2,
        )

        await adapter.initialize()
        result = await adapter.run("Weighted voting test")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_unanimous_voting_flow(self, sample_participants):
        """測試一致通過投票流程。"""
        adapter = create_unanimous_voting_chat(
            id="unanimous-test",
            participants=sample_participants,
            max_rounds=2,
        )

        await adapter.initialize()
        result = await adapter.run("Need unanimous agreement")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_ranked_voting_flow(self, sample_participants):
        """測試排序投票流程。"""
        adapter = create_ranked_voting_chat(
            id="ranked-test",
            participants=sample_participants,
            max_rounds=2,
        )

        await adapter.initialize()
        result = await adapter.run("Rank your preferences")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

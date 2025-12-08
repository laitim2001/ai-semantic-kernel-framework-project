"""
GroupChatBuilderAdapter Extended Unit Tests - Sprint 20 (S20-5)

Sprint 20 新增功能測試:
    - PRIORITY 選擇方法
    - EXPERTISE 選擇方法
    - 終止條件 (TerminationType)
    - 終止條件工廠函數
    - 工廠函數 (create_priority_chat, create_expertise_chat)

測試覆蓋:
    - create_priority_selector
    - create_expertise_selector
    - TerminationType 枚舉
    - create_max_rounds_termination
    - create_max_messages_termination
    - create_keyword_termination
    - create_timeout_termination
    - create_consensus_termination
    - create_no_progress_termination
    - create_combined_termination
    - create_priority_chat
    - create_expertise_chat

Author: IPA Platform Team
Sprint: 20 - S20-5 測試遷移
Created: 2025-12-06
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from typing import Dict, Any, List

# Import modules under test
from src.integrations.agent_framework.builders.groupchat import (
    # Enums
    SpeakerSelectionMethod,
    GroupChatStatus,
    MessageRole,
    TerminationType,
    DEFAULT_TERMINATION_KEYWORDS,
    # Data classes
    GroupChatParticipant,
    GroupChatMessage,
    GroupChatState,
    GroupChatResult,
    # Sprint 20: Priority and Expertise Selectors
    create_priority_selector,
    create_expertise_selector,
    # Sprint 20: Termination Conditions
    create_max_rounds_termination,
    create_max_messages_termination,
    create_keyword_termination,
    create_timeout_termination,
    create_consensus_termination,
    create_no_progress_termination,
    create_combined_termination,
    # Main class
    GroupChatBuilderAdapter,
    # Sprint 20: Factory functions
    create_priority_chat,
    create_expertise_chat,
)


# =============================================================================
# Sprint 20: TerminationType Enum Tests
# =============================================================================


class TestTerminationType:
    """測試 TerminationType 枚舉。"""

    def test_enum_values(self):
        """測試枚舉值。"""
        assert TerminationType.MAX_ROUNDS == "max_rounds"
        assert TerminationType.MAX_MESSAGES == "max_messages"
        assert TerminationType.TIMEOUT == "timeout"
        assert TerminationType.KEYWORD == "keyword"
        assert TerminationType.CONSENSUS == "consensus"
        assert TerminationType.CUSTOM == "custom"
        assert TerminationType.NO_PROGRESS == "no_progress"

    def test_enum_from_string(self):
        """測試從字符串創建枚舉。"""
        term_type = TerminationType("keyword")
        assert term_type == TerminationType.KEYWORD

    def test_all_values_exist(self):
        """測試所有預期值都存在。"""
        expected_values = [
            "max_rounds",
            "max_messages",
            "timeout",
            "keyword",
            "consensus",
            "custom",
            "no_progress",
        ]
        actual_values = [t.value for t in TerminationType]
        for expected in expected_values:
            assert expected in actual_values


class TestDefaultTerminationKeywords:
    """測試預設終止關鍵字。"""

    def test_default_keywords_exist(self):
        """測試預設關鍵字存在。"""
        assert len(DEFAULT_TERMINATION_KEYWORDS) > 0

    def test_contains_common_keywords(self):
        """測試包含常見關鍵字。"""
        assert "TERMINATE" in DEFAULT_TERMINATION_KEYWORDS
        assert "DONE" in DEFAULT_TERMINATION_KEYWORDS

    def test_contains_chinese_keywords(self):
        """測試包含中文關鍵字。"""
        assert "完成" in DEFAULT_TERMINATION_KEYWORDS
        assert "結束" in DEFAULT_TERMINATION_KEYWORDS


# =============================================================================
# Sprint 20: SpeakerSelectionMethod Enum Tests (PRIORITY, EXPERTISE)
# =============================================================================


class TestSpeakerSelectionMethodSprint20:
    """測試 Sprint 20 新增的選擇方法。"""

    def test_priority_value(self):
        """測試 PRIORITY 枚舉值。"""
        assert SpeakerSelectionMethod.PRIORITY == "priority"

    def test_expertise_value(self):
        """測試 EXPERTISE 枚舉值。"""
        assert SpeakerSelectionMethod.EXPERTISE == "expertise"

    def test_enum_from_string_priority(self):
        """測試從字符串創建 PRIORITY。"""
        method = SpeakerSelectionMethod("priority")
        assert method == SpeakerSelectionMethod.PRIORITY

    def test_enum_from_string_expertise(self):
        """測試從字符串創建 EXPERTISE。"""
        method = SpeakerSelectionMethod("expertise")
        assert method == SpeakerSelectionMethod.EXPERTISE


# =============================================================================
# Sprint 20: Priority Selector Tests
# =============================================================================


class TestPrioritySelector:
    """測試優先級選擇器。"""

    @pytest.fixture
    def priority_participants(self):
        """創建帶優先級的參與者。"""
        return {
            "senior": GroupChatParticipant(
                name="senior",
                description="Senior Developer",
                metadata={"priority": 1},
            ),
            "mid": GroupChatParticipant(
                name="mid",
                description="Mid-level Developer",
                metadata={"priority": 2},
            ),
            "junior": GroupChatParticipant(
                name="junior",
                description="Junior Developer",
                metadata={"priority": 3},
            ),
        }

    def test_selects_highest_priority(self, priority_participants):
        """測試選擇最高優先級（數值最小）的參與者。"""
        selector = create_priority_selector(priority_participants)
        state = {"history": [], "round_index": 0}
        result = selector(state)
        assert result == "senior"  # priority=1 is highest

    def test_avoids_last_speaker(self, priority_participants):
        """測試避免連續發言。"""
        selector = create_priority_selector(priority_participants)
        state = {
            "history": [{"speaker": "senior"}],
            "round_index": 1,
        }
        result = selector(state)
        # senior was last speaker, so should skip to next highest priority
        assert result == "mid"

    def test_fallback_when_all_filtered(self, priority_participants):
        """測試當所有人都被過濾時的回退。"""
        # 只有一個參與者
        single = {
            "only": GroupChatParticipant(
                name="only",
                description="Only one",
                metadata={"priority": 1},
            ),
        }
        selector = create_priority_selector(single)
        state = {"history": [{"speaker": "only"}]}
        result = selector(state)
        # Should still return the only participant
        assert result == "only"

    def test_default_priority(self):
        """測試無優先級設置時的預設行為。"""
        participants = {
            "no_priority": GroupChatParticipant(
                name="no_priority",
                description="No priority set",
            ),
            "with_priority": GroupChatParticipant(
                name="with_priority",
                description="Has priority",
                metadata={"priority": 50},
            ),
        }
        selector = create_priority_selector(participants)
        state = {"history": []}
        result = selector(state)
        # with_priority has 50, no_priority defaults to 100
        assert result == "with_priority"

    def test_empty_participants(self):
        """測試空參與者列表。"""
        selector = create_priority_selector({})
        result = selector({"history": []})
        assert result is None


# =============================================================================
# Sprint 20: Expertise Selector Tests
# =============================================================================


class TestExpertiseSelector:
    """測試專業能力匹配選擇器。"""

    @pytest.fixture
    def expertise_participants(self):
        """創建帶專業能力的參與者。"""
        return {
            "coder": GroupChatParticipant(
                name="coder",
                description="Software Developer",
                capabilities=["coding", "debugging"],
            ),
            "tester": GroupChatParticipant(
                name="tester",
                description="QA Engineer",
                capabilities=["testing", "qa"],
            ),
            "designer": GroupChatParticipant(
                name="designer",
                description="UX Designer",
                capabilities=["design", "analysis"],
            ),
        }

    def test_matches_direct_keyword(self, expertise_participants):
        """測試直接關鍵字匹配。"""
        selector = create_expertise_selector(expertise_participants)
        state = {
            "conversation": [
                {"content": "We need to write some code for this feature", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        # "code" should match "coding" capability
        assert result == "coder"

    def test_matches_synonym(self, expertise_participants):
        """測試同義詞匹配。"""
        selector = create_expertise_selector(expertise_participants)
        state = {
            "conversation": [
                {"content": "Can someone debug this issue?", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        # "debug" is a synonym for "debugging"
        assert result == "coder"

    def test_matches_testing_keywords(self, expertise_participants):
        """測試測試相關關鍵字匹配。"""
        selector = create_expertise_selector(expertise_participants)
        state = {
            "conversation": [
                {"content": "Please test the new functionality", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "tester"

    def test_matches_design_keywords(self, expertise_participants):
        """測試設計相關關鍵字匹配。"""
        selector = create_expertise_selector(expertise_participants)
        state = {
            "conversation": [
                {"content": "We need a new UI design for this page", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "designer"

    def test_fallback_first_participant(self, expertise_participants):
        """測試無匹配時返回第一個參與者。"""
        selector = create_expertise_selector(expertise_participants)
        state = {
            "conversation": [
                {"content": "Hello everyone", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        # No specific match, returns first participant
        assert result in expertise_participants.keys()

    def test_empty_conversation(self, expertise_participants):
        """測試空對話。"""
        selector = create_expertise_selector(expertise_participants)
        state = {"conversation": [], "history": []}
        result = selector(state)
        # Returns first participant when no context
        assert result in expertise_participants.keys()

    def test_custom_synonym_map(self, expertise_participants):
        """測試自定義同義詞映射。"""
        custom_synonyms = {
            "testing": ["unit", "integration", "e2e", "regression"],
        }
        selector = create_expertise_selector(
            expertise_participants,
            synonym_map=custom_synonyms,
        )
        state = {
            "conversation": [
                {"content": "Run the unit tests", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        assert result == "tester"

    def test_min_score_threshold(self, expertise_participants):
        """測試最小分數閾值。"""
        selector = create_expertise_selector(
            expertise_participants,
            min_score_threshold=0.9,  # Very high threshold
        )
        state = {
            "conversation": [
                {"content": "Hello world", "author_name": "user"}
            ],
            "history": [],
        }
        result = selector(state)
        # Low match score, returns first participant
        assert result in expertise_participants.keys()

    def test_empty_participants(self):
        """測試空參與者列表。"""
        selector = create_expertise_selector({})
        result = selector({"conversation": [], "history": []})
        assert result is None


# =============================================================================
# Sprint 20: Termination Condition Tests
# =============================================================================


class TestMaxRoundsTermination:
    """測試最大輪數終止條件。"""

    def test_below_max_rounds(self):
        """測試未達到最大輪數。"""
        condition = create_max_rounds_termination(5)
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content=f"Response {i}")
            for i in range(3)
        ]
        assert condition(messages) is False

    def test_at_max_rounds(self):
        """測試達到最大輪數。"""
        condition = create_max_rounds_termination(3)
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content=f"Response {i}")
            for i in range(3)
        ]
        assert condition(messages) is True

    def test_above_max_rounds(self):
        """測試超過最大輪數。"""
        condition = create_max_rounds_termination(2)
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content=f"Response {i}")
            for i in range(5)
        ]
        assert condition(messages) is True

    def test_ignores_user_messages(self):
        """測試忽略用戶消息。"""
        condition = create_max_rounds_termination(2)
        messages = [
            GroupChatMessage(role=MessageRole.USER, content="User 1"),
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Agent 1"),
            GroupChatMessage(role=MessageRole.USER, content="User 2"),
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Agent 2"),
        ]
        # Only 2 agent messages
        assert condition(messages) is True


class TestMaxMessagesTermination:
    """測試最大訊息數終止條件。"""

    def test_below_max_messages(self):
        """測試未達到最大訊息數。"""
        condition = create_max_messages_termination(10)
        messages = [
            GroupChatMessage(role=MessageRole.USER, content=f"Message {i}")
            for i in range(5)
        ]
        assert condition(messages) is False

    def test_at_max_messages(self):
        """測試達到最大訊息數。"""
        condition = create_max_messages_termination(5)
        messages = [
            GroupChatMessage(role=MessageRole.USER, content=f"Message {i}")
            for i in range(5)
        ]
        assert condition(messages) is True


class TestKeywordTermination:
    """測試關鍵字終止條件。"""

    def test_default_keywords(self):
        """測試預設關鍵字。"""
        condition = create_keyword_termination()
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Task is DONE")
        ]
        assert condition(messages) is True

    def test_custom_keywords(self):
        """測試自定義關鍵字。"""
        condition = create_keyword_termination(keywords=["STOP", "FINISH"])
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Let's STOP here")
        ]
        assert condition(messages) is True

    def test_no_keyword_match(self):
        """測試無關鍵字匹配。"""
        condition = create_keyword_termination(keywords=["TERMINATE"])
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Continuing work...")
        ]
        assert condition(messages) is False

    def test_case_insensitive(self):
        """測試不區分大小寫。"""
        condition = create_keyword_termination(
            keywords=["DONE"],
            case_sensitive=False,
        )
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="done with task")
        ]
        assert condition(messages) is True

    def test_case_sensitive(self):
        """測試區分大小寫。"""
        condition = create_keyword_termination(
            keywords=["DONE"],
            case_sensitive=True,
        )
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="done with task")
        ]
        assert condition(messages) is False

    def test_check_last_n(self):
        """測試只檢查最後 N 條訊息。"""
        condition = create_keyword_termination(
            keywords=["DONE"],
            check_last_n=2,
        )
        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="First DONE"),
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Second message"),
            GroupChatMessage(role=MessageRole.ASSISTANT, content="Third message"),
        ]
        # "DONE" is in first message, but we only check last 2
        assert condition(messages) is False

    def test_empty_messages(self):
        """測試空訊息列表。"""
        condition = create_keyword_termination()
        assert condition([]) is False


class TestTimeoutTermination:
    """測試超時終止條件。"""

    def test_within_timeout(self):
        """測試在超時範圍內。"""
        condition = create_timeout_termination(10.0)
        messages = [
            GroupChatMessage(role=MessageRole.USER, content="Message")
        ]
        assert condition(messages) is False

    def test_after_timeout(self):
        """測試超時後。"""
        # Create condition with a very small timeout
        start_time = time.time() - 5.0  # 5 seconds ago
        condition = create_timeout_termination(1.0, start_time=start_time)
        messages = [
            GroupChatMessage(role=MessageRole.USER, content="Message")
        ]
        assert condition(messages) is True


class TestConsensusTermination:
    """測試共識終止條件。"""

    def test_consensus_reached(self):
        """測試達成共識。"""
        condition = create_consensus_termination(
            agreement_keyword="agree",
            threshold=0.5,
            check_last_n=5,
        )
        messages = [
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="I agree with this approach",
                author_name="agent1",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="I also agree",
                author_name="agent2",
            ),
        ]
        assert condition(messages) is True

    def test_no_consensus(self):
        """測試未達成共識。"""
        condition = create_consensus_termination(
            agreement_keyword="agree",
            threshold=0.8,
            check_last_n=5,
        )
        messages = [
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="I disagree",
                author_name="agent1",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Let me think about it",
                author_name="agent2",
            ),
        ]
        assert condition(messages) is False

    def test_empty_messages(self):
        """測試空訊息列表。"""
        condition = create_consensus_termination()
        assert condition([]) is False


class TestNoProgressTermination:
    """測試無進展終止條件。"""

    def test_repeated_messages(self):
        """測試重複訊息。"""
        condition = create_no_progress_termination(
            min_repeats=3,
            check_last_n=5,
        )
        messages = [
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Same response",
                author_name="agent1",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Same response",
                author_name="agent2",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Same response",
                author_name="agent3",
            ),
        ]
        assert condition(messages) is True

    def test_different_messages(self):
        """測試不同訊息。"""
        condition = create_no_progress_termination(min_repeats=3)
        messages = [
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="First response",
                author_name="agent1",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Second response",
                author_name="agent2",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Third response",
                author_name="agent3",
            ),
        ]
        assert condition(messages) is False

    def test_not_enough_messages(self):
        """測試訊息數不足。"""
        condition = create_no_progress_termination(min_repeats=5)
        messages = [
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Same",
                author_name="agent1",
            ),
            GroupChatMessage(
                role=MessageRole.ASSISTANT,
                content="Same",
                author_name="agent2",
            ),
        ]
        assert condition(messages) is False


class TestCombinedTermination:
    """測試組合終止條件。"""

    def test_any_mode(self):
        """測試 any 模式（任一滿足則終止）。"""
        cond1 = create_max_rounds_termination(10)
        cond2 = create_keyword_termination(keywords=["DONE"])

        combined = create_combined_termination(cond1, cond2, mode="any")

        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="DONE")
        ]
        # keyword matches, even though rounds < 10
        assert combined(messages) is True

    def test_all_mode(self):
        """測試 all 模式（全部滿足才終止）。"""
        cond1 = create_max_rounds_termination(1)
        cond2 = create_keyword_termination(keywords=["DONE"])

        combined = create_combined_termination(cond1, cond2, mode="all")

        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="DONE")
        ]
        # Both conditions met (1 agent message >= 1, and "DONE" keyword)
        assert combined(messages) is True

    def test_all_mode_not_all_met(self):
        """測試 all 模式未全部滿足。"""
        cond1 = create_max_rounds_termination(10)  # Not met
        cond2 = create_keyword_termination(keywords=["DONE"])  # Met

        combined = create_combined_termination(cond1, cond2, mode="all")

        messages = [
            GroupChatMessage(role=MessageRole.ASSISTANT, content="DONE")
        ]
        # Only keyword matches, rounds < 10
        assert combined(messages) is False

    def test_invalid_mode(self):
        """測試無效模式。"""
        cond1 = create_max_rounds_termination(5)
        combined = create_combined_termination(cond1, mode="invalid")

        with pytest.raises(ValueError, match="Unknown mode"):
            combined([])


# =============================================================================
# Sprint 20: GroupChatBuilderAdapter with PRIORITY/EXPERTISE Tests
# =============================================================================


class TestGroupChatBuilderAdapterSprint20:
    """測試 Sprint 20 新增的適配器功能。"""

    @pytest.fixture
    def priority_participants(self):
        """創建帶優先級的參與者列表。"""
        return [
            GroupChatParticipant(
                name="senior",
                description="Senior Developer",
                metadata={"priority": 1},
            ),
            GroupChatParticipant(
                name="junior",
                description="Junior Developer",
                metadata={"priority": 2},
            ),
        ]

    @pytest.fixture
    def expertise_participants(self):
        """創建帶專業能力的參與者列表。"""
        return [
            GroupChatParticipant(
                name="coder",
                description="Developer",
                capabilities=["coding", "debugging"],
            ),
            GroupChatParticipant(
                name="tester",
                description="QA Engineer",
                capabilities=["testing", "qa"],
            ),
        ]

    def test_priority_selection_method(self, priority_participants):
        """測試 PRIORITY 選擇方法。"""
        adapter = GroupChatBuilderAdapter(
            id="priority-test",
            participants=priority_participants,
            selection_method=SpeakerSelectionMethod.PRIORITY,
        )
        assert adapter.selection_method == SpeakerSelectionMethod.PRIORITY

    def test_expertise_selection_method(self, expertise_participants):
        """測試 EXPERTISE 選擇方法。"""
        adapter = GroupChatBuilderAdapter(
            id="expertise-test",
            participants=expertise_participants,
            selection_method=SpeakerSelectionMethod.EXPERTISE,
        )
        assert adapter.selection_method == SpeakerSelectionMethod.EXPERTISE

    def test_get_speaker_selector_priority(self, priority_participants):
        """測試獲取 PRIORITY 選擇器。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=priority_participants,
            selection_method=SpeakerSelectionMethod.PRIORITY,
        )
        selector = adapter._get_speaker_selector()
        assert callable(selector)

    def test_get_speaker_selector_expertise(self, expertise_participants):
        """測試獲取 EXPERTISE 選擇器。"""
        adapter = GroupChatBuilderAdapter(
            id="test",
            participants=expertise_participants,
            selection_method=SpeakerSelectionMethod.EXPERTISE,
        )
        selector = adapter._get_speaker_selector()
        assert callable(selector)

    @pytest.mark.asyncio
    async def test_run_with_priority(self, priority_participants):
        """測試使用 PRIORITY 選擇方法執行。"""
        adapter = GroupChatBuilderAdapter(
            id="priority-run-test",
            participants=priority_participants,
            selection_method=SpeakerSelectionMethod.PRIORITY,
            max_rounds=2,
        )
        await adapter.initialize()
        result = await adapter.run("Test task")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_run_with_expertise(self, expertise_participants):
        """測試使用 EXPERTISE 選擇方法執行。"""
        adapter = GroupChatBuilderAdapter(
            id="expertise-run-test",
            participants=expertise_participants,
            selection_method=SpeakerSelectionMethod.EXPERTISE,
            max_rounds=2,
        )
        await adapter.initialize()
        result = await adapter.run("Please write some code")

        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()


# =============================================================================
# Sprint 20: Factory Function Tests
# =============================================================================


class TestFactoryFunctionsSprint20:
    """測試 Sprint 20 新增的工廠函數。"""

    @pytest.fixture
    def priority_participants(self):
        """創建帶優先級的參與者列表。"""
        return [
            GroupChatParticipant(
                name="senior",
                description="Senior Developer",
                metadata={"priority": 1},
            ),
            GroupChatParticipant(
                name="junior",
                description="Junior Developer",
                metadata={"priority": 2},
            ),
        ]

    @pytest.fixture
    def expertise_participants(self):
        """創建帶專業能力的參與者列表。"""
        return [
            GroupChatParticipant(
                name="coder",
                description="Developer",
                capabilities=["coding"],
            ),
            GroupChatParticipant(
                name="tester",
                description="QA Engineer",
                capabilities=["testing"],
            ),
        ]

    def test_create_priority_chat(self, priority_participants):
        """測試 create_priority_chat 工廠函數。"""
        adapter = create_priority_chat(
            id="priority-factory-test",
            participants=priority_participants,
            max_rounds=5,
        )
        assert adapter.id == "priority-factory-test"
        assert adapter.selection_method == SpeakerSelectionMethod.PRIORITY
        assert adapter._max_rounds == 5

    def test_create_expertise_chat(self, expertise_participants):
        """測試 create_expertise_chat 工廠函數。"""
        adapter = create_expertise_chat(
            id="expertise-factory-test",
            participants=expertise_participants,
            max_rounds=10,
        )
        assert adapter.id == "expertise-factory-test"
        assert adapter.selection_method == SpeakerSelectionMethod.EXPERTISE
        assert adapter._max_rounds == 10

    def test_create_priority_chat_defaults(self, priority_participants):
        """測試 create_priority_chat 預設值。"""
        adapter = create_priority_chat(
            id="test",
            participants=priority_participants,
        )
        # Default max_rounds is 10
        assert adapter._max_rounds == 10

    def test_create_expertise_chat_defaults(self, expertise_participants):
        """測試 create_expertise_chat 預設值。"""
        adapter = create_expertise_chat(
            id="test",
            participants=expertise_participants,
        )
        # Default max_rounds is 15
        assert adapter._max_rounds == 15

    @pytest.mark.asyncio
    async def test_create_priority_chat_execution(self, priority_participants):
        """測試 create_priority_chat 創建的適配器執行。"""
        adapter = create_priority_chat(
            id="priority-exec-test",
            participants=priority_participants,
            max_rounds=2,
        )
        await adapter.initialize()
        result = await adapter.run("Test priority chat")
        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

    @pytest.mark.asyncio
    async def test_create_expertise_chat_execution(self, expertise_participants):
        """測試 create_expertise_chat 創建的適配器執行。"""
        adapter = create_expertise_chat(
            id="expertise-exec-test",
            participants=expertise_participants,
            max_rounds=2,
        )
        await adapter.initialize()
        result = await adapter.run("Test expertise chat")
        assert result.status == GroupChatStatus.COMPLETED
        await adapter.cleanup()

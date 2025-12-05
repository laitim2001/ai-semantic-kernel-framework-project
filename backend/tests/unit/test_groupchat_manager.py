# =============================================================================
# IPA Platform - GroupChatManager Tests
# =============================================================================
# Sprint 9: S9-1 GroupChatManager (8 points)
#
# Unit tests for GroupChatManager, GroupChatState, and related classes.
# =============================================================================

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.domain.orchestration.groupchat.manager import (
    AgentInfo,
    GroupChatConfig,
    GroupChatManager,
    GroupChatState,
    GroupChatStatus,
    GroupMessage,
    MessageType,
    SpeakerSelectionMethod,
)
from src.domain.orchestration.groupchat.termination import (
    TerminationChecker,
    TerminationCondition,
    TerminationResult,
    TerminationType,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_agents():
    """Create sample agents for testing."""
    return [
        AgentInfo(
            agent_id="agent-1",
            name="Planning Agent",
            description="Handles project planning tasks",
            capabilities=["planning", "scheduling", "coordination"],
            priority=1,
        ),
        AgentInfo(
            agent_id="agent-2",
            name="Technical Agent",
            description="Handles technical implementation",
            capabilities=["coding", "debugging", "testing"],
            priority=2,
        ),
        AgentInfo(
            agent_id="agent-3",
            name="Review Agent",
            description="Reviews and provides feedback",
            capabilities=["review", "feedback", "quality"],
            priority=3,
        ),
    ]


@pytest.fixture
def sample_config():
    """Create sample group chat config."""
    return GroupChatConfig(
        max_rounds=5,
        max_messages_per_round=3,
        speaker_selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
        allow_repeat_speaker=False,
        timeout_seconds=120,
        enable_voting=False,
    )


@pytest.fixture
def manager():
    """Create a GroupChatManager instance."""
    return GroupChatManager()


@pytest.fixture
def manager_with_llm():
    """Create a GroupChatManager with mock LLM client."""
    llm_client = MagicMock()
    llm_client.complete = AsyncMock(return_value="agent-1")
    return GroupChatManager(llm_client=llm_client)


# =============================================================================
# GroupMessage Tests
# =============================================================================

class TestGroupMessage:
    """Tests for GroupMessage dataclass."""

    def test_create_message(self):
        """Test creating a group message."""
        message = GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="agent-1",
            sender_name="Test Agent",
            content="Hello, world!",
            message_type=MessageType.AGENT,
        )

        assert message.id == "msg-1"
        assert message.group_id == "group-1"
        assert message.sender_id == "agent-1"
        assert message.sender_name == "Test Agent"
        assert message.content == "Hello, world!"
        assert message.message_type == MessageType.AGENT
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}
        assert message.reply_to is None

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="agent-1",
            sender_name="Test Agent",
            content="Hello",
            message_type=MessageType.USER,
            metadata={"round": 1},
            reply_to="msg-0",
        )

        data = message.to_dict()

        assert data["id"] == "msg-1"
        assert data["group_id"] == "group-1"
        assert data["sender_id"] == "agent-1"
        assert data["message_type"] == "user"
        assert data["metadata"] == {"round": 1}
        assert data["reply_to"] == "msg-0"

    def test_message_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "id": "msg-1",
            "group_id": "group-1",
            "sender_id": "agent-1",
            "sender_name": "Test Agent",
            "content": "Hello",
            "message_type": "agent",
            "timestamp": "2025-01-01T00:00:00",
            "metadata": {"round": 1},
            "reply_to": None,
        }

        message = GroupMessage.from_dict(data)

        assert message.id == "msg-1"
        assert message.message_type == MessageType.AGENT
        assert message.metadata == {"round": 1}

    def test_all_message_types(self):
        """Test all message types."""
        types = [
            MessageType.USER,
            MessageType.AGENT,
            MessageType.SYSTEM,
            MessageType.FUNCTION_CALL,
            MessageType.FUNCTION_RESULT,
        ]

        for msg_type in types:
            message = GroupMessage(
                id="msg-1",
                group_id="group-1",
                sender_id="sender-1",
                sender_name="Sender",
                content="Test",
                message_type=msg_type,
            )
            assert message.message_type == msg_type


# =============================================================================
# GroupChatConfig Tests
# =============================================================================

class TestGroupChatConfig:
    """Tests for GroupChatConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GroupChatConfig()

        assert config.max_rounds == 10
        assert config.max_messages_per_round == 5
        assert config.speaker_selection_method == SpeakerSelectionMethod.AUTO
        assert config.allow_repeat_speaker is False
        assert config.timeout_seconds == 300
        assert config.enable_voting is False
        assert config.consensus_threshold == 0.7

    def test_custom_config(self, sample_config):
        """Test custom configuration."""
        assert sample_config.max_rounds == 5
        assert sample_config.max_messages_per_round == 3
        assert sample_config.speaker_selection_method == SpeakerSelectionMethod.ROUND_ROBIN
        assert sample_config.timeout_seconds == 120

    def test_config_to_dict(self, sample_config):
        """Test converting config to dictionary."""
        data = sample_config.to_dict()

        assert data["max_rounds"] == 5
        assert data["speaker_selection_method"] == "round_robin"
        assert data["enable_voting"] is False

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "max_rounds": 8,
            "speaker_selection_method": "priority",
            "enable_voting": True,
        }

        config = GroupChatConfig.from_dict(data)

        assert config.max_rounds == 8
        assert config.speaker_selection_method == SpeakerSelectionMethod.PRIORITY
        assert config.enable_voting is True

    def test_all_speaker_selection_methods(self):
        """Test all speaker selection methods."""
        methods = [
            SpeakerSelectionMethod.AUTO,
            SpeakerSelectionMethod.ROUND_ROBIN,
            SpeakerSelectionMethod.RANDOM,
            SpeakerSelectionMethod.MANUAL,
            SpeakerSelectionMethod.PRIORITY,
            SpeakerSelectionMethod.EXPERTISE,
        ]

        for method in methods:
            config = GroupChatConfig(speaker_selection_method=method)
            assert config.speaker_selection_method == method


# =============================================================================
# AgentInfo Tests
# =============================================================================

class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_create_agent_info(self):
        """Test creating agent info."""
        agent = AgentInfo(
            agent_id="agent-1",
            name="Test Agent",
            description="A test agent",
            capabilities=["test", "demo"],
            priority=5,
        )

        assert agent.agent_id == "agent-1"
        assert agent.name == "Test Agent"
        assert agent.capabilities == ["test", "demo"]
        assert agent.priority == 5
        assert agent.is_active is True

    def test_agent_to_dict(self, sample_agents):
        """Test converting agent to dictionary."""
        agent = sample_agents[0]
        data = agent.to_dict()

        assert data["agent_id"] == "agent-1"
        assert data["name"] == "Planning Agent"
        assert "planning" in data["capabilities"]
        assert data["is_active"] is True


# =============================================================================
# GroupChatState Tests
# =============================================================================

class TestGroupChatState:
    """Tests for GroupChatState dataclass."""

    def test_create_state(self, sample_agents, sample_config):
        """Test creating group chat state."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
            config=sample_config,
        )

        assert state.group_id == "group-1"
        assert state.name == "Test Group"
        assert state.status == GroupChatStatus.CREATED
        assert len(state.agents) == 3
        assert state.current_round == 0
        assert state.current_speaker_id is None

    def test_state_agent_ids(self, sample_agents):
        """Test getting agent IDs from state."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
        )

        assert state.agent_ids == ["agent-1", "agent-2", "agent-3"]

    def test_state_active_agents(self, sample_agents):
        """Test getting active agents."""
        sample_agents[1].is_active = False
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
        )

        active = state.active_agents
        assert len(active) == 2
        assert all(a.is_active for a in active)

    def test_state_message_count(self, sample_agents):
        """Test message count property."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
        )

        assert state.message_count == 0

        state.messages.append(GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="Hello",
            message_type=MessageType.USER,
        ))

        assert state.message_count == 1

    def test_state_round_message_count(self, sample_agents):
        """Test round message count property."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
        )
        state.current_round = 2

        # Add messages for different rounds
        state.messages.append(GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="Hello",
            message_type=MessageType.USER,
            metadata={"round": 1},
        ))
        state.messages.append(GroupMessage(
            id="msg-2",
            group_id="group-1",
            sender_id="agent-1",
            sender_name="Agent",
            content="Hi",
            message_type=MessageType.AGENT,
            metadata={"round": 2},
        ))
        state.messages.append(GroupMessage(
            id="msg-3",
            group_id="group-1",
            sender_id="agent-2",
            sender_name="Agent 2",
            content="Hello",
            message_type=MessageType.AGENT,
            metadata={"round": 2},
        ))

        assert state.round_message_count == 2

    def test_state_to_dict(self, sample_agents, sample_config):
        """Test converting state to dictionary."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
            config=sample_config,
        )

        data = state.to_dict()

        assert data["group_id"] == "group-1"
        assert data["name"] == "Test Group"
        assert data["status"] == "created"
        assert len(data["agents"]) == 3
        assert data["config"]["max_rounds"] == 5


# =============================================================================
# GroupChatManager - Creation Tests
# =============================================================================

class TestGroupChatManagerCreation:
    """Tests for GroupChatManager creation operations."""

    @pytest.mark.asyncio
    async def test_create_group_chat(self, manager, sample_agents, sample_config):
        """Test creating a new group chat."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=sample_config,
            metadata={"project": "test"},
        )

        assert state.name == "Test Group"
        assert state.status == GroupChatStatus.CREATED
        assert len(state.agents) == 3
        assert state.config.max_rounds == 5
        assert state.metadata["project"] == "test"

    @pytest.mark.asyncio
    async def test_create_group_chat_without_config(self, manager, sample_agents):
        """Test creating group chat with default config."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        assert state.config.max_rounds == 10  # Default value
        assert state.config.speaker_selection_method == SpeakerSelectionMethod.AUTO

    @pytest.mark.asyncio
    async def test_create_group_chat_empty_agents(self, manager):
        """Test creating group chat with empty agents raises error."""
        with pytest.raises(ValueError, match="At least one agent"):
            await manager.create_group_chat(
                name="Empty Group",
                agents=[],
            )

    @pytest.mark.asyncio
    async def test_get_group_chat(self, manager, sample_agents):
        """Test getting group chat by ID."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        retrieved = await manager.get_group_chat(state.group_id)

        assert retrieved is not None
        assert retrieved.group_id == state.group_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_group_chat(self, manager):
        """Test getting nonexistent group chat returns None."""
        result = await manager.get_group_chat("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_group_chat(self, manager, sample_agents):
        """Test deleting a group chat."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        result = await manager.delete_group_chat(state.group_id)
        assert result is True

        # Verify deleted
        retrieved = await manager.get_group_chat(state.group_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_group_chat(self, manager):
        """Test deleting nonexistent group chat returns False."""
        result = await manager.delete_group_chat("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_group_chats(self, manager, sample_agents):
        """Test listing all group chats."""
        # Create multiple groups
        await manager.create_group_chat(name="Group 1", agents=sample_agents)
        await manager.create_group_chat(name="Group 2", agents=sample_agents)
        await manager.create_group_chat(name="Group 3", agents=sample_agents)

        groups = await manager.list_group_chats()
        assert len(groups) == 3

    @pytest.mark.asyncio
    async def test_list_group_chats_with_filter(self, manager, sample_agents):
        """Test listing group chats with status filter."""
        state1 = await manager.create_group_chat(name="Group 1", agents=sample_agents)
        await manager.create_group_chat(name="Group 2", agents=sample_agents)

        # Start one conversation
        await manager.start_conversation(state1.group_id, "Hello")

        active = await manager.list_group_chats(status=GroupChatStatus.ACTIVE)
        created = await manager.list_group_chats(status=GroupChatStatus.CREATED)

        assert len(active) == 1
        assert len(created) == 1


# =============================================================================
# GroupChatManager - Agent Management Tests
# =============================================================================

class TestGroupChatManagerAgents:
    """Tests for GroupChatManager agent management."""

    @pytest.mark.asyncio
    async def test_add_agent(self, manager, sample_agents):
        """Test adding an agent to group chat."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents[:2],
        )

        new_agent = sample_agents[2]
        result = await manager.add_agent(state.group_id, new_agent)

        assert result is True
        updated = await manager.get_group_chat(state.group_id)
        assert len(updated.agents) == 3
        assert any(a.agent_id == new_agent.agent_id for a in updated.agents)

    @pytest.mark.asyncio
    async def test_add_duplicate_agent(self, manager, sample_agents):
        """Test adding duplicate agent returns False."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        result = await manager.add_agent(state.group_id, sample_agents[0])
        assert result is False

    @pytest.mark.asyncio
    async def test_add_agent_to_nonexistent_group(self, manager, sample_agents):
        """Test adding agent to nonexistent group returns False."""
        result = await manager.add_agent("nonexistent", sample_agents[0])
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_agent(self, manager, sample_agents):
        """Test removing an agent from group chat."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        result = await manager.remove_agent(state.group_id, "agent-2")

        assert result is True
        updated = await manager.get_group_chat(state.group_id)
        assert len(updated.agents) == 2
        assert "agent-2" not in updated.agent_ids

    @pytest.mark.asyncio
    async def test_remove_nonexistent_agent(self, manager, sample_agents):
        """Test removing nonexistent agent returns False."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        result = await manager.remove_agent(state.group_id, "nonexistent-agent")
        assert result is False


# =============================================================================
# GroupChatManager - Conversation Control Tests
# =============================================================================

class TestGroupChatManagerConversation:
    """Tests for GroupChatManager conversation control."""

    @pytest.mark.asyncio
    async def test_start_conversation(self, manager, sample_agents):
        """Test starting a conversation."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        updated = await manager.start_conversation(
            state.group_id,
            initial_message="Let's begin the discussion",
            sender_name="Moderator",
        )

        assert updated.status == GroupChatStatus.ACTIVE
        assert updated.started_at is not None
        assert updated.current_round == 1
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Let's begin the discussion"

    @pytest.mark.asyncio
    async def test_start_conversation_without_message(self, manager, sample_agents):
        """Test starting conversation without initial message."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        updated = await manager.start_conversation(state.group_id)

        assert updated.status == GroupChatStatus.ACTIVE
        assert len(updated.messages) == 0

    @pytest.mark.asyncio
    async def test_start_conversation_nonexistent_group(self, manager):
        """Test starting conversation in nonexistent group raises error."""
        with pytest.raises(ValueError, match="not found"):
            await manager.start_conversation("nonexistent")

    @pytest.mark.asyncio
    async def test_start_conversation_invalid_status(self, manager, sample_agents):
        """Test starting conversation in active group raises error."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)

        with pytest.raises(ValueError, match="Cannot start"):
            await manager.start_conversation(state.group_id)

    @pytest.mark.asyncio
    async def test_pause_conversation(self, manager, sample_agents):
        """Test pausing a conversation."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)

        result = await manager.pause_conversation(state.group_id)

        assert result is True
        updated = await manager.get_group_chat(state.group_id)
        assert updated.status == GroupChatStatus.PAUSED

    @pytest.mark.asyncio
    async def test_pause_inactive_conversation(self, manager, sample_agents):
        """Test pausing inactive conversation returns False."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        result = await manager.pause_conversation(state.group_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_conversation(self, manager, sample_agents):
        """Test resuming a paused conversation."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)
        await manager.pause_conversation(state.group_id)

        result = await manager.resume_conversation(state.group_id)

        assert result is True
        updated = await manager.get_group_chat(state.group_id)
        assert updated.status == GroupChatStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_terminate_conversation(self, manager, sample_agents):
        """Test terminating a conversation."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)

        result = await manager.terminate_conversation(
            state.group_id,
            reason="Test termination",
        )

        assert result is True
        updated = await manager.get_group_chat(state.group_id)
        assert updated.status == GroupChatStatus.TERMINATED
        assert updated.ended_at is not None
        assert updated.metadata["termination_reason"] == "Test termination"

    @pytest.mark.asyncio
    async def test_terminate_already_terminated(self, manager, sample_agents):
        """Test terminating already terminated conversation returns False."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)
        await manager.terminate_conversation(state.group_id)

        result = await manager.terminate_conversation(state.group_id)
        assert result is False


# =============================================================================
# GroupChatManager - Message Tests
# =============================================================================

class TestGroupChatManagerMessages:
    """Tests for GroupChatManager message handling."""

    @pytest.mark.asyncio
    async def test_add_message(self, manager, sample_agents):
        """Test adding a message to group chat."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id)

        message = await manager.add_message(
            group_id=state.group_id,
            content="Hello, everyone!",
            sender_id="user-1",
            sender_name="User",
            message_type=MessageType.USER,
        )

        assert message is not None
        assert message.content == "Hello, everyone!"
        assert message.sender_name == "User"

    @pytest.mark.asyncio
    async def test_add_message_with_reply(self, manager, sample_agents):
        """Test adding a reply message."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Initial message")

        original_id = state.messages[0].id

        reply = await manager.add_message(
            group_id=state.group_id,
            content="This is a reply",
            sender_id="agent-1",
            sender_name="Agent 1",
            message_type=MessageType.AGENT,
            reply_to=original_id,
        )

        assert reply.reply_to == original_id

    @pytest.mark.asyncio
    async def test_add_message_nonexistent_group(self, manager):
        """Test adding message to nonexistent group returns None."""
        result = await manager.add_message(
            group_id="nonexistent",
            content="Hello",
            sender_id="user",
            sender_name="User",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_transcript(self, manager, sample_agents):
        """Test getting conversation transcript."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Hello")
        await manager.add_message(
            group_id=state.group_id,
            content="Response",
            sender_id="agent-1",
            sender_name="Agent 1",
            message_type=MessageType.AGENT,
        )

        transcript = await manager.get_transcript(state.group_id)

        assert len(transcript) == 2
        assert transcript[0].content == "Hello"
        assert transcript[1].content == "Response"

    @pytest.mark.asyncio
    async def test_get_transcript_exclude_system(self, manager, sample_agents):
        """Test getting transcript excludes system messages by default."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Hello")
        await manager.add_agent(state.group_id, AgentInfo(
            agent_id="new-agent",
            name="New Agent",
        ))

        transcript = await manager.get_transcript(state.group_id, include_system=False)

        # Should not include the "joined" system message
        assert all(m.message_type != MessageType.SYSTEM for m in transcript)

    @pytest.mark.asyncio
    async def test_get_summary(self, manager, sample_agents):
        """Test getting conversation summary."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Hello")
        await manager.add_message(
            group_id=state.group_id,
            content="Response",
            sender_id="agent-1",
            sender_name="Agent 1",
            message_type=MessageType.AGENT,
        )

        summary = await manager.get_summary(state.group_id)

        assert summary is not None
        assert "Test Group" in summary
        assert "2" in summary  # Total messages


# =============================================================================
# GroupChatManager - Speaker Selection Tests
# =============================================================================

class TestGroupChatManagerSpeakerSelection:
    """Tests for speaker selection in GroupChatManager."""

    @pytest.mark.asyncio
    async def test_round_robin_selection(self, manager, sample_agents):
        """Test round-robin speaker selection."""
        config = GroupChatConfig(
            speaker_selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
            allow_repeat_speaker=False,
        )
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=config,
        )
        await manager.start_conversation(state.group_id, "Start")

        # Track speakers
        speakers = []

        def mock_response(agent_id, context, messages):
            speakers.append(agent_id)
            return f"Response from {agent_id}"

        # Execute multiple rounds
        for _ in range(3):
            await manager.execute_round(state.group_id, mock_response)

        # Verify round-robin order
        assert speakers == ["agent-1", "agent-2", "agent-3"]

    @pytest.mark.asyncio
    async def test_priority_selection(self, manager, sample_agents):
        """Test priority-based speaker selection."""
        config = GroupChatConfig(
            speaker_selection_method=SpeakerSelectionMethod.PRIORITY,
            allow_repeat_speaker=True,
        )
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=config,
        )
        await manager.start_conversation(state.group_id, "Start")

        speakers = []

        def mock_response(agent_id, context, messages):
            speakers.append(agent_id)
            return f"Response from {agent_id}"

        # Execute rounds
        for _ in range(3):
            await manager.execute_round(state.group_id, mock_response)

        # agent-1 has priority 1 (lowest = highest priority)
        assert speakers == ["agent-1", "agent-1", "agent-1"]

    @pytest.mark.asyncio
    async def test_random_selection(self, manager, sample_agents):
        """Test random speaker selection."""
        config = GroupChatConfig(
            speaker_selection_method=SpeakerSelectionMethod.RANDOM,
        )
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=config,
        )
        await manager.start_conversation(state.group_id, "Start")

        def mock_response(agent_id, context, messages):
            return f"Response from {agent_id}"

        # Execute round
        message = await manager.execute_round(state.group_id, mock_response)

        assert message is not None
        assert message.sender_id in ["agent-1", "agent-2", "agent-3"]

    @pytest.mark.asyncio
    async def test_no_repeat_speaker(self, manager, sample_agents):
        """Test no repeat speaker constraint."""
        config = GroupChatConfig(
            speaker_selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
            allow_repeat_speaker=False,
        )
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=config,
        )
        await manager.start_conversation(state.group_id, "Start")

        speakers = []

        def mock_response(agent_id, context, messages):
            speakers.append(agent_id)
            return f"Response from {agent_id}"

        # Execute rounds
        for _ in range(6):
            await manager.execute_round(state.group_id, mock_response)

        # No consecutive duplicates
        for i in range(1, len(speakers)):
            assert speakers[i] != speakers[i - 1]


# =============================================================================
# GroupChatManager - Execute Round Tests
# =============================================================================

class TestGroupChatManagerExecuteRound:
    """Tests for execute_round in GroupChatManager."""

    @pytest.mark.asyncio
    async def test_execute_round(self, manager, sample_agents, sample_config):
        """Test executing a conversation round."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=sample_config,
        )
        await manager.start_conversation(state.group_id, "What should we discuss?")

        def mock_response(agent_id, context, messages):
            return f"I think we should discuss planning from {agent_id}"

        message = await manager.execute_round(state.group_id, mock_response)

        assert message is not None
        assert message.message_type == MessageType.AGENT
        assert "planning" in message.content

    @pytest.mark.asyncio
    async def test_execute_round_inactive_group(self, manager, sample_agents):
        """Test execute_round returns None for inactive group."""
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        def mock_response(agent_id, context, messages):
            return "Response"

        result = await manager.execute_round(state.group_id, mock_response)
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_round_max_rounds_termination(self, manager, sample_agents):
        """Test conversation terminates at max rounds."""
        config = GroupChatConfig(max_rounds=2, max_messages_per_round=1)
        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
            config=config,
        )
        await manager.start_conversation(state.group_id, "Start")

        def mock_response(agent_id, context, messages):
            return "Response"

        # Execute until termination
        results = []
        for _ in range(5):
            result = await manager.execute_round(state.group_id, mock_response)
            results.append(result)

        # Some results should be None (after termination)
        assert None in results

        updated = await manager.get_group_chat(state.group_id)
        assert updated.status == GroupChatStatus.COMPLETED


# =============================================================================
# GroupChatManager - Event Handling Tests
# =============================================================================

class TestGroupChatManagerEvents:
    """Tests for event handling in GroupChatManager."""

    @pytest.mark.asyncio
    async def test_message_handler(self, manager, sample_agents):
        """Test message handler callback."""
        received_messages = []

        def handler(message):
            received_messages.append(message)

        manager.on_message(handler)

        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Hello")
        await manager.add_message(
            group_id=state.group_id,
            content="Response",
            sender_id="agent-1",
            sender_name="Agent 1",
        )

        assert len(received_messages) == 1
        assert received_messages[0].content == "Response"

    @pytest.mark.asyncio
    async def test_event_handler(self, manager, sample_agents):
        """Test event handler callback."""
        events = []

        def handler(data):
            events.append(data)

        manager.on_event("group_created", handler)

        await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )

        assert len(events) == 1
        assert events[0].name == "Test Group"


# =============================================================================
# TerminationChecker Tests
# =============================================================================

class TestTerminationChecker:
    """Tests for TerminationChecker."""

    @pytest.fixture
    def checker(self):
        """Create a TerminationChecker instance."""
        return TerminationChecker()

    @pytest.fixture
    def sample_state(self, sample_agents):
        """Create a sample group chat state for testing."""
        state = GroupChatState(
            group_id="group-1",
            name="Test Group",
            agents=sample_agents,
            status=GroupChatStatus.ACTIVE,
            current_round=1,
            started_at=datetime.utcnow(),
        )
        state.messages.append(GroupMessage(
            id="msg-1",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="Hello, let's discuss",
            message_type=MessageType.USER,
            metadata={"round": 1},
        ))
        return state

    def test_add_condition(self, checker):
        """Test adding a termination condition."""
        condition = TerminationCondition(
            condition_id="test-condition",
            condition_type=TerminationType.KEYWORD,
            parameters={"keywords": ["DONE"]},
        )

        checker.add_condition(condition)

        assert checker.get_condition("test-condition") is not None

    def test_remove_condition(self, checker):
        """Test removing a termination condition."""
        condition = TerminationCondition(
            condition_id="test-condition",
            condition_type=TerminationType.KEYWORD,
        )
        checker.add_condition(condition)

        result = checker.remove_condition("test-condition")

        assert result is True
        assert checker.get_condition("test-condition") is None

    def test_list_conditions(self, checker):
        """Test listing termination conditions."""
        conditions = [
            TerminationCondition(
                condition_id="cond-1",
                condition_type=TerminationType.KEYWORD,
                priority=2,
            ),
            TerminationCondition(
                condition_id="cond-2",
                condition_type=TerminationType.MAX_ROUNDS,
                priority=1,
            ),
        ]

        for c in conditions:
            checker.add_condition(c)

        listed = checker.list_conditions()

        assert len(listed) == 2
        # Should be sorted by priority
        assert listed[0].condition_id == "cond-2"

    def test_enable_disable_condition(self, checker):
        """Test enabling and disabling conditions."""
        condition = TerminationCondition(
            condition_id="test-condition",
            condition_type=TerminationType.KEYWORD,
        )
        checker.add_condition(condition)

        checker.disable_condition("test-condition")
        assert checker.get_condition("test-condition").is_enabled is False

        checker.enable_condition("test-condition")
        assert checker.get_condition("test-condition").is_enabled is True

    @pytest.mark.asyncio
    async def test_check_max_rounds(self, checker, sample_state, sample_agents):
        """Test max rounds termination check."""
        checker.add_condition(TerminationCondition(
            condition_id="max-rounds",
            condition_type=TerminationType.MAX_ROUNDS,
            parameters={"max_rounds": 5},
        ))

        # Not at limit
        sample_state.current_round = 3
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # At limit
        sample_state.current_round = 6
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.MAX_ROUNDS

    @pytest.mark.asyncio
    async def test_check_timeout(self, checker, sample_state, sample_agents):
        """Test timeout termination check."""
        checker.add_condition(TerminationCondition(
            condition_id="timeout",
            condition_type=TerminationType.TIMEOUT,
            parameters={"timeout_seconds": 60},
        ))

        # Not timed out
        sample_state.started_at = datetime.utcnow()
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # Timed out
        sample_state.started_at = datetime.utcnow() - timedelta(seconds=120)
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.TIMEOUT

    @pytest.mark.asyncio
    async def test_check_keyword(self, checker, sample_state, sample_agents):
        """Test keyword termination check."""
        checker.add_condition(TerminationCondition(
            condition_id="keyword",
            condition_type=TerminationType.KEYWORD,
            parameters={"keywords": ["DONE", "TERMINATE"]},
        ))

        # No keyword
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # Add message with keyword
        sample_state.messages.append(GroupMessage(
            id="msg-2",
            group_id="group-1",
            sender_id="agent-1",
            sender_name="Agent 1",
            content="Task is DONE, we can finish now",
            message_type=MessageType.AGENT,
        ))
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.KEYWORD

    @pytest.mark.asyncio
    async def test_check_pattern(self, checker, sample_state, sample_agents):
        """Test pattern termination check."""
        checker.add_condition(TerminationCondition(
            condition_id="pattern",
            condition_type=TerminationType.PATTERN,
            parameters={"pattern": r"\[END\]"},
        ))

        # No match
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # Add matching message
        sample_state.messages.append(GroupMessage(
            id="msg-2",
            group_id="group-1",
            sender_id="agent-1",
            sender_name="Agent 1",
            content="This is the final response [END]",
            message_type=MessageType.AGENT,
        ))
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.PATTERN

    @pytest.mark.asyncio
    async def test_check_explicit(self, checker, sample_state, sample_agents):
        """Test explicit termination command check."""
        checker.add_condition(TerminationCondition(
            condition_id="explicit",
            condition_type=TerminationType.EXPLICIT,
            parameters={"commands": ["/terminate", "/end"]},
        ))

        # No command
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # Add termination command
        sample_state.messages.append(GroupMessage(
            id="msg-2",
            group_id="group-1",
            sender_id="user",
            sender_name="User",
            content="/terminate",
            message_type=MessageType.USER,
        ))
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.EXPLICIT

    @pytest.mark.asyncio
    async def test_check_no_progress(self, checker, sample_state, sample_agents):
        """Test no progress detection."""
        checker.add_condition(TerminationCondition(
            condition_id="no-progress",
            condition_type=TerminationType.NO_PROGRESS,
            parameters={"min_repeats": 3},
        ))

        # Add repeated messages
        for i in range(3):
            sample_state.messages.append(GroupMessage(
                id=f"msg-{i+2}",
                group_id="group-1",
                sender_id="agent-1",
                sender_name="Agent 1",
                content="I don't know how to proceed",
                message_type=MessageType.AGENT,
            ))

        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.NO_PROGRESS

    @pytest.mark.asyncio
    async def test_check_custom(self, checker, sample_state, sample_agents):
        """Test custom termination condition."""
        def custom_checker(state):
            return len(state.messages) >= 5

        condition = TerminationCondition(
            condition_id="custom",
            condition_type=TerminationType.CUSTOM,
        )
        checker.add_condition(condition)
        checker.register_custom_checker("custom", custom_checker)

        # Not at limit
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is False

        # At limit
        for i in range(4):
            sample_state.messages.append(GroupMessage(
                id=f"msg-{i+2}",
                group_id="group-1",
                sender_id="agent-1",
                sender_name="Agent 1",
                content=f"Message {i}",
                message_type=MessageType.AGENT,
            ))
        result = await checker.should_terminate(sample_state)
        assert result.should_terminate is True
        assert result.condition_type == TerminationType.CUSTOM

    def test_create_default_checker(self):
        """Test creating default termination checker."""
        checker = TerminationChecker.create_default()

        conditions = checker.list_conditions()

        assert len(conditions) >= 4
        condition_types = [c.condition_type for c in conditions]
        assert TerminationType.MAX_ROUNDS in condition_types
        assert TerminationType.TIMEOUT in condition_types
        assert TerminationType.KEYWORD in condition_types
        assert TerminationType.EXPLICIT in condition_types


# =============================================================================
# Integration Tests
# =============================================================================

class TestGroupChatIntegration:
    """Integration tests for GroupChatManager and TerminationChecker."""

    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, sample_agents):
        """Test a complete conversation flow."""
        # Create manager with custom termination checker
        checker = TerminationChecker.create_default()
        checker.add_condition(TerminationCondition(
            condition_id="test-keyword",
            condition_type=TerminationType.KEYWORD,
            parameters={"keywords": ["CONCLUSION"]},
            priority=0,
        ))

        async def termination_check(state):
            result = await checker.should_terminate(state)
            return result.should_terminate

        manager = GroupChatManager(termination_checker=termination_check)

        # Create and start group
        state = await manager.create_group_chat(
            name="Planning Session",
            agents=sample_agents,
            config=GroupChatConfig(
                max_rounds=10,
                speaker_selection_method=SpeakerSelectionMethod.ROUND_ROBIN,
            ),
        )

        await manager.start_conversation(
            state.group_id,
            "Let's plan the project timeline",
        )

        # Simulate conversation
        responses = [
            "I suggest we start with requirements gathering",
            "Good point. We also need to consider the technical constraints",
            "Let me add that we should include testing phases. CONCLUSION: We have a plan",
        ]
        response_idx = 0

        def mock_response(agent_id, context, messages):
            nonlocal response_idx
            response = responses[response_idx % len(responses)]
            response_idx += 1
            return response

        # Execute rounds until termination
        for _ in range(5):
            result = await manager.execute_round(state.group_id, mock_response)
            if result is None:
                break

        # Verify termination
        final_state = await manager.get_group_chat(state.group_id)
        assert final_state.status == GroupChatStatus.COMPLETED
        assert final_state.message_count >= 3  # Initial + responses

        # Get summary
        summary = await manager.get_summary(state.group_id)
        assert summary is not None

    @pytest.mark.asyncio
    async def test_pause_resume_flow(self, sample_agents):
        """Test pause and resume conversation flow."""
        manager = GroupChatManager()

        state = await manager.create_group_chat(
            name="Test Group",
            agents=sample_agents,
        )
        await manager.start_conversation(state.group_id, "Hello")

        # Pause
        await manager.pause_conversation(state.group_id)
        state = await manager.get_group_chat(state.group_id)
        assert state.status == GroupChatStatus.PAUSED

        # Add message while paused
        await manager.add_message(
            group_id=state.group_id,
            content="Message during pause",
            sender_id="user",
            sender_name="User",
        )

        # Resume
        await manager.resume_conversation(state.group_id)
        state = await manager.get_group_chat(state.group_id)
        assert state.status == GroupChatStatus.ACTIVE
        assert state.message_count == 2

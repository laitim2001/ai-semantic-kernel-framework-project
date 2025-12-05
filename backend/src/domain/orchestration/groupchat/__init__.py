# =============================================================================
# IPA Platform - GroupChat Module
# =============================================================================
# Sprint 9: GroupChat & Multi-turn Conversation (Phase 2)
#
# Multi-Agent group chat orchestration with speaker selection,
# termination control, and message management.
# =============================================================================

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
from src.domain.orchestration.groupchat.speaker_selector import (
    AutoStrategy,
    BaseSpeakerStrategy,
    ExpertiseMatcher,
    ExpertiseMatchResult,
    ExpertiseStrategy,
    ManualStrategy,
    PriorityStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    SelectionContext,
    SelectionResult,
    SelectionStrategy,
    SpeakerSelector,
)
from src.domain.orchestration.groupchat.termination import (
    TerminationChecker,
    TerminationCondition,
    TerminationResult,
    TerminationType,
)
from src.domain.orchestration.groupchat.voting import (
    Vote,
    VoteResult,
    VoteType,
    VotingManager,
    VotingSession,
    VotingSessionStatus,
)

__all__ = [
    # Manager
    "GroupChatManager",
    "GroupChatConfig",
    "GroupChatState",
    "GroupChatStatus",
    "GroupMessage",
    "AgentInfo",
    # Enums
    "SpeakerSelectionMethod",
    "MessageType",
    "SelectionStrategy",
    # Speaker Selector
    "SpeakerSelector",
    "SelectionContext",
    "SelectionResult",
    "BaseSpeakerStrategy",
    "RoundRobinStrategy",
    "RandomStrategy",
    "PriorityStrategy",
    "ManualStrategy",
    "ExpertiseStrategy",
    "AutoStrategy",
    # Expertise Matcher
    "ExpertiseMatcher",
    "ExpertiseMatchResult",
    # Termination
    "TerminationChecker",
    "TerminationCondition",
    "TerminationType",
    "TerminationResult",
    # Voting
    "VotingManager",
    "VotingSession",
    "Vote",
    "VoteType",
    "VoteResult",
    "VotingSessionStatus",
]

# =============================================================================
# IPA Platform - GroupChat API Schemas
# =============================================================================
# Sprint 9: S9-6 GroupChat API (8 points)
#
# Pydantic schemas for GroupChat API endpoints.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field


# =============================================================================
# GroupChat Schemas
# =============================================================================


class CreateGroupChatRequest(BaseModel):
    """Request to create a new group chat."""
    name: str = Field(..., description="Group chat name")
    description: str = Field(default="", description="Group chat description")
    agent_ids: List[str] = Field(..., description="List of agent IDs to include")
    workflow_id: Optional[UUID] = Field(None, description="Associated workflow ID")
    config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Group chat configuration",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Technical Discussion",
                "description": "Discuss technical approaches",
                "agent_ids": ["agent-1", "agent-2", "agent-3"],
                "config": {
                    "max_rounds": 10,
                    "speaker_selection_method": "auto",
                    "allow_repeat_speaker": False,
                },
            }
        }
    }


class GroupChatConfigUpdate(BaseModel):
    """Update group chat configuration."""
    max_rounds: Optional[int] = Field(None, ge=1, le=100)
    max_messages_per_round: Optional[int] = Field(None, ge=1, le=50)
    speaker_selection_method: Optional[str] = None
    allow_repeat_speaker: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=1)


class SendMessageRequest(BaseModel):
    """Request to send a message to group chat."""
    content: str = Field(..., description="Message content")
    sender_name: str = Field(default="user", description="Sender name")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StartConversationRequest(BaseModel):
    """Request to start a group conversation."""
    initial_message: str = Field(..., description="Initial message to start conversation")
    initiator: str = Field(default="user", description="Conversation initiator")


class GroupChatResponse(BaseModel):
    """Response for group chat operations."""
    group_id: UUID
    name: str
    description: str
    status: str
    participants: List[str]
    message_count: int
    current_round: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class MessageResponse(BaseModel):
    """Response for a single message."""
    id: str
    sender_id: str
    sender_name: str
    content: str
    message_type: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ConversationResultResponse(BaseModel):
    """Response for conversation result."""
    status: str
    rounds_completed: int
    messages: List[Dict[str, Any]]
    termination_reason: Optional[str] = None


class GroupChatSummaryResponse(BaseModel):
    """Response for group chat summary."""
    group_id: UUID
    name: str
    total_rounds: int
    total_messages: int
    participants: List[str]
    duration_seconds: Optional[float] = None
    termination_reason: Optional[str] = None
    messages_per_participant: Optional[Dict[str, int]] = None


# =============================================================================
# Multi-turn Session Schemas
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a new multi-turn session."""
    user_id: str = Field(..., description="User ID")
    workflow_id: Optional[UUID] = Field(None, description="Associated workflow ID")
    initial_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Initial session context",
    )
    session_timeout_minutes: int = Field(default=30, ge=1, le=1440)
    max_turns: int = Field(default=50, ge=1, le=500)


class SessionResponse(BaseModel):
    """Response for session operations."""
    session_id: UUID
    user_id: str
    status: str
    turn_count: int
    context: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class ExecuteTurnRequest(BaseModel):
    """Request to execute a turn in a session."""
    user_input: str = Field(..., description="User input for this turn")
    agent_id: Optional[str] = Field(None, description="Specific agent to handle this turn")
    context_updates: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Context updates for this turn",
    )


class TurnResponse(BaseModel):
    """Response for a single turn."""
    turn_id: UUID
    turn_number: int
    user_input: str
    agent_response: str
    agent_id: Optional[str] = None
    processing_time_ms: int
    timestamp: datetime


class SessionHistoryResponse(BaseModel):
    """Response for session history."""
    session_id: UUID
    turns: List[TurnResponse]
    total_turns: int


class SessionContextUpdate(BaseModel):
    """Request to update session context."""
    context: Dict[str, Any] = Field(..., description="Context values to update")


# =============================================================================
# Voting Schemas
# =============================================================================


class CreateVotingSessionRequest(BaseModel):
    """Request to create a voting session."""
    group_id: Optional[UUID] = Field(None, description="Associated group ID")
    topic: str = Field(..., description="Voting topic")
    description: str = Field(default="", description="Voting description")
    vote_type: str = Field(default="approve_reject", description="Type of vote")
    options: Optional[List[str]] = Field(None, description="Options for multiple choice")
    deadline_minutes: Optional[int] = Field(None, ge=1, description="Deadline in minutes")
    required_quorum: float = Field(default=0.5, ge=0, le=1)
    pass_threshold: float = Field(default=0.5, ge=0, le=1)
    eligible_voters: Optional[List[str]] = Field(None, description="List of eligible voter IDs")


class CastVoteRequest(BaseModel):
    """Request to cast a vote."""
    voter_id: str = Field(..., description="Voter ID")
    voter_name: str = Field(..., description="Voter name")
    choice: Any = Field(..., description="Vote choice")
    weight: float = Field(default=1.0, ge=0)
    reason: Optional[str] = Field(None, description="Reason for vote")


class ChangeVoteRequest(BaseModel):
    """Request to change a vote."""
    new_choice: Any = Field(..., description="New vote choice")
    reason: Optional[str] = Field(None, description="Reason for change")


class VoteResponse(BaseModel):
    """Response for a single vote."""
    vote_id: UUID
    voter_id: str
    voter_name: str
    choice: Any
    weight: float
    timestamp: datetime
    reason: Optional[str] = None


class VotingSessionResponse(BaseModel):
    """Response for voting session."""
    session_id: UUID
    group_id: Optional[UUID] = None
    topic: str
    description: str
    vote_type: str
    options: List[str]
    status: str
    result: str
    vote_count: int
    participation_rate: float
    required_quorum: float
    pass_threshold: float
    created_at: datetime
    deadline: Optional[datetime] = None


class VotingResultResponse(BaseModel):
    """Response for voting result."""
    session_id: UUID
    result: str
    result_details: Dict[str, Any]
    participation_rate: float
    total_votes: int


class VotingStatisticsResponse(BaseModel):
    """Response for voting statistics."""
    session_id: UUID
    topic: str
    vote_type: str
    status: str
    result: str
    total_votes: int
    eligible_voters: int
    participation_rate: float
    first_vote: Optional[datetime] = None
    last_vote: Optional[datetime] = None


# =============================================================================
# Common Schemas
# =============================================================================


class PaginationParams(BaseModel):
    """Pagination parameters."""
    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None

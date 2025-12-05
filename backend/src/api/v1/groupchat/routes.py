# =============================================================================
# IPA Platform - GroupChat API Routes
# =============================================================================
# Sprint 9: S9-6 GroupChat API (8 points)
#
# RESTful API routes for group chat, multi-turn sessions, and voting.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.api.v1.groupchat.schemas import (
    # GroupChat
    CreateGroupChatRequest,
    GroupChatConfigUpdate,
    GroupChatResponse,
    GroupChatSummaryResponse,
    SendMessageRequest,
    StartConversationRequest,
    ConversationResultResponse,
    MessageResponse,
    # Session
    CreateSessionRequest,
    SessionResponse,
    ExecuteTurnRequest,
    TurnResponse,
    SessionHistoryResponse,
    SessionContextUpdate,
    # Voting
    CreateVotingSessionRequest,
    CastVoteRequest,
    ChangeVoteRequest,
    VoteResponse,
    VotingSessionResponse,
    VotingResultResponse,
    VotingStatisticsResponse,
    # Common
    SuccessResponse,
)

# Domain imports
from src.domain.orchestration.groupchat import (
    GroupChatManager,
    GroupChatConfig,
    GroupChatState,
    GroupChatStatus,
    AgentInfo,
    MessageType,
    SpeakerSelectionMethod,
    VotingManager,
    VotingSession,
    VoteType,
    VoteResult,
    VotingSessionStatus,
)
from src.domain.orchestration.multiturn import (
    MultiTurnSessionManager,
    MultiTurnSession,
    SessionStatus,
)
from src.domain.orchestration.memory import (
    InMemoryConversationMemoryStore,
    ConversationSession,
    ConversationTurn,
)

router = APIRouter(prefix="/groupchat", tags=["GroupChat"])


# =============================================================================
# In-Memory State (for MVP - replace with proper DI in production)
# =============================================================================

# Single shared GroupChatManager instance
_group_chat_manager = GroupChatManager()

# Session storage
_session_manager = MultiTurnSessionManager()
_memory_store = InMemoryConversationMemoryStore()

# Voting storage
_voting_manager = VotingManager()

# WebSocket connections
_websocket_connections: Dict[UUID, List[WebSocket]] = {}


# =============================================================================
# GroupChat Routes
# =============================================================================


@router.post("/", response_model=GroupChatResponse, status_code=201)
async def create_group_chat(request: CreateGroupChatRequest):
    """Create a new group chat.

    建立新的群組聊天。
    """
    # Create agent info from IDs
    agents = [
        AgentInfo(
            agent_id=agent_id,
            name=f"Agent-{agent_id[:8]}",
            description="",
            capabilities=[],
        )
        for agent_id in request.agent_ids
    ]

    # Create config
    config_data = request.config or {}
    config = GroupChatConfig(
        max_rounds=config_data.get("max_rounds", 10),
        max_messages_per_round=config_data.get("max_messages_per_round", 5),
        speaker_selection_method=SpeakerSelectionMethod(
            config_data.get("speaker_selection_method", "round_robin")
        ),
        allow_repeat_speaker=config_data.get("allow_repeat_speaker", False),
    )

    # Use the shared manager to create group chat
    state = await _group_chat_manager.create_group_chat(
        name=request.name,
        agents=agents,
        config=config,
        metadata={"description": request.description, "workflow_id": str(request.workflow_id) if request.workflow_id else None},
    )

    return GroupChatResponse(
        group_id=UUID(state.group_id),
        name=state.name,
        description=request.description,
        status=state.status.value,
        participants=[a.name for a in state.agents],
        message_count=state.message_count,
        current_round=state.current_round,
        created_at=state.created_at,
    )


@router.get("/", response_model=List[GroupChatResponse])
async def list_group_chats(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all group chats.

    列出所有群組聊天。
    """
    all_groups = await _group_chat_manager.list_group_chats()
    groups = all_groups[offset:offset + limit]

    return [
        GroupChatResponse(
            group_id=UUID(g.group_id),
            name=g.name,
            description=g.metadata.get("description", ""),
            status=g.status.value,
            participants=[a.name for a in g.agents],
            message_count=g.message_count,
            current_round=g.current_round,
            created_at=g.created_at,
            updated_at=g.started_at,
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=GroupChatResponse)
async def get_group_chat(group_id: UUID):
    """Get group chat details.

    獲取群組聊天詳情。
    """
    state = await _group_chat_manager.get_group_chat(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    return GroupChatResponse(
        group_id=UUID(state.group_id),
        name=state.name,
        description=state.metadata.get("description", ""),
        status=state.status.value,
        participants=[a.name for a in state.agents],
        message_count=state.message_count,
        current_round=state.current_round,
        created_at=state.created_at,
        updated_at=state.started_at,
    )


@router.patch("/{group_id}/config", response_model=SuccessResponse)
async def update_group_config(group_id: UUID, config: GroupChatConfigUpdate):
    """Update group chat configuration.

    更新群組聊天配置。
    """
    state = await _group_chat_manager.get_group_chat(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Update config
    if config.max_rounds is not None:
        state.config.max_rounds = config.max_rounds
    if config.max_messages_per_round is not None:
        state.config.max_messages_per_round = config.max_messages_per_round
    if config.speaker_selection_method is not None:
        state.config.speaker_selection_method = SpeakerSelectionMethod(
            config.speaker_selection_method
        )
    if config.allow_repeat_speaker is not None:
        state.config.allow_repeat_speaker = config.allow_repeat_speaker

    return SuccessResponse(message="Configuration updated")


@router.post("/{group_id}/agents/{agent_id}", response_model=SuccessResponse)
async def add_agent_to_group(
    group_id: UUID,
    agent_id: str,
    name: str = Query(...),
    capabilities: List[str] = Query(default=[]),
):
    """Add an agent to the group chat.

    添加 Agent 到群組聊天。
    """
    agent = AgentInfo(
        agent_id=agent_id,
        name=name,
        capabilities=capabilities,
    )
    result = await _group_chat_manager.add_agent(str(group_id), agent)
    if not result:
        raise HTTPException(status_code=404, detail="Group chat not found")

    return SuccessResponse(message=f"Agent {agent_id} added to group")


@router.delete("/{group_id}/agents/{agent_id}", response_model=SuccessResponse)
async def remove_agent_from_group(group_id: UUID, agent_id: str):
    """Remove an agent from the group chat.

    從群組聊天移除 Agent。
    """
    result = await _group_chat_manager.remove_agent(str(group_id), agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Group chat not found")

    return SuccessResponse(message=f"Agent {agent_id} removed from group")


@router.post("/{group_id}/start", response_model=ConversationResultResponse)
async def start_conversation(group_id: UUID, request: StartConversationRequest):
    """Start a group conversation.

    開始群組對話。
    """
    try:
        state = await _group_chat_manager.start_conversation(
            group_id=str(group_id),
            initial_message=request.initial_message,
            sender_name=request.initiator,
        )

        return ConversationResultResponse(
            status="started",
            rounds_completed=state.current_round,
            messages=[m.to_dict() for m in state.messages],
            termination_reason=None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{group_id}/message", response_model=MessageResponse)
async def send_message(group_id: UUID, request: SendMessageRequest):
    """Send a message to the group.

    發送訊息到群組。
    """
    message = await _group_chat_manager.add_message(
        group_id=str(group_id),
        content=request.content,
        sender_id=request.sender_name,
        sender_name=request.sender_name,
        message_type=MessageType.USER,
        metadata=request.metadata,
    )

    if not message:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Broadcast to WebSocket connections
    await _broadcast_to_group(group_id, {
        "type": "message",
        "data": message.to_dict(),
    })

    return MessageResponse(
        id=str(message.id),
        sender_id=message.sender_id,
        sender_name=message.sender_name,
        content=message.content,
        message_type=message.message_type.value,
        timestamp=message.timestamp,
        metadata=message.metadata,
    )


@router.get("/{group_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    group_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Get messages from the group chat.

    獲取群組聊天訊息。
    """
    state = await _group_chat_manager.get_group_chat(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    messages = state.messages[offset:offset + limit]

    return [
        MessageResponse(
            id=str(m.id),
            sender_id=m.sender_id,
            sender_name=m.sender_name,
            content=m.content,
            message_type=m.message_type.value,
            timestamp=m.timestamp,
            metadata=m.metadata,
        )
        for m in messages
    ]


@router.get("/{group_id}/transcript")
async def get_transcript(group_id: UUID):
    """Get the full conversation transcript.

    獲取完整對話記錄。
    """
    messages = await _group_chat_manager.get_transcript(str(group_id))
    if not messages and not await _group_chat_manager.get_group_chat(str(group_id)):
        raise HTTPException(status_code=404, detail="Group chat not found")

    transcript = []
    for msg in messages:
        transcript.append({
            "speaker": msg.sender_name,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        })

    return {"transcript": transcript}


@router.get("/{group_id}/summary", response_model=GroupChatSummaryResponse)
async def get_summary(group_id: UUID):
    """Get group chat summary.

    獲取群組聊天摘要。
    """
    state = await _group_chat_manager.get_group_chat(str(group_id))
    if not state:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Calculate messages per participant
    messages_per_participant: Dict[str, int] = {}
    for msg in state.messages:
        messages_per_participant[msg.sender_name] = (
            messages_per_participant.get(msg.sender_name, 0) + 1
        )

    # Calculate duration
    duration = None
    if state.started_at and state.ended_at:
        duration = (state.ended_at - state.started_at).total_seconds()

    return GroupChatSummaryResponse(
        group_id=UUID(state.group_id),
        name=state.name,
        total_rounds=state.current_round,
        total_messages=len(state.messages),
        participants=[a.name for a in state.agents],
        duration_seconds=duration,
        termination_reason=state.metadata.get("termination_reason"),
        messages_per_participant=messages_per_participant,
    )


@router.post("/{group_id}/terminate", response_model=SuccessResponse)
async def terminate_group_chat(
    group_id: UUID,
    reason: str = Query(default="manual_termination"),
):
    """Terminate the group chat.

    終止群組聊天。
    """
    result = await _group_chat_manager.terminate_conversation(str(group_id), reason)
    if not result:
        raise HTTPException(status_code=404, detail="Group chat not found")

    # Notify WebSocket clients
    await _broadcast_to_group(group_id, {
        "type": "terminated",
        "reason": reason,
    })

    return SuccessResponse(message=f"Group chat terminated: {reason}")


@router.delete("/{group_id}", response_model=SuccessResponse)
async def delete_group_chat(group_id: UUID):
    """Delete a group chat.

    刪除群組聊天。
    """
    result = await _group_chat_manager.delete_group_chat(str(group_id))
    if not result:
        raise HTTPException(status_code=404, detail="Group chat not found")

    return SuccessResponse(message="Group chat deleted")


# =============================================================================
# WebSocket Routes
# =============================================================================


@router.websocket("/{group_id}/ws")
async def websocket_endpoint(websocket: WebSocket, group_id: UUID):
    """WebSocket endpoint for real-time group chat.

    WebSocket 端點用於實時群組聊天。
    """
    await websocket.accept()

    # Register connection
    if group_id not in _websocket_connections:
        _websocket_connections[group_id] = []
    _websocket_connections[group_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                # Handle incoming message via shared manager
                message = await _group_chat_manager.add_message(
                    group_id=str(group_id),
                    content=data.get("content", ""),
                    sender_id=data.get("sender", "user"),
                    sender_name=data.get("sender", "user"),
                    message_type=MessageType.USER,
                )

                if message:
                    # Broadcast to all connections
                    await _broadcast_to_group(group_id, {
                        "type": "message",
                        "data": message.to_dict(),
                    })

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif data.get("type") == "terminate":
                await _broadcast_to_group(group_id, {
                    "type": "terminated",
                    "reason": "websocket_request",
                })
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
        })
    finally:
        # Unregister connection
        if group_id in _websocket_connections:
            _websocket_connections[group_id].remove(websocket)


async def _broadcast_to_group(group_id: UUID, message: Dict[str, Any]):
    """Broadcast message to all WebSocket connections for a group."""
    connections = _websocket_connections.get(group_id, [])
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            pass


# =============================================================================
# Multi-turn Session Routes
# =============================================================================


@router.post("/sessions/", response_model=SessionResponse, status_code=201)
async def create_session(request: CreateSessionRequest):
    """Create a new multi-turn session.

    建立新的多輪對話會話。
    """
    session = await _session_manager.create_session(
        user_id=request.user_id,
        initial_context=request.initial_context,
    )

    return SessionResponse(
        session_id=UUID(session.session_id),
        user_id=session.user_id,
        status=session.status.value,
        turn_count=session.current_turn,
        context=session.context,
        created_at=session.created_at,
        updated_at=session.last_activity,
        expires_at=session.expires_at,
    )


@router.get("/sessions/", response_model=List[SessionResponse])
async def list_sessions(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List multi-turn sessions.

    列出多輪對話會話。
    """
    sessions = await _session_manager.list_sessions(user_id=user_id)

    if status:
        sessions = [s for s in sessions if s.status.value == status]

    sessions = sessions[offset:offset + limit]

    return [
        SessionResponse(
            session_id=UUID(s.session_id),
            user_id=s.user_id,
            status=s.status.value,
            turn_count=s.current_turn,
            context=s.context,
            created_at=s.created_at,
            updated_at=s.last_activity,
            expires_at=s.expires_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: UUID):
    """Get session details.

    獲取會話詳情。
    """
    session = await _session_manager.get_session(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionResponse(
        session_id=UUID(session.session_id),
        user_id=session.user_id,
        status=session.status.value,
        turn_count=session.current_turn,
        context=session.context,
        created_at=session.created_at,
        updated_at=session.last_activity,
        expires_at=session.expires_at,
    )


@router.post("/sessions/{session_id}/turns", response_model=TurnResponse)
async def execute_turn(session_id: UUID, request: ExecuteTurnRequest):
    """Execute a turn in the session.

    執行對話輪次。
    """
    session = await _session_manager.get_session(str(session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        import time
        start_time = time.time()

        # Simple mock agent handler for MVP
        def mock_agent_handler(agent_id: str, user_input: str, history: list) -> str:
            return f"Response to: {user_input}"

        # Execute turn with mock handler
        response_message = await _session_manager.execute_turn(
            session_id=str(session_id),
            user_input=request.user_input,
            agent_handler=mock_agent_handler,
            agent_id=request.agent_id,
        )

        processing_time_ms = int((time.time() - start_time) * 1000)

        if not response_message:
            raise HTTPException(status_code=500, detail="Failed to execute turn")

        # Get updated session for turn number
        updated_session = await _session_manager.get_session(str(session_id))

        return TurnResponse(
            turn_id=UUID(response_message.message_id),
            turn_number=response_message.turn_number,
            user_input=request.user_input,
            agent_response=response_message.content,
            agent_id=response_message.sender_id,
            processing_time_ms=processing_time_ms,
            timestamp=response_message.timestamp,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: UUID,
    limit: int = Query(default=50, ge=1, le=500),
):
    """Get session turn history.

    獲取會話輪次歷史。
    """
    history = await _session_manager.get_history(str(session_id), limit=limit)

    # Group messages by turn to create turn responses
    turns_by_number: Dict[int, Dict[str, Any]] = {}
    for msg in history:
        turn_num = msg.turn_number
        if turn_num not in turns_by_number:
            turns_by_number[turn_num] = {
                "turn_id": msg.message_id,
                "turn_number": turn_num,
                "user_input": "",
                "agent_response": "",
                "agent_id": None,
                "timestamp": msg.timestamp,
            }
        if msg.role == "user":
            turns_by_number[turn_num]["user_input"] = msg.content
        elif msg.role == "agent":
            turns_by_number[turn_num]["agent_response"] = msg.content
            turns_by_number[turn_num]["agent_id"] = msg.sender_id

    return SessionHistoryResponse(
        session_id=session_id,
        turns=[
            TurnResponse(
                turn_id=UUID(t["turn_id"]),
                turn_number=t["turn_number"],
                user_input=t["user_input"],
                agent_response=t["agent_response"],
                agent_id=t["agent_id"],
                processing_time_ms=0,
                timestamp=t["timestamp"],
            )
            for t in sorted(turns_by_number.values(), key=lambda x: x["turn_number"])
        ],
        total_turns=len(turns_by_number),
    )


@router.patch("/sessions/{session_id}/context", response_model=SuccessResponse)
async def update_session_context(session_id: UUID, request: SessionContextUpdate):
    """Update session context.

    更新會話上下文。
    """
    result = await _session_manager.update_session(
        str(session_id),
        context=request.context,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Context updated")


@router.post("/sessions/{session_id}/close", response_model=SuccessResponse)
async def close_session(session_id: UUID):
    """Close a session.

    關閉會話。
    """
    result = await _session_manager.close_session(str(session_id))
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Session closed")


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_session(session_id: UUID):
    """Delete a session.

    刪除會話。
    """
    result = await _session_manager.delete_session(str(session_id))
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")

    return SuccessResponse(message="Session deleted")


# =============================================================================
# Voting Routes
# =============================================================================


@router.post("/voting/", response_model=VotingSessionResponse, status_code=201)
async def create_voting_session(request: CreateVotingSessionRequest):
    """Create a new voting session.

    建立新的投票會話。
    """
    try:
        vote_type = VoteType(request.vote_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid vote type: {request.vote_type}")

    session = _voting_manager.create_session(
        group_id=request.group_id,
        topic=request.topic,
        description=request.description,
        vote_type=vote_type,
        options=request.options,
        deadline_minutes=request.deadline_minutes,
        required_quorum=request.required_quorum,
        pass_threshold=request.pass_threshold,
        eligible_voters=set(request.eligible_voters) if request.eligible_voters else None,
    )

    return VotingSessionResponse(
        session_id=session.session_id,
        group_id=session.group_id,
        topic=session.topic,
        description=session.description,
        vote_type=session.vote_type.value,
        options=session.options,
        status=session.status.value,
        result=session.result.value,
        vote_count=session.vote_count,
        participation_rate=session.participation_rate,
        required_quorum=session.required_quorum,
        pass_threshold=session.pass_threshold,
        created_at=session.created_at,
        deadline=session.deadline,
    )


@router.get("/voting/", response_model=List[VotingSessionResponse])
async def list_voting_sessions(
    group_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
):
    """List voting sessions.

    列出投票會話。
    """
    voting_status = VotingSessionStatus(status) if status else None
    sessions = _voting_manager.list_sessions(group_id=group_id, status=voting_status)

    return [
        VotingSessionResponse(
            session_id=s.session_id,
            group_id=s.group_id,
            topic=s.topic,
            description=s.description,
            vote_type=s.vote_type.value,
            options=s.options,
            status=s.status.value,
            result=s.result.value,
            vote_count=s.vote_count,
            participation_rate=s.participation_rate,
            required_quorum=s.required_quorum,
            pass_threshold=s.pass_threshold,
            created_at=s.created_at,
            deadline=s.deadline,
        )
        for s in sessions
    ]


@router.get("/voting/{session_id}", response_model=VotingSessionResponse)
async def get_voting_session(session_id: UUID):
    """Get voting session details.

    獲取投票會話詳情。
    """
    session = _voting_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return VotingSessionResponse(
        session_id=session.session_id,
        group_id=session.group_id,
        topic=session.topic,
        description=session.description,
        vote_type=session.vote_type.value,
        options=session.options,
        status=session.status.value,
        result=session.result.value,
        vote_count=session.vote_count,
        participation_rate=session.participation_rate,
        required_quorum=session.required_quorum,
        pass_threshold=session.pass_threshold,
        created_at=session.created_at,
        deadline=session.deadline,
    )


@router.post("/voting/{session_id}/vote", response_model=VoteResponse)
async def cast_vote(session_id: UUID, request: CastVoteRequest):
    """Cast a vote.

    投票。
    """
    try:
        vote = _voting_manager.cast_vote(
            session_id=session_id,
            voter_id=request.voter_id,
            voter_name=request.voter_name,
            choice=request.choice,
            weight=request.weight,
            reason=request.reason,
        )

        return VoteResponse(
            vote_id=vote.vote_id,
            voter_id=vote.voter_id,
            voter_name=vote.voter_name,
            choice=vote.choice,
            weight=vote.weight,
            timestamp=vote.timestamp,
            reason=vote.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/voting/{session_id}/vote/{voter_id}", response_model=VoteResponse)
async def change_vote(session_id: UUID, voter_id: str, request: ChangeVoteRequest):
    """Change a vote.

    更改投票。
    """
    vote = _voting_manager.change_vote(
        session_id=session_id,
        voter_id=voter_id,
        new_choice=request.new_choice,
        reason=request.reason,
    )

    if not vote:
        raise HTTPException(status_code=404, detail="Vote not found")

    return VoteResponse(
        vote_id=vote.vote_id,
        voter_id=vote.voter_id,
        voter_name=vote.voter_name,
        choice=vote.choice,
        weight=vote.weight,
        timestamp=vote.timestamp,
        reason=vote.reason,
    )


@router.delete("/voting/{session_id}/vote/{voter_id}", response_model=SuccessResponse)
async def withdraw_vote(session_id: UUID, voter_id: str):
    """Withdraw a vote.

    撤回投票。
    """
    result = _voting_manager.withdraw_vote(session_id, voter_id)
    if not result:
        raise HTTPException(status_code=404, detail="Vote not found")

    return SuccessResponse(message="Vote withdrawn")


@router.get("/voting/{session_id}/votes", response_model=List[VoteResponse])
async def get_votes(session_id: UUID):
    """Get all votes for a session.

    獲取會話的所有投票。
    """
    session = _voting_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return [
        VoteResponse(
            vote_id=v.vote_id,
            voter_id=v.voter_id,
            voter_name=v.voter_name,
            choice=v.choice,
            weight=v.weight,
            timestamp=v.timestamp,
            reason=v.reason,
        )
        for v in session.votes.values()
    ]


@router.post("/voting/{session_id}/calculate", response_model=VotingResultResponse)
async def calculate_voting_result(
    session_id: UUID,
    total_eligible_voters: Optional[int] = Query(None),
):
    """Calculate voting result.

    計算投票結果。
    """
    try:
        result = _voting_manager.calculate_result(
            session_id=session_id,
            total_eligible_voters=total_eligible_voters,
        )

        session = _voting_manager.get_session(session_id)

        return VotingResultResponse(
            session_id=session_id,
            result=session.result.value if session else "unknown",
            result_details=result,
            participation_rate=result.get("participation_rate", 0),
            total_votes=result.get("total_votes", 0),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/voting/{session_id}/statistics", response_model=VotingStatisticsResponse)
async def get_voting_statistics(session_id: UUID):
    """Get voting statistics.

    獲取投票統計。
    """
    stats = _voting_manager.get_statistics(session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return VotingStatisticsResponse(
        session_id=UUID(stats["session_id"]),
        topic=stats["topic"],
        vote_type=stats["vote_type"],
        status=stats["status"],
        result=stats["result"],
        total_votes=stats["total_votes"],
        eligible_voters=stats["eligible_voters"],
        participation_rate=stats["participation_rate"],
        first_vote=datetime.fromisoformat(stats["first_vote"]) if stats.get("first_vote") else None,
        last_vote=datetime.fromisoformat(stats["last_vote"]) if stats.get("last_vote") else None,
    )


@router.post("/voting/{session_id}/close", response_model=SuccessResponse)
async def close_voting_session(session_id: UUID):
    """Close a voting session.

    關閉投票會話。
    """
    result = _voting_manager.close_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return SuccessResponse(message="Voting session closed")


@router.post("/voting/{session_id}/cancel", response_model=SuccessResponse)
async def cancel_voting_session(
    session_id: UUID,
    reason: str = Query(default=""),
):
    """Cancel a voting session.

    取消投票會話。
    """
    result = _voting_manager.cancel_session(session_id, reason)
    if not result:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return SuccessResponse(message=f"Voting session cancelled: {reason}")


@router.delete("/voting/{session_id}", response_model=SuccessResponse)
async def delete_voting_session(session_id: UUID):
    """Delete a voting session.

    刪除投票會話。
    """
    result = _voting_manager.delete_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Voting session not found")

    return SuccessResponse(message="Voting session deleted")

"""Claude SDK API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from src.integrations.claude_sdk.client import ClaudeSDKClient
from src.integrations.claude_sdk.exceptions import ClaudeSDKError, AuthenticationError
from .schemas import (
    QueryRequest,
    QueryResponse,
    ToolCallSchema,
    CreateSessionRequest,
    SessionResponse,
    SessionQueryRequest,
    SessionQueryResponse,
    SessionHistoryResponse,
    SessionHistoryMessageSchema,
    CloseSessionResponse,
)


router = APIRouter(prefix="/claude-sdk", tags=["Claude SDK"])

# Global client instance (should be properly managed in production)
_client: Optional[ClaudeSDKClient] = None


def get_client() -> ClaudeSDKClient:
    """Get or create Claude SDK client."""
    global _client
    if _client is None:
        try:
            _client = ClaudeSDKClient()
        except AuthenticationError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Claude SDK not configured: {e.message}",
            )
    return _client


async def get_optional_client() -> Optional[ClaudeSDKClient]:
    """Get Claude SDK client if available, None otherwise."""
    try:
        return get_client()
    except HTTPException:
        return None


# --- Endpoints ---


@router.post("/query", response_model=QueryResponse)
async def execute_query(
    request: QueryRequest,
    client: ClaudeSDKClient = Depends(get_client),
):
    """
    Execute a one-shot autonomous query.

    This endpoint sends a prompt to Claude and returns the result.
    The agent will use enabled tools to complete the task autonomously.
    """
    try:
        result = await client.query(
            prompt=request.prompt,
            tools=request.tools,
            max_tokens=request.max_tokens,
            timeout=request.timeout,
            working_directory=request.working_directory,
        )

        return QueryResponse(
            content=result.content,
            tool_calls=[
                ToolCallSchema(id=tc.id, name=tc.name, args=tc.args)
                for tc in result.tool_calls
            ],
            tokens_used=result.tokens_used,
            duration=result.duration,
            status=result.status,
        )

    except ClaudeSDKError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    client: ClaudeSDKClient = Depends(get_client),
):
    """
    Create a new conversation session.

    Sessions maintain conversation history across multiple queries,
    allowing for multi-turn interactions with context preservation.
    """
    try:
        session = await client.create_session(
            session_id=request.session_id,
            context=request.context,
        )

        return SessionResponse(session_id=session.session_id)

    except ClaudeSDKError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/sessions/{session_id}/query",
    response_model=SessionQueryResponse,
)
async def session_query(
    session_id: str,
    request: SessionQueryRequest,
    client: ClaudeSDKClient = Depends(get_client),
):
    """
    Execute a query within an existing session.

    The session maintains conversation history, so the agent has
    context from previous interactions in this session.
    """
    try:
        session = await client.resume_session(session_id)
        result = await session.query(
            prompt=request.prompt,
            tools=request.tools,
            max_tokens=request.max_tokens,
        )

        return SessionQueryResponse(
            content=result.content,
            tool_calls=[
                ToolCallSchema(id=tc.id, name=tc.name, args=tc.args)
                for tc in result.tool_calls
            ],
            tokens_used=result.tokens_used,
            message_index=result.message_index,
        )

    except ClaudeSDKError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/sessions/{session_id}", response_model=CloseSessionResponse)
async def close_session(
    session_id: str,
    client: ClaudeSDKClient = Depends(get_client),
):
    """
    Close a session and cleanup resources.

    After closing, the session cannot be used for further queries.
    """
    try:
        session = await client.resume_session(session_id)
        await session.close()
        return CloseSessionResponse(status="closed", session_id=session_id)

    except ClaudeSDKError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    client: ClaudeSDKClient = Depends(get_client),
):
    """
    Get conversation history for a session.

    Returns all messages exchanged in this session, including
    user prompts and assistant responses.
    """
    try:
        session = await client.resume_session(session_id)
        history = session.get_history()

        return SessionHistoryResponse(
            session_id=session_id,
            messages=[
                SessionHistoryMessageSchema(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp,
                    tool_calls=[
                        ToolCallSchema(id=tc.id, name=tc.name, args=tc.args)
                        for tc in msg.tool_calls
                    ] if msg.tool_calls else None,
                )
                for msg in history
            ],
        )

    except ClaudeSDKError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/health")
async def health_check(
    client: Optional[ClaudeSDKClient] = Depends(get_optional_client),
):
    """
    Check Claude SDK health status.

    Returns configuration status and whether the client is ready.
    """
    if client is None:
        return {
            "status": "unconfigured",
            "message": "ANTHROPIC_API_KEY not set",
            "ready": False,
        }

    return {
        "status": "healthy",
        "model": client.config.model,
        "max_tokens": client.config.max_tokens,
        "active_sessions": len(client.get_sessions()),
        "ready": True,
    }

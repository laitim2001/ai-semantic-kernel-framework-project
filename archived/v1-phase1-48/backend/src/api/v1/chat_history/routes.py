"""
Chat History API Routes -- Sprint 111

Endpoints for syncing chat messages between frontend localStorage and
backend persistent storage (SessionStore).

Endpoints:
    POST /api/v1/chat-history/sync           -- Bulk sync messages from frontend
    GET  /api/v1/chat-history/{session_id}   -- Get chat history for a session
    DELETE /api/v1/chat-history/{session_id}  -- Delete chat history for a session
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status

from src.domain.chat_history.models import (
    ChatHistorySync,
    ChatMessage,
    ChatSyncResponse,
)
from src.infrastructure.storage.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat-history", tags=["Chat History"])

# Module-level store instance, lazily initialized
_chat_store: Optional[SessionStore] = None


async def _get_store() -> SessionStore:
    """
    Get or create the SessionStore for chat history.

    Uses a dedicated SessionStore with namespace 'chat_history'
    and 7-day TTL for message retention.
    """
    global _chat_store
    if _chat_store is None:
        _chat_store = await SessionStore.create(
            backend_type="auto",
            ttl_hours=168,  # 7 days
            namespace="chat_history",
        )
    return _chat_store


def _make_chat_key(session_id: str) -> str:
    """Build a namespaced storage key for a session's chat history."""
    return f"chat:{session_id}"


@router.post(
    "/sync",
    response_model=ChatSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync chat messages from frontend",
    description=(
        "Receives messages from frontend localStorage and stores them "
        "in the backend for persistence. Replaces any existing messages "
        "for the session."
    ),
)
async def sync_chat_history(payload: ChatHistorySync) -> ChatSyncResponse:
    """
    Bulk sync chat messages from frontend to backend.

    The frontend periodically sends its full message list for a session.
    The backend stores it as a single session document in SessionStore.
    """
    store = await _get_store()

    if not payload.session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id is required",
        )

    # Convert messages to serializable dicts
    messages_data: List[Dict[str, Any]] = [
        msg.model_dump(mode="json") for msg in payload.messages
    ]

    sync_at = datetime.now(timezone.utc)

    # Store the full message list for this session
    chat_data: Dict[str, Any] = {
        "session_id": payload.session_id,
        "messages": messages_data,
        "message_count": len(messages_data),
        "last_sync_at": sync_at.isoformat(),
    }

    key = _make_chat_key(payload.session_id)
    await store.set(key, chat_data)

    logger.info(
        f"Chat history synced: session={payload.session_id}, "
        f"messages={len(messages_data)}"
    )

    return ChatSyncResponse(
        session_id=payload.session_id,
        synced_count=len(messages_data),
        sync_at=sync_at,
    )


@router.get(
    "/{session_id}",
    response_model=Dict[str, Any],
    summary="Get chat history for a session",
    description="Retrieves all stored chat messages for a session.",
)
async def get_chat_history(session_id: str) -> Dict[str, Any]:
    """
    Get chat history for a specific session.

    Returns the full message list and sync metadata.
    """
    store = await _get_store()
    key = _make_chat_key(session_id)
    data = await store.get(key)

    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No chat history found for session {session_id}",
        )

    return {
        "data": data,
        "message": "Success",
    }


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete chat history for a session",
    description="Removes all stored chat messages for a session.",
)
async def delete_chat_history(session_id: str) -> Dict[str, Any]:
    """
    Delete chat history for a specific session.

    Removes the session's messages from persistent storage.
    """
    store = await _get_store()
    key = _make_chat_key(session_id)

    existed = await store.exists(key)
    if not existed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No chat history found for session {session_id}",
        )

    await store.delete(key)

    logger.info(f"Chat history deleted: session={session_id}")

    return {
        "data": {"session_id": session_id, "deleted": True},
        "message": "Chat history deleted",
    }

"""
Session Chat API (S46-3)

REST API endpoints for AI-powered chat with streaming support.
Uses SessionAgentBridge for Agent integration.

Features:
- Synchronous chat endpoint
- Server-Sent Events (SSE) streaming
- Tool approval management
- Cancel operations
"""

from typing import Optional, Dict, Any, List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import logging
import json
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.domain.sessions.bridge import (
    SessionAgentBridge,
    BridgeConfig,
    SessionNotFoundError as BridgeSessionNotFoundError,
    SessionNotActiveError as BridgeSessionNotActiveError,
    AgentNotFoundError as BridgeAgentNotFoundError,
    create_session_agent_bridge,
)
from src.domain.sessions.events import ExecutionEvent, ExecutionEventType
from src.domain.sessions.service import SessionService
from src.domain.sessions.repository import SQLAlchemySessionRepository
from src.domain.sessions.cache import SessionCache
from src.domain.sessions.executor import AgentExecutor
from src.domain.sessions.approval import (
    ToolApprovalManager,
    ApprovalStatus,
    ApprovalNotFoundError,
    create_approval_manager,
)
from src.infrastructure.database.session import get_session
from src.integrations.llm.factory import LLMServiceFactory


logger = logging.getLogger(__name__)

router = APIRouter(tags=["sessions-chat"])


# =============================================================================
# Request/Response Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """聊天請求"""
    content: str = Field(..., min_length=1, max_length=100000, description="訊息內容")
    attachments: Optional[List[Dict[str, Any]]] = Field(
        None, description="附件列表 (包含 id, type 等)"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")
    stream: bool = Field(False, description="是否啟用串流回應")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello, can you help me with Python?",
                "stream": False,
            }
        }


class ChatResponse(BaseModel):
    """聊天回應"""
    session_id: str
    message_id: Optional[str] = None
    content: str
    tool_calls: List[Dict[str, Any]] = []
    pending_approvals: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "Hello! I'd be happy to help you with Python.",
                "tool_calls": [],
                "pending_approvals": [],
                "created_at": "2025-12-24T10:00:00Z",
            }
        }


class ApprovalRequest(BaseModel):
    """審批請求"""
    approved: bool = Field(..., description="是否批准")
    feedback: Optional[str] = Field(None, description="審批回饋")

    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "feedback": "Looks good, proceed.",
            }
        }


class ApprovalResponse(BaseModel):
    """審批回應"""
    approval_id: str
    session_id: str
    status: str
    approved: bool
    feedback: Optional[str] = None
    result_events: List[Dict[str, Any]] = []
    timestamp: datetime


class PendingApprovalItem(BaseModel):
    """待審批項目"""
    approval_id: str
    session_id: str
    tool_name: str
    arguments: Dict[str, Any]
    created_at: datetime
    expires_at: datetime


class PendingApprovalsResponse(BaseModel):
    """待審批列表回應"""
    session_id: str
    approvals: List[PendingApprovalItem]
    total: int


class CancelResponse(BaseModel):
    """取消回應"""
    session_id: str
    cancelled_count: int
    reason: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


# =============================================================================
# Dependencies
# =============================================================================

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """獲取 Redis 客戶端"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password if settings.redis_password else None,
            decode_responses=True,
        )
    return _redis_client


# Agent repository protocol implementation for dependency injection
class SimpleAgentRepository:
    """簡單的 Agent Repository 實現"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get(self, agent_id: str) -> Optional[Any]:
        """獲取 Agent (簡化實現)"""
        # TODO: 整合實際的 Agent Repository
        return None


async def get_session_bridge(
    db: AsyncSession = Depends(get_session),
) -> SessionAgentBridge:
    """獲取 SessionAgentBridge 實例"""
    redis_client = await get_redis()

    repository = SQLAlchemySessionRepository(db)
    cache = SessionCache(redis_client)
    session_service = SessionService(repository=repository, cache=cache)

    # 創建 Agent 相關依賴
    # 使用 LLMServiceFactory 創建 LLM 服務 (自動檢測環境: Azure/Mock)
    llm_service = LLMServiceFactory.create()
    agent_executor = AgentExecutor(llm_service=llm_service)
    agent_repository = SimpleAgentRepository(db)

    approval_manager = create_approval_manager(redis_client)

    bridge = create_session_agent_bridge(
        session_service=session_service,
        agent_executor=agent_executor,
        agent_repository=agent_repository,
        approval_manager=approval_manager,
    )

    return bridge


async def get_current_user_id() -> str:
    """獲取當前用戶 ID"""
    return "00000000-0000-0000-0000-000000000001"


# =============================================================================
# SSE Streaming Helper
# =============================================================================

async def stream_events(
    events: AsyncGenerator[ExecutionEvent, None],
) -> AsyncGenerator[str, None]:
    """將 ExecutionEvent 轉換為 SSE 格式

    Args:
        events: ExecutionEvent 異步生成器

    Yields:
        SSE 格式的字串
    """
    async for event in events:
        data = json.dumps(event.to_dict())
        yield f"event: {event.event_type.value}\ndata: {data}\n\n"

    yield "event: done\ndata: {}\n\n"


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post(
    "/{session_id}/chat",
    response_model=ChatResponse,
    summary="發送聊天訊息",
    description="發送訊息到 Session 並獲取 AI 回應",
    responses={
        200: {"description": "成功"},
        400: {"model": ErrorResponse, "description": "無效請求"},
        404: {"model": ErrorResponse, "description": "Session 未找到"},
        410: {"model": ErrorResponse, "description": "Session 未激活"},
    }
)
async def chat(
    session_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> ChatResponse:
    """發送聊天訊息 (非串流)

    處理用戶訊息並返回完整的 AI 回應。
    適用於不需要實時串流的場景。
    """
    # 如果請求串流模式，重定向到串流端點
    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "STREAM_NOT_SUPPORTED",
                "message": "Use POST /{session_id}/chat/stream for streaming responses",
            }
        )

    try:
        # 收集所有事件
        content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        pending_approvals: List[Dict[str, Any]] = []
        metadata: Dict[str, Any] = {}

        async for event in bridge.process_message(
            session_id=session_id,
            content=request.content,
            attachments=request.attachments,
            stream=False,
        ):
            if event.event_type == ExecutionEventType.CONTENT:
                if event.content:
                    content_parts.append(event.content)

            elif event.event_type == ExecutionEventType.CONTENT_DELTA:
                if event.content:
                    content_parts.append(event.content)

            elif event.event_type == ExecutionEventType.TOOL_CALL:
                if event.tool_call:
                    tool_calls.append(event.tool_call.to_dict())

            elif event.event_type == ExecutionEventType.APPROVAL_REQUIRED:
                # 從事件中提取審批請求信息
                approval_info = {
                    "approval_request_id": event.approval_request_id,
                    "tool_name": event.tool_call.name if event.tool_call else None,
                    "arguments": event.tool_call.arguments if event.tool_call else {},
                }
                pending_approvals.append(approval_info)

            elif event.event_type == ExecutionEventType.DONE:
                if event.metadata:
                    metadata.update(event.metadata)

            elif event.event_type == ExecutionEventType.ERROR:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "EXECUTION_ERROR",
                        "message": event.error or "Unknown execution error",
                    }
                )

        return ChatResponse(
            session_id=session_id,
            message_id=metadata.get("message_id"),
            content="".join(content_parts),
            tool_calls=tool_calls,
            pending_approvals=pending_approvals,
            metadata=metadata,
            created_at=datetime.utcnow(),
        )

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )
    except BridgeSessionNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "SESSION_NOT_ACTIVE", "message": "Session is not active"},
        )
    except BridgeAgentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "AGENT_NOT_FOUND", "message": "Agent not found"},
        )


@router.post(
    "/{session_id}/chat/stream",
    summary="發送聊天訊息 (串流)",
    description="發送訊息到 Session 並獲取串流 AI 回應 (SSE)",
    responses={
        200: {"description": "SSE 串流回應"},
        404: {"model": ErrorResponse, "description": "Session 未找到"},
    }
)
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> StreamingResponse:
    """發送聊天訊息 (SSE 串流)

    使用 Server-Sent Events 串流返回 AI 回應。
    適用於實時顯示回應的場景。
    """
    try:
        # 創建事件生成器
        events = bridge.process_message(
            session_id=session_id,
            content=request.content,
            attachments=request.attachments,
            stream=True,
        )

        return StreamingResponse(
            stream_events(events),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )
    except BridgeSessionNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "SESSION_NOT_ACTIVE", "message": "Session is not active"},
        )


# =============================================================================
# Approval Endpoints
# =============================================================================

@router.get(
    "/{session_id}/approvals",
    response_model=PendingApprovalsResponse,
    summary="獲取待審批列表",
    description="獲取 Session 中所有待審批的工具調用",
)
async def get_pending_approvals(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> PendingApprovalsResponse:
    """獲取待審批列表"""
    try:
        approvals = await bridge.get_pending_approvals(session_id)

        items = [
            PendingApprovalItem(
                approval_id=a.id,
                session_id=a.session_id,
                tool_name=a.tool_name,
                arguments=a.tool_arguments,
                created_at=a.created_at,
                expires_at=a.expires_at,
            )
            for a in approvals
        ]

        return PendingApprovalsResponse(
            session_id=session_id,
            approvals=items,
            total=len(items),
        )

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )


@router.post(
    "/{session_id}/approvals/{approval_id}",
    response_model=ApprovalResponse,
    summary="處理審批請求",
    description="批准或拒絕工具調用審批請求",
    responses={
        200: {"description": "審批處理成功"},
        404: {"model": ErrorResponse, "description": "審批請求未找到"},
    }
)
async def handle_approval(
    session_id: str,
    approval_id: str,
    request: ApprovalRequest,
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> ApprovalResponse:
    """處理審批請求"""
    try:
        result_events: List[Dict[str, Any]] = []

        async for event in bridge.handle_tool_approval(
            session_id=session_id,
            approval_id=approval_id,
            approved=request.approved,
            feedback=request.feedback,
            approver_id=user_id,
        ):
            result_events.append(event.to_dict())

        return ApprovalResponse(
            approval_id=approval_id,
            session_id=session_id,
            status="approved" if request.approved else "rejected",
            approved=request.approved,
            feedback=request.feedback,
            result_events=result_events,
            timestamp=datetime.utcnow(),
        )

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )
    except ApprovalNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "APPROVAL_NOT_FOUND", "message": "Approval request not found"},
        )


@router.delete(
    "/{session_id}/approvals",
    response_model=CancelResponse,
    summary="取消所有待審批",
    description="取消 Session 中所有待審批的請求",
)
async def cancel_approvals(
    session_id: str,
    reason: str = Query("user_cancelled", description="取消原因"),
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> CancelResponse:
    """取消所有待審批請求"""
    try:
        cancelled_count = await bridge.cancel_pending_approvals(
            session_id=session_id,
            reason=reason,
        )

        return CancelResponse(
            session_id=session_id,
            cancelled_count=cancelled_count,
            reason=reason,
            timestamp=datetime.utcnow(),
        )

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )


# =============================================================================
# Status Endpoint
# =============================================================================

@router.get(
    "/{session_id}/chat/status",
    summary="獲取聊天狀態",
    description="獲取 Session 的聊天處理狀態",
)
async def get_chat_status(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    bridge: SessionAgentBridge = Depends(get_session_bridge),
) -> Dict[str, Any]:
    """獲取聊天狀態"""
    try:
        pending_approvals = await bridge.get_pending_approvals(session_id)

        return {
            "session_id": session_id,
            "is_processing": False,  # TODO: 追蹤實際處理狀態
            "pending_approvals_count": len(pending_approvals),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except BridgeSessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

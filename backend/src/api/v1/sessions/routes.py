"""
Session API Routes

REST API endpoints for Session management.
Provides CRUD operations for sessions and messages.
"""

from typing import Optional, List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import FileResponse
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.sessions.schemas import (
    CreateSessionRequest,
    SendMessageRequest,
    UpdateSessionRequest,
    ToolCallActionRequest,
    SessionResponse,
    SessionDetailResponse,
    SessionListResponse,
    MessageResponse,
    MessageListResponse,
    AttachmentResponse,
    ErrorResponse,
)
from src.core.config import get_settings
from src.domain.sessions.models import SessionStatus
from src.domain.sessions.service import (
    SessionService,
    SessionNotFoundError,
    SessionExpiredError,
    SessionNotActiveError,
    MessageLimitExceededError,
)
from src.domain.sessions.repository import SQLAlchemySessionRepository
from src.domain.sessions.cache import SessionCache
from src.infrastructure.database.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ===== Redis 連接管理 =====

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """獲取 Redis 客戶端 (單例)"""
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


# ===== 依賴注入 =====

async def get_session_service(
    db: AsyncSession = Depends(get_session),
) -> AsyncGenerator[SessionService, None]:
    """獲取 Session 服務 (依賴注入)

    創建完整的 SessionService 實例，包括:
    - SQLAlchemySessionRepository: 資料庫存取
    - SessionCache: Redis 快取
    - SessionEventPublisher: 事件發布 (使用預設)
    """
    # 獲取 Redis 客戶端
    redis_client = await get_redis()

    # 創建 Repository 和 Cache
    repository = SQLAlchemySessionRepository(db)
    cache = SessionCache(redis_client)

    # 創建 SessionService
    service = SessionService(repository=repository, cache=cache)

    yield service


async def get_current_user_id() -> str:
    """獲取當前用戶 ID (依賴注入)

    NOTE: 目前返回預設用戶 ID，實際應用需整合認證系統
    - 整合 JWT Token 驗證
    - 從 Authorization header 提取用戶 ID
    - 驗證用戶權限
    """
    # 預設用戶 ID (開發/測試用) - 必須是有效的 UUID 格式
    # 在生產環境中，應從 JWT token 或 session 提取
    return "00000000-0000-0000-0000-000000000001"


# ===== Session CRUD =====

@router.post(
    "",
    response_model=SessionDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="創建 Session",
    description="創建新的互動式對話 Session",
    responses={
        201: {"description": "Session 創建成功"},
        400: {"model": ErrorResponse, "description": "無效請求"},
        401: {"model": ErrorResponse, "description": "未認證"},
    }
)
async def create_session(
    request: CreateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """創建新 Session"""
    try:
        config = request.config.to_domain() if request.config else None

        session = await service.create_session(
            user_id=user_id,
            agent_id=request.agent_id,
            config=config,
            system_prompt=request.system_prompt,
            metadata=request.metadata,
        )

        return SessionDetailResponse.from_domain(session)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_REQUEST", "message": str(e)},
        )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="列出 Sessions",
    description="列出當前用戶的所有 Sessions",
)
async def list_sessions(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="狀態過濾: created, active, suspended, ended"
    ),
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(20, ge=1, le=100, description="每頁數量"),
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionListResponse:
    """列出用戶的 Sessions"""
    # 解析狀態過濾
    session_status = None
    if status_filter:
        try:
            session_status = SessionStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "INVALID_STATUS",
                    "message": f"Invalid status: {status_filter}",
                },
            )

    offset = (page - 1) * page_size

    sessions = await service.list_sessions(
        user_id=user_id,
        status=session_status,
        limit=page_size + 1,  # 多取一個判斷是否有更多
        offset=offset,
    )

    has_more = len(sessions) > page_size
    if has_more:
        sessions = sessions[:page_size]

    total = await service.count_sessions(user_id, session_status)

    return SessionListResponse(
        data=[SessionResponse.from_domain(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="獲取 Session",
    description="獲取 Session 詳細資訊",
    responses={
        200: {"description": "成功"},
        403: {"model": ErrorResponse, "description": "無權限"},
        404: {"model": ErrorResponse, "description": "Session 未找到"},
    }
)
async def get_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """獲取 Session 詳情"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    # 權限檢查
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    return SessionDetailResponse.from_domain(session)


@router.patch(
    "/{session_id}",
    response_model=SessionDetailResponse,
    summary="更新 Session",
    description="更新 Session 標題或元數據",
)
async def update_session(
    session_id: str,
    request: UpdateSessionRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """更新 Session"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    if request.title is not None:
        session = await service.update_session_title(session_id, request.title)

    if request.metadata is not None:
        session = await service.update_session_metadata(session_id, request.metadata)

    return SessionDetailResponse.from_domain(session)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="結束 Session",
    description="結束並關閉 Session",
)
async def end_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> None:
    """結束 Session"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    await service.end_session(session_id, reason="user_request")


# ===== Session 狀態操作 =====

@router.post(
    "/{session_id}/activate",
    response_model=SessionDetailResponse,
    summary="激活 Session",
    description="激活已創建或暫停的 Session",
)
async def activate_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """激活 Session"""
    try:
        session = await service.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCESS_DENIED", "message": "Access denied"},
            )

        session = await service.activate_session(session_id)
        return SessionDetailResponse.from_domain(session)

    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "SESSION_EXPIRED", "message": "Session has expired"},
        )
    except SessionNotActiveError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_STATE", "message": str(e)},
        )


@router.post(
    "/{session_id}/suspend",
    response_model=SessionDetailResponse,
    summary="暫停 Session",
    description="暫停活躍的 Session",
)
async def suspend_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """暫停 Session"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    try:
        session = await service.suspend_session(session_id)
        return SessionDetailResponse.from_domain(session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_STATE", "message": str(e)},
        )


@router.post(
    "/{session_id}/resume",
    response_model=SessionDetailResponse,
    summary="恢復 Session",
    description="恢復暫停的 Session",
)
async def resume_session(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> SessionDetailResponse:
    """恢復 Session"""
    try:
        session = await service.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCESS_DENIED", "message": "Access denied"},
            )

        session = await service.resume_session(session_id)
        return SessionDetailResponse.from_domain(session)

    except SessionExpiredError:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"error": "SESSION_EXPIRED", "message": "Session has expired"},
        )


# ===== 訊息操作 =====

@router.get(
    "/{session_id}/messages",
    response_model=MessageListResponse,
    summary="獲取訊息",
    description="獲取 Session 的訊息歷史",
)
async def get_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=100, description="返回數量"),
    before_id: Optional[str] = Query(None, description="在此 ID 之前的訊息"),
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> MessageListResponse:
    """獲取訊息歷史"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    messages = await service.get_messages(
        session_id,
        limit=limit + 1,
        before_id=before_id,
    )

    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    next_cursor = messages[0].id if has_more and messages else None

    return MessageListResponse(
        data=[MessageResponse.from_domain(m) for m in messages],
        has_more=has_more,
        next_cursor=next_cursor,
    )


@router.post(
    "/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="發送訊息",
    description="發送用戶訊息到 Session",
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> MessageResponse:
    """發送訊息"""
    try:
        session = await service.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
            )

        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCESS_DENIED", "message": "Access denied"},
            )

        message = await service.send_message(
            session_id=session_id,
            content=request.content,
            metadata=request.metadata,
        )

        return MessageResponse.from_domain(message)

    except SessionNotActiveError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SESSION_NOT_ACTIVE", "message": "Session is not active"},
        )
    except MessageLimitExceededError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "MESSAGE_LIMIT_EXCEEDED", "message": str(e)},
        )


# ===== 附件操作 =====

@router.post(
    "/{session_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上傳附件",
    description="上傳附件到 Session",
)
async def upload_attachment(
    session_id: str,
    file: UploadFile = File(..., description="上傳的文件"),
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> AttachmentResponse:
    """上傳附件"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    # 檢查文件大小
    if file.size and file.size > session.config.max_attachment_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": "FILE_TOO_LARGE",
                "message": f"File size exceeds limit of {session.config.max_attachment_size} bytes",
            },
        )

    # TODO: 實現實際的附件存儲
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": "NOT_IMPLEMENTED", "message": "Attachment storage not implemented"},
    )


@router.get(
    "/{session_id}/attachments/{attachment_id}",
    summary="下載附件",
    description="下載 Session 中的附件",
)
async def download_attachment(
    session_id: str,
    attachment_id: str,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
):
    """下載附件"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    # TODO: 實現實際的附件下載
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={"error": "NOT_IMPLEMENTED", "message": "Attachment storage not implemented"},
    )


# ===== 工具調用操作 =====

@router.post(
    "/{session_id}/tool-calls/{tool_call_id}",
    status_code=status.HTTP_200_OK,
    summary="處理工具調用",
    description="批准或拒絕工具調用",
)
async def handle_tool_call(
    session_id: str,
    tool_call_id: str,
    request: ToolCallActionRequest,
    user_id: str = Depends(get_current_user_id),
    service: SessionService = Depends(get_session_service),
) -> dict:
    """處理工具調用"""
    session = await service.get_session(session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": "Session not found"},
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACCESS_DENIED", "message": "Access denied"},
        )

    if request.action == "approve":
        await service.approve_tool_call(session_id, tool_call_id, user_id)
        return {"status": "approved", "tool_call_id": tool_call_id}
    else:
        await service.reject_tool_call(session_id, tool_call_id, user_id, request.reason)
        return {"status": "rejected", "tool_call_id": tool_call_id, "reason": request.reason}

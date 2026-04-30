"""
Session API Schemas

Pydantic models for Session REST API requests and responses.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from src.domain.sessions.models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
    AttachmentType,
    ToolCall,
    ToolCallStatus,
)


# ===== Configuration Schemas =====

class SessionConfigSchema(BaseModel):
    """Session 配置 Schema"""
    max_messages: int = Field(100, ge=10, le=1000, description="最大訊息數量")
    max_attachments: int = Field(10, ge=1, le=50, description="最大附件數量")
    max_attachment_size: int = Field(
        10 * 1024 * 1024,
        ge=1024,
        le=100 * 1024 * 1024,
        description="最大附件大小 (bytes)"
    )
    timeout_minutes: int = Field(60, ge=5, le=1440, description="過期時間 (分鐘)")
    enable_code_interpreter: bool = Field(True, description="啟用程式碼解譯器")
    enable_mcp_tools: bool = Field(True, description="啟用 MCP 工具")
    enable_file_search: bool = Field(True, description="啟用檔案搜尋")
    allowed_tools: List[str] = Field(default_factory=list, description="允許的工具列表")
    blocked_tools: List[str] = Field(default_factory=list, description="禁用的工具列表")
    system_prompt_override: Optional[str] = Field(None, description="覆蓋系統提示")

    def to_domain(self) -> SessionConfig:
        """轉換為領域物件"""
        return SessionConfig(
            max_messages=self.max_messages,
            max_attachments=self.max_attachments,
            max_attachment_size=self.max_attachment_size,
            timeout_minutes=self.timeout_minutes,
            enable_code_interpreter=self.enable_code_interpreter,
            enable_mcp_tools=self.enable_mcp_tools,
            enable_file_search=self.enable_file_search,
            allowed_tools=self.allowed_tools,
            blocked_tools=self.blocked_tools,
            system_prompt_override=self.system_prompt_override,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "max_messages": 100,
                "timeout_minutes": 60,
                "enable_code_interpreter": True,
                "enable_mcp_tools": True,
            }
        }


# ===== Request Schemas =====

class CreateSessionRequest(BaseModel):
    """創建 Session 請求"""
    agent_id: str = Field(..., description="Agent ID")
    config: Optional[SessionConfigSchema] = Field(None, description="Session 配置")
    system_prompt: Optional[str] = Field(None, description="系統提示詞")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "config": {
                    "timeout_minutes": 60,
                    "enable_code_interpreter": True,
                },
                "metadata": {
                    "source": "web_app",
                }
            }
        }


class SendMessageRequest(BaseModel):
    """發送訊息請求"""
    content: str = Field(..., min_length=1, max_length=100000, description="訊息內容")
    attachment_ids: List[str] = Field(default_factory=list, description="附件 ID 列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello, can you help me with Python?",
                "attachment_ids": [],
            }
        }


class UpdateSessionRequest(BaseModel):
    """更新 Session 請求"""
    title: Optional[str] = Field(None, max_length=200, description="標題")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Python Programming Help",
                "metadata": {"tags": ["python", "programming"]},
            }
        }


class ToolCallActionRequest(BaseModel):
    """工具調用操作請求"""
    action: str = Field(..., pattern="^(approve|reject)$", description="操作: approve/reject")
    reason: Optional[str] = Field(None, description="原因 (用於拒絕)")

    class Config:
        json_schema_extra = {
            "example": {
                "action": "approve",
            }
        }


# ===== Response Schemas =====

class AttachmentResponse(BaseModel):
    """附件響應"""
    id: str
    filename: str
    content_type: str
    size: int
    attachment_type: str
    uploaded_at: datetime

    @classmethod
    def from_domain(cls, attachment: Attachment) -> "AttachmentResponse":
        """從領域物件創建"""
        return cls(
            id=attachment.id,
            filename=attachment.filename,
            content_type=attachment.content_type,
            size=attachment.size,
            attachment_type=attachment.attachment_type.value,
            uploaded_at=attachment.uploaded_at,
        )


class ToolCallResponse(BaseModel):
    """工具調用響應"""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    status: str
    requires_approval: bool
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    executed_at: Optional[datetime]
    error: Optional[str]

    @classmethod
    def from_domain(cls, tool_call: ToolCall) -> "ToolCallResponse":
        """從領域物件創建"""
        return cls(
            id=tool_call.id,
            tool_name=tool_call.tool_name,
            arguments=tool_call.arguments,
            result=tool_call.result,
            status=tool_call.status.value,
            requires_approval=tool_call.requires_approval,
            approved_by=tool_call.approved_by,
            approved_at=tool_call.approved_at,
            executed_at=tool_call.executed_at,
            error=tool_call.error,
        )


class ToolCallListResponse(BaseModel):
    """工具調用列表響應"""
    session_id: str
    tool_calls: List[ToolCallResponse] = []
    total: int = 0


class MessageResponse(BaseModel):
    """訊息響應"""
    id: str
    session_id: str
    role: str
    content: str
    attachments: List[AttachmentResponse] = []
    tool_calls: List[ToolCallResponse] = []
    parent_id: Optional[str] = None
    created_at: datetime

    @classmethod
    def from_domain(cls, message: Message) -> "MessageResponse":
        """從領域物件創建"""
        return cls(
            id=message.id,
            session_id=message.session_id,
            role=message.role.value,
            content=message.content,
            attachments=[AttachmentResponse.from_domain(a) for a in message.attachments],
            tool_calls=[ToolCallResponse.from_domain(tc) for tc in message.tool_calls],
            parent_id=message.parent_id,
            created_at=message.created_at,
        )


class SessionResponse(BaseModel):
    """Session 響應"""
    id: str
    user_id: str
    agent_id: str
    status: str
    title: Optional[str]
    message_count: int
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime]

    @classmethod
    def from_domain(cls, session: Session) -> "SessionResponse":
        """從領域物件創建"""
        return cls(
            id=session.id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            status=session.status.value,
            title=session.title,
            message_count=session.get_message_count(),
            created_at=session.created_at,
            updated_at=session.updated_at,
            expires_at=session.expires_at,
        )


class SessionDetailResponse(SessionResponse):
    """Session 詳細響應 (包含配置和元數據)"""
    config: SessionConfigSchema
    metadata: Dict[str, Any]
    ended_at: Optional[datetime]

    @classmethod
    def from_domain(cls, session: Session) -> "SessionDetailResponse":
        """從領域物件創建"""
        config = SessionConfigSchema(
            max_messages=session.config.max_messages,
            max_attachments=session.config.max_attachments,
            max_attachment_size=session.config.max_attachment_size,
            timeout_minutes=session.config.timeout_minutes,
            enable_code_interpreter=session.config.enable_code_interpreter,
            enable_mcp_tools=session.config.enable_mcp_tools,
            enable_file_search=session.config.enable_file_search,
            allowed_tools=session.config.allowed_tools,
            blocked_tools=session.config.blocked_tools,
            system_prompt_override=session.config.system_prompt_override,
        )

        return cls(
            id=session.id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            status=session.status.value,
            title=session.title,
            message_count=session.get_message_count(),
            created_at=session.created_at,
            updated_at=session.updated_at,
            expires_at=session.expires_at,
            ended_at=session.ended_at,
            config=config,
            metadata=session.metadata,
        )


class SessionListResponse(BaseModel):
    """Session 列表響應"""
    data: List[SessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class MessageListResponse(BaseModel):
    """訊息列表響應"""
    data: List[MessageResponse]
    has_more: bool
    next_cursor: Optional[str] = None


# ===== Error Response =====

class ErrorResponse(BaseModel):
    """錯誤響應"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "SESSION_NOT_FOUND",
                "message": "Session not found",
                "details": {"session_id": "xxx"},
            }
        }

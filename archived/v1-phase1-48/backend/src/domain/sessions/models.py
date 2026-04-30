"""
Session Domain Models

Session Mode API - Interactive chat functionality with state machine management.
Implements Session, Message, Attachment, and ToolCall domain models.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid


class SessionStatus(str, Enum):
    """Session 狀態枚舉

    狀態轉換:
        CREATED → ACTIVE → SUSPENDED → ENDED
                    ↓          ↑
                    └──────────┘
    """
    CREATED = "created"      # 已創建，尚未連接
    ACTIVE = "active"        # 活躍中
    SUSPENDED = "suspended"  # 暫停 (連接中斷)
    ENDED = "ended"          # 已結束


class MessageRole(str, Enum):
    """訊息角色枚舉"""
    USER = "user"            # 用戶訊息
    ASSISTANT = "assistant"  # 助手回覆
    SYSTEM = "system"        # 系統提示
    TOOL = "tool"            # 工具回覆


class AttachmentType(str, Enum):
    """附件類型枚舉"""
    IMAGE = "image"          # 圖片
    DOCUMENT = "document"    # 文檔
    CODE = "code"            # 程式碼
    DATA = "data"            # 資料文件
    OTHER = "other"          # 其他


class ToolCallStatus(str, Enum):
    """工具調用狀態枚舉"""
    PENDING = "pending"      # 待執行
    APPROVED = "approved"    # 已批准
    REJECTED = "rejected"    # 已拒絕
    RUNNING = "running"      # 執行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 執行失敗


@dataclass
class Attachment:
    """附件模型

    支援上傳圖片、文檔、程式碼等附件。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    filename: str = ""
    content_type: str = ""
    size: int = 0
    storage_path: str = ""
    attachment_type: AttachmentType = AttachmentType.OTHER
    uploaded_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_upload(
        cls,
        filename: str,
        content_type: str,
        size: int,
        storage_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "Attachment":
        """從上傳創建附件

        Args:
            filename: 文件名
            content_type: MIME 類型
            size: 文件大小 (bytes)
            storage_path: 存儲路徑
            metadata: 額外元數據

        Returns:
            Attachment instance
        """
        attachment_type = cls._detect_type(content_type)
        return cls(
            filename=filename,
            content_type=content_type,
            size=size,
            storage_path=storage_path,
            attachment_type=attachment_type,
            metadata=metadata or {}
        )

    @staticmethod
    def _detect_type(content_type: str) -> AttachmentType:
        """檢測附件類型

        Args:
            content_type: MIME 類型

        Returns:
            AttachmentType
        """
        if content_type.startswith("image/"):
            return AttachmentType.IMAGE
        elif content_type in [
            "application/pdf",
            "text/plain",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]:
            return AttachmentType.DOCUMENT
        elif content_type in [
            "text/x-python",
            "text/python",
            "application/javascript",
            "text/javascript",
            "text/x-java",
            "text/x-c",
            "text/x-csharp"
        ]:
            return AttachmentType.CODE
        elif content_type in [
            "text/csv",
            "application/json",
            "application/xml",
            "text/xml",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]:
            return AttachmentType.DATA
        else:
            return AttachmentType.OTHER

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "storage_path": self.storage_path,
            "attachment_type": self.attachment_type.value,
            "uploaded_at": self.uploaded_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Attachment":
        """從字典創建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            filename=data.get("filename", ""),
            content_type=data.get("content_type", ""),
            size=data.get("size", 0),
            storage_path=data.get("storage_path", ""),
            attachment_type=AttachmentType(data.get("attachment_type", "other")),
            uploaded_at=datetime.fromisoformat(data["uploaded_at"]) if "uploaded_at" in data else datetime.utcnow(),
            metadata=data.get("metadata", {})
        )


@dataclass
class ToolCall:
    """工具調用記錄

    記錄 Agent 調用工具的完整過程，包括參數、結果和審批狀態。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    status: ToolCallStatus = ToolCallStatus.PENDING
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def approve(self, approver_id: str) -> None:
        """批准工具調用

        Args:
            approver_id: 批准者 ID
        """
        if self.status != ToolCallStatus.PENDING:
            raise ValueError(f"Cannot approve tool call in status: {self.status}")
        self.status = ToolCallStatus.APPROVED
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()

    def reject(self, approver_id: str, reason: Optional[str] = None) -> None:
        """拒絕工具調用

        Args:
            approver_id: 拒絕者 ID
            reason: 拒絕原因
        """
        if self.status != ToolCallStatus.PENDING:
            raise ValueError(f"Cannot reject tool call in status: {self.status}")
        self.status = ToolCallStatus.REJECTED
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()
        if reason:
            self.error = reason

    def start_execution(self) -> None:
        """開始執行"""
        if self.status not in [ToolCallStatus.PENDING, ToolCallStatus.APPROVED]:
            raise ValueError(f"Cannot execute tool call in status: {self.status}")
        self.status = ToolCallStatus.RUNNING
        self.executed_at = datetime.utcnow()

    def complete(self, result: Dict[str, Any]) -> None:
        """完成執行

        Args:
            result: 執行結果
        """
        if self.status != ToolCallStatus.RUNNING:
            raise ValueError(f"Cannot complete tool call in status: {self.status}")
        self.status = ToolCallStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        """執行失敗

        Args:
            error: 錯誤訊息
        """
        if self.status != ToolCallStatus.RUNNING:
            raise ValueError(f"Cannot fail tool call in status: {self.status}")
        self.status = ToolCallStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "status": self.status.value,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        """從字典創建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            tool_name=data.get("tool_name", ""),
            arguments=data.get("arguments", {}),
            result=data.get("result"),
            status=ToolCallStatus(data.get("status", "pending")),
            requires_approval=data.get("requires_approval", False),
            approved_by=data.get("approved_by"),
            approved_at=datetime.fromisoformat(data["approved_at"]) if data.get("approved_at") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )


@dataclass
class Message:
    """對話訊息

    代表 Session 中的一條訊息，可以是用戶輸入、助手回覆、系統提示或工具回覆。
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    role: MessageRole = MessageRole.USER
    content: str = ""
    attachments: List[Attachment] = field(default_factory=list)
    tool_calls: List[ToolCall] = field(default_factory=list)
    parent_id: Optional[str] = None  # 支援分支對話
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_attachment(self, attachment: Attachment) -> None:
        """添加附件

        Args:
            attachment: 附件物件
        """
        self.attachments.append(attachment)

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """添加工具調用

        Args:
            tool_call: 工具調用物件
        """
        self.tool_calls.append(tool_call)

    def has_pending_tool_calls(self) -> bool:
        """檢查是否有待處理的工具調用"""
        return any(tc.status == ToolCallStatus.PENDING for tc in self.tool_calls)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role.value,
            "content": self.content,
            "attachments": [a.to_dict() for a in self.attachments],
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "parent_id": self.parent_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """從字典創建"""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            session_id=data.get("session_id", ""),
            role=MessageRole(data.get("role", "user")),
            content=data.get("content", ""),
            attachments=[Attachment.from_dict(a) for a in data.get("attachments", [])],
            tool_calls=[ToolCall.from_dict(tc) for tc in data.get("tool_calls", [])],
            parent_id=data.get("parent_id"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            metadata=data.get("metadata", {})
        )

    def to_llm_format(self) -> Dict[str, Any]:
        """轉換為 LLM API 格式"""
        msg = {
            "role": self.role.value,
            "content": self.content
        }

        # 處理附件 (如圖片)
        if self.attachments:
            content_parts = [{"type": "text", "text": self.content}]
            for att in self.attachments:
                if att.attachment_type == AttachmentType.IMAGE:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": att.storage_path}
                    })
            msg["content"] = content_parts

        return msg


@dataclass
class SessionConfig:
    """Session 配置

    定義 Session 的行為限制和功能開關。
    """
    max_messages: int = 100                          # 最大訊息數量
    max_attachments: int = 10                        # 最大附件數量
    max_attachment_size: int = 10 * 1024 * 1024      # 最大附件大小 (10MB)
    timeout_minutes: int = 60                        # 過期時間 (分鐘)
    enable_code_interpreter: bool = True             # 啟用程式碼解譯器
    enable_mcp_tools: bool = True                    # 啟用 MCP 工具
    enable_file_search: bool = True                  # 啟用檔案搜尋
    allowed_tools: List[str] = field(default_factory=list)  # 允許的工具 (空=全部)
    blocked_tools: List[str] = field(default_factory=list)  # 禁用的工具
    system_prompt_override: Optional[str] = None     # 覆蓋系統提示

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "max_messages": self.max_messages,
            "max_attachments": self.max_attachments,
            "max_attachment_size": self.max_attachment_size,
            "timeout_minutes": self.timeout_minutes,
            "enable_code_interpreter": self.enable_code_interpreter,
            "enable_mcp_tools": self.enable_mcp_tools,
            "enable_file_search": self.enable_file_search,
            "allowed_tools": self.allowed_tools,
            "blocked_tools": self.blocked_tools,
            "system_prompt_override": self.system_prompt_override
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionConfig":
        """從字典創建"""
        return cls(
            max_messages=data.get("max_messages", 100),
            max_attachments=data.get("max_attachments", 10),
            max_attachment_size=data.get("max_attachment_size", 10 * 1024 * 1024),
            timeout_minutes=data.get("timeout_minutes", 60),
            enable_code_interpreter=data.get("enable_code_interpreter", True),
            enable_mcp_tools=data.get("enable_mcp_tools", True),
            enable_file_search=data.get("enable_file_search", True),
            allowed_tools=data.get("allowed_tools", []),
            blocked_tools=data.get("blocked_tools", []),
            system_prompt_override=data.get("system_prompt_override")
        )

    def is_tool_allowed(self, tool_name: str) -> bool:
        """檢查工具是否允許

        Args:
            tool_name: 工具名稱

        Returns:
            bool: 是否允許
        """
        # 先檢查黑名單
        if tool_name in self.blocked_tools:
            return False
        # 如果有白名單，只允許白名單中的工具
        if self.allowed_tools:
            return tool_name in self.allowed_tools
        return True


@dataclass
class Session:
    """Session 模型

    代表一個互動式對話會話。管理對話生命週期、訊息和附件。

    狀態機:
        CREATED → ACTIVE → SUSPENDED → ENDED
                    ↓          ↑
                    └──────────┘
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    agent_id: str = ""
    status: SessionStatus = SessionStatus.CREATED
    config: SessionConfig = field(default_factory=SessionConfig)
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    title: Optional[str] = None  # 對話標題
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化後處理"""
        if self.expires_at is None and self.config:
            self.expires_at = self.created_at + timedelta(
                minutes=self.config.timeout_minutes
            )

    # ===== 狀態轉換 =====

    def activate(self) -> None:
        """激活 Session

        Raises:
            ValueError: 如果當前狀態不允許激活
        """
        if self.status not in [SessionStatus.CREATED, SessionStatus.SUSPENDED]:
            raise ValueError(f"Cannot activate session in status: {self.status}")
        if self.is_expired():
            raise ValueError("Session has expired")
        self.status = SessionStatus.ACTIVE
        self.updated_at = datetime.utcnow()
        self._extend_expiry()

    def suspend(self) -> None:
        """暫停 Session

        Raises:
            ValueError: 如果當前狀態不允許暫停
        """
        if self.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot suspend session in status: {self.status}")
        self.status = SessionStatus.SUSPENDED
        self.updated_at = datetime.utcnow()

    def resume(self) -> None:
        """恢復暫停的 Session

        Raises:
            ValueError: 如果當前狀態不允許恢復
        """
        if self.status != SessionStatus.SUSPENDED:
            raise ValueError(f"Cannot resume session in status: {self.status}")
        if self.is_expired():
            raise ValueError("Session has expired")
        self.status = SessionStatus.ACTIVE
        self.updated_at = datetime.utcnow()
        self._extend_expiry()

    def end(self) -> None:
        """結束 Session"""
        if self.status == SessionStatus.ENDED:
            return  # 已經結束，忽略
        self.status = SessionStatus.ENDED
        self.ended_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def is_expired(self) -> bool:
        """檢查是否過期

        Returns:
            bool: 是否已過期
        """
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_active(self) -> bool:
        """檢查是否處於活躍狀態

        Returns:
            bool: 是否活躍
        """
        return self.status == SessionStatus.ACTIVE and not self.is_expired()

    def can_accept_message(self) -> bool:
        """檢查是否可以接收新訊息

        Returns:
            bool: 是否可以接收訊息
        """
        if not self.is_active():
            return False
        if len(self.messages) >= self.config.max_messages:
            return False
        return True

    # ===== 訊息操作 =====

    def add_message(self, message: Message) -> None:
        """添加訊息

        Args:
            message: 訊息物件

        Raises:
            ValueError: 如果超過最大訊息數量
        """
        if len(self.messages) >= self.config.max_messages:
            raise ValueError(f"Maximum messages ({self.config.max_messages}) reached")

        message.session_id = self.id
        self.messages.append(message)
        self.updated_at = datetime.utcnow()
        self._extend_expiry()

        # 自動生成標題
        if self.title is None and message.role == MessageRole.USER:
            self._generate_title(message.content)

    def _generate_title(self, content: str) -> None:
        """從第一條用戶訊息生成標題

        Args:
            content: 訊息內容
        """
        # 取前 50 字元作為標題
        title = content[:50].strip()
        if len(content) > 50:
            title += "..."
        self.title = title

    def _extend_expiry(self) -> None:
        """延長過期時間"""
        if self.config:
            self.expires_at = datetime.utcnow() + timedelta(
                minutes=self.config.timeout_minutes
            )

    def get_conversation_history(
        self,
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Message]:
        """獲取對話歷史

        Args:
            limit: 最大訊息數量
            include_system: 是否包含系統訊息

        Returns:
            訊息列表
        """
        messages = self.messages
        if not include_system:
            messages = [m for m in messages if m.role != MessageRole.SYSTEM]
        if limit:
            messages = messages[-limit:]
        return messages

    def get_last_message(self) -> Optional[Message]:
        """獲取最後一條訊息

        Returns:
            最後一條訊息或 None
        """
        return self.messages[-1] if self.messages else None

    def get_message_count(self) -> int:
        """獲取訊息數量

        Returns:
            訊息數量
        """
        return len(self.messages)

    def get_attachment_count(self) -> int:
        """獲取附件總數

        Returns:
            附件數量
        """
        return sum(len(m.attachments) for m in self.messages)

    # ===== 序列化 =====

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "config": self.config.to_dict() if self.config else {},
            "messages": [m.to_dict() for m in self.messages],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "title": self.title,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """從字典創建"""
        config_data = data.get("config", {})
        config = SessionConfig.from_dict(config_data) if config_data else SessionConfig()

        session = cls(
            id=data.get("id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            agent_id=data.get("agent_id", ""),
            status=SessionStatus(data.get("status", "created")),
            config=config,
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            ended_at=datetime.fromisoformat(data["ended_at"]) if data.get("ended_at") else None,
            title=data.get("title"),
            metadata=data.get("metadata", {})
        )

        return session

    def to_llm_messages(self, include_system: bool = True) -> List[Dict[str, Any]]:
        """轉換為 LLM API 訊息格式

        Args:
            include_system: 是否包含系統訊息

        Returns:
            LLM 格式的訊息列表
        """
        messages = self.messages
        if not include_system:
            messages = [m for m in messages if m.role != MessageRole.SYSTEM]
        return [m.to_llm_format() for m in messages]

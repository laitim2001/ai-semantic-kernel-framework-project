"""
Session Database Models

SQLAlchemy ORM models for Session Mode API.
Includes SessionModel, MessageModel, and AttachmentModel.
"""

from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Integer,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin, UUIDMixin


class SessionModel(Base, UUIDMixin, TimestampMixin):
    """
    Session 數據庫模型

    Table: sessions
    """
    __tablename__ = "sessions"

    # 關聯欄位
    user_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    agent_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # 狀態欄位
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="created",
        index=True,
    )

    # 配置欄位
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # 時間欄位
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 標題
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )

    # 元數據 (使用 session_metadata 避免 SQLAlchemy 保留字衝突)
    session_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # 關聯
    messages: Mapped[List["MessageModel"]] = relationship(
        "MessageModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MessageModel.created_at",
    )

    attachments: Mapped[List["AttachmentModel"]] = relationship(
        "AttachmentModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # 索引
    __table_args__ = (
        Index("idx_sessions_user_status", "user_id", "status"),
        Index("idx_sessions_expires", "expires_at", postgresql_where=(status != "ended")),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, status={self.status})>"


class MessageModel(Base, UUIDMixin):
    """
    Message 數據庫模型

    Table: messages
    """
    __tablename__ = "messages"

    # 關聯欄位
    session_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 訊息欄位
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    # 分支支援
    parent_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 附件和工具調用 (JSON)
    attachments_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    tool_calls_json: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # 時間戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # 元數據 (使用 message_metadata 避免 SQLAlchemy 保留字衝突)
    message_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # 關聯
    session: Mapped["SessionModel"] = relationship(
        "SessionModel",
        back_populates="messages",
    )

    parent: Mapped[Optional["MessageModel"]] = relationship(
        "MessageModel",
        remote_side="MessageModel.id",
        foreign_keys=[parent_id],
    )

    # 索引
    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, session_id={self.session_id}, role={self.role})>"


class AttachmentModel(Base, UUIDMixin):
    """
    Attachment 數據庫模型

    Table: attachments
    """
    __tablename__ = "attachments"

    # 關聯欄位
    session_id: Mapped[uuid4] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id: Mapped[Optional[uuid4]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    # 文件資訊
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    attachment_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # 時間戳
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    # 元數據 (使用 attachment_metadata 避免 SQLAlchemy 保留字衝突)
    attachment_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )

    # 關聯
    session: Mapped["SessionModel"] = relationship(
        "SessionModel",
        back_populates="attachments",
    )

    def __repr__(self) -> str:
        return f"<Attachment(id={self.id}, filename={self.filename})>"

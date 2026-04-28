"""
Session Repository

Data access layer for Session domain models.
Implements PostgreSQL persistence with SQLAlchemy.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import asdict

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.sessions.models import (
    Session,
    SessionStatus,
    SessionConfig,
    Message,
    MessageRole,
    Attachment,
    ToolCall,
)
from src.infrastructure.database.models.session import (
    SessionModel,
    MessageModel,
    AttachmentModel,
)


class SessionRepository(ABC):
    """Session 存儲抽象類"""

    @abstractmethod
    async def create(self, session: Session) -> Session:
        """創建 Session"""
        pass

    @abstractmethod
    async def get(self, session_id: str) -> Optional[Session]:
        """獲取 Session"""
        pass

    @abstractmethod
    async def update(self, session: Session) -> Session:
        """更新 Session"""
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> bool:
        """刪除 Session"""
        pass

    @abstractmethod
    async def list_by_user(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """列出用戶的 Sessions"""
        pass

    @abstractmethod
    async def add_message(self, session_id: str, message: Message) -> Message:
        """添加訊息"""
        pass

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Message]:
        """獲取訊息"""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """清理過期 Sessions"""
        pass


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy Session Repository 實現"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(self, session: Session) -> Session:
        """創建 Session

        Args:
            session: Session 領域物件

        Returns:
            創建後的 Session
        """
        db_session = SessionModel(
            id=session.id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            status=session.status.value,
            config=session.config.to_dict() if session.config else {},
            created_at=session.created_at,
            updated_at=session.updated_at,
            expires_at=session.expires_at,
            title=session.title,
            session_metadata=session.metadata,
        )
        self._db.add(db_session)
        await self._db.commit()
        await self._db.refresh(db_session)
        return session

    async def get(self, session_id: str) -> Optional[Session]:
        """獲取 Session

        Args:
            session_id: Session ID

        Returns:
            Session 或 None
        """
        result = await self._db.execute(
            select(SessionModel)
            .where(SessionModel.id == session_id)
            .options(selectinload(SessionModel.messages))
        )
        db_session = result.scalar_one_or_none()
        if db_session is None:
            return None
        return self._to_domain(db_session)

    async def update(self, session: Session) -> Session:
        """更新 Session

        Args:
            session: Session 領域物件

        Returns:
            更新後的 Session
        """
        await self._db.execute(
            update(SessionModel)
            .where(SessionModel.id == session.id)
            .values(
                status=session.status.value,
                config=session.config.to_dict() if session.config else {},
                updated_at=session.updated_at,
                expires_at=session.expires_at,
                ended_at=session.ended_at,
                title=session.title,
                session_metadata=session.metadata,
            )
        )
        await self._db.commit()
        return session

    async def delete(self, session_id: str) -> bool:
        """刪除 Session

        Args:
            session_id: Session ID

        Returns:
            是否成功刪除
        """
        result = await self._db.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )
        await self._db.commit()
        return result.rowcount > 0

    async def list_by_user(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Session]:
        """列出用戶的 Sessions

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾
            limit: 返回數量限制
            offset: 跳過數量

        Returns:
            Session 列表
        """
        query = select(SessionModel).where(SessionModel.user_id == user_id)

        if status:
            query = query.where(SessionModel.status == status.value)

        query = query.order_by(SessionModel.updated_at.desc()).offset(offset).limit(limit)

        result = await self._db.execute(query)
        db_sessions = result.scalars().all()

        return [self._to_domain(s, include_messages=False) for s in db_sessions]

    async def add_message(self, session_id: str, message: Message) -> Message:
        """添加訊息

        Args:
            session_id: Session ID
            message: Message 領域物件

        Returns:
            創建後的 Message
        """
        db_message = MessageModel(
            id=message.id,
            session_id=session_id,
            role=message.role.value,
            content=message.content,
            parent_id=message.parent_id,
            attachments_json=[a.to_dict() for a in message.attachments],
            tool_calls_json=[tc.to_dict() for tc in message.tool_calls],
            created_at=message.created_at,
            message_metadata=message.metadata,
        )
        self._db.add(db_message)

        # 更新 Session 的 updated_at
        await self._db.execute(
            update(SessionModel)
            .where(SessionModel.id == session_id)
            .values(updated_at=datetime.utcnow())
        )

        await self._db.commit()
        await self._db.refresh(db_message)

        message.session_id = session_id
        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        before_id: Optional[str] = None,
    ) -> List[Message]:
        """獲取訊息

        Args:
            session_id: Session ID
            limit: 返回數量限制
            before_id: 在此 ID 之前的訊息

        Returns:
            Message 列表
        """
        query = select(MessageModel).where(MessageModel.session_id == session_id)

        if before_id:
            # 獲取 before_id 的創建時間
            before_result = await self._db.execute(
                select(MessageModel.created_at).where(MessageModel.id == before_id)
            )
            before_time = before_result.scalar_one_or_none()
            if before_time:
                query = query.where(MessageModel.created_at < before_time)

        query = query.order_by(MessageModel.created_at.desc()).limit(limit)
        result = await self._db.execute(query)
        db_messages = result.scalars().all()

        # 反轉以保持時間順序
        return [self._message_to_domain(m) for m in reversed(list(db_messages))]

    async def cleanup_expired(self) -> int:
        """清理過期 Sessions

        Returns:
            清理的 Session 數量
        """
        now = datetime.utcnow()
        result = await self._db.execute(
            update(SessionModel)
            .where(SessionModel.expires_at < now)
            .where(SessionModel.status != SessionStatus.ENDED.value)
            .values(
                status=SessionStatus.ENDED.value,
                ended_at=now,
                updated_at=now,
            )
        )
        await self._db.commit()
        return result.rowcount

    async def count_by_user(
        self,
        user_id: str,
        status: Optional[SessionStatus] = None,
    ) -> int:
        """計算用戶的 Session 數量

        Args:
            user_id: 用戶 ID
            status: 可選狀態過濾

        Returns:
            Session 數量
        """
        query = select(func.count(SessionModel.id)).where(
            SessionModel.user_id == user_id
        )
        if status:
            query = query.where(SessionModel.status == status.value)

        result = await self._db.execute(query)
        return result.scalar_one()

    async def get_active_sessions(self, limit: int = 100) -> List[Session]:
        """獲取活躍的 Sessions

        Args:
            limit: 返回數量限制

        Returns:
            Session 列表
        """
        result = await self._db.execute(
            select(SessionModel)
            .where(SessionModel.status == SessionStatus.ACTIVE.value)
            .order_by(SessionModel.updated_at.desc())
            .limit(limit)
        )
        db_sessions = result.scalars().all()
        return [self._to_domain(s, include_messages=False) for s in db_sessions]

    # ===== 私有方法 =====

    def _to_domain(
        self,
        db_session: SessionModel,
        include_messages: bool = True,
    ) -> Session:
        """將 DB 模型轉換為領域物件

        Args:
            db_session: SQLAlchemy 模型
            include_messages: 是否包含訊息

        Returns:
            Session 領域物件
        """
        config = SessionConfig.from_dict(db_session.config) if db_session.config else SessionConfig()

        messages = []
        if include_messages and db_session.messages:
            messages = [self._message_to_domain(m) for m in db_session.messages]

        return Session(
            id=str(db_session.id),
            user_id=str(db_session.user_id),
            agent_id=str(db_session.agent_id),
            status=SessionStatus(db_session.status),
            config=config,
            messages=messages,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            expires_at=db_session.expires_at,
            ended_at=db_session.ended_at,
            title=db_session.title,
            metadata=db_session.session_metadata or {},
        )

    def _message_to_domain(self, db_message: MessageModel) -> Message:
        """將 DB Message 轉換為領域物件

        Args:
            db_message: SQLAlchemy Message 模型

        Returns:
            Message 領域物件
        """
        attachments = [
            Attachment.from_dict(a)
            for a in (db_message.attachments_json or [])
        ]
        tool_calls = [
            ToolCall.from_dict(tc)
            for tc in (db_message.tool_calls_json or [])
        ]

        return Message(
            id=str(db_message.id),
            session_id=str(db_message.session_id),
            role=MessageRole(db_message.role),
            content=db_message.content,
            attachments=attachments,
            tool_calls=tool_calls,
            parent_id=str(db_message.parent_id) if db_message.parent_id else None,
            created_at=db_message.created_at,
            metadata=db_message.message_metadata or {},
        )

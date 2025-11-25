"""
User Model

Database model for users.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class User(BaseModel):
    """User model.

    Represents a platform user with authentication and authorization info.
    """

    __tablename__ = "users"

    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=True, index=True)
    is_superuser = Column(Boolean, default=False, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"

    @property
    def role(self) -> str:
        """Get user role based on is_superuser flag."""
        return "admin" if self.is_superuser else "user"

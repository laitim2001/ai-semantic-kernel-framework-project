# =============================================================================
# IPA Platform - Auth Schemas
# =============================================================================
# Sprint 70: S70-2 - UserRepository + AuthService
# Phase 18: Authentication System
#
# Pydantic schemas for authentication API requests and responses.
# =============================================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    full_name: Optional[str] = Field(None, max_length=255, description="User display name")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        # Add more complexity rules as needed
        return v


class UserLogin(BaseModel):
    """Schema for login request (alternative to OAuth2 form)."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserResponse(BaseModel):
    """Schema for user data in responses."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, description="User display name")
    role: str = Field(..., description="User role (admin, operator, viewer)")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema for authentication token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(default=3600, description="Token expiration in seconds")
    refresh_token: Optional[str] = Field(None, description="Optional refresh token")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""

    refresh_token: str = Field(..., description="Refresh token to exchange")


class PasswordChange(BaseModel):
    """Schema for password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 chars)")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

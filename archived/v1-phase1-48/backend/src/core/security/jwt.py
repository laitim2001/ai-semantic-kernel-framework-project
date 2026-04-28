# =============================================================================
# IPA Platform - JWT Token Management
# =============================================================================
# Sprint 70: S70-1 - JWT Utilities
# Phase 18: Authentication System
#
# JSON Web Token (JWT) creation and validation utilities.
# Uses HS256 algorithm with configurable secret key and expiration.
#
# Dependencies:
#   - python-jose[cryptography]
#   - Settings (src.core.config)
# =============================================================================

from datetime import datetime, timedelta
from typing import Optional

from jose import jwt, JWTError
from pydantic import BaseModel

from src.core.config import get_settings


class TokenPayload(BaseModel):
    """
    JWT token payload structure.

    Attributes:
        sub: Subject (user ID)
        role: User role (admin, operator, viewer)
        exp: Expiration timestamp
        iat: Issued at timestamp
    """

    sub: str
    role: str
    exp: datetime
    iat: datetime


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        role: User role to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token("user-123", "viewer")
        >>> # Returns: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string to decode

    Returns:
        TokenPayload with decoded claims

    Raises:
        ValueError: If token is invalid or expired

    Example:
        >>> payload = decode_token(token)
        >>> print(payload.sub)  # "user-123"
        >>> print(payload.role)  # "viewer"
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )

        return TokenPayload(
            sub=payload["sub"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
        )

    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")


def create_refresh_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Refresh tokens are valid for 7 days by default.

    Args:
        user_id: User ID to encode in token
        role: User role to encode in token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Refresh tokens last 7 days
        expire = datetime.utcnow() + timedelta(days=7)

    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",  # Distinguish from access tokens
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    return encoded_jwt

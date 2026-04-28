# =============================================================================
# IPA Platform - Global Auth Dependency Tests
# =============================================================================
# Sprint 123: S123-2 - Auth Module Tests
# Phase 33: Comprehensive Testing
#
# Unit tests for src.core.auth module.
# Tests lightweight JWT validation dependencies (require_auth,
# require_auth_optional) without database lookups.
#
# Dependencies:
#   - pytest
#   - pytest-asyncio
# =============================================================================

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError

from src.core.auth import require_auth, require_auth_optional

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "test-secret-key-for-auth-testing"
TEST_ALGORITHM = "HS256"


def _make_mock_settings() -> MagicMock:
    """Create a mock settings object with JWT configuration."""
    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = TEST_SECRET_KEY
    mock_settings.jwt_algorithm = TEST_ALGORITHM
    return mock_settings


def _make_credentials(token: str = "fake-token") -> MagicMock:
    """Create a mock HTTPAuthorizationCredentials."""
    creds = MagicMock()
    creds.credentials = token
    return creds


# ---------------------------------------------------------------------------
# TestRequireAuth
# ---------------------------------------------------------------------------


class TestRequireAuth:
    """Tests for require_auth dependency."""

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode")
    @patch("src.core.auth.get_settings")
    async def test_valid_token_returns_claims(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """A valid token returns a dict with user_id and role."""
        mock_get_settings.return_value = _make_mock_settings()
        mock_jwt_decode.return_value = {
            "sub": "user-123",
            "role": "admin",
            "email": "admin@test.com",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        result = await require_auth(credentials=_make_credentials("valid-token"))

        assert result["user_id"] == "user-123"
        assert result["role"] == "admin"
        assert result["email"] == "admin@test.com"

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode")
    @patch("src.core.auth.get_settings")
    async def test_missing_sub_raises_401(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """A token without 'sub' claim must raise HTTPException 401."""
        mock_get_settings.return_value = _make_mock_settings()
        mock_jwt_decode.return_value = {
            "role": "viewer",
            "exp": 9999999999,
            "iat": 1000000000,
            # "sub" is intentionally missing
        }

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(credentials=_make_credentials("token-no-sub"))

        assert exc_info.value.status_code == 401
        assert "missing user ID" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode", side_effect=JWTError("signature verification failed"))
    @patch("src.core.auth.get_settings")
    async def test_jwt_error_raises_401(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """A JWTError during decoding must raise HTTPException 401."""
        mock_get_settings.return_value = _make_mock_settings()

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(credentials=_make_credentials("corrupted-token"))

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode")
    @patch("src.core.auth.get_settings")
    async def test_returns_role_from_payload(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """The returned dict must include the role from the JWT payload."""
        mock_get_settings.return_value = _make_mock_settings()
        mock_jwt_decode.return_value = {
            "sub": "user-456",
            "role": "operator",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        result = await require_auth(credentials=_make_credentials("operator-token"))

        assert result["role"] == "operator"


# ---------------------------------------------------------------------------
# TestRequireAuthOptional
# ---------------------------------------------------------------------------


class TestRequireAuthOptional:
    """Tests for require_auth_optional dependency."""

    @pytest.mark.asyncio
    async def test_no_credentials_returns_none(self) -> None:
        """When no credentials are provided, return None (not raise)."""
        result = await require_auth_optional(credentials=None)

        assert result is None

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode")
    @patch("src.core.auth.get_settings")
    async def test_valid_token_returns_claims(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """With a valid token, returns the same claims dict as require_auth."""
        mock_get_settings.return_value = _make_mock_settings()
        mock_jwt_decode.return_value = {
            "sub": "user-789",
            "role": "viewer",
            "exp": 9999999999,
            "iat": 1000000000,
        }

        result = await require_auth_optional(credentials=_make_credentials("valid-optional"))

        assert result is not None
        assert result["user_id"] == "user-789"
        assert result["role"] == "viewer"

    @pytest.mark.asyncio
    @patch("src.core.auth.jwt.decode", side_effect=JWTError("bad token"))
    @patch("src.core.auth.get_settings")
    async def test_invalid_token_returns_none(
        self,
        mock_get_settings: MagicMock,
        mock_jwt_decode: MagicMock,
    ) -> None:
        """With an invalid token, return None instead of raising."""
        mock_get_settings.return_value = _make_mock_settings()

        result = await require_auth_optional(credentials=_make_credentials("bad-token"))

        assert result is None

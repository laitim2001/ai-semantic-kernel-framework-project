# =============================================================================
# IPA Platform - JWT Token Management Tests
# =============================================================================
# Sprint 123: S123-2 - Auth Module Tests
# Phase 33: Comprehensive Testing
#
# Unit tests for src.core.security.jwt module.
# Tests JWT token creation, decoding, and refresh token functionality.
#
# Dependencies:
#   - pytest
#   - python-jose[cryptography]
# =============================================================================

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt as jose_jwt

from src.core.security.jwt import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    decode_token,
)

# ---------------------------------------------------------------------------
# Shared test constants and fixtures
# ---------------------------------------------------------------------------

TEST_SECRET_KEY = "test-secret-key-for-jwt-testing-only"
TEST_ALGORITHM = "HS256"
TEST_EXPIRE_MINUTES = 30

TEST_USER_ID = "user-abc-123"
TEST_ROLE = "viewer"


def _make_mock_settings() -> MagicMock:
    """Create a mock settings object with JWT configuration."""
    mock_settings = MagicMock()
    mock_settings.jwt_secret_key = TEST_SECRET_KEY
    mock_settings.jwt_algorithm = TEST_ALGORITHM
    mock_settings.jwt_access_token_expire_minutes = TEST_EXPIRE_MINUTES
    return mock_settings


# ---------------------------------------------------------------------------
# TestCreateAccessToken
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    """Tests for create_access_token function."""

    @patch("src.core.security.jwt.get_settings")
    def test_creates_valid_jwt(self, mock_get_settings: MagicMock) -> None:
        """Token returned by create_access_token is a decodable JWT string."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_access_token(TEST_USER_ID, TEST_ROLE)

        assert isinstance(token, str)
        # Must be decodable without errors
        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        assert "sub" in payload
        assert "role" in payload
        assert "exp" in payload
        assert "iat" in payload

    @patch("src.core.security.jwt.get_settings")
    def test_token_contains_user_id(self, mock_get_settings: MagicMock) -> None:
        """The 'sub' claim must match the user_id argument."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_access_token(TEST_USER_ID, TEST_ROLE)

        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        assert payload["sub"] == TEST_USER_ID

    @patch("src.core.security.jwt.get_settings")
    def test_token_contains_role(self, mock_get_settings: MagicMock) -> None:
        """The 'role' claim must match the role argument."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_access_token(TEST_USER_ID, "admin")

        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        assert payload["role"] == "admin"

    @patch("src.core.security.jwt.get_settings")
    def test_custom_expiration(self, mock_get_settings: MagicMock) -> None:
        """When expires_delta is provided, the token expiration should match it."""
        mock_get_settings.return_value = _make_mock_settings()

        custom_delta = timedelta(minutes=5)
        before = datetime.utcnow()
        token = create_access_token(TEST_USER_ID, TEST_ROLE, expires_delta=custom_delta)
        after = datetime.utcnow()

        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        exp_dt = datetime.utcfromtimestamp(payload["exp"])

        # Expiration should be roughly (now + 5 minutes), within a 5-second tolerance
        assert exp_dt >= before + custom_delta - timedelta(seconds=5)
        assert exp_dt <= after + custom_delta + timedelta(seconds=5)

    @patch("src.core.security.jwt.get_settings")
    def test_default_expiration(self, mock_get_settings: MagicMock) -> None:
        """Without expires_delta, token uses settings.jwt_access_token_expire_minutes."""
        mock_get_settings.return_value = _make_mock_settings()

        before = datetime.utcnow()
        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        after = datetime.utcnow()

        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        exp_dt = datetime.utcfromtimestamp(payload["exp"])

        expected_delta = timedelta(minutes=TEST_EXPIRE_MINUTES)
        assert exp_dt >= before + expected_delta - timedelta(seconds=5)
        assert exp_dt <= after + expected_delta + timedelta(seconds=5)


# ---------------------------------------------------------------------------
# TestDecodeToken
# ---------------------------------------------------------------------------


class TestDecodeToken:
    """Tests for decode_token function."""

    @patch("src.core.security.jwt.get_settings")
    def test_decodes_valid_token(self, mock_get_settings: MagicMock) -> None:
        """A valid token should decode into a TokenPayload with correct fields."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_access_token(TEST_USER_ID, TEST_ROLE)
        payload = decode_token(token)

        assert isinstance(payload, TokenPayload)
        assert payload.sub == TEST_USER_ID
        assert payload.role == TEST_ROLE
        assert isinstance(payload.exp, datetime)
        assert isinstance(payload.iat, datetime)

    @patch("src.core.security.jwt.get_settings")
    def test_expired_token_raises_value_error(self, mock_get_settings: MagicMock) -> None:
        """An expired token must raise ValueError."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_access_token(
            TEST_USER_ID,
            TEST_ROLE,
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(token)

    @patch("src.core.security.jwt.get_settings")
    def test_invalid_token_raises_value_error(self, mock_get_settings: MagicMock) -> None:
        """A random string that is not a JWT must raise ValueError."""
        mock_get_settings.return_value = _make_mock_settings()

        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("not-a-valid-jwt-token")

    @patch("src.core.security.jwt.get_settings")
    def test_wrong_secret_raises_value_error(self, mock_get_settings: MagicMock) -> None:
        """A token signed with a different secret must raise ValueError on decode."""
        settings = _make_mock_settings()
        mock_get_settings.return_value = settings

        # Encode with a different secret
        payload = {
            "sub": TEST_USER_ID,
            "role": TEST_ROLE,
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
        }
        token_wrong_secret = jose_jwt.encode(
            payload, "completely-different-secret", algorithm=TEST_ALGORITHM
        )

        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(token_wrong_secret)


# ---------------------------------------------------------------------------
# TestCreateRefreshToken
# ---------------------------------------------------------------------------


class TestCreateRefreshToken:
    """Tests for create_refresh_token function."""

    @patch("src.core.security.jwt.get_settings")
    def test_creates_valid_jwt(self, mock_get_settings: MagicMock) -> None:
        """Refresh token is a decodable JWT string."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_refresh_token(TEST_USER_ID, TEST_ROLE)

        assert isinstance(token, str)
        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        assert payload["sub"] == TEST_USER_ID
        assert payload["role"] == TEST_ROLE

    @patch("src.core.security.jwt.get_settings")
    def test_refresh_token_has_type_claim(self, mock_get_settings: MagicMock) -> None:
        """Refresh token payload must contain 'type': 'refresh'."""
        mock_get_settings.return_value = _make_mock_settings()

        token = create_refresh_token(TEST_USER_ID, TEST_ROLE)

        raw_payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        assert raw_payload.get("type") == "refresh"

    @patch("src.core.security.jwt.get_settings")
    def test_default_7_day_expiration(self, mock_get_settings: MagicMock) -> None:
        """Without expires_delta, refresh token defaults to 7-day expiration."""
        mock_get_settings.return_value = _make_mock_settings()

        before = datetime.utcnow()
        token = create_refresh_token(TEST_USER_ID, TEST_ROLE)
        after = datetime.utcnow()

        payload = jose_jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        exp_dt = datetime.utcfromtimestamp(payload["exp"])

        expected_delta = timedelta(days=7)
        assert exp_dt >= before + expected_delta - timedelta(seconds=5)
        assert exp_dt <= after + expected_delta + timedelta(seconds=5)

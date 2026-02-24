# =============================================================================
# IPA Platform - AuthService Tests
# =============================================================================
# Sprint 123: S123-2 - Auth Module Tests
# Phase 33: Comprehensive Testing
#
# Unit tests for src.domain.auth.service.AuthService.
# All repository and security dependencies are mocked to isolate business logic.
#
# Dependencies:
#   - pytest
#   - pytest-asyncio
# =============================================================================

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.auth.service import AuthService


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_fake_user(
    user_id: str = "user-123",
    email: str = "test@test.com",
    role: str = "viewer",
    is_active: bool = True,
    hashed_password: str = "hashed-pw",
) -> MagicMock:
    """Create a fake User object for testing."""
    user = MagicMock()
    user.id = user_id
    user.email = email
    user.role = role
    user.is_active = is_active
    user.hashed_password = hashed_password
    return user


def _make_service_and_repo() -> tuple[AuthService, MagicMock]:
    """Create an AuthService with a fully-mocked UserRepository."""
    mock_repo = MagicMock()
    mock_repo.get = AsyncMock()
    mock_repo.create = AsyncMock()
    mock_repo.update = AsyncMock()
    mock_repo.get_active_by_email = AsyncMock()
    mock_repo.email_exists = AsyncMock()
    service = AuthService(user_repo=mock_repo)
    return service, mock_repo


# ---------------------------------------------------------------------------
# TestRegister
# ---------------------------------------------------------------------------


class TestRegister:
    """Tests for AuthService.register."""

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.create_access_token", return_value="access-token-abc")
    @patch("src.domain.auth.service.hash_password", return_value="hashed-new-password")
    async def test_register_success(
        self,
        mock_hash: MagicMock,
        mock_create_token: MagicMock,
    ) -> None:
        """Successful registration creates a user and returns (user, token)."""
        service, repo = _make_service_and_repo()
        fake_user = _make_fake_user()
        repo.email_exists.return_value = False
        repo.create.return_value = fake_user

        user, token = await service.register("new@test.com", "password123", "Test User")

        repo.email_exists.assert_awaited_once_with("new@test.com")
        repo.create.assert_awaited_once()
        create_kwargs = repo.create.call_args
        assert create_kwargs.kwargs["email"] == "new@test.com"
        assert create_kwargs.kwargs["hashed_password"] == "hashed-new-password"
        assert user is fake_user
        assert token == "access-token-abc"

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises(self) -> None:
        """Registering with an existing email must raise ValueError."""
        service, repo = _make_service_and_repo()
        repo.email_exists.return_value = True

        with pytest.raises(ValueError, match="Email already registered"):
            await service.register("existing@test.com", "password123")


# ---------------------------------------------------------------------------
# TestAuthenticate
# ---------------------------------------------------------------------------


class TestAuthenticate:
    """Tests for AuthService.authenticate."""

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.create_refresh_token", return_value="refresh-token-xyz")
    @patch("src.domain.auth.service.create_access_token", return_value="access-token-abc")
    @patch("src.domain.auth.service.verify_password", return_value=True)
    async def test_authenticate_success(
        self,
        mock_verify: MagicMock,
        mock_access: MagicMock,
        mock_refresh: MagicMock,
    ) -> None:
        """Successful authentication returns (user, access_token, refresh_token)."""
        service, repo = _make_service_and_repo()
        fake_user = _make_fake_user()
        repo.get_active_by_email.return_value = fake_user

        user, access_token, refresh_token = await service.authenticate(
            "test@test.com", "correct-password"
        )

        mock_verify.assert_called_once_with("correct-password", fake_user.hashed_password)
        assert user is fake_user
        assert access_token == "access-token-abc"
        assert refresh_token == "refresh-token-xyz"
        repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.verify_password", return_value=False)
    async def test_authenticate_wrong_password(self, mock_verify: MagicMock) -> None:
        """Wrong password must raise ValueError."""
        service, repo = _make_service_and_repo()
        repo.get_active_by_email.return_value = _make_fake_user()

        with pytest.raises(ValueError, match="Invalid credentials"):
            await service.authenticate("test@test.com", "wrong-password")

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self) -> None:
        """Non-existent email must raise ValueError."""
        service, repo = _make_service_and_repo()
        repo.get_active_by_email.return_value = None

        with pytest.raises(ValueError, match="Invalid credentials"):
            await service.authenticate("nobody@test.com", "any-password")


# ---------------------------------------------------------------------------
# TestGetUserFromToken
# ---------------------------------------------------------------------------


class TestGetUserFromToken:
    """Tests for AuthService.get_user_from_token."""

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.decode_token")
    async def test_get_user_success(self, mock_decode: MagicMock) -> None:
        """Valid token for an active user returns the User."""
        service, repo = _make_service_and_repo()
        fake_user = _make_fake_user()
        mock_decode.return_value = MagicMock(sub="user-123")
        repo.get.return_value = fake_user

        user = await service.get_user_from_token("valid-token")

        mock_decode.assert_called_once_with("valid-token")
        repo.get.assert_awaited_once_with("user-123")
        assert user is fake_user

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.decode_token", side_effect=ValueError("Invalid token"))
    async def test_invalid_token_raises(self, mock_decode: MagicMock) -> None:
        """Invalid token must raise ValueError."""
        service, repo = _make_service_and_repo()

        with pytest.raises(ValueError, match="Invalid token"):
            await service.get_user_from_token("bad-token")

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.decode_token")
    async def test_user_not_found_raises(self, mock_decode: MagicMock) -> None:
        """Token for a non-existent user must raise ValueError."""
        service, repo = _make_service_and_repo()
        mock_decode.return_value = MagicMock(sub="deleted-user")
        repo.get.return_value = None

        with pytest.raises(ValueError, match="User not found"):
            await service.get_user_from_token("valid-token-deleted-user")

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.decode_token")
    async def test_inactive_user_raises(self, mock_decode: MagicMock) -> None:
        """Token for an inactive user must raise ValueError."""
        service, repo = _make_service_and_repo()
        mock_decode.return_value = MagicMock(sub="user-123")
        repo.get.return_value = _make_fake_user(is_active=False)

        with pytest.raises(ValueError, match="inactive"):
            await service.get_user_from_token("valid-token-inactive-user")


# ---------------------------------------------------------------------------
# TestRefreshAccessToken
# ---------------------------------------------------------------------------


class TestRefreshAccessToken:
    """Tests for AuthService.refresh_access_token."""

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.create_refresh_token", return_value="new-refresh-token")
    @patch("src.domain.auth.service.create_access_token", return_value="new-access-token")
    @patch("src.domain.auth.service.decode_token")
    async def test_refresh_success(
        self,
        mock_decode: MagicMock,
        mock_access: MagicMock,
        mock_refresh: MagicMock,
    ) -> None:
        """Valid refresh token returns new (access_token, refresh_token)."""
        service, repo = _make_service_and_repo()
        mock_decode.return_value = MagicMock(sub="user-123")
        repo.get.return_value = _make_fake_user()

        access_token, refresh_token = await service.refresh_access_token("old-refresh-token")

        assert access_token == "new-access-token"
        assert refresh_token == "new-refresh-token"

    @pytest.mark.asyncio
    @patch(
        "src.domain.auth.service.decode_token",
        side_effect=ValueError("Invalid token"),
    )
    async def test_invalid_refresh_token_raises(self, mock_decode: MagicMock) -> None:
        """Invalid refresh token must raise ValueError."""
        service, repo = _make_service_and_repo()

        with pytest.raises(ValueError, match="Invalid refresh token"):
            await service.refresh_access_token("bad-refresh-token")

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.decode_token")
    async def test_inactive_user_raises(self, mock_decode: MagicMock) -> None:
        """Refresh for an inactive user must raise ValueError."""
        service, repo = _make_service_and_repo()
        mock_decode.return_value = MagicMock(sub="user-123")
        repo.get.return_value = _make_fake_user(is_active=False)

        with pytest.raises(ValueError, match="User not found or inactive"):
            await service.refresh_access_token("refresh-token-inactive")


# ---------------------------------------------------------------------------
# TestChangePassword
# ---------------------------------------------------------------------------


class TestChangePassword:
    """Tests for AuthService.change_password."""

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.hash_password", return_value="hashed-new-pw")
    @patch("src.domain.auth.service.verify_password", return_value=True)
    async def test_change_password_success(
        self,
        mock_verify: MagicMock,
        mock_hash: MagicMock,
    ) -> None:
        """Correct current password allows changing to new password."""
        service, repo = _make_service_and_repo()
        repo.get.return_value = _make_fake_user()

        result = await service.change_password("user-123", "current-pw", "new-pw")

        assert result is True
        mock_verify.assert_called_once_with("current-pw", "hashed-pw")
        mock_hash.assert_called_once_with("new-pw")
        repo.update.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.domain.auth.service.verify_password", return_value=False)
    async def test_wrong_current_password_raises(self, mock_verify: MagicMock) -> None:
        """Wrong current password must raise ValueError."""
        service, repo = _make_service_and_repo()
        repo.get.return_value = _make_fake_user()

        with pytest.raises(ValueError, match="Current password is incorrect"):
            await service.change_password("user-123", "wrong-pw", "new-pw")

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self) -> None:
        """Non-existent user must raise ValueError."""
        service, repo = _make_service_and_repo()
        repo.get.return_value = None

        with pytest.raises(ValueError, match="User not found"):
            await service.change_password("ghost-user", "any-pw", "new-pw")

# =============================================================================
# IPA Platform - Rate Limiting Tests
# =============================================================================
# Sprint 123: S123-2 - Auth Module Tests
# Phase 33: Comprehensive Testing
#
# Unit tests for src.middleware.rate_limit module.
# Tests default rate limit calculation and app setup.
#
# Dependencies:
#   - pytest
#   - slowapi
# =============================================================================

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_settings(app_env: str = "development") -> MagicMock:
    """Create a mock settings object with app_env configuration."""
    mock_settings = MagicMock()
    mock_settings.app_env = app_env
    return mock_settings


# ---------------------------------------------------------------------------
# TestGetDefaultLimit
# ---------------------------------------------------------------------------


class TestGetDefaultLimit:
    """Tests for _get_default_limit function."""

    @patch("src.middleware.rate_limit.get_settings")
    def test_development_returns_1000(self, mock_get_settings: MagicMock) -> None:
        """Development environment should return '1000/minute'."""
        mock_get_settings.return_value = _make_mock_settings(app_env="development")

        # Re-import to invoke the patched version
        from src.middleware.rate_limit import _get_default_limit

        result = _get_default_limit()

        assert result == "1000/minute"

    @patch("src.middleware.rate_limit.get_settings")
    def test_production_returns_100(self, mock_get_settings: MagicMock) -> None:
        """Production environment should return '100/minute'."""
        mock_get_settings.return_value = _make_mock_settings(app_env="production")

        from src.middleware.rate_limit import _get_default_limit

        result = _get_default_limit()

        assert result == "100/minute"


# ---------------------------------------------------------------------------
# TestSetupRateLimiting
# ---------------------------------------------------------------------------


class TestSetupRateLimiting:
    """Tests for setup_rate_limiting function."""

    @patch("src.middleware.rate_limit.get_settings")
    def test_attaches_limiter_to_app_state(self, mock_get_settings: MagicMock) -> None:
        """setup_rate_limiting must set app.state.limiter."""
        mock_get_settings.return_value = _make_mock_settings()

        from src.middleware.rate_limit import setup_rate_limiting

        app = FastAPI()
        setup_rate_limiting(app)

        assert hasattr(app.state, "limiter")
        assert app.state.limiter is not None

    @patch("src.middleware.rate_limit.get_settings")
    def test_adds_exception_handler(self, mock_get_settings: MagicMock) -> None:
        """setup_rate_limiting must register a RateLimitExceeded exception handler."""
        mock_get_settings.return_value = _make_mock_settings()

        from src.middleware.rate_limit import setup_rate_limiting

        app = FastAPI()
        setup_rate_limiting(app)

        # FastAPI stores exception handlers in a dict keyed by exception class.
        # The app.exception_handlers dict should contain our RateLimitExceeded handler.
        assert RateLimitExceeded in app.exception_handlers

"""Unit tests for sensitive information filter.

Sprint 122, Story 122-3: Tests SensitiveInfoFilter for proper masking
of passwords, tokens, API keys, and other credentials.
"""

import pytest

from src.core.logging.filters import (
    SensitiveInfoFilter,
    _is_sensitive_key,
    _mask_dict,
    _mask_value,
    _MASK,
)


class TestIsSensitiveKey:
    """Tests for _is_sensitive_key() function."""

    @pytest.mark.parametrize(
        "key",
        [
            "password",
            "PASSWORD",
            "db_password",
            "user_password",
            "secret",
            "SECRET_KEY",
            "app_secret",
            "token",
            "access_token",
            "refresh_token",
            "api_key",
            "API_KEY",
            "apikey",
            "APIKEY",
            "authorization",
            "AUTHORIZATION",
            "credential",
            "credentials",
            "private_key",
            "PRIVATE_KEY",
            "access_key",
            "ACCESS_KEY",
            "connection_string",
            "CONNECTION_STRING",
        ],
    )
    def test_detects_sensitive_keys(self, key: str):
        """Should detect known sensitive key patterns."""
        assert _is_sensitive_key(key) is True

    @pytest.mark.parametrize(
        "key",
        [
            "username",
            "email",
            "agent_id",
            "session_id",
            "status",
            "event",
            "level",
            "timestamp",
            "message",
            "duration_ms",
            "request_id",
        ],
    )
    def test_allows_non_sensitive_keys(self, key: str):
        """Should not flag non-sensitive keys."""
        assert _is_sensitive_key(key) is False


class TestMaskValue:
    """Tests for _mask_value() function."""

    def test_masks_string_value(self):
        """Should replace string with REDACTED mask."""
        assert _mask_value("my-secret-password") == _MASK

    def test_masks_integer_value(self):
        """Should mask integer values."""
        assert _mask_value(12345) == _MASK

    def test_preserves_none(self):
        """Should not mask None values."""
        assert _mask_value(None) is None

    def test_preserves_empty_string(self):
        """Should not mask empty strings."""
        assert _mask_value("") == ""


class TestMaskDict:
    """Tests for _mask_dict() function."""

    def test_masks_sensitive_fields(self):
        """Should mask values of sensitive keys."""
        data = {
            "username": "admin",
            "password": "secret123",
            "api_key": "sk-abcdef",
        }
        result = _mask_dict(data)
        assert result["username"] == "admin"
        assert result["password"] == _MASK
        assert result["api_key"] == _MASK

    def test_preserves_non_sensitive_fields(self):
        """Should not modify non-sensitive fields."""
        data = {
            "event": "login",
            "user_id": "user-123",
            "status": "success",
        }
        result = _mask_dict(data)
        assert result == data

    def test_masks_nested_dicts(self):
        """Should recursively mask nested dictionaries."""
        data = {
            "user": "admin",
            "config": {
                "db_password": "pg-secret",
                "host": "localhost",
            },
        }
        result = _mask_dict(data)
        assert result["user"] == "admin"
        assert result["config"]["db_password"] == _MASK
        assert result["config"]["host"] == "localhost"

    def test_masks_in_list_elements(self):
        """Should mask sensitive fields in list elements."""
        data = {
            "connections": [
                {"host": "db1", "password": "pass1"},
                {"host": "db2", "password": "pass2"},
            ]
        }
        result = _mask_dict(data)
        assert result["connections"][0]["host"] == "db1"
        assert result["connections"][0]["password"] == _MASK
        assert result["connections"][1]["password"] == _MASK

    def test_handles_empty_dict(self):
        """Should handle empty dictionaries."""
        assert _mask_dict({}) == {}

    def test_does_not_mutate_original(self):
        """Should return a new dict, not mutate the original."""
        original = {"password": "secret", "user": "admin"}
        result = _mask_dict(original)
        assert original["password"] == "secret"
        assert result["password"] == _MASK


class TestSensitiveInfoFilter:
    """Tests for SensitiveInfoFilter structlog processor."""

    def setup_method(self):
        """Create filter instance."""
        self.filter = SensitiveInfoFilter()

    def test_masks_sensitive_event_fields(self):
        """Should mask sensitive fields in event_dict."""
        event_dict = {
            "event": "db_connection",
            "password": "secret123",
            "host": "localhost",
        }
        result = self.filter(None, "info", event_dict)
        assert result["event"] == "db_connection"
        assert result["password"] == _MASK
        assert result["host"] == "localhost"

    def test_masks_authorization_header(self):
        """Should mask authorization fields."""
        event_dict = {
            "event": "api_call",
            "authorization": "Bearer sk-xxxxx",
        }
        result = self.filter(None, "info", event_dict)
        assert result["authorization"] == _MASK

    def test_masks_connection_string(self):
        """Should mask connection string fields."""
        event_dict = {
            "event": "init",
            "connection_string": "InstrumentationKey=abc123",
        }
        result = self.filter(None, "info", event_dict)
        assert result["connection_string"] == _MASK

    def test_preserves_standard_log_fields(self):
        """Should not mask standard log fields."""
        event_dict = {
            "event": "request_completed",
            "level": "info",
            "timestamp": "2026-02-24T10:00:00Z",
            "request_id": "req-123",
            "logger": "src.api.agents",
            "duration_ms": 150,
        }
        result = self.filter(None, "info", event_dict)
        assert result == event_dict

    def test_handles_complex_nested_structure(self):
        """Should handle deeply nested structures."""
        event_dict = {
            "event": "config_loaded",
            "config": {
                "database": {
                    "host": "localhost",
                    "password": "db-secret",
                    "settings": {
                        "connection_string": "pg://...",
                    },
                },
            },
        }
        result = self.filter(None, "info", event_dict)
        assert result["config"]["database"]["host"] == "localhost"
        assert result["config"]["database"]["password"] == _MASK
        assert result["config"]["database"]["settings"]["connection_string"] == _MASK

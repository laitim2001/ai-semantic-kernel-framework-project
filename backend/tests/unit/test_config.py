"""
Configuration Tests

Tests for application configuration.
"""
import os

import pytest


def test_settings_default_values():
    """Test that settings have sensible defaults."""
    from src.core.config import Settings

    # Create settings without environment variables
    settings = Settings(
        _env_file=None,  # Disable .env file loading for this test
    )

    assert settings.app_env == "development"
    assert settings.db_host == "localhost"
    assert settings.db_port == 5432
    assert settings.redis_host == "localhost"
    assert settings.redis_port == 6379


def test_database_url_property():
    """Test database URL construction."""
    from src.core.config import Settings

    settings = Settings(
        _env_file=None,
        db_host="testhost",
        db_port=5432,
        db_name="testdb",
        db_user="testuser",
        db_password="testpass",
    )

    assert "postgresql+asyncpg://" in settings.database_url
    assert "testuser:testpass" in settings.database_url
    assert "testhost:5432/testdb" in settings.database_url


def test_redis_url_property_with_password():
    """Test Redis URL construction with password."""
    from src.core.config import Settings

    settings = Settings(
        _env_file=None,
        redis_host="redishost",
        redis_port=6379,
        redis_password="redispass",
    )

    assert "redis://:redispass@redishost:6379" == settings.redis_url


def test_redis_url_property_without_password():
    """Test Redis URL construction without password."""
    from src.core.config import Settings

    settings = Settings(
        _env_file=None,
        redis_host="redishost",
        redis_port=6379,
        redis_password="",
    )

    assert "redis://redishost:6379" == settings.redis_url


def test_cors_origins_list():
    """Test CORS origins parsing."""
    from src.core.config import Settings

    settings = Settings(
        _env_file=None,
        cors_origins="http://localhost:3000, http://localhost:8000 , http://example.com",
    )

    origins = settings.cors_origins_list
    assert len(origins) == 3
    assert "http://localhost:3000" in origins
    assert "http://localhost:8000" in origins
    assert "http://example.com" in origins


def test_azure_openai_configured():
    """Test Azure OpenAI configuration check."""
    from src.core.config import Settings

    # Not configured
    settings_unconfigured = Settings(
        _env_file=None,
        azure_openai_endpoint="",
        azure_openai_api_key="",
    )
    assert settings_unconfigured.is_azure_openai_configured is False

    # Configured
    settings_configured = Settings(
        _env_file=None,
        azure_openai_endpoint="https://test.openai.azure.com/",
        azure_openai_api_key="test-key",
    )
    assert settings_configured.is_azure_openai_configured is True


def test_log_level_validation():
    """Test log level validation."""
    from src.core.config import Settings

    # Valid log levels
    for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        settings = Settings(_env_file=None, log_level=level)
        assert settings.log_level == level

    # Case insensitive
    settings = Settings(_env_file=None, log_level="debug")
    assert settings.log_level == "DEBUG"

    # Invalid log level
    with pytest.raises(ValueError):
        Settings(_env_file=None, log_level="INVALID")

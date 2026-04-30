"""Unit tests for ServerConfig — Sprint 117.

Tests environment-aware server configuration for development,
staging, and production environments.

47 tests covering:
- ServerEnvironment enum (5 tests)
- ServerConfig default values (6 tests)
- Development environment (5 tests)
- Staging environment (5 tests)
- Production environment (5 tests)
- Environment variable overrides (8 tests)
- Worker count limits (5 tests)
- Serialization and repr (4 tests)
- Edge cases and error handling (4 tests)
"""

import multiprocessing
import os
from unittest.mock import patch

import pytest

from src.core.server_config import ServerConfig, ServerEnvironment


# =============================================================================
# ServerEnvironment Enum Tests
# =============================================================================


class TestServerEnvironment:
    """Tests for ServerEnvironment enum."""

    def test_development_value(self) -> None:
        """Development enum has correct string value."""
        assert ServerEnvironment.DEVELOPMENT.value == "development"

    def test_staging_value(self) -> None:
        """Staging enum has correct string value."""
        assert ServerEnvironment.STAGING.value == "staging"

    def test_production_value(self) -> None:
        """Production enum has correct string value."""
        assert ServerEnvironment.PRODUCTION.value == "production"

    def test_is_str_subclass(self) -> None:
        """ServerEnvironment is a str enum for JSON serialization."""
        assert isinstance(ServerEnvironment.DEVELOPMENT, str)
        assert ServerEnvironment.DEVELOPMENT == "development"

    def test_all_values(self) -> None:
        """All three environments are defined."""
        values = [e.value for e in ServerEnvironment]
        assert sorted(values) == ["development", "production", "staging"]


# =============================================================================
# ServerConfig Default Values
# =============================================================================


class TestServerConfigDefaults:
    """Tests for ServerConfig default values."""

    @patch.dict(os.environ, {}, clear=True)
    def test_default_environment_is_development(self) -> None:
        """Without SERVER_ENV, defaults to development."""
        config = ServerConfig()
        assert config.environment == ServerEnvironment.DEVELOPMENT

    @patch.dict(os.environ, {}, clear=True)
    def test_default_host(self) -> None:
        """Default host is 0.0.0.0."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"

    @patch.dict(os.environ, {}, clear=True)
    def test_default_port(self) -> None:
        """Default port is 8000."""
        config = ServerConfig()
        assert config.port == 8000

    @patch.dict(os.environ, {}, clear=True)
    def test_default_worker_class(self) -> None:
        """Worker class is always UvicornWorker."""
        config = ServerConfig()
        assert config.worker_class == "uvicorn.workers.UvicornWorker"

    @patch.dict(os.environ, {}, clear=True)
    def test_default_bind(self) -> None:
        """Default bind string combines host and port."""
        config = ServerConfig()
        assert config.bind == "0.0.0.0:8000"

    @patch.dict(os.environ, {}, clear=True)
    def test_explicit_env_parameter(self) -> None:
        """Explicit env parameter overrides environment variable."""
        config = ServerConfig(env="production")
        assert config.environment == ServerEnvironment.PRODUCTION


# =============================================================================
# Development Environment
# =============================================================================


class TestDevelopmentConfig:
    """Tests for development environment configuration."""

    def test_single_worker(self) -> None:
        """Development always uses 1 worker."""
        config = ServerConfig(env="development")
        assert config.workers == 1

    def test_reload_enabled(self) -> None:
        """Hot-reload enabled in development."""
        config = ServerConfig(env="development")
        assert config.reload is True

    @patch.dict(os.environ, {}, clear=True)
    def test_debug_log_level(self) -> None:
        """Development defaults to debug log level."""
        config = ServerConfig(env="development")
        assert config.log_level == "debug"

    def test_access_log_enabled(self) -> None:
        """Access logging enabled in development."""
        config = ServerConfig(env="development")
        assert config.access_log is True

    def test_is_development_flag(self) -> None:
        """is_development returns True."""
        config = ServerConfig(env="development")
        assert config.is_development is True
        assert config.is_production is False


# =============================================================================
# Staging Environment
# =============================================================================


class TestStagingConfig:
    """Tests for staging environment configuration."""

    def test_multi_worker(self) -> None:
        """Staging uses multiple workers."""
        config = ServerConfig(env="staging")
        assert config.workers > 1 or multiprocessing.cpu_count() == 1

    def test_reload_disabled(self) -> None:
        """Hot-reload disabled in staging."""
        config = ServerConfig(env="staging")
        assert config.reload is False

    @patch.dict(os.environ, {}, clear=True)
    def test_info_log_level(self) -> None:
        """Staging defaults to info log level."""
        config = ServerConfig(env="staging")
        assert config.log_level == "info"

    def test_access_log_enabled(self) -> None:
        """Access logging enabled in staging."""
        config = ServerConfig(env="staging")
        assert config.access_log is True

    def test_not_development_or_production(self) -> None:
        """Staging is neither development nor production."""
        config = ServerConfig(env="staging")
        assert config.is_development is False
        assert config.is_production is False


# =============================================================================
# Production Environment
# =============================================================================


class TestProductionConfig:
    """Tests for production environment configuration."""

    def test_multi_worker(self) -> None:
        """Production uses multiple workers."""
        config = ServerConfig(env="production")
        assert config.workers > 1 or multiprocessing.cpu_count() == 1

    def test_reload_disabled(self) -> None:
        """Hot-reload disabled in production."""
        config = ServerConfig(env="production")
        assert config.reload is False

    @patch.dict(os.environ, {}, clear=True)
    def test_info_log_level(self) -> None:
        """Production defaults to info log level."""
        config = ServerConfig(env="production")
        assert config.log_level == "info"

    def test_access_log_disabled(self) -> None:
        """Access logging disabled in production for performance."""
        config = ServerConfig(env="production")
        assert config.access_log is False

    def test_is_production_flag(self) -> None:
        """is_production returns True."""
        config = ServerConfig(env="production")
        assert config.is_production is True
        assert config.is_development is False


# =============================================================================
# Environment Variable Overrides
# =============================================================================


class TestEnvironmentOverrides:
    """Tests for environment variable override behavior."""

    @patch.dict(os.environ, {"SERVER_ENV": "staging"})
    def test_server_env_from_env(self) -> None:
        """SERVER_ENV environment variable sets environment."""
        config = ServerConfig()
        assert config.environment == ServerEnvironment.STAGING

    @patch.dict(os.environ, {"SERVER_HOST": "127.0.0.1"})
    def test_host_override(self) -> None:
        """SERVER_HOST overrides default host."""
        config = ServerConfig(env="development")
        assert config.host == "127.0.0.1"

    @patch.dict(os.environ, {"SERVER_PORT": "9000"})
    def test_port_override(self) -> None:
        """SERVER_PORT overrides default port."""
        config = ServerConfig(env="development")
        assert config.port == 9000

    @patch.dict(os.environ, {"UVICORN_WORKERS": "6"})
    def test_workers_override_in_production(self) -> None:
        """UVICORN_WORKERS overrides calculated worker count."""
        config = ServerConfig(env="production")
        assert config.workers == 6

    @patch.dict(os.environ, {"UVICORN_WORKERS": "6"})
    def test_workers_override_ignored_in_development(self) -> None:
        """UVICORN_WORKERS is ignored in development (always 1)."""
        config = ServerConfig(env="development")
        assert config.workers == 1

    @patch.dict(os.environ, {"LOG_LEVEL": "warning"})
    def test_log_level_override(self) -> None:
        """LOG_LEVEL overrides default log level."""
        config = ServerConfig(env="production")
        assert config.log_level == "warning"

    @patch.dict(os.environ, {"LOG_LEVEL": "WARNING"})
    def test_log_level_normalized_to_lowercase(self) -> None:
        """LOG_LEVEL is normalized to lowercase."""
        config = ServerConfig(env="production")
        assert config.log_level == "warning"

    @patch.dict(os.environ, {"SERVER_HOST": "10.0.0.1", "SERVER_PORT": "3000"})
    def test_bind_reflects_overrides(self) -> None:
        """Bind string reflects host/port overrides."""
        config = ServerConfig(env="development")
        assert config.bind == "10.0.0.1:3000"


# =============================================================================
# Worker Count Limits
# =============================================================================


class TestWorkerLimits:
    """Tests for worker count boundary conditions."""

    @patch.dict(os.environ, {"UVICORN_WORKERS": "0"})
    def test_minimum_worker_count(self) -> None:
        """Worker count cannot go below 1."""
        config = ServerConfig(env="production")
        assert config.workers >= 1

    @patch.dict(os.environ, {"UVICORN_WORKERS": "100"})
    def test_maximum_worker_override(self) -> None:
        """UVICORN_WORKERS capped at 32."""
        config = ServerConfig(env="production")
        assert config.workers <= 32

    @patch("multiprocessing.cpu_count", return_value=16)
    @patch.dict(os.environ, {}, clear=True)
    def test_auto_workers_capped_at_8(self, mock_cpu: object) -> None:
        """Auto-calculated workers capped at 8 (CPU*2+1 would be 33)."""
        config = ServerConfig(env="production")
        assert config.workers == 8

    @patch("multiprocessing.cpu_count", return_value=2)
    @patch.dict(os.environ, {}, clear=True)
    def test_auto_workers_formula(self, mock_cpu: object) -> None:
        """Auto-calculated workers = CPU * 2 + 1."""
        config = ServerConfig(env="production")
        assert config.workers == 5  # 2 * 2 + 1 = 5

    @patch("multiprocessing.cpu_count", return_value=1)
    @patch.dict(os.environ, {}, clear=True)
    def test_single_cpu_workers(self, mock_cpu: object) -> None:
        """Single CPU gets 3 workers (1 * 2 + 1)."""
        config = ServerConfig(env="production")
        assert config.workers == 3


# =============================================================================
# Serialization and Repr
# =============================================================================


class TestSerialization:
    """Tests for to_dict() and __repr__."""

    @patch.dict(os.environ, {}, clear=True)
    def test_to_dict_keys(self) -> None:
        """to_dict includes all configuration keys."""
        config = ServerConfig(env="development")
        d = config.to_dict()
        expected_keys = {
            "environment",
            "workers",
            "reload",
            "host",
            "port",
            "log_level",
            "access_log",
            "worker_class",
            "bind",
        }
        assert set(d.keys()) == expected_keys

    @patch.dict(os.environ, {}, clear=True)
    def test_to_dict_development_values(self) -> None:
        """to_dict returns correct development values."""
        config = ServerConfig(env="development")
        d = config.to_dict()
        assert d["environment"] == "development"
        assert d["workers"] == 1
        assert d["reload"] is True
        assert d["log_level"] == "debug"

    @patch.dict(os.environ, {}, clear=True)
    def test_to_dict_production_values(self) -> None:
        """to_dict returns correct production values."""
        config = ServerConfig(env="production")
        d = config.to_dict()
        assert d["environment"] == "production"
        assert d["reload"] is False
        assert d["access_log"] is False

    def test_repr_format(self) -> None:
        """__repr__ shows environment, workers, reload, bind."""
        config = ServerConfig(env="development")
        r = repr(config)
        assert "development" in r
        assert "workers=1" in r
        assert "reload=True" in r


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and invalid inputs."""

    def test_invalid_env_falls_back_to_development(self) -> None:
        """Invalid environment string falls back to development."""
        config = ServerConfig(env="invalid_env")
        assert config.environment == ServerEnvironment.DEVELOPMENT

    @patch.dict(os.environ, {"SERVER_PORT": "not_a_number"})
    def test_invalid_port_falls_back_to_default(self) -> None:
        """Non-numeric SERVER_PORT falls back to 8000."""
        config = ServerConfig(env="development")
        assert config.port == 8000

    @patch.dict(os.environ, {"UVICORN_WORKERS": "not_a_number"})
    @patch("multiprocessing.cpu_count", return_value=2)
    def test_invalid_workers_falls_back_to_auto(self, mock_cpu: object) -> None:
        """Non-numeric UVICORN_WORKERS falls back to auto-calculation."""
        config = ServerConfig(env="production")
        assert config.workers == 5  # 2 * 2 + 1

    @patch.dict(os.environ, {"SERVER_ENV": "PRODUCTION"})
    def test_case_insensitive_env(self) -> None:
        """SERVER_ENV is case-insensitive."""
        config = ServerConfig()
        assert config.environment == ServerEnvironment.PRODUCTION

"""
Application Configuration

Centralized configuration management using Pydantic Settings.
Supports environment variables and .env files.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str = "change-this-to-a-secure-random-string"

    # ==========================================================================
    # Database (PostgreSQL)
    # ==========================================================================
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ipa_platform"
    db_user: str = "ipa_user"
    db_password: str = ""

    @property
    def database_url(self) -> str:
        """Async database URL for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def database_url_sync(self) -> str:
        """Sync database URL for Alembic migrations."""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}"
        return f"redis://{self.redis_host}:{self.redis_port}"

    # ==========================================================================
    # RabbitMQ (Local Development)
    # ==========================================================================
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"

    @property
    def rabbitmq_url(self) -> str:
        """RabbitMQ connection URL."""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )

    # ==========================================================================
    # Azure OpenAI (Required for Agent Framework)
    # ==========================================================================
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-15-preview"

    @property
    def is_azure_openai_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured."""
        return bool(self.azure_openai_endpoint and self.azure_openai_api_key)

    # ==========================================================================
    # Azure Service Bus (Production)
    # ==========================================================================
    azure_service_bus_connection_string: str = ""

    @property
    def use_azure_service_bus(self) -> bool:
        """Determine whether to use Azure Service Bus or RabbitMQ."""
        return bool(self.azure_service_bus_connection_string)

    # ==========================================================================
    # JWT Authentication
    # ==========================================================================
    jwt_secret_key: str = "change-this-to-a-secure-random-string"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ==========================================================================
    # CORS
    # ==========================================================================
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ==========================================================================
    # Feature Flags
    # ==========================================================================
    feature_workflow_enabled: bool = True
    feature_agent_enabled: bool = True
    feature_checkpoint_enabled: bool = True

    # ==========================================================================
    # Development Settings
    # ==========================================================================
    enable_api_docs: bool = True
    enable_sql_logging: bool = False

    # ==========================================================================
    # Observability
    # ==========================================================================
    otel_enabled: bool = False
    otel_service_name: str = "ipa-platform"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # ==========================================================================
    # Validators
    # ==========================================================================
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v_upper


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Uses lru_cache to ensure settings are only loaded once.
    """
    return Settings()

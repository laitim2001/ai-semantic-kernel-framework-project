"""
Application configuration management
"""
import os
import socket
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, PostgresDsn, field_validator


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    app_name: str = Field(default="AI Semantic Kernel Framework", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")

    # API
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")
    allowed_hosts: list[str] = Field(default=["*"], alias="ALLOWED_HOSTS")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/ai_framework",
        alias="DATABASE_URL"
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_pool_pre_ping: bool = Field(default=True, alias="DB_POOL_PRE_PING")
    db_pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")  # 1 hour

    # Redis Cache
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL")
    redis_ssl_cert_reqs: str = Field(default="required", alias="REDIS_SSL_CERT_REQS")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    redis_health_check_interval: int = Field(default=30, alias="REDIS_HEALTH_CHECK_INTERVAL")
    redis_retry_on_timeout: bool = Field(default=True, alias="REDIS_RETRY_ON_TIMEOUT")
    redis_decode_responses: bool = Field(default=True, alias="REDIS_DECODE_RESPONSES")

    # Message Queue
    mq_provider: str = Field(default="rabbitmq", alias="MQ_PROVIDER")  # 'rabbitmq' or 'servicebus'

    # RabbitMQ (Local Development)
    rabbitmq_host: str = Field(default="localhost", alias="RABBITMQ_HOST")
    rabbitmq_port: int = Field(default=5672, alias="RABBITMQ_PORT")
    rabbitmq_user: str = Field(default="admin", alias="RABBITMQ_USER")
    rabbitmq_password: str = Field(default="admin", alias="RABBITMQ_PASSWORD")
    rabbitmq_vhost: str = Field(default="ai-framework", alias="RABBITMQ_VHOST")
    rabbitmq_ssl: bool = Field(default=False, alias="RABBITMQ_SSL")
    rabbitmq_management_port: int = Field(default=15672, alias="RABBITMQ_MANAGEMENT_PORT")

    # Azure Service Bus (Production)
    servicebus_connection_string: Optional[str] = Field(default=None, alias="SERVICEBUS_CONNECTION_STRING")
    servicebus_namespace: Optional[str] = Field(default=None, alias="SERVICEBUS_NAMESPACE")

    # Queue Configuration
    queue_max_retries: int = Field(default=3, alias="QUEUE_MAX_RETRIES")
    queue_retry_delay_base: float = Field(default=1.0, alias="QUEUE_RETRY_DELAY_BASE")
    queue_retry_delay_max: float = Field(default=60.0, alias="QUEUE_RETRY_DELAY_MAX")
    queue_message_ttl: int = Field(default=3600, alias="QUEUE_MESSAGE_TTL")  # 1 hour
    queue_prefetch_count: int = Field(default=10, alias="QUEUE_PREFETCH_COUNT")

    # Security
    secret_key: str = Field(default="development-secret-key-change-in-production", alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")

    # Azure OpenAI (if using Azure)
    azure_openai_endpoint: Optional[str] = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    azure_openai_deployment_name: Optional[str] = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT_NAME")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        alias="LOG_FORMAT"
    )

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: list[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")

    # Rate Limiting (using Redis)
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")  # seconds

    # Session Management (using Redis)
    session_ttl: int = Field(default=86400, alias="SESSION_TTL")  # 24 hours
    session_cookie_name: str = Field(default="session_id", alias="SESSION_COOKIE_NAME")
    session_cookie_httponly: bool = Field(default=True, alias="SESSION_COOKIE_HTTPONLY")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")  # True in production
    session_cookie_samesite: str = Field(default="lax", alias="SESSION_COOKIE_SAMESITE")

    # JWT Authentication
    secret_key: str = Field(
        default="your-secret-key-change-in-production-min-32-chars",
        alias="SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Azure Monitor / Application Insights
    appinsights_connection_string: Optional[str] = Field(default=None, alias="APPLICATIONINSIGHTS_CONNECTION_STRING")
    appinsights_instrumentation_key: Optional[str] = Field(default=None, alias="APPINSIGHTS_INSTRUMENTATION_KEY")
    otel_service_name: str = Field(default="ai-framework-backend", alias="OTEL_SERVICE_NAME")
    otel_traces_sampler: str = Field(default="always_on", alias="OTEL_TRACES_SAMPLER")  # always_on, always_off, traceidratio
    otel_traces_sampler_arg: float = Field(default=1.0, alias="OTEL_TRACES_SAMPLER_ARG")  # For traceidratio

    # Prometheus
    prometheus_enabled: bool = Field(default=False, alias="PROMETHEUS_ENABLED")
    prometheus_metrics_path: str = Field(default="/metrics", alias="PROMETHEUS_METRICS_PATH")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v.lower()

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v.upper()

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == "development"

    @property
    def redis_url(self) -> str:
        """Construct Redis connection URL"""
        if self.redis_ssl:
            protocol = "rediss"
        else:
            protocol = "redis"

        if self.redis_password:
            return f"{protocol}://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"{protocol}://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def redis_socket_keepalive_options(self) -> dict:
        """Socket keepalive options for Redis connection"""
        return {
            socket.TCP_KEEPIDLE: 60,
            socket.TCP_KEEPINTVL: 10,
            socket.TCP_KEEPCNT: 3
        }

    @property
    def rabbitmq_url(self) -> str:
        """Construct RabbitMQ connection URL"""
        protocol = "amqps" if self.rabbitmq_ssl else "amqp"
        return (
            f"{protocol}://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/{self.rabbitmq_vhost}"
        )

    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from .env


# Global settings instance
settings = Settings()

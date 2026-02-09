"""Application configuration using Pydantic Settings.

All settings are loaded from environment variables or .env file.
Secrets are handled via SecretStr to prevent accidental logging.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    """Application settings with validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="GPS_",
    )

    # Application
    app_name: str = "Git Phantom Scope"
    app_version: str = "0.1.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl: int = 1800  # 30 minutes
    redis_asset_ttl: int = 14400  # 4 hours

    # PostgreSQL (analytics only - NO PII)
    database_url: str = "postgresql+asyncpg://gps:gps_dev_password@localhost:5432/gps_analytics"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # GitHub API
    github_api_base: str = "https://api.github.com"
    github_cache_ttl: int = 900  # 15 minutes
    github_token: SecretStr | None = None

    # Rate Limiting
    rate_limit_analyze_per_day: int = 3
    rate_limit_generate_per_day: int = 5
    rate_limit_requests_per_minute: int = 30

    # Gemini (shared free key for free tier)
    gemini_shared_key: SecretStr | None = None
    gemini_rate_limit_per_minute: int = 15
    gemini_rate_limit_per_day: int = 1500

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # MinIO / S3 (temp asset storage)
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: SecretStr = SecretStr("minioadmin")
    s3_secret_key: SecretStr = SecretStr("minioadmin")
    s3_bucket: str = "gps-assets"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Security
    session_secret_key: SecretStr = SecretStr("change-me-in-production")
    byok_encryption_key: SecretStr | None = None

    # Stripe (payment processing)
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_publishable_key: str | None = None

    # Prometheus
    metrics_enabled: bool = True

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        return v.lower()

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()

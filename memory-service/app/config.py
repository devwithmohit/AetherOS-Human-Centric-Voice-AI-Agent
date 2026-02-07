"""Configuration management for Memory Service."""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service configuration
    service_name: str = "memory-service"
    service_host: str = "0.0.0.0"
    service_port: int = 8001
    environment: str = "development"
    log_level: str = "INFO"

    # PostgreSQL configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "aetheros_memory"
    postgres_user: str = "aetheros"
    postgres_password: str = "change_me"
    database_url: Optional[str] = None

    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_url: Optional[str] = None

    # ChromaDB configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_persist_dir: str = "./chroma_data"

    # Security
    encryption_key: str = Field(default="", description="Fernet encryption key")
    secret_key: str = Field(default="dev_secret_key", description="JWT secret key")
    algorithm: str = "HS256"

    # Memory retention policies (seconds)
    short_term_ttl: int = 3600  # 1 hour
    working_memory_ttl: int = 86400  # 24 hours
    episodic_retention_days: int = 90

    # Performance
    max_connections: int = 100
    pool_size: int = 20
    max_overflow: int = 10

    # Privacy
    enable_encryption: bool = True
    require_consent: bool = True
    anonymize_pii: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def build_database_url(cls, v: Optional[str], info) -> str:
        """Build database URL if not provided."""
        if v:
            return v
        values = info.data
        return (
            f"postgresql+asyncpg://{values.get('postgres_user')}:"
            f"{values.get('postgres_password')}@{values.get('postgres_host')}:"
            f"{values.get('postgres_port')}/{values.get('postgres_db')}"
        )

    @field_validator("redis_url", mode="before")
    @classmethod
    def build_redis_url(cls, v: Optional[str], info) -> str:
        """Build Redis URL if not provided."""
        if v:
            return v
        values = info.data
        password = values.get("redis_password")
        auth = f":{password}@" if password else ""
        return (
            f"redis://{auth}{values.get('redis_host')}:"
            f"{values.get('redis_port')}/{values.get('redis_db')}"
        )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        """Get CORS origins based on environment."""
        if self.is_production:
            return [
                "https://aetheros.ai",
                "https://api.aetheros.ai",
            ]
        return ["*"]  # Allow all in development


# Global settings instance
settings = Settings()

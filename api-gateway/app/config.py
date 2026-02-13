"""
Configuration management for API Gateway.

Loads settings from environment variables with sensible defaults.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:5173",
    ]

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 60
    JWT_REFRESH_EXPIRATION_DAYS: int = 7

    # Redis (Rate Limiting & Caching)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100  # requests per window
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Circuit Breaker
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    CIRCUIT_BREAKER_RECOVERY_TIMEOUT: int = 60
    CIRCUIT_BREAKER_EXPECTED_EXCEPTION: type = Exception

    # gRPC Service Endpoints
    VOICE_STT_GRPC_URL: str = "localhost:50051"  # M2 - Speech-to-Text
    VOICE_TTS_GRPC_URL: str = "localhost:50052"  # M3 - Text-to-Speech
    INTENT_GRPC_URL: str = "localhost:50053"  # M4 - Intent Recognition
    PLANNER_GRPC_URL: str = "localhost:50054"  # M5 - Action Planner
    SAFETY_GRPC_URL: str = "localhost:50055"  # M6 - Safety Validator
    BROWSER_GRPC_URL: str = "localhost:50056"  # M7 - Browser Executor
    OS_GRPC_URL: str = "localhost:50057"  # M8 - OS Executor
    SEARCH_GRPC_URL: str = "localhost:50058"  # M9 - Search Executor
    MEMORY_GRPC_URL: str = "localhost:50059"  # M10 - Memory Manager

    # gRPC Client Settings
    GRPC_MAX_RETRIES: int = 3
    GRPC_TIMEOUT_SECONDS: int = 30
    GRPC_KEEPALIVE_TIME_MS: int = 10000
    GRPC_KEEPALIVE_TIMEOUT_MS: int = 5000

    # Timeouts (seconds)
    STT_TIMEOUT: int = 30
    TTS_TIMEOUT: int = 30
    INTENT_TIMEOUT: int = 10
    PLANNER_TIMEOUT: int = 15
    SAFETY_TIMEOUT: int = 5
    EXECUTOR_TIMEOUT: int = 60
    MEMORY_TIMEOUT: int = 10

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # Prometheus
    METRICS_ENABLED: bool = True

    # WebSocket
    WS_MAX_CONNECTIONS: int = 1000
    WS_HEARTBEAT_INTERVAL: int = 30


# Create global settings instance
settings = Settings()

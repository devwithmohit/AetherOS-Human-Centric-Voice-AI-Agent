"""Configuration management for TTS service."""

from typing import List
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

    # Service Configuration
    service_name: str = Field(default="tts-service", description="Service name")
    service_host: str = Field(default="0.0.0.0", description="Host to bind")
    service_port: int = Field(default=8002, description="Port to bind")
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # TTS Model Configuration
    tts_model_name: str = Field(
        default="tts_models/en/ljspeech/tacotron2-DDC",
        description="Coqui TTS model name",
    )
    tts_model_path: str = Field(default="./models/", description="Model storage path")
    tts_config_path: str = Field(default="./models/config.json", description="Model config path")

    # Audio Configuration
    audio_sample_rate: int = Field(default=22050, description="Sample rate in Hz")
    audio_channels: int = Field(default=1, description="Number of audio channels")
    audio_bit_depth: int = Field(default=16, description="Bit depth")
    audio_format: str = Field(default="wav", description="Output audio format")

    # Voice Configuration
    default_speaker: str = Field(default="ljspeech", description="Default speaker ID")
    default_language: str = Field(default="en", description="Default language code")

    # Performance Settings
    use_cuda: bool = Field(default=True, description="Use CUDA if available")
    enable_half_precision: bool = Field(default=False, description="Enable FP16 inference")
    num_threads: int = Field(default=4, description="Number of CPU threads")

    # Cache Configuration
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_dir: str = Field(default="./cache/", description="Cache directory")
    cache_size_mb: int = Field(default=500, description="Max cache size in MB")
    cache_ttl_seconds: int = Field(default=86400, description="Cache TTL in seconds")
    cache_max_entries: int = Field(default=1000, description="Max cache entries")

    # Quality Settings
    target_mos_score: float = Field(default=3.5, description="Target Mean Opinion Score")
    max_text_length: int = Field(default=500, description="Maximum text length per request")
    min_text_length: int = Field(default=1, description="Minimum text length per request")

    # Streaming Configuration
    stream_chunk_size: int = Field(default=4096, description="Stream chunk size")
    enable_streaming: bool = Field(default=True, description="Enable audio streaming")

    # Rate Limiting
    max_requests_per_minute: int = Field(default=60, description="Max requests per minute")
    max_concurrent_requests: int = Field(default=10, description="Max concurrent requests")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Allowed CORS origins",
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials")
    cors_allow_methods: str = Field(default="*", description="Allowed methods")
    cors_allow_headers: str = Field(default="*", description="Allowed headers")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable metrics")
    metrics_port: int = Field(default=9090, description="Metrics port")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def cache_size_bytes(self) -> int:
        """Get cache size in bytes."""
        return self.cache_size_mb * 1024 * 1024

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()

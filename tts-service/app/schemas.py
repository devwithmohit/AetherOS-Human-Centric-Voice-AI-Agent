"""Pydantic schemas for TTS service API."""

from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AudioFormat(str, Enum):
    """Supported audio formats."""

    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"


class VoiceProfile(str, Enum):
    """Available voice profiles."""

    LJSPEECH = "ljspeech"  # Female, neutral
    VCTK_P225 = "p225"  # Female, British
    VCTK_P226 = "p226"  # Male, British
    VCTK_P227 = "p227"  # Male, British
    DEFAULT = "ljspeech"


class SynthesisRequest(BaseModel):
    """Request schema for text synthesis."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Text to synthesize",
        examples=["Hello, how can I help you today?"],
    )
    speaker_id: Optional[str] = Field(
        default=None,
        description="Speaker ID for multi-speaker models",
        examples=["ljspeech", "p225"],
    )
    language: Optional[str] = Field(
        default="en",
        description="Language code",
        examples=["en", "es", "fr"],
    )
    speed: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Speech speed multiplier",
        examples=[1.0, 1.2, 0.8],
    )
    pitch: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Pitch multiplier",
        examples=[1.0, 1.1, 0.9],
    )
    format: AudioFormat = Field(
        default=AudioFormat.WAV,
        description="Output audio format",
    )
    use_cache: bool = Field(
        default=True,
        description="Use cached audio if available",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata",
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and clean text input."""
        text = v.strip()
        if not text:
            raise ValueError("Text cannot be empty")
        # Remove multiple spaces
        text = " ".join(text.split())
        return text


class SynthesisResponse(BaseModel):
    """Response schema for synthesis request."""

    audio_url: Optional[str] = Field(
        default=None,
        description="URL to download audio file",
    )
    duration_seconds: float = Field(
        ...,
        description="Audio duration in seconds",
    )
    sample_rate: int = Field(
        ...,
        description="Audio sample rate in Hz",
    )
    format: str = Field(
        ...,
        description="Audio format",
    )
    cached: bool = Field(
        default=False,
        description="Whether audio was served from cache",
    )
    generation_time_ms: float = Field(
        ...,
        description="Time taken to generate audio in milliseconds",
    )
    text_length: int = Field(
        ...,
        description="Length of input text in characters",
    )
    model_used: str = Field(
        ...,
        description="TTS model used for synthesis",
    )


class VoiceListResponse(BaseModel):
    """Response schema for available voices."""

    voices: List[Dict[str, Any]] = Field(
        ...,
        description="List of available voices",
    )
    total_count: int = Field(
        ...,
        description="Total number of voices",
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    model_loaded: bool = Field(..., description="Whether TTS model is loaded")
    cache_enabled: bool = Field(..., description="Whether cache is enabled")
    cache_size: int = Field(..., description="Number of cached entries")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")


class CacheStats(BaseModel):
    """Cache statistics."""

    enabled: bool = Field(..., description="Whether cache is enabled")
    size: int = Field(..., description="Number of cached entries")
    size_bytes: int = Field(..., description="Cache size in bytes")
    max_size_bytes: int = Field(..., description="Max cache size in bytes")
    hit_rate: float = Field(..., description="Cache hit rate")
    total_hits: int = Field(..., description="Total cache hits")
    total_misses: int = Field(..., description="Total cache misses")


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(default=None, description="Error code")
    timestamp: str = Field(..., description="Error timestamp")

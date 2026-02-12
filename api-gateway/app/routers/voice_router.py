"""
Voice Services Router

Routes requests to:
- M2: Speech-to-Text (STT)
- M3: Text-to-Speech (TTS)
"""

from typing import Dict, Any
import structlog
from fastapi import APIRouter, Request, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter()


# Request/Response Models


class TTSRequest(BaseModel):
    """Text-to-Speech request."""

    text: str = Field(..., description="Text to convert to speech", min_length=1, max_length=5000)
    voice: str = Field(default="en-US-Standard-A", description="Voice ID")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed")
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0, description="Speech pitch")
    format: str = Field(default="mp3", description="Audio format (mp3, wav, ogg)")


class STTResponse(BaseModel):
    """Speech-to-Text response."""

    transcript: str = Field(..., description="Transcribed text")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    language: str = Field(..., description="Detected language")
    duration_ms: int = Field(..., description="Processing duration in milliseconds")


class TTSResponse(BaseModel):
    """Text-to-Speech response."""

    audio_url: str = Field(..., description="URL to generated audio file")
    audio_data: str = Field(..., description="Base64 encoded audio data")
    duration_seconds: float = Field(..., description="Audio duration in seconds")
    format: str = Field(..., description="Audio format")


# Endpoints


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    request: Request,
    audio: UploadFile = File(..., description="Audio file for transcription"),
    language: str = "en-US",
) -> STTResponse:
    """
    Convert speech to text (M2).

    Args:
        audio: Audio file (mp3, wav, ogg, etc.)
        language: Language code (e.g., en-US, es-ES)

    Returns:
        Transcription result with confidence score
    """
    try:
        # Get gRPC client
        grpc_manager = request.app.state.grpc_manager
        stt_client = grpc_manager.get_client("stt")

        if not stt_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Speech-to-Text service unavailable",
            )

        # Read audio data
        audio_data = await audio.read()

        if len(audio_data) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio file too large (max 10MB)",
            )

        logger.info(
            "stt_request",
            filename=audio.filename,
            content_type=audio.content_type,
            size=len(audio_data),
            language=language,
        )

        # TODO: Make gRPC call to M2 when gRPC service is ready
        # For now, return mock response
        response = STTResponse(
            transcript="This is a sample transcription",
            confidence=0.95,
            language=language,
            duration_ms=1250,
        )

        logger.info("stt_success", transcript_length=len(response.transcript))
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("stt_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Speech-to-Text processing failed: {str(e)}",
        )


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    request: Request,
    tts_request: TTSRequest,
) -> TTSResponse:
    """
    Convert text to speech (M3).

    Args:
        tts_request: TTS configuration

    Returns:
        Generated audio file URL and data
    """
    try:
        import os

        # Check if in testing mode
        if os.getenv("TESTING") == "true" or not hasattr(request.app.state, "grpc_manager"):
            # Return mock response for testing
            logger.info(
                "tts_request_test_mode",
                text_length=len(tts_request.text),
            )

            response = TTSResponse(
                audio_url="https://example.com/audio/rust_video.mp3",
                audio_data="UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
                duration_seconds=2.5,
                format=tts_request.format,
            )

            logger.info(
                "tts_success_test_mode",
                duration=response.duration_seconds,
            )
            return response

        # Production mode with gRPC
        # Get gRPC client
        grpc_manager = request.app.state.grpc_manager
        tts_client = grpc_manager.get_client("tts")

        if not tts_client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Text-to-Speech service unavailable",
            )

        logger.info(
            "tts_request",
            text_length=len(tts_request.text),
            voice=tts_request.voice,
            speed=tts_request.speed,
            format=tts_request.format,
        )

        # TODO: Make gRPC call to M3 when gRPC service is ready
        # For now, return mock response
        response = TTSResponse(
            audio_url="https://example.com/audio/sample.mp3",
            audio_data="UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
            duration_seconds=3.5,
            format=tts_request.format,
        )

        logger.info(
            "tts_success",
            audio_url=response.audio_url,
            duration=response.duration_seconds,
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("tts_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Text-to-Speech processing failed: {str(e)}",
        )


@router.get("/voices")
async def list_voices() -> Dict[str, Any]:
    """
    List available TTS voices.

    Returns:
        List of available voice configurations
    """
    # TODO: Query from M3 when available
    return {
        "voices": [
            {
                "id": "en-US-Standard-A",
                "name": "US English (Female)",
                "language": "en-US",
                "gender": "female",
            },
            {
                "id": "en-US-Standard-B",
                "name": "US English (Male)",
                "language": "en-US",
                "gender": "male",
            },
            {
                "id": "en-GB-Standard-A",
                "name": "British English (Female)",
                "language": "en-GB",
                "gender": "female",
            },
        ]
    }

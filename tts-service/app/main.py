"""FastAPI main application for TTS service."""

import io
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas import (
    SynthesisRequest,
    SynthesisResponse,
    HealthResponse,
    CacheStats,
    VoiceListResponse,
    ErrorResponse,
)
from app.synthesizer import synthesizer
from app.voice_cache import voice_cache

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Track service start time
SERVICE_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.service_name} v0.1.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Service will listen on {settings.service_host}:{settings.service_port}")

    try:
        # Load TTS model
        logger.info("Loading TTS model...")
        synthesizer.load_model()
        logger.info("TTS model loaded successfully")

    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down service...")

    # Unload model
    synthesizer.unload_model()

    # Close cache
    voice_cache.close()

    logger.info("Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AetherOS TTS Service",
    description="Text-to-Speech synthesis service using Coqui TTS",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"] if settings.cors_allow_methods == "*" else [settings.cors_allow_methods],
    allow_headers=["*"] if settings.cors_allow_headers == "*" else [settings.cors_allow_headers],
)


@app.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict:
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service health status and statistics.
    """
    uptime = time.time() - SERVICE_START_TIME
    cache_stats = voice_cache.get_stats()

    return HealthResponse(
        status="healthy" if synthesizer.is_loaded() else "unhealthy",
        version="0.1.0",
        model_loaded=synthesizer.is_loaded(),
        cache_enabled=cache_stats["enabled"],
        cache_size=cache_stats["size"],
        uptime_seconds=uptime,
    )


@app.get("/cache/stats", response_model=CacheStats, status_code=status.HTTP_200_OK)
async def get_cache_stats() -> CacheStats:
    """
    Get cache statistics.

    Returns detailed cache statistics including hit rate and size.
    """
    stats = voice_cache.get_stats()
    return CacheStats(**stats)


@app.delete("/cache", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cache() -> None:
    """
    Clear entire cache.

    Deletes all cached audio files.
    """
    success = voice_cache.clear()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache",
        )


@app.get("/voices", response_model=VoiceListResponse, status_code=status.HTTP_200_OK)
async def list_voices() -> VoiceListResponse:
    """
    List available voices.

    Returns list of available voice profiles and speakers.
    """
    # Available voices based on loaded model
    voices = [
        {
            "id": "ljspeech",
            "name": "LJSpeech",
            "language": "en",
            "gender": "female",
            "description": "Neutral female voice",
        },
        {
            "id": "p225",
            "name": "VCTK P225",
            "language": "en",
            "gender": "female",
            "description": "British female voice",
        },
        {
            "id": "p226",
            "name": "VCTK P226",
            "language": "en",
            "gender": "male",
            "description": "British male voice",
        },
    ]

    return VoiceListResponse(voices=voices, total_count=len(voices))


@app.post(
    "/synthesize",
    response_model=SynthesisResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Synthesis failed"},
    },
)
async def synthesize_text(request: SynthesisRequest) -> SynthesisResponse:
    """
    Synthesize text to speech.

    Generates audio from input text with optional voice customization.

    Args:
        request: Synthesis request with text and parameters

    Returns:
        Synthesis response with audio metadata

    Raises:
        HTTPException: If synthesis fails
    """
    try:
        start_time = time.time()
        cached = False

        # Check cache first if enabled
        if request.use_cache and voice_cache.enabled:
            cached_audio = voice_cache.get(
                text=request.text,
                speaker_id=request.speaker_id,
                language=request.language,
                speed=request.speed,
                pitch=request.pitch,
                audio_format=request.format.value,
            )

            if cached_audio:
                cached = True
                audio_bytes = cached_audio
                logger.info(f"Serving cached audio for: '{request.text[:50]}...'")
            else:
                # Generate audio
                audio_bytes = synthesizer.synthesize_to_bytes(
                    text=request.text,
                    speaker_id=request.speaker_id,
                    language=request.language,
                    speed=request.speed,
                    audio_format=request.format.value,
                    use_cache=False,
                )

                # Cache the result
                voice_cache.set(
                    audio_bytes=audio_bytes,
                    text=request.text,
                    speaker_id=request.speaker_id,
                    language=request.language,
                    speed=request.speed,
                    pitch=request.pitch,
                    audio_format=request.format.value,
                )
        else:
            # Generate audio without cache
            audio_bytes = synthesizer.synthesize_to_bytes(
                text=request.text,
                speaker_id=request.speaker_id,
                language=request.language,
                speed=request.speed,
                audio_format=request.format.value,
                use_cache=False,
            )

        generation_time = time.time() - start_time

        # Calculate audio duration (approximate for WAV)
        if request.format.value == "wav":
            # WAV: 44 bytes header, then samples
            audio_samples = (len(audio_bytes) - 44) / 2  # 16-bit = 2 bytes per sample
            duration = audio_samples / settings.audio_sample_rate
        else:
            # Approximate for other formats
            duration = len(request.text) * 0.05  # ~50ms per character

        return SynthesisResponse(
            audio_url=None,  # Could be set if storing files
            duration_seconds=duration,
            sample_rate=synthesizer.get_model_sample_rate(),
            format=request.format.value,
            cached=cached,
            generation_time_ms=generation_time * 1000,
            text_length=len(request.text),
            model_used=settings.tts_model_name,
        )

    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthesis failed: {str(e)}",
        ) from e


@app.post("/synthesize/stream", status_code=status.HTTP_200_OK)
async def synthesize_stream(request: SynthesisRequest) -> StreamingResponse:
    """
    Synthesize text to speech with streaming response.

    Generates audio and streams it back to the client.

    Args:
        request: Synthesis request with text and parameters

    Returns:
        StreamingResponse with audio data

    Raises:
        HTTPException: If synthesis fails
    """
    try:
        # Check cache first
        cached_audio = None
        if request.use_cache and voice_cache.enabled:
            cached_audio = voice_cache.get(
                text=request.text,
                speaker_id=request.speaker_id,
                language=request.language,
                speed=request.speed,
                pitch=request.pitch,
                audio_format=request.format.value,
            )

        if cached_audio:
            # Stream cached audio
            logger.info(f"Streaming cached audio for: '{request.text[:50]}...'")
            audio_bytes = cached_audio
        else:
            # Generate audio
            audio_bytes = synthesizer.synthesize_to_bytes(
                text=request.text,
                speaker_id=request.speaker_id,
                language=request.language,
                speed=request.speed,
                audio_format=request.format.value,
                use_cache=False,
            )

            # Cache the result
            if request.use_cache:
                voice_cache.set(
                    audio_bytes=audio_bytes,
                    text=request.text,
                    speaker_id=request.speaker_id,
                    language=request.language,
                    speed=request.speed,
                    pitch=request.pitch,
                    audio_format=request.format.value,
                )

        # Create streaming response
        def audio_stream():
            """Generator to stream audio in chunks."""
            buffer = io.BytesIO(audio_bytes)
            while True:
                chunk = buffer.read(settings.stream_chunk_size)
                if not chunk:
                    break
                yield chunk

        # Determine media type
        media_type_map = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg",
            "flac": "audio/flac",
        }
        media_type = media_type_map.get(request.format.value, "audio/wav")

        return StreamingResponse(
            audio_stream(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="synthesis.{request.format.value}"',
                "X-Audio-Duration": str(len(request.text) * 0.05),
                "X-Text-Length": str(len(request.text)),
            },
        )

    except Exception as e:
        logger.error(f"Stream synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stream synthesis failed: {str(e)}",
        ) from e


@app.get("/stats", status_code=status.HTTP_200_OK)
async def get_stats() -> dict:
    """
    Get service statistics.

    Returns synthesizer and cache statistics.
    """
    synth_stats = synthesizer.get_stats()
    cache_stats = voice_cache.get_stats()

    return {
        "synthesizer": synth_stats,
        "cache": cache_stats,
        "uptime_seconds": time.time() - SERVICE_START_TIME,
    }


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError) -> Response:
    """Handle ValueError exceptions."""
    return Response(
        content=f'{{"detail": "{str(exc)}", "error_code": "INVALID_INPUT"}}',
        status_code=status.HTTP_400_BAD_REQUEST,
        media_type="application/json",
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request, exc: RuntimeError) -> Response:
    """Handle RuntimeError exceptions."""
    return Response(
        content=f'{{"detail": "{str(exc)}", "error_code": "INTERNAL_ERROR"}}',
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        media_type="application/json",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.is_development(),
        log_level=settings.log_level.lower(),
    )

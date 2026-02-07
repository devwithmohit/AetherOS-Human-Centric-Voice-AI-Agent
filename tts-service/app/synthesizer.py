"""TTS Synthesizer - Core text-to-speech synthesis logic."""

import io
import os
import time
import logging
from typing import Optional, Tuple
import numpy as np
import soundfile as sf
import torch
from TTS.api import TTS

from app.config import settings

logger = logging.getLogger(__name__)


class TTSSynthesizer:
    """Text-to-speech synthesizer using Coqui TTS."""

    def __init__(self) -> None:
        """Initialize TTS synthesizer."""
        self.model: Optional[TTS] = None
        self.model_name: str = settings.tts_model_name
        self.device: str = "cuda" if settings.use_cuda and torch.cuda.is_available() else "cpu"
        self.sample_rate: int = settings.audio_sample_rate
        self._model_loaded: bool = False
        self._inference_count: int = 0
        self._total_inference_time: float = 0.0

        logger.info(f"Initializing TTS Synthesizer with model: {self.model_name}")
        logger.info(f"Using device: {self.device}")

    def load_model(self) -> None:
        """Load TTS model into memory."""
        if self._model_loaded:
            logger.info("Model already loaded")
            return

        try:
            start_time = time.time()
            logger.info(f"Loading TTS model: {self.model_name}")

            # Initialize TTS model
            self.model = TTS(
                model_name=self.model_name,
                progress_bar=True,
                gpu=(self.device == "cuda"),
            )

            # Set model to evaluation mode
            if hasattr(self.model, "synthesizer") and hasattr(self.model.synthesizer, "tts_model"):
                self.model.synthesizer.tts_model.eval()

            # Warm up model with a test synthesis
            logger.info("Warming up model with test synthesis...")
            _ = self.synthesize_text("Hello world", use_cache=False)

            load_time = time.time() - start_time
            self._model_loaded = True

            logger.info(f"Model loaded successfully in {load_time:.2f}s")
            logger.info(f"Model sample rate: {self.get_model_sample_rate()} Hz")

        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise RuntimeError(f"Failed to load TTS model: {e}") from e

    def unload_model(self) -> None:
        """Unload model from memory."""
        if self.model is not None:
            logger.info("Unloading TTS model")
            del self.model
            self.model = None
            self._model_loaded = False

            # Clear CUDA cache if using GPU
            if self.device == "cuda":
                torch.cuda.empty_cache()

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded

    def get_model_sample_rate(self) -> int:
        """Get model's native sample rate."""
        if self.model and hasattr(self.model, "synthesizer"):
            if hasattr(self.model.synthesizer, "output_sample_rate"):
                return self.model.synthesizer.output_sample_rate
        return self.sample_rate

    def synthesize_text(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        use_cache: bool = True,
    ) -> Tuple[np.ndarray, int]:
        """
        Synthesize text to audio.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID for multi-speaker models
            language: Language code
            speed: Speech speed multiplier
            use_cache: Whether to use cache (placeholder for cache integration)

        Returns:
            Tuple of (audio array, sample rate)

        Raises:
            RuntimeError: If model is not loaded or synthesis fails
        """
        if not self._model_loaded or self.model is None:
            raise RuntimeError("TTS model not loaded. Call load_model() first.")

        try:
            start_time = time.time()
            logger.debug(f"Synthesizing text: '{text[:50]}...' (length: {len(text)})")

            # Prepare synthesis parameters
            synthesis_kwargs = {}

            if speaker_id:
                synthesis_kwargs["speaker"] = speaker_id

            if language:
                synthesis_kwargs["language"] = language

            # Synthesize audio
            audio = self.model.tts(text=text, **synthesis_kwargs)

            # Convert to numpy array if not already
            if isinstance(audio, list):
                audio = np.array(audio, dtype=np.float32)
            elif isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()

            # Apply speed adjustment if needed
            if speed != 1.0:
                audio = self._adjust_speed(audio, speed)

            # Normalize audio
            audio = self._normalize_audio(audio)

            # Get actual sample rate
            actual_sample_rate = self.get_model_sample_rate()

            inference_time = time.time() - start_time
            self._inference_count += 1
            self._total_inference_time += inference_time

            logger.info(
                f"Synthesis completed in {inference_time * 1000:.2f}ms "
                f"for {len(text)} chars ({len(text) / inference_time:.1f} chars/s)"
            )

            return audio, actual_sample_rate

        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            raise RuntimeError(f"Synthesis failed: {e}") from e

    def synthesize_to_bytes(
        self,
        text: str,
        speaker_id: Optional[str] = None,
        language: Optional[str] = None,
        speed: float = 1.0,
        audio_format: str = "wav",
        use_cache: bool = True,
    ) -> bytes:
        """
        Synthesize text to audio bytes.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID for multi-speaker models
            language: Language code
            speed: Speech speed multiplier
            audio_format: Output format (wav, mp3, ogg, flac)
            use_cache: Whether to use cache

        Returns:
            Audio data as bytes

        Raises:
            RuntimeError: If synthesis fails
        """
        # Generate audio
        audio, sample_rate = self.synthesize_text(
            text=text,
            speaker_id=speaker_id,
            language=language,
            speed=speed,
            use_cache=use_cache,
        )

        # Convert to bytes
        audio_bytes = self._audio_to_bytes(audio, sample_rate, audio_format)

        return audio_bytes

    def _audio_to_bytes(self, audio: np.ndarray, sample_rate: int, audio_format: str) -> bytes:
        """
        Convert audio array to bytes.

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            audio_format: Output format (wav, mp3, ogg, flac)

        Returns:
            Audio data as bytes
        """
        # Create in-memory buffer
        buffer = io.BytesIO()

        # Write audio to buffer
        if audio_format == "wav":
            sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")
        elif audio_format == "flac":
            sf.write(buffer, audio, sample_rate, format="FLAC")
        elif audio_format == "ogg":
            sf.write(buffer, audio, sample_rate, format="OGG")
        else:
            # Default to WAV
            sf.write(buffer, audio, sample_rate, format="WAV", subtype="PCM_16")

        # Get bytes
        buffer.seek(0)
        audio_bytes = buffer.read()

        return audio_bytes

    def _normalize_audio(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio to prevent clipping.

        Args:
            audio: Audio data

        Returns:
            Normalized audio
        """
        # Find peak
        peak = np.abs(audio).max()

        # Normalize if needed (leave some headroom)
        if peak > 0.95:
            audio = audio * (0.95 / peak)

        return audio

    def _adjust_speed(self, audio: np.ndarray, speed: float) -> np.ndarray:
        """
        Adjust audio speed.

        Args:
            audio: Audio data
            speed: Speed multiplier (>1.0 = faster, <1.0 = slower)

        Returns:
            Speed-adjusted audio
        """
        try:
            import librosa

            # Use librosa for high-quality time stretching
            audio = librosa.effects.time_stretch(audio, rate=speed)
            return audio

        except ImportError:
            logger.warning("librosa not available, speed adjustment disabled")
            return audio

    def get_stats(self) -> dict:
        """
        Get synthesizer statistics.

        Returns:
            Dictionary with statistics
        """
        avg_inference_time = (
            self._total_inference_time / self._inference_count if self._inference_count > 0 else 0.0
        )

        return {
            "model_loaded": self._model_loaded,
            "model_name": self.model_name,
            "device": self.device,
            "inference_count": self._inference_count,
            "total_inference_time": self._total_inference_time,
            "avg_inference_time_ms": avg_inference_time * 1000,
            "sample_rate": self.sample_rate,
        }


# Global synthesizer instance
synthesizer = TTSSynthesizer()

"""TTS Synthesizer - Core text-to-speech synthesis logic using Piper TTS."""

import io
import os
import time
import logging
import subprocess
import wave
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class TTSSynthesizer:
    """Text-to-speech synthesizer using Piper TTS."""

    def __init__(self) -> None:
        """Initialize TTS synthesizer."""
        self.sample_rate: int = 22050  # Piper default sample rate
        self._model_loaded: bool = False
        self._inference_count: int = 0
        self._total_inference_time: float = 0.0

        # Piper paths (relative to tts-service root)
        self.models_dir = Path(__file__).parent.parent / "models"
        self.piper_binary = self.models_dir / "piper" / "piper"
        self.model_path = self.models_dir / "en_US-lessac-medium.onnx"
        self.model_config = self.models_dir / "en_US-lessac-medium.onnx.json"

        logger.info("Initializing Piper TTS Synthesizer")
        logger.info(f"Models directory: {self.models_dir}")
        logger.info(f"Piper binary: {self.piper_binary}")

    def load_model(self) -> None:
        """Load TTS model into memory (verify Piper binary and model exist)."""
        if self._model_loaded:
            logger.info("Model already loaded")
            return

        try:
            start_time = time.time()
            logger.info("Loading Piper TTS model")

            # Verify Piper binary exists and is executable
            if not self.piper_binary.exists():
                raise RuntimeError(
                    f"Piper binary not found at {self.piper_binary}. "
                    "Please download from https://github.com/rhasspy/piper/releases"
                )

            # Make binary executable on Unix systems
            if os.name != "nt":
                os.chmod(self.piper_binary, 0o755)

            # Verify model files exist
            if not self.model_path.exists():
                raise RuntimeError(
                    f"Piper model not found at {self.model_path}. "
                    "Please download en_US-lessac-medium.onnx"
                )

            if not self.model_config.exists():
                raise RuntimeError(
                    f"Model config not found at {self.model_config}. "
                    "Please download en_US-lessac-medium.onnx.json"
                )

            # Mark model as loaded (files verified)
            self._model_loaded = True

            # Test synthesis to warm up
            logger.info("Warming up model with test synthesis...")
            _ = self.synthesize_text("Hello world", use_cache=False)

            load_time = time.time() - start_time

            logger.info(f"Model loaded successfully in {load_time:.2f}s")
            logger.info(f"Model sample rate: {self.sample_rate} Hz")

        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise RuntimeError(f"Failed to load TTS model: {e}") from e

    def unload_model(self) -> None:
        """Unload model from memory (no-op for Piper, but kept for API compatibility)."""
        if self._model_loaded:
            logger.info("Unloading Piper TTS model (no-op)")
            self._model_loaded = False

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self._model_loaded

    def get_model_sample_rate(self) -> int:
        """Get model's native sample rate."""
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
        Synthesize text to audio using Piper.

        Args:
            text: Text to synthesize
            speaker_id: Speaker ID (unused for single-speaker Piper models)
            language: Language code (unused, model is English-only)
            speed: Speech speed multiplier (passed to Piper via --length-scale)
            use_cache: Whether to use cache (placeholder for cache integration)

        Returns:
            Tuple of (audio array, sample rate)

        Raises:
            RuntimeError: If model is not loaded or synthesis fails
        """
        if not self._model_loaded:
            raise RuntimeError("TTS model not loaded. Call load_model() first.")

        try:
            start_time = time.time()
            logger.debug(f"Synthesizing text: '{text[:50]}...' (length: {len(text)})")

            # Prepare Piper command
            # Piper uses --length-scale (inverse of speed: 1.0 = normal, <1.0 = faster, >1.0 = slower)
            length_scale = 1.0 / speed if speed != 0 else 1.0

            cmd = [
                str(self.piper_binary),
                "--model",
                str(self.model_path),
                "--config",
                str(self.model_config),
                "--output-raw",  # Output raw PCM data
                "--length_scale",
                str(length_scale),
            ]

            # Run Piper subprocess
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Send text to stdin and get raw audio from stdout
            stdout, stderr = process.communicate(input=text.encode("utf-8"))

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore")
                raise RuntimeError(f"Piper synthesis failed: {error_msg}")

            # Convert raw PCM bytes to numpy array
            # Piper outputs 16-bit signed PCM at 22050 Hz
            audio = np.frombuffer(stdout, dtype=np.int16).astype(np.float32) / 32768.0

            # Normalize audio
            audio = self._normalize_audio(audio)

            inference_time = time.time() - start_time
            self._inference_count += 1
            self._total_inference_time += inference_time

            logger.info(
                f"Synthesis completed in {inference_time * 1000:.2f}ms "
                f"for {len(text)} chars ({len(text) / inference_time:.1f} chars/s)"
            )

            return audio, self.sample_rate

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
            speaker_id: Speaker ID (unused)
            language: Language code (unused)
            speed: Speech speed multiplier
            audio_format: Output format (only 'wav' supported)
            use_cache: Whether to use cache

        Returns:
            Audio data as bytes (WAV format)

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
        Convert audio array to WAV bytes.

        Args:
            audio: Audio data as numpy array (float32, range -1.0 to 1.0)
            sample_rate: Sample rate in Hz
            audio_format: Output format (only 'wav' supported)

        Returns:
            Audio data as bytes (WAV format)
        """
        # Convert float32 audio to int16 PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Create WAV file in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

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
            "model_name": "piper:en_US-lessac-medium",
            "device": "cpu",
            "inference_count": self._inference_count,
            "total_inference_time": self._total_inference_time,
            "avg_inference_time_ms": avg_inference_time * 1000,
            "sample_rate": self.sample_rate,
        }


# Global synthesizer instance
synthesizer = TTSSynthesizer()

"""Unit tests for TTS synthesizer."""

import pytest
import numpy as np
from app.synthesizer import TTSSynthesizer


@pytest.fixture
def synthesizer():
    """Create synthesizer instance for testing."""
    synth = TTSSynthesizer()
    synth.load_model()
    yield synth
    synth.unload_model()


def test_synthesizer_initialization():
    """Test synthesizer can be initialized."""
    synth = TTSSynthesizer()
    assert synth is not None
    assert not synth.is_loaded()


def test_model_loading(synthesizer):
    """Test model loads successfully."""
    assert synthesizer.is_loaded()
    assert synthesizer.model is not None


def test_basic_synthesis(synthesizer):
    """Test basic text synthesis."""
    text = "Hello world"
    audio, sample_rate = synthesizer.synthesize_text(text, use_cache=False)

    assert isinstance(audio, np.ndarray)
    assert sample_rate > 0
    assert len(audio) > 0
    assert audio.dtype == np.float32


def test_synthesis_different_lengths(synthesizer):
    """Test synthesis with different text lengths."""
    texts = [
        "Hi",
        "Hello world",
        "This is a longer sentence to test the synthesizer.",
        "The quick brown fox jumps over the lazy dog.",
    ]

    for text in texts:
        audio, sr = synthesizer.synthesize_text(text, use_cache=False)
        assert len(audio) > 0
        assert sr == synthesizer.get_model_sample_rate()


def test_synthesis_speed_adjustment(synthesizer):
    """Test speed adjustment works."""
    text = "Testing speed adjustment"

    # Normal speed
    audio_normal, _ = synthesizer.synthesize_text(text, speed=1.0, use_cache=False)

    # Fast speed
    audio_fast, _ = synthesizer.synthesize_text(text, speed=1.5, use_cache=False)

    # Slow speed
    audio_slow, _ = synthesizer.synthesize_text(text, speed=0.8, use_cache=False)

    # Fast should be shorter than normal
    assert len(audio_fast) < len(audio_normal)

    # Slow should be longer than normal
    assert len(audio_slow) > len(audio_normal)


def test_synthesis_to_bytes(synthesizer):
    """Test synthesis to bytes."""
    text = "Convert to bytes"
    audio_bytes = synthesizer.synthesize_to_bytes(text, audio_format="wav", use_cache=False)

    assert isinstance(audio_bytes, bytes)
    assert len(audio_bytes) > 0

    # WAV should start with RIFF header
    assert audio_bytes[:4] == b"RIFF"


def test_audio_normalization(synthesizer):
    """Test audio normalization prevents clipping."""
    text = "Test normalization!"
    audio, _ = synthesizer.synthesize_text(text, use_cache=False)

    # Check audio is normalized
    peak = np.abs(audio).max()
    assert peak <= 1.0, "Audio peak exceeds 1.0"
    assert peak > 0.0, "Audio is silent"


def test_synthesizer_stats(synthesizer):
    """Test statistics collection."""
    text = "Get statistics"
    synthesizer.synthesize_text(text, use_cache=False)

    stats = synthesizer.get_stats()

    assert stats["model_loaded"] is True
    assert stats["inference_count"] > 0
    assert stats["avg_inference_time_ms"] > 0


def test_empty_text_raises_error(synthesizer):
    """Test empty text raises error."""
    with pytest.raises(Exception):
        synthesizer.synthesize_text("", use_cache=False)


def test_very_long_text(synthesizer):
    """Test very long text is handled."""
    text = "Hello world. " * 50  # 650 characters
    audio, sr = synthesizer.synthesize_text(text, use_cache=False)

    assert len(audio) > 0
    assert sr > 0


@pytest.mark.parametrize("audio_format", ["wav", "flac", "ogg"])
def test_different_formats(synthesizer, audio_format):
    """Test different audio formats."""
    text = "Test audio format"
    audio_bytes = synthesizer.synthesize_to_bytes(text, audio_format=audio_format, use_cache=False)

    assert len(audio_bytes) > 0


def test_concurrent_synthesis(synthesizer):
    """Test concurrent synthesis requests."""
    import concurrent.futures

    texts = [f"Concurrent test {i}" for i in range(5)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(synthesizer.synthesize_text, text, use_cache=False) for text in texts
        ]

        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == len(texts)
    for audio, sr in results:
        assert len(audio) > 0
        assert sr > 0

"""Performance and quality tests."""

import time
import pytest
import numpy as np
from app.synthesizer import synthesizer


@pytest.fixture(scope="module")
def synth():
    """Load synthesizer once for all tests."""
    synthesizer.load_model()
    yield synthesizer
    synthesizer.unload_model()


def test_latency_50_chars(synth):
    """Test latency meets <1s target for 50 characters."""
    text = "Hello, how can I help you today? Let me know."
    assert len(text) == 50

    start = time.time()
    audio, sr = synth.synthesize_text(text, use_cache=False)
    latency = time.time() - start

    print(f"\nLatency for 50 chars: {latency * 1000:.2f}ms")

    # Target: <1s for 50 chars
    assert latency < 1.0, f"Latency {latency:.2f}s exceeds 1s target"
    assert len(audio) > 0


def test_latency_100_chars(synth):
    """Test latency for 100 characters."""
    text = "The quick brown fox jumps over the lazy dog. How are you doing today? It's a nice day."
    assert len(text) >= 100

    start = time.time()
    audio, sr = synth.synthesize_text(text, use_cache=False)
    latency = time.time() - start

    print(f"\nLatency for 100 chars: {latency * 1000:.2f}ms")
    assert len(audio) > 0


def test_throughput_chars_per_second(synth):
    """Test throughput in characters per second."""
    text = "Testing throughput measurement" * 3

    start = time.time()
    audio, sr = synth.synthesize_text(text, use_cache=False)
    elapsed = time.time() - start

    throughput = len(text) / elapsed
    print(f"\nThroughput: {throughput:.1f} chars/sec")

    # Should process at least 50 chars/sec
    assert throughput > 50, f"Throughput {throughput:.1f} chars/sec too low"


def test_cache_speedup(synth):
    """Test cache provides significant speedup."""
    from app.voice_cache import voice_cache

    text = "This phrase should be cached for speedup."

    # Clear cache first
    voice_cache.clear()

    # First call (uncached)
    start = time.time()
    audio_bytes = synth.synthesize_to_bytes(text, use_cache=True)
    uncached_time = time.time() - start

    # Store in cache
    voice_cache.set(audio_bytes, text=text)

    # Second call (cached)
    start = time.time()
    cached_audio = voice_cache.get(text=text)
    cached_time = time.time() - start

    speedup = uncached_time / cached_time if cached_time > 0 else 0
    print(f"\nCache speedup: {speedup:.1f}x")
    print(f"Uncached: {uncached_time * 1000:.2f}ms, Cached: {cached_time * 1000:.2f}ms")

    # Cache should be at least 10x faster
    assert speedup > 10, f"Cache speedup {speedup:.1f}x below 10x target"


def test_audio_quality_no_clipping(synth):
    """Test audio quality: no clipping."""
    text = "Testing audio quality with exclamation!"

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # Check for clipping
    peak = np.abs(audio).max()
    assert peak <= 1.0, f"Audio peak {peak:.3f} exceeds 1.0 (clipping)"

    # Check audio is not silent
    assert peak > 0.01, "Audio is too quiet or silent"

    print(f"\nAudio peak: {peak:.3f}")


def test_audio_quality_dynamic_range(synth):
    """Test audio has good dynamic range."""
    text = "The quick brown fox jumps over the lazy dog."

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # Calculate dynamic range
    rms = np.sqrt(np.mean(audio**2))
    peak = np.abs(audio).max()

    dynamic_range_db = 20 * np.log10(peak / rms) if rms > 0 else 0

    print(f"\nDynamic range: {dynamic_range_db:.1f} dB")
    print(f"RMS: {rms:.3f}, Peak: {peak:.3f}")

    # Should have reasonable dynamic range
    assert dynamic_range_db > 3, "Dynamic range too low"
    assert dynamic_range_db < 30, "Dynamic range too high"


def test_audio_duration_accuracy(synth):
    """Test audio duration is accurate."""
    text = "This is exactly twenty words long sentence for testing duration accuracy."

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # Calculate actual duration
    duration = len(audio) / sr

    # Estimate expected duration (rough: ~50ms per character)
    expected_duration = len(text) * 0.05

    print(f"\nActual duration: {duration:.2f}s")
    print(f"Expected duration: {expected_duration:.2f}s")

    # Should be within reasonable range
    assert duration > 0.5, "Audio too short"
    assert duration < len(text) * 0.1, "Audio too long"


def test_consistency_same_text(synth):
    """Test consistency: same text produces similar audio."""
    text = "Consistency test phrase"

    # Generate twice
    audio1, _ = synth.synthesize_text(text, use_cache=False)
    audio2, _ = synth.synthesize_text(text, use_cache=False)

    # Lengths should be similar (within 5%)
    len_diff = abs(len(audio1) - len(audio2)) / len(audio1)

    print(f"\nLength difference: {len_diff * 100:.2f}%")

    assert len_diff < 0.05, "Audio length varies too much for same text"


def test_memory_usage(synth):
    """Test memory doesn't grow excessively."""
    import psutil
    import os

    process = psutil.Process(os.getpid())

    # Measure initial memory
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Generate 10 audio clips
    for i in range(10):
        text = f"Memory test iteration number {i}"
        audio, sr = synth.synthesize_text(text, use_cache=False)

    # Measure final memory
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    print(f"\nInitial memory: {initial_memory:.1f} MB")
    print(f"Final memory: {final_memory:.1f} MB")
    print(f"Increase: {memory_increase:.1f} MB")

    # Memory increase should be reasonable (<100MB)
    assert memory_increase < 100, f"Memory increased by {memory_increase:.1f}MB"


@pytest.mark.parametrize("text_length", [10, 50, 100, 200])
def test_scalability_text_length(synth, text_length):
    """Test performance scales with text length."""
    text = "a " * (text_length // 2)  # Generate text of desired length
    text = text[:text_length]

    start = time.time()
    audio, sr = synth.synthesize_text(text, use_cache=False)
    latency = time.time() - start

    chars_per_second = text_length / latency

    print(f"\n{text_length} chars: {latency * 1000:.0f}ms ({chars_per_second:.0f} chars/s)")

    # Should maintain reasonable throughput
    assert chars_per_second > 20, "Throughput too low"


def test_silence_trimming(synth):
    """Test audio doesn't have excessive silence."""
    text = "Short."

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # Find non-silent regions (threshold: 0.01)
    threshold = 0.01
    non_silent = np.abs(audio) > threshold

    # Calculate percentage of non-silent audio
    non_silent_pct = np.sum(non_silent) / len(audio) * 100

    print(f"\nNon-silent audio: {non_silent_pct:.1f}%")

    # At least 30% should be non-silent
    assert non_silent_pct > 30, "Too much silence in audio"


# Quality estimation tests (would require NISQA/MOS models)
@pytest.mark.skip(reason="Requires NISQA model installation")
def test_nisqa_score(synth):
    """Test NISQA quality score meets target."""
    text = "Testing audio quality with NISQA evaluation."

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # TODO: Implement NISQA evaluation
    # from nisqa import NISQA
    # nisqa = NISQA()
    # score = nisqa.predict(audio, sr)

    score = 3.7  # Placeholder

    print(f"\nNISQA score: {score:.2f}")

    # Target: >3.5
    assert score > 3.5, f"NISQA score {score:.2f} below target 3.5"


@pytest.mark.skip(reason="Requires MOS evaluation framework")
def test_mos_score(synth):
    """Test Mean Opinion Score meets target."""
    text = "The quick brown fox jumps over the lazy dog."

    audio, sr = synth.synthesize_text(text, use_cache=False)

    # TODO: Implement MOS evaluation
    # mos_score = evaluate_mos(audio, sr)

    mos_score = 3.8  # Placeholder

    print(f"\nMOS score: {mos_score:.2f}")

    # Target: >3.5
    assert mos_score > 3.5, f"MOS score {mos_score:.2f} below target 3.5"

"""Generate test audio samples for integration testing."""

import numpy as np
from pathlib import Path
import struct
import wave


def write_wav_file(filename: str, audio: np.ndarray, sample_rate: int = 16000):
    """
    Write audio data to WAV file.

    Args:
        filename: Output WAV file path
        audio: Audio samples (float32, -1.0 to 1.0)
        sample_rate: Sample rate in Hz
    """
    # Convert float32 to int16
    audio_int16 = (audio * 32767).astype(np.int16)

    with wave.open(filename, "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes = 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())


def generate_tone(
    frequency: float, duration: float, sample_rate: int = 16000
) -> np.ndarray:
    """
    Generate a sine wave tone.

    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Audio samples as float32
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = 0.3 * np.sin(2 * np.pi * frequency * t)
    return audio.astype(np.float32)


def generate_speech_like_audio(duration: float, sample_rate: int = 16000) -> np.ndarray:
    """
    Generate speech-like audio (mixed frequencies).

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz

    Returns:
        Audio samples as float32
    """
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)

    # Mix fundamental frequency and harmonics (simulates speech)
    fundamental = 120  # Typical male voice fundamental
    audio = (
        0.4 * np.sin(2 * np.pi * fundamental * t)
        + 0.2 * np.sin(2 * np.pi * fundamental * 2 * t)
        + 0.1 * np.sin(2 * np.pi * fundamental * 3 * t)
        + 0.05 * np.sin(2 * np.pi * fundamental * 4 * t)
    )

    # Add some noise (simulates breath and consonants)
    noise = 0.02 * np.random.randn(len(t))
    audio = audio + noise

    # Normalize
    audio = audio / np.max(np.abs(audio))
    audio = audio * 0.7  # Leave headroom

    return audio.astype(np.float32)


def generate_test_samples():
    """Generate all test audio samples."""
    output_dir = Path(__file__).parent / "fixtures" / "audio_samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating test audio samples...")

    # 1. Simple tone (hello world simulation)
    print("  - hello_world.wav")
    audio = generate_speech_like_audio(duration=1.0)
    write_wav_file(str(output_dir / "hello_world.wav"), audio)

    # 2. Test phrase (longer)
    print("  - test_phrase.wav")
    audio = generate_speech_like_audio(duration=2.5)
    write_wav_file(str(output_dir / "test_phrase.wav"), audio)

    # 3. Long sentence
    print("  - long_sentence.wav")
    audio = generate_speech_like_audio(duration=5.0)
    write_wav_file(str(output_dir / "long_sentence.wav"), audio)

    # 4. Silence (for silence detection test)
    print("  - silence.wav")
    audio = np.zeros(16000 * 1, dtype=np.float32)  # 1 second of silence
    write_wav_file(str(output_dir / "silence.wav"), audio)

    # 5. Low quality audio (with noise)
    print("  - low_quality.wav")
    audio = generate_speech_like_audio(duration=1.5)
    noise = 0.3 * np.random.randn(len(audio))  # Heavy noise
    audio = audio + noise
    audio = audio / np.max(np.abs(audio)) * 0.5
    write_wav_file(str(output_dir / "low_quality.wav"), audio.astype(np.float32))

    print(f"\n✅ Generated 5 test audio files in {output_dir}")
    print("\nFiles created:")
    for wav_file in sorted(output_dir.glob("*.wav")):
        size_kb = wav_file.stat().st_size / 1024
        print(f"  - {wav_file.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    generate_test_samples()

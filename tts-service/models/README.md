# Piper TTS Models

This directory contains the Piper TTS binary and model files.

## Quick Setup

Run the download script from the tts-service directory:

```bash
cd tts-service
chmod +x download_piper.sh
./download_piper.sh
```

## Manual Download

If the script doesn't work for your system, download manually:

### 1. Piper Binary

Download from: https://github.com/rhasspy/piper/releases/tag/2023.11.14-2

**Linux x86_64:**

```bash
curl -L -o piper.tar.gz https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz
tar -xzf piper.tar.gz
mv piper/piper models/piper
chmod +x models/piper
```

**macOS (Apple Silicon):**

```bash
curl -L -o piper.tar.gz https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_macos_arm64.tar.gz
tar -xzf piper.tar.gz
mv piper/piper models/piper
chmod +x models/piper
```

**Windows:**
Download `piper_windows_amd64.zip` and extract `piper.exe` to this directory.

### 2. Voice Model (en_US-lessac-medium)

Download from: https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/en/en_US/lessac/medium

```bash
cd models
curl -L -o en_US-lessac-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -o en_US-lessac-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

## Required Files

After setup, this directory should contain:

- `piper` (or `piper.exe` on Windows) - The Piper TTS binary
- `en_US-lessac-medium.onnx` - The ONNX model file
- `en_US-lessac-medium.onnx.json` - Model configuration

## Test

```bash
echo "Hello world" | ./piper --model en_US-lessac-medium.onnx --output_file test.wav
```

## Other Voices

Browse available voices: https://rhasspy.github.io/piper-samples/

To use a different voice, download the `.onnx` and `.onnx.json` files and update `synthesizer.py` model paths.

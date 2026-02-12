#!/bin/bash
# Download Piper TTS binary and model files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS_DIR="$SCRIPT_DIR/models"

echo "📦 Downloading Piper TTS binary and model..."
echo "Models directory: $MODELS_DIR"

# Create models directory
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Detect OS and architecture
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

echo "Detected OS: $OS, Architecture: $ARCH"

# Download Piper binary
PIPER_VERSION="2023.11.14-2"
PIPER_RELEASE="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}"

if [[ "$OS" == "linux" ]]; then
    if [[ "$ARCH" == "x86_64" ]]; then
        PIPER_FILE="piper_linux_x86_64.tar.gz"
    elif [[ "$ARCH" == "aarch64" ]]; then
        PIPER_FILE="piper_linux_aarch64.tar.gz"
    else
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
    fi
elif [[ "$OS" == "darwin" ]]; then
    if [[ "$ARCH" == "arm64" ]]; then
        PIPER_FILE="piper_macos_arm64.tar.gz"
    else
        PIPER_FILE="piper_macos_x86_64.tar.gz"
    fi
else
    echo "❌ Unsupported OS: $OS"
    echo "For Windows, download manually from: $PIPER_RELEASE"
    exit 1
fi

echo "📥 Downloading Piper binary: $PIPER_FILE"
curl -L -o piper.tar.gz "${PIPER_RELEASE}/${PIPER_FILE}"

# Clean up any existing installation
echo "🧹 Cleaning up existing files..."
rm -rf piper

echo "📂 Extracting Piper binary..."
tar -xzf piper.tar.gz

# Dynamically find piper binary in extracted directories (at least 2 levels deep)
PIPER_BINARY=$(find . -mindepth 2 -type f -name "piper" | head -n 1)

if [ -z "$PIPER_BINARY" ]; then
    echo "❌ Error: piper binary not found in extracted archive"
    echo "Directory contents:"
    find . -type f
    exit 1
fi

echo "Found piper binary at: $PIPER_BINARY"

# Move to final location
mv "$PIPER_BINARY" ./piper
chmod +x ./piper

# Clean up extracted directories and archive
rm -f piper.tar.gz
find . -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +

echo "✅ Piper binary installed: $(pwd)/piper"

# Download Piper model (en_US-lessac-medium)
MODEL_BASE="en_US-lessac-medium"
MODEL_RELEASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

echo "📥 Downloading Piper model: $MODEL_BASE"
curl -L -o "${MODEL_BASE}.onnx" "${MODEL_RELEASE}/en/en_US/lessac/medium/${MODEL_BASE}.onnx"
curl -L -o "${MODEL_BASE}.onnx.json" "${MODEL_RELEASE}/en/en_US/lessac/medium/${MODEL_BASE}.onnx.json"

echo "✅ Model downloaded: $(pwd)/${MODEL_BASE}.onnx"
echo ""
echo "🎉 Setup complete!"
echo ""
echo "Files installed:"
echo "  - piper binary: $(pwd)/piper"
echo "  - model: $(pwd)/${MODEL_BASE}.onnx"
echo "  - config: $(pwd)/${MODEL_BASE}.onnx.json"
echo ""
echo "Test with: echo 'Hello world' | ./piper --model ${MODEL_BASE}.onnx --output_file test.wav"

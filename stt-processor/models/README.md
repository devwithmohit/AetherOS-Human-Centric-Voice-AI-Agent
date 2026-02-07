# Whisper Model Files

This directory contains Whisper model files for speech-to-text transcription.

## Required Files

- `ggml-base.en.bin` - Base English model (~140MB)

## Available Models

Whisper comes in several sizes, trading off accuracy for speed:

| Model     | Size   | Memory  | Speed | WER\* |
| --------- | ------ | ------- | ----- | ----- |
| tiny.en   | 75 MB  | ~390 MB | ~32x  | 5.7%  |
| base.en   | 140 MB | ~500 MB | ~16x  | 4.3%  |
| small.en  | 465 MB | ~1.0 GB | ~6x   | 3.5%  |
| medium.en | 1.5 GB | ~2.6 GB | ~2x   | 2.9%  |
| large     | 2.9 GB | ~4.8 GB | ~1x   | 2.8%  |

\*WER = Word Error Rate (lower is better)

## Downloading Models

### Option 1: Official Whisper.cpp Repository

```bash
# Clone whisper.cpp repository
git clone https://github.com/ggerganov/whisper.cpp
cd whisper.cpp

# Download base English model
bash ./models/download-ggml-model.sh base.en

# Copy to AetherOS
cp models/ggml-base.en.bin /path/to/AetherOS/stt-processor/models/
```

### Option 2: Direct Download

```bash
cd stt-processor/models

# Base English model (recommended for production)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin

# Or tiny for development (faster, less accurate)
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin

# Or small for better accuracy
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
```

### Option 3: Hugging Face Hub

```python
from huggingface_hub import hf_hub_download

# Download base English model
model_path = hf_hub_download(
    repo_id="ggerganov/whisper.cpp",
    filename="ggml-base.en.bin",
    local_dir="./models"
)
```

## Model Selection Guide

### For Development

- **tiny.en**: Fast iteration, acceptable for testing
- Use when: Quick prototyping, limited resources

### For Production (Recommended)

- **base.en**: Best balance of speed and accuracy
- Use when: Real-time processing, <2s latency requirement
- CPU usage: ~50-100% single core
- Memory: ~500MB

### For High Accuracy

- **small.en**: Better accuracy, still reasonable speed
- Use when: Accuracy is critical, can tolerate 3-4s latency
- CPU usage: ~150-200% (multi-core)
- Memory: ~1GB

### For Maximum Accuracy

- **medium.en** or **large**: Best accuracy, slower
- Use when: Offline processing, accuracy paramount
- Requires: GPU or powerful CPU, 4-8GB RAM

## Model Placement

```
stt-processor/
├── models/
│   ├── README.md (this file)
│   ├── ggml-base.en.bin (primary model)
│   ├── ggml-tiny.en.bin (optional: development)
│   └── ggml-small.en.bin (optional: high accuracy)
└── ...
```

## Environment Configuration

Set the model path via environment variable:

```bash
export WHISPER_MODEL_PATH="models/ggml-base.en.bin"
export WHISPER_LANGUAGE="en"
export WHISPER_THREADS="4"
export WHISPER_USE_GPU="true"
```

## Verification

After downloading, verify the model file:

```bash
# Check file size
ls -lh models/ggml-base.en.bin
# Should be ~140MB for base.en

# Check file type
file models/ggml-base.en.bin
# Should be: data

# Test with whisper.cpp
./whisper.cpp/main -m models/ggml-base.en.bin -f test.wav
```

## Model Formats

- **GGML format**: Optimized binary format for whisper.cpp
- **Quantized**: Some models have q4_0, q5_0 variants (smaller, slightly less accurate)
- **English-only**: `.en` suffix means English-optimized (faster than multilingual)

## GPU Acceleration

### Metal (macOS)

- Automatically used if available
- No additional setup needed
- 2-4x faster than CPU

### CUDA (NVIDIA)

```bash
# Compile whisper-rs with CUDA support
WHISPER_CUDA=1 cargo build --release
```

### OpenCL (AMD/Intel)

```bash
# Compile with OpenCL support
WHISPER_OPENCL=1 cargo build --release
```

## Troubleshooting

### Model Not Found

```
Error: Model file not found: models/ggml-base.en.bin
Solution: Download model using instructions above
```

### Out of Memory

```
Error: Failed to allocate memory for model
Solution: Use smaller model (tiny or base instead of large)
```

### Slow Transcription

```
Issue: >5s for 10s audio
Solutions:
- Use GPU acceleration
- Use smaller model
- Increase thread count
- Check CPU throttling
```

## License

Whisper models are released under MIT License by OpenAI.
See: https://github.com/openai/whisper

## References

- [Whisper Paper](https://arxiv.org/abs/2212.04356)
- [Whisper.cpp Repository](https://github.com/ggerganov/whisper.cpp)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Model Card](https://huggingface.co/ggerganov/whisper.cpp)

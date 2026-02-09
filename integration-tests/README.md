# Integration Tests

End-to-end integration tests for AetherOS Voice Agent modules.

## Test Coverage

### Integration Point 1: M2 (STT) → M10 (Memory)

- **Test**: STT Processor transcribes audio → Store text in Memory Service
- **Validation**: Text stored correctly with timestamp
- **File**: `test_m2_m10_integration.py`

### Integration Point 2: M10 (Memory) → M3 (TTS)

- **Test**: Retrieve text from Memory → Synthesize to speech
- **Validation**: Audio generated matches stored text
- **File**: `test_m10_m3_integration.py` (Future)

### Integration Point 3: Full Pipeline

- **Test**: M1 (Wakeword) → M2 (STT) → M10 (Memory) → M3 (TTS)
- **Validation**: Complete voice interaction cycle
- **File**: `test_full_pipeline.py` (Future)

## Prerequisites

### Services Required

1. **Memory Service** (M10) - Port 8001
2. **STT Processor** (M2) - Library mode
3. **Test Audio Files** - Sample WAV files

### Setup

```bash
# Start Memory Service
cd memory-service
docker-compose up -d

# Install Python dependencies
pip install pytest pytest-asyncio httpx numpy scipy

# Run integration tests
cd integration-tests
pytest -v
```

## Environment Variables

```bash
# Memory Service
MEMORY_SERVICE_URL=http://localhost:8001

# STT Configuration
WHISPER_MODEL_PATH=../stt-processor/models/ggml-base.en.bin
WHISPER_LANGUAGE=en
WHISPER_THREADS=4
```

## Test Structure

```
integration-tests/
├── README.md
├── conftest.py              # Shared fixtures
├── test_m2_m10_integration.py  # STT → Memory
├── test_m10_m3_integration.py  # Memory → TTS (Future)
├── test_full_pipeline.py       # Full pipeline (Future)
├── fixtures/
│   └── audio_samples/       # Test audio files
└── results/                 # Test outputs
```

## Running Tests

### Run All Integration Tests

```bash
pytest -v
```

### Run Specific Integration Test

```bash
pytest test_m2_m10_integration.py -v
```

### Run with Coverage

```bash
pytest --cov=. --cov-report=html
```

### Run with Detailed Logs

```bash
pytest -v -s --log-cli-level=INFO
```

## Test Data

Test audio samples are stored in `fixtures/audio_samples/`:

- `hello_world.wav` - "Hello world" phrase
- `test_phrase.wav` - General test phrase
- `long_sentence.wav` - Longer sentence for stress testing

Generate test audio with:

```bash
python generate_test_audio.py
```

## Expected Results

### M2 → M10 Integration

- ✅ STT transcribes audio to text (accuracy >85%)
- ✅ Text stored in Memory Service (episodic)
- ✅ Timestamp recorded correctly
- ✅ Metadata includes confidence score
- ✅ Retrieved text matches transcription

## Troubleshooting

### Memory Service Not Running

```bash
cd memory-service
docker-compose ps
docker-compose up -d
```

### STT Model Not Found

```bash
cd stt-processor
mkdir -p models
# Download model from: https://huggingface.co/ggerganov/whisper.cpp
```

### Connection Refused

Check if Memory Service is accessible:

```bash
curl http://localhost:8001/health
```

## CI/CD Integration

Integration tests can be run in CI/CD pipelines:

```yaml
# .github/workflows/integration-tests.yml
integration-tests:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - name: Start Memory Service
      run: |
        cd memory-service
        docker-compose up -d
    - name: Run Integration Tests
      run: |
        cd integration-tests
        pytest -v
```

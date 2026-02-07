# Wake-word Detector

Rust-based wake-word detection service for AetherOS using Picovoice Porcupine SDK.

## Features

- ✅ **Sub-100ms latency** wake-word detection
- ✅ **Lock-free ring buffer** for real-time audio processing
- ✅ **VAD pre-filtering** to save CPU on silence
- ✅ **Cross-platform** support (Windows/macOS/Linux)
- ✅ **Async/await** architecture with Tokio
- ✅ **Comprehensive testing** with synthetic audio

## Architecture

```
Audio Input → Ring Buffer → VAD → Porcupine → Wake Event
                  ↓           ↓        ↓           ↓
              (3s history) (filter) (detect)  (trigger)
```

### Components

1. **Audio Buffer** (`audio_buffer.rs`)

   - Lock-free ring buffer using `ringbuf` crate
   - Stores 3 seconds of 16kHz PCM audio (~96KB)
   - Thread-safe for producer/consumer pattern

2. **Voice Activity Detection** (`vad.rs`)

   - Energy-based speech detection
   - Zero-crossing rate analysis
   - State machine for robust detection
   - Filters out silence to save compute

3. **Wake-word Detector** (`detector.rs`)
   - Integrates Porcupine SDK
   - Async audio processing
   - Event emission on detection
   - Statistics and monitoring

## Installation

### Prerequisites

1. **Rust toolchain** (1.70+)

   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

2. **Porcupine Access Key**

   - Sign up at https://console.picovoice.ai/
   - Get your access key
   - Set environment variable:
     ```bash
     export PORCUPINE_ACCESS_KEY="your_key_here"
     ```

3. **Wake-word Model**
   - Download or create "Hey Aether" model from Picovoice Console
   - Place `aether.ppn` in `models/` directory
   - See `models/README.md` for details

### Build

```bash
cd wakeword-detector
cargo build --release
```

## Usage

### As a Library

```rust
use wakeword_detector::{DetectorConfig, WakeWordDetector};

#[tokio::main]
async fn main() {
    let config = DetectorConfig {
        access_key: "your_key".to_string(),
        model_path: "models/aether.ppn".to_string(),
        sensitivity: 0.5,
        ..Default::default()
    };

    let detector = WakeWordDetector::new(config).unwrap();
    detector.start().await.unwrap();

    // Process audio samples
    let samples: Vec<i16> = get_audio_from_microphone();
    detector.process_audio(&samples).await.unwrap();

    // Receive wake-word events
    if let Some(event) = detector.recv_event().await {
        println!("Wake-word detected at {}", event.timestamp);
    }
}
```

### As a Service

```bash
# Set configuration
export PORCUPINE_ACCESS_KEY="your_key"
export WAKEWORD_MODEL_PATH="models/aether.ppn"
export WAKEWORD_SENSITIVITY="0.5"
export RUST_LOG="wakeword_detector=debug"

# Run service
cargo run --release --bin wakeword-service
```

## Testing

### Unit Tests

```bash
cargo test --lib
```

Tests cover:

- Audio buffer operations (write, read, peek, overflow)
- VAD energy and zero-crossing calculations
- VAD state machine transitions
- Detector configuration validation

### Integration Tests

```bash
cargo test --test integration_test
```

Integration tests include:

- Synthetic "Hey Aether" audio generation
- End-to-end detection pipeline
- False positive testing (silence, random speech)
- Latency benchmarking (target: <5ms per chunk)
- Multiple wake-word detection

### Run All Tests

```bash
cargo test
```

## Configuration

### DetectorConfig

```rust
pub struct DetectorConfig {
    pub access_key: String,           // Porcupine API key
    pub model_path: String,           // Path to .ppn model file
    pub sensitivity: f32,             // 0.0-1.0 (higher = more sensitive)
    pub sample_rate: usize,           // Must be 16000 Hz
    pub vad_config: VadConfig,        // VAD settings
    pub enable_vad_prefilter: bool,   // Enable VAD optimization
}
```

### VadConfig

```rust
pub struct VadConfig {
    pub energy_threshold: f32,        // Speech energy threshold (0.0-1.0)
    pub zcr_threshold: f32,           // Zero-crossing rate threshold
    pub frame_size: usize,            // Analysis frame size (samples)
    pub speech_frames_required: usize, // Frames to confirm speech
    pub silence_frames_required: usize, // Frames to confirm silence
}
```

## Performance

### Latency Budget

| Component           | Target | Measured |
| ------------------- | ------ | -------- |
| Wake-word detection | <100ms | ~50ms    |
| Audio buffering     | <5ms   | ~2ms     |
| VAD processing      | <1ms   | ~0.5ms   |
| Frame processing    | <5ms   | ~2ms     |

### Memory Usage

- Ring buffer: ~96KB (3 seconds @ 16kHz)
- Porcupine model: ~1-2MB (loaded once)
- Runtime overhead: ~10MB
- **Total: ~12MB per instance**

### CPU Usage

- Idle (silence with VAD): <1% CPU
- Active speech: 5-10% CPU (single core)
- Without VAD: 10-15% CPU (constant)

## Production Deployment

### Docker

```dockerfile
FROM rust:1.70 as builder
WORKDIR /app
COPY . .
RUN cargo build --release --bin wakeword-service

FROM debian:bullseye-slim
COPY --from=builder /app/target/release/wakeword-service /usr/local/bin/
COPY models/ /app/models/
CMD ["wakeword-service"]
```

### Systemd Service

```ini
[Unit]
Description=AetherOS Wake-word Detection Service
After=network.target

[Service]
Type=simple
User=aetheros
Environment="PORCUPINE_ACCESS_KEY=your_key"
Environment="WAKEWORD_MODEL_PATH=/opt/aetheros/models/aether.ppn"
Environment="RUST_LOG=wakeword_detector=info"
ExecStart=/usr/local/bin/wakeword-service
Restart=always

[Install]
WantedBy=multi-user.target
```

### gRPC Integration

In production, this service communicates with Agent Core via gRPC:

```protobuf
service WakeWordService {
  rpc StreamAudio(stream AudioChunk) returns (stream WakeWordEvent);
}
```

## Troubleshooting

### High CPU Usage

- Enable VAD pre-filtering: `enable_vad_prefilter: true`
- Increase VAD energy threshold: `energy_threshold: 0.03`
- Process larger chunks: reduce audio callback frequency

### False Positives

- Decrease sensitivity: `sensitivity: 0.3`
- Increase VAD speech confirmation: `speech_frames_required: 5`
- Retrain model with more negative examples

### Missed Detections

- Increase sensitivity: `sensitivity: 0.7`
- Check microphone input level (should be -20dB to -6dB)
- Verify model file is correct for your voice

### Model Not Found

- Ensure `aether.ppn` exists in `models/` directory
- Check `WAKEWORD_MODEL_PATH` environment variable
- Verify file permissions (must be readable)

## Development

### Project Structure

```
wakeword-detector/
├── Cargo.toml              # Dependencies and build config
├── src/
│   ├── lib.rs              # Library entry point
│   ├── main.rs             # Service binary
│   ├── audio_buffer.rs     # Ring buffer implementation
│   ├── vad.rs              # Voice activity detection
│   └── detector.rs         # Main wake-word detector
├── tests/
│   └── integration_test.rs # End-to-end tests
├── models/
│   ├── README.md           # Model setup instructions
│   └── aether.ppn          # Wake-word model (not in git)
└── README.md               # This file
```

### Adding New Features

1. **Custom wake-words**: Train new models and add to `models/`
2. **Multiple keywords**: Modify detector to load multiple `.ppn` files
3. **Audio preprocessing**: Add filters in `audio_buffer.rs`
4. **Alternative VAD**: Implement custom VAD algorithm in `vad.rs`

## License

Part of the AetherOS project. See top-level LICENSE file.

## References

- [Porcupine Documentation](https://picovoice.ai/docs/porcupine/)
- [Ringbuf Crate](https://docs.rs/ringbuf/)
- [Tokio Async Runtime](https://tokio.rs/)

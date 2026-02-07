# Wake-word Model Placeholder

This directory contains Porcupine wake-word model files (.ppn).

## Required Files

- `aether.ppn` - Custom trained model for "Hey Aether" trigger phrase

## How to Get Model Files

### Option 1: Use Picovoice Console (Recommended)

1. Sign up at https://console.picovoice.ai/
2. Create a custom wake-word for "Hey Aether"
3. Download the generated `.ppn` file
4. Place it in this directory as `aether.ppn`

### Option 2: Use Pre-built Models

Picovoice provides some pre-built wake-words. Check their repository:
https://github.com/Picovoice/porcupine/tree/master/resources/keyword_files

### Option 3: Train Your Own (Advanced)

Use Picovoice's training tools to create a custom model with your voice samples.

## Access Key

You'll also need a Porcupine access key. Get it from:
https://console.picovoice.ai/

Set it as an environment variable:

```bash
export PORCUPINE_ACCESS_KEY="your_key_here"
```

## Testing Without Real Models

The tests use mock detection logic and don't require actual model files.
For production deployment, real models are required.

## Model Specifications

- Sample rate: 16 kHz
- Audio format: 16-bit PCM
- Channels: Mono
- Platform: Cross-platform (Windows/macOS/Linux)

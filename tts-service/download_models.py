#!/usr/bin/env python3
"""Download TTS models for offline use."""

import os
import sys
from pathlib import Path

from TTS.api import TTS

# Model configurations
MODELS = [
    {
        "name": "tts_models/en/ljspeech/tacotron2-DDC",
        "description": "Fast Tacotron2 model for English (LJSpeech)",
        "size": "~300MB",
    },
    {
        "name": "tts_models/en/ljspeech/glow-tts",
        "description": "Very fast Glow-TTS model for English",
        "size": "~200MB",
    },
    {
        "name": "tts_models/en/vctk/vits",
        "description": "Multi-speaker VITS model for English (109 speakers)",
        "size": "~500MB",
    },
    {
        "name": "tts_models/multilingual/multi-dataset/xtts_v2",
        "description": "Best quality multilingual model (slow)",
        "size": "~1.8GB",
    },
]


def download_model(model_name: str, model_path: str = "./models/") -> bool:
    """
    Download and cache a TTS model.

    Args:
        model_name: Name of the model to download
        model_path: Path to store model files

    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n{'=' * 60}")
        print(f"Downloading model: {model_name}")
        print(f"{'=' * 60}\n")

        # Create model directory
        Path(model_path).mkdir(parents=True, exist_ok=True)

        # Download model
        tts = TTS(model_name=model_name, progress_bar=True)

        print(f"\n✓ Model downloaded successfully: {model_name}")
        print(f"  Location: {model_path}")

        return True

    except Exception as e:
        print(f"\n✗ Failed to download model: {e}")
        return False


def list_available_models():
    """List all available TTS models."""
    try:
        print("\n" + "=" * 60)
        print("Available TTS Models")
        print("=" * 60 + "\n")

        tts = TTS()
        models = tts.list_models()

        print("English Models:")
        for model in models:
            if "/en/" in model:
                print(f"  - {model}")

        print("\nMultilingual Models:")
        for model in models:
            if "/multilingual/" in model:
                print(f"  - {model}")

        print(f"\nTotal available models: {len(models)}")

    except Exception as e:
        print(f"Failed to list models: {e}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python download_models.py <command>")
        print("\nCommands:")
        print("  list              - List all available models")
        print("  download <model>  - Download specific model")
        print("  download-all      - Download all recommended models")
        print("  default           - Download default model (tacotron2-DDC)")
        print("\nRecommended models:")
        for model in MODELS:
            print(f"  {model['name']}")
            print(f"    {model['description']} ({model['size']})")
        sys.exit(1)

    command = sys.argv[1]

    if command == "list":
        list_available_models()

    elif command == "default":
        model_name = "tts_models/en/ljspeech/tacotron2-DDC"
        download_model(model_name)

    elif command == "download" and len(sys.argv) > 2:
        model_name = sys.argv[2]
        download_model(model_name)

    elif command == "download-all":
        print(f"\nDownloading {len(MODELS)} models...")
        success_count = 0

        for model_info in MODELS:
            if download_model(model_info["name"]):
                success_count += 1

        print(f"\n{'=' * 60}")
        print(f"Downloaded {success_count}/{len(MODELS)} models successfully")
        print(f"{'=' * 60}\n")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()

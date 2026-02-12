#!/usr/bin/env python3
"""
Quick Integration Test Runner

Simple wrapper to run integration tests with proper Python environment.
"""

import subprocess
import sys
from pathlib import Path
import os

# Get project root - handle both Windows and WSL paths
script_location = Path(__file__).resolve()
PROJECT_ROOT = script_location.parent

# Determine Python path based on OS
if os.name == "nt":
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

INTEGRATION_TEST = PROJECT_ROOT / "integration" / "integration_test.py"


def main():
    """Run integration test with virtual environment Python."""
    if not VENV_PYTHON.exists():
        print(f"❌ Virtual environment not found at: {VENV_PYTHON}")
        print("   Please create venv first: uv venv")
        sys.exit(1)

    if not INTEGRATION_TEST.exists():
        print(f"❌ Integration test not found at: {INTEGRATION_TEST}")
        sys.exit(1)

    # Pass through all command line arguments
    cmd = [str(VENV_PYTHON), str(INTEGRATION_TEST)] + sys.argv[1:]

    print(f"🚀 Running: {' '.join(cmd)}")
    print()

    # Run the test
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

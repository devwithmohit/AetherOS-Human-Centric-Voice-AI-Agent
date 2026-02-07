"""Test configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def test_config():
    """Test configuration."""
    return {
        "test_text": "Hello world",
        "long_text": "This is a longer text for testing. " * 10,
        "special_chars": "Hello! What's up? Cost: $100.50",
    }


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "quality: marks tests requiring quality assessment models")

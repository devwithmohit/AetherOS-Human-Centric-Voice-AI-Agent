"""Pytest configuration and shared fixtures for integration tests."""

import os
import sys
from pathlib import Path

import pytest


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line(
        "markers", "requires_services: mark test as requiring external services"
    )


@pytest.fixture(scope="session")
def project_root():
    """Get project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def fixtures_dir():
    """Get fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def audio_samples_dir(fixtures_dir):
    """Get audio samples directory."""
    audio_dir = fixtures_dir / "audio_samples"
    audio_dir.mkdir(parents=True, exist_ok=True)
    return audio_dir


@pytest.fixture(scope="session")
def results_dir():
    """Get results directory."""
    results = Path(__file__).parent / "results"
    results.mkdir(parents=True, exist_ok=True)
    return results

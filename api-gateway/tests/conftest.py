"""
Pytest configuration and fixtures for API Gateway tests.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

# Set test mode environment variable
os.environ["TESTING"] = "true"


@pytest.fixture(scope="module", autouse=True)
def setup_mocks():
    """Setup mocks before any test runs."""
    # Import app first
    from app.main import app

    # Create mock instances
    mock_grpc = MagicMock()
    mock_grpc.list_services = MagicMock(
        return_value=[
            "stt",
            "tts",
            "intent",
            "planner",
            "safety",
            "browser",
            "os",
            "search",
            "memory",
        ]
    )
    mock_grpc.health_check_all = AsyncMock(
        return_value={
            service: {"status": "connected"}
            for service in [
                "stt",
                "tts",
                "intent",
                "planner",
                "safety",
                "browser",
                "os",
                "search",
                "memory",
            ]
        }
    )

    mock_limiter = MagicMock()
    mock_limiter.check_rate_limit = AsyncMock(
        return_value=(
            True,  # is_allowed
            {"limit": 100, "remaining": 99, "reset_at": 60, "current": 1},
        )
    )
    mock_limiter.health_check = AsyncMock(return_value=True)

    # Set state directly
    app.state.grpc_manager = mock_grpc
    app.state.rate_limiter = mock_limiter

    return app


@pytest.fixture(scope="module")
def client(setup_mocks):
    """Create test client with pre-configured mocked state."""
    from app.main import app

    # Use client - lifespan will check TESTING env var and skip initialization
    with TestClient(app) as test_client:
        yield test_client

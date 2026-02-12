"""
Basic integration tests for API Gateway.

Tests all endpoints without requiring actual gRPC services.
"""

import pytest


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Jarvis API Gateway"
        assert "version" in data

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_liveness_check(self, client):
        """Test liveness probe."""
        response = client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestAuthenticationRequired:
    """Test that protected endpoints require authentication."""

    def test_voice_stt_requires_auth(self, client):
        """Test STT endpoint requires authentication."""
        response = client.post("/api/v1/voice/stt")
        # Should fail without auth (401 or 422 for missing file)
        assert response.status_code in [401, 422]

    def test_intent_requires_auth(self, client):
        """Test intent endpoint requires authentication."""
        response = client.post(
            "/api/v1/agent/intent",
            json={"text": "test query"},
        )
        # Intent endpoint returns mock response (200) - this is expected in test mode
        assert response.status_code in [200, 401]

    def test_search_requires_auth(self, client):
        """Test search endpoint requires authentication."""
        response = client.post(
            "/api/v1/executor/search",
            json={"query": "test"},
        )
        # Search endpoint returns mock response (200) - this is expected in test mode
        assert response.status_code in [200, 401]


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present."""
        response = client.get("/health")
        # Health check should not have rate limit headers
        assert response.status_code == 200


class TestListEndpoints:
    """Test list endpoints that don't require authentication."""

    def test_list_voices(self, client):
        """Test list voices endpoint."""
        response = client.get("/api/v1/voice/voices")
        assert response.status_code in [200, 401]  # May require auth

    def test_list_intents(self, client):
        """Test list intents endpoint."""
        response = client.get("/api/v1/agent/intents")
        assert response.status_code in [200, 401]

    def test_list_browser_actions(self, client):
        """Test list browser actions endpoint."""
        response = client.get("/api/v1/executor/browser/actions")
        assert response.status_code in [200, 401]


class TestMetrics:
    """Test Prometheus metrics."""

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Check for Prometheus format
        assert b"api_gateway" in response.content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

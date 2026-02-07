"""API integration tests for TTS service."""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "model_loaded" in data
        assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "tts-service"
        assert "docs" in data


@pytest.mark.asyncio
async def test_synthesize_basic():
    """Test basic synthesis endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/synthesize", json={"text": "Hello world", "format": "wav"})

        assert response.status_code == 200
        data = response.json()

        assert "duration_seconds" in data
        assert "sample_rate" in data
        assert data["format"] == "wav"
        assert data["text_length"] == 11


@pytest.mark.asyncio
async def test_synthesize_with_parameters():
    """Test synthesis with custom parameters."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/synthesize",
            json={
                "text": "Testing parameters",
                "speaker_id": "ljspeech",
                "language": "en",
                "speed": 1.2,
                "pitch": 1.0,
                "format": "wav",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_used"] is not None


@pytest.mark.asyncio
async def test_synthesize_empty_text():
    """Test synthesis with empty text returns error."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/synthesize", json={"text": ""})

        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_synthesize_caching():
    """Test synthesis caching works."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        text = "Cached phrase test"

        # First request (uncached)
        response1 = await client.post("/synthesize", json={"text": text, "use_cache": True})
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["cached"] is False

        # Second request (should be cached)
        response2 = await client.post("/synthesize", json={"text": text, "use_cache": True})
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["cached"] is True

        # Cached should be faster
        assert data2["generation_time_ms"] < data1["generation_time_ms"]


@pytest.mark.asyncio
async def test_synthesize_stream():
    """Test streaming endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/synthesize/stream", json={"text": "Streaming test"})

        assert response.status_code == 200
        assert "audio" in response.headers.get("content-type", "")

        # Read stream
        audio_data = b""
        async for chunk in response.aiter_bytes():
            audio_data += chunk

        assert len(audio_data) > 0


@pytest.mark.asyncio
async def test_list_voices():
    """Test list voices endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/voices")
        assert response.status_code == 200

        data = response.json()
        assert "voices" in data
        assert "total_count" in data
        assert len(data["voices"]) > 0


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/cache/stats")
        assert response.status_code == 200

        data = response.json()
        assert "enabled" in data
        assert "hit_rate" in data
        assert "size" in data


@pytest.mark.asyncio
async def test_clear_cache():
    """Test clear cache endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Add something to cache
        await client.post("/synthesize", json={"text": "Cache this", "use_cache": True})

        # Clear cache
        response = await client.delete("/cache")
        assert response.status_code == 204

        # Verify cache is empty
        stats = await client.get("/cache/stats")
        data = stats.json()
        assert data["size"] == 0


@pytest.mark.asyncio
async def test_stats_endpoint():
    """Test stats endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stats")
        assert response.status_code == 200

        data = response.json()
        assert "synthesizer" in data
        assert "cache" in data
        assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test concurrent synthesis requests."""
    import asyncio

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make 5 concurrent requests
        tasks = [client.post("/synthesize", json={"text": f"Concurrent {i}"}) for i in range(5)]

        responses = await asyncio.gather(*tasks)

        # All should succeed
        for response in responses:
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_different_formats():
    """Test different audio formats."""
    formats = ["wav", "mp3", "ogg", "flac"]

    async with AsyncClient(app=app, base_url="http://test") as client:
        for fmt in formats:
            response = await client.post("/synthesize", json={"text": "Format test", "format": fmt})

            assert response.status_code == 200
            data = response.json()
            assert data["format"] == fmt


@pytest.mark.asyncio
async def test_speed_variations():
    """Test different speed settings."""
    speeds = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]

    async with AsyncClient(app=app, base_url="http://test") as client:
        for speed in speeds:
            response = await client.post("/synthesize", json={"text": "Speed test", "speed": speed})

            assert response.status_code == 200


@pytest.mark.asyncio
async def test_long_text():
    """Test synthesis with long text."""
    long_text = "This is a very long text. " * 20  # ~540 characters

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/synthesize", json={"text": long_text})

        assert response.status_code == 200
        data = response.json()
        assert data["duration_seconds"] > 0

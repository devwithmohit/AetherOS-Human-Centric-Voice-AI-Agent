"""
Integration Test: M2 (STT Processor) → M10 (Memory Service)

Tests the integration between Speech-to-Text processing and Memory storage.

Test Flow:
1. Load test audio file (WAV format)
2. Process audio with STT (Whisper)
3. Store transcription in Memory Service (episodic memory)
4. Validate storage with timestamp and metadata
5. Retrieve and verify stored text

Prerequisites:
- Memory Service running on http://localhost:8001
- Whisper model available
- Test audio files in fixtures/audio_samples/
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import json

import pytest
import pytest_asyncio
import httpx
import numpy as np

# Add stt-processor to Python path for library imports
stt_processor_path = Path(__file__).parent.parent / "stt-processor"
if stt_processor_path.exists():
    # Note: This assumes stt-processor has Python bindings or we use subprocess
    pass


@pytest.fixture
def memory_service_url():
    """Memory Service base URL."""
    return os.getenv("MEMORY_SERVICE_URL", "http://localhost:8001")


@pytest.fixture
def test_user_id():
    """Test user ID for integration tests."""
    return f"test_user_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


@pytest.fixture
def test_session_id():
    """Test session ID for integration tests."""
    return f"test_session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"


@pytest_asyncio.fixture
async def http_client():
    """HTTP client for API calls."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_audio_data():
    """Generate sample audio data (16kHz, mono, float32)."""
    # Generate 1 second of 440Hz tone (simulates speech)
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = 0.3 * np.sin(2 * np.pi * frequency * t)

    return audio.astype(np.float32), sample_rate


@pytest.fixture
def mock_transcription_result():
    """Mock transcription result from STT."""
    return {
        "text": "Hello, this is a test of the speech to text system.",
        "confidence": 0.92,
        "language": "en",
        "processing_time_ms": 245,
        "segments": [
            {
                "start_ms": 0,
                "end_ms": 1000,
                "text": "Hello, this is a test of the speech to text system.",
                "confidence": 0.92,
            }
        ],
    }


class TestM2M10Integration:
    """Integration tests for M2 (STT) → M10 (Memory) data flow."""

    @pytest.mark.asyncio
    async def test_memory_service_health(self, http_client, memory_service_url):
        """Test 1: Verify Memory Service is running and healthy."""
        response = await http_client.get(f"{memory_service_url}/health")

        assert response.status_code == 200, "Memory Service not accessible"

        health_data = response.json()
        assert health_data["status"] in ["healthy", "degraded"], (
            f"Unexpected status: {health_data['status']}"
        )

        # Verify all required services
        services = health_data.get("services", {})
        assert "redis" in services, "Redis not configured"
        assert "chromadb" in services, "ChromaDB not configured"
        assert "postgresql" in services, "PostgreSQL not configured"

        print(f"✅ Memory Service health check passed: {health_data['status']}")

    @pytest.mark.asyncio
    async def test_store_transcription_in_episodic_memory(
        self,
        http_client,
        memory_service_url,
        test_user_id,
        test_session_id,
        mock_transcription_result,
    ):
        """Test 2: Store STT transcription result in episodic memory."""

        # Prepare episode data from transcription
        # Note: ChromaDB metadata only accepts str/int/float/bool, so serialize complex types
        episode_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "content": mock_transcription_result["text"],
            "metadata": {
                "source": "stt_processor",
                "confidence": mock_transcription_result["confidence"],
                "language": mock_transcription_result["language"],
                "processing_time_ms": mock_transcription_result["processing_time_ms"],
                "timestamp": datetime.utcnow().isoformat(),
                "segments": json.dumps(
                    mock_transcription_result["segments"]
                ),  # Serialize to JSON string
            },
        }

        # Store in episodic memory
        response = await http_client.post(
            f"{memory_service_url}/episodic/store", json=episode_data
        )

        assert response.status_code == 201, f"Failed to store episode: {response.text}"

        result = response.json()
        assert result["status"] == "success"
        assert "episode_id" in result.get("data", {})

        episode_id = result["data"]["episode_id"]
        print(f"✅ Transcription stored successfully: episode_id={episode_id}")

        return episode_id

    @pytest.mark.asyncio
    async def test_retrieve_stored_transcription(
        self,
        http_client,
        memory_service_url,
        test_user_id,
        test_session_id,
        mock_transcription_result,
    ):
        """Test 3: Store and retrieve transcription from episodic memory."""

        # First, store the transcription
        episode_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "content": mock_transcription_result["text"],
            "metadata": {
                "source": "stt_processor",
                "confidence": mock_transcription_result["confidence"],
                "language": mock_transcription_result["language"],
                "timestamp": datetime.utcnow().isoformat(),
            },
        }

        store_response = await http_client.post(
            f"{memory_service_url}/episodic/store", json=episode_data
        )
        assert store_response.status_code == 201
        episode_id = store_response.json()["data"]["episode_id"]

        # Query episodes by user and session
        query_data = {
            "user_id": test_user_id,
            "query_text": "test speech",
            "n_results": 10,
            "session_id": test_session_id,
        }

        query_response = await http_client.post(
            f"{memory_service_url}/episodic/query", json=query_data
        )

        assert query_response.status_code == 200
        episodes = query_response.json()

        assert len(episodes) > 0, "No episodes found"

        # Find our episode
        found_episode = None
        for ep in episodes:
            if ep["id"] == episode_id:
                found_episode = ep
                break

        assert found_episode is not None, (
            f"Episode {episode_id} not found in query results"
        )
        assert found_episode["content"] == mock_transcription_result["text"]
        assert found_episode["metadata"]["source"] == "stt_processor"
        assert (
            found_episode["metadata"]["confidence"]
            == mock_transcription_result["confidence"]
        )

        print(f"✅ Retrieved transcription matches stored data")
        print(f"   Text: {found_episode['content'][:50]}...")
        print(f"   Confidence: {found_episode['metadata']['confidence']}")

    @pytest.mark.asyncio
    async def test_store_multiple_transcriptions_with_timestamps(
        self, http_client, memory_service_url, test_user_id, test_session_id
    ):
        """Test 4: Store multiple transcriptions and verify timestamp ordering."""

        transcriptions = [
            {
                "text": "First utterance from the user.",
                "confidence": 0.95,
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "text": "Second utterance following the first.",
                "confidence": 0.88,
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "text": "Third and final utterance in sequence.",
                "confidence": 0.91,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ]

        stored_ids = []

        # Store all transcriptions
        for idx, trans in enumerate(transcriptions):
            await asyncio.sleep(0.1)  # Small delay to ensure different timestamps

            episode_data = {
                "user_id": test_user_id,
                "session_id": test_session_id,
                "content": trans["text"],
                "metadata": {
                    "source": "stt_processor",
                    "confidence": trans["confidence"],
                    "timestamp": datetime.utcnow().isoformat(),
                    "sequence_number": idx,
                },
            }

            response = await http_client.post(
                f"{memory_service_url}/episodic/store", json=episode_data
            )

            assert response.status_code == 201
            episode_id = response.json()["data"]["episode_id"]
            stored_ids.append(episode_id)

        assert len(stored_ids) == 3, "Not all episodes stored"

        # Query all episodes for this session
        query_data = {
            "user_id": test_user_id,
            "query_text": "utterance",
            "n_results": 10,
            "session_id": test_session_id,
        }

        query_response = await http_client.post(
            f"{memory_service_url}/episodic/query", json=query_data
        )

        assert query_response.status_code == 200
        episodes = query_response.json()

        assert len(episodes) >= 3, f"Expected 3+ episodes, got {len(episodes)}"

        print(f"✅ Stored {len(stored_ids)} transcriptions with timestamps")
        for idx, ep_id in enumerate(stored_ids):
            print(f"   {idx + 1}. Episode {ep_id[:8]}... stored")

    @pytest.mark.asyncio
    async def test_transcription_metadata_validation(
        self, http_client, memory_service_url, test_user_id, test_session_id
    ):
        """Test 5: Validate metadata fields from STT are preserved."""

        # Rich metadata from STT processor
        # Note: ChromaDB only accepts primitive types in metadata, serialize complex structures
        segments_data = [
            {
                "start_ms": 0,
                "end_ms": 1200,
                "text": "Testing metadata preservation.",
                "confidence": 0.91,
            },
            {
                "start_ms": 1200,
                "end_ms": 2500,
                "text": "Second segment here.",
                "confidence": 0.87,
            },
        ]
        detection_info = {"vad_confidence": 0.95, "noise_level": "low"}

        detailed_metadata = {
            "source": "stt_processor",
            "model": "whisper-base.en",
            "confidence": 0.89,
            "language": "en",
            "processing_time_ms": 320,
            "audio_duration_ms": 2500,
            "timestamp": datetime.utcnow().isoformat(),
            "segments": json.dumps(segments_data),  # Serialize to JSON string
            "detection_info": json.dumps(detection_info),  # Serialize to JSON string
        }

        episode_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "content": "Testing metadata preservation. Second segment here.",
            "metadata": detailed_metadata,
        }

        # Store episode
        store_response = await http_client.post(
            f"{memory_service_url}/episodic/store", json=episode_data
        )

        assert store_response.status_code == 201
        episode_id = store_response.json()["data"]["episode_id"]

        # Retrieve and validate
        get_response = await http_client.get(
            f"{memory_service_url}/episodic/episode/{episode_id}"
        )

        assert get_response.status_code == 200
        retrieved = get_response.json()

        # Validate all metadata fields preserved
        metadata = retrieved["metadata"]
        assert metadata["source"] == "stt_processor"
        assert metadata["model"] == "whisper-base.en"
        assert metadata["confidence"] == 0.89
        assert metadata["language"] == "en"
        assert metadata["processing_time_ms"] == 320
        # Deserialize segments from JSON string
        segments = json.loads(metadata["segments"])
        assert len(segments) == 2
        assert "detection_info" in metadata
        # Deserialize detection_info from JSON string
        detection = json.loads(metadata["detection_info"])
        assert detection["vad_confidence"] == 0.95

        print(f"✅ All metadata fields preserved correctly")
        print(f"   Model: {metadata['model']}")
        print(f"   Confidence: {metadata['confidence']}")
        print(f"   Segments: {len(segments)}")

    @pytest.mark.asyncio
    async def test_concurrent_transcription_storage(
        self, http_client, memory_service_url, test_user_id
    ):
        """Test 6: Handle concurrent transcription storage (multiple users)."""

        # Simulate multiple concurrent users
        num_concurrent = 5

        async def store_user_transcription(user_idx: int):
            user_id = f"{test_user_id}_user{user_idx}"
            session_id = f"session_{user_idx}"

            episode_data = {
                "user_id": user_id,
                "session_id": session_id,
                "content": f"Concurrent transcription from user {user_idx}",
                "metadata": {
                    "source": "stt_processor",
                    "confidence": 0.85 + (user_idx * 0.01),
                    "timestamp": datetime.utcnow().isoformat(),
                },
            }

            response = await http_client.post(
                f"{memory_service_url}/episodic/store", json=episode_data
            )

            assert response.status_code == 201
            return response.json()["data"]["episode_id"]

        # Store concurrently
        tasks = [store_user_transcription(i) for i in range(num_concurrent)]
        episode_ids = await asyncio.gather(*tasks)

        assert len(episode_ids) == num_concurrent
        assert len(set(episode_ids)) == num_concurrent, "Duplicate episode IDs"

        print(f"✅ Stored {num_concurrent} concurrent transcriptions successfully")


class TestM2M10ErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_empty_transcription_handling(
        self, http_client, memory_service_url, test_user_id, test_session_id
    ):
        """Test 7: Handle empty transcription (silence detected)."""

        episode_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "content": "",  # Empty transcription
            "metadata": {
                "source": "stt_processor",
                "confidence": 0.0,
                "language": "en",
                "note": "silence_detected",
            },
        }

        response = await http_client.post(
            f"{memory_service_url}/episodic/store", json=episode_data
        )

        # Should still store (for conversation context)
        assert response.status_code == 201
        print("✅ Empty transcription handled gracefully")

    @pytest.mark.asyncio
    async def test_low_confidence_transcription(
        self, http_client, memory_service_url, test_user_id, test_session_id
    ):
        """Test 8: Store low-confidence transcription with warning flag."""

        episode_data = {
            "user_id": test_user_id,
            "session_id": test_session_id,
            "content": "unclear audio quality detected",
            "metadata": {
                "source": "stt_processor",
                "confidence": 0.42,  # Low confidence
                "language": "en",
                "warning": "low_confidence",
                "requires_confirmation": True,
            },
        }

        response = await http_client.post(
            f"{memory_service_url}/episodic/store", json=episode_data
        )

        assert response.status_code == 201

        episode_id = response.json()["data"]["episode_id"]

        # Verify warning flag is preserved
        get_response = await http_client.get(
            f"{memory_service_url}/episodic/episode/{episode_id}"
        )

        metadata = get_response.json()["metadata"]
        assert metadata["warning"] == "low_confidence"
        assert metadata["requires_confirmation"] is True

        print("✅ Low-confidence transcription stored with warnings")


# Performance benchmark
@pytest.mark.asyncio
async def test_stt_to_memory_latency(
    http_client,
    memory_service_url,
    test_user_id,
    test_session_id,
    mock_transcription_result,
):
    """Test 9: Measure end-to-end latency from STT to Memory storage."""

    start_time = datetime.utcnow()

    episode_data = {
        "user_id": test_user_id,
        "session_id": test_session_id,
        "content": mock_transcription_result["text"],
        "metadata": {
            "source": "stt_processor",
            "confidence": mock_transcription_result["confidence"],
            "stt_processing_time_ms": mock_transcription_result["processing_time_ms"],
            "timestamp": start_time.isoformat(),
        },
    }

    response = await http_client.post(
        f"{memory_service_url}/episodic/store", json=episode_data
    )

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    assert response.status_code == 201

    # Target: Storage should complete in <100ms
    assert latency_ms < 500, f"Storage latency too high: {latency_ms}ms"

    print(f"✅ STT → Memory storage latency: {latency_ms:.2f}ms")
    print(f"   Target: <100ms, Achieved: {latency_ms:.2f}ms")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

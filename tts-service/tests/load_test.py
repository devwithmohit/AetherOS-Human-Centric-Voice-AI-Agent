"""Load testing with Locust."""

from locust import HttpUser, task, between
import random


class TTSUser(HttpUser):
    """Simulated TTS user."""

    wait_time = between(1, 3)

    # Common phrases to test caching
    phrases = [
        "Hello, how can I help you?",
        "What's the weather like today?",
        "Tell me the time.",
        "What's on my calendar?",
        "Play some music.",
        "Set a timer for 5 minutes.",
        "Turn on the lights.",
        "What's the temperature?",
        "Read my messages.",
        "Call John.",
    ]

    @task(5)
    def synthesize_common_phrase(self):
        """Synthesize common phrase (high cache hit expected)."""
        phrase = random.choice(self.phrases)

        self.client.post(
            "/synthesize",
            json={"text": phrase, "use_cache": True, "format": "wav"},
            name="/synthesize (cached)",
        )

    @task(2)
    def synthesize_unique(self):
        """Synthesize unique text (cache miss)."""
        text = f"Unique request number {random.randint(1, 10000)}"

        self.client.post(
            "/synthesize",
            json={"text": text, "use_cache": True, "format": "wav"},
            name="/synthesize (unique)",
        )

    @task(1)
    def synthesize_stream(self):
        """Synthesize with streaming."""
        phrase = random.choice(self.phrases)

        self.client.post(
            "/synthesize/stream", json={"text": phrase, "format": "wav"}, name="/synthesize/stream"
        )

    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health")

    @task(1)
    def cache_stats(self):
        """Get cache statistics."""
        self.client.get("/cache/stats")

    @task(1)
    def list_voices(self):
        """List available voices."""
        self.client.get("/voices")


class StressTestUser(HttpUser):
    """Stress test user with concurrent requests."""

    wait_time = between(0.1, 0.5)  # Much faster

    @task
    def rapid_synthesis(self):
        """Rapid synthesis requests."""
        text = f"Stress test {random.randint(1, 1000)}"

        self.client.post(
            "/synthesize", json={"text": text, "use_cache": False}, name="/synthesize (stress)"
        )

"""Load testing for Memory Service with Locust."""

from locust import HttpUser, task, between
import random
import json


class MemoryServiceUser(HttpUser):
    """Simulated user for memory service load testing."""

    wait_time = between(0.1, 1.0)

    def on_start(self):
        """Initialize user data."""
        self.user_id = f"user_{random.randint(1, 100)}"
        self.session_id = f"session_{random.randint(1, 1000)}"

    @task(5)
    def short_term_set_get(self):
        """Test short-term memory operations."""
        key = f"key_{random.randint(1, 100)}"

        # Set memory
        self.client.post(
            "/short-term/set",
            json={
                "key": key,
                "value": {"data": f"value_{random.randint(1, 1000)}"},
                "namespace": self.user_id,
                "ttl": 300,
            },
            name="/short-term/set",
        )

        # Get memory
        self.client.get(f"/short-term/get/{self.user_id}/{key}", name="/short-term/get")

    @task(3)
    def conversation_context(self):
        """Test conversation context operations."""
        # Set context
        self.client.post(
            f"/short-term/conversation/{self.session_id}",
            json={
                "current_intent": "weather_query",
                "entities": ["weather", "location"],
                "message_count": random.randint(1, 10),
            },
            name="/short-term/conversation/set",
        )

        # Get context
        self.client.get(
            f"/short-term/conversation/{self.session_id}", name="/short-term/conversation/get"
        )

    @task(2)
    def user_preferences(self):
        """Test user preferences."""
        self.client.post(
            "/long-term/preferences",
            json={
                "user_id": self.user_id,
                "language": random.choice(["en", "es", "fr"]),
                "timezone": "UTC",
                "voice_speed": random.uniform(0.8, 1.2),
            },
            name="/long-term/preferences/set",
        )

        self.client.get(f"/long-term/preferences/{self.user_id}", name="/long-term/preferences/get")

    @task(2)
    def execution_history(self):
        """Test execution logging."""
        self.client.post(
            "/long-term/execution",
            json={
                "user_id": self.user_id,
                "session_id": self.session_id,
                "command": f"command_{random.randint(1, 10)}",
                "tool_name": random.choice(["weather", "timer", "reminder"]),
                "success": random.choice([True, False]),
                "execution_time_ms": random.randint(50, 500),
            },
            name="/long-term/execution/log",
        )

    @task(1)
    def episodic_store_query(self):
        """Test episodic memory operations."""
        # Store episode
        self.client.post(
            "/episodic/store",
            json={
                "user_id": self.user_id,
                "session_id": self.session_id,
                "content": f"User asked about {random.choice(['weather', 'time', 'news'])}",
                "metadata": {"intent": "query"},
            },
            name="/episodic/store",
        )

        # Query episodes
        self.client.post(
            "/episodic/query",
            json={"user_id": self.user_id, "query_text": "What did I ask about?", "n_results": 5},
            name="/episodic/query",
        )

    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health", name="/health")


class StressTestUser(HttpUser):
    """High-frequency stress test user."""

    wait_time = between(0.01, 0.1)

    def on_start(self):
        """Initialize user data."""
        self.user_id = f"stress_user_{random.randint(1, 1000)}"

    @task
    def rapid_short_term_operations(self):
        """Rapid short-term memory operations."""
        key = f"stress_key_{random.randint(1, 10000)}"

        self.client.post(
            "/short-term/set",
            json={"key": key, "value": {"data": "stress_test"}, "namespace": self.user_id},
            name="/short-term/set (stress)",
        )


class ReadHeavyUser(HttpUser):
    """Read-heavy workload user."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        """Initialize user data."""
        self.user_id = f"read_user_{random.randint(1, 50)}"

        # Pre-populate some data
        for i in range(10):
            self.client.post(
                "/short-term/set",
                json={
                    "key": f"read_key_{i}",
                    "value": {"data": f"value_{i}"},
                    "namespace": self.user_id,
                },
            )

    @task(10)
    def read_memory(self):
        """Read operations."""
        key = f"read_key_{random.randint(0, 9)}"
        self.client.get(
            f"/short-term/get/{self.user_id}/{key}", name="/short-term/get (read-heavy)"
        )

    @task(1)
    def write_memory(self):
        """Occasional write."""
        key = f"read_key_{random.randint(0, 9)}"
        self.client.post(
            "/short-term/set",
            json={"key": key, "value": {"data": "updated"}, "namespace": self.user_id},
            name="/short-term/set (read-heavy)",
        )

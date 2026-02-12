"""
gRPC Client Manager

Manages gRPC client connections to all downstream services with
circuit breaker pattern and connection pooling.
"""

from typing import Dict, Any, Optional
import asyncio
import structlog
import grpc
from grpc import aio
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = structlog.get_logger()


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""

    pass


class GRPCClient:
    """Base gRPC client with retry and circuit breaker."""

    def __init__(
        self,
        service_name: str,
        host: str,
        timeout: int = 30,
    ):
        """
        Initialize gRPC client.

        Args:
            service_name: Name of the service
            host: gRPC server host:port
            timeout: Default timeout in seconds
        """
        self.service_name = service_name
        self.host = host
        self.timeout = timeout
        self.channel: Optional[aio.Channel] = None
        self.connected = False

    async def connect(self):
        """Establish gRPC channel connection."""
        try:
            # Create channel with keepalive options
            self.channel = aio.insecure_channel(
                self.host,
                options=[
                    ("grpc.keepalive_time_ms", settings.GRPC_KEEPALIVE_TIME_MS),
                    ("grpc.keepalive_timeout_ms", settings.GRPC_KEEPALIVE_TIMEOUT_MS),
                    ("grpc.http2.max_pings_without_data", 0),
                    ("grpc.keepalive_permit_without_calls", 1),
                ],
            )

            # Wait for channel to be ready
            await self.channel.channel_ready()

            self.connected = True
            logger.info("grpc_client_connected", service=self.service_name, host=self.host)

        except Exception as e:
            self.connected = False
            logger.error(
                "grpc_client_connect_failed",
                service=self.service_name,
                host=self.host,
                error=str(e),
            )
            raise

    async def close(self):
        """Close gRPC channel."""
        if self.channel:
            await self.channel.close()
            self.connected = False
            logger.info("grpc_client_closed", service=self.service_name)

    @circuit(
        failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT,
        expected_exception=settings.CIRCUIT_BREAKER_EXPECTED_EXCEPTION,
    )
    @retry(
        stop=stop_after_attempt(settings.GRPC_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def call(
        self,
        stub_class: type,
        method_name: str,
        request: Any,
        timeout: Optional[int] = None,
    ) -> Any:
        """
        Make gRPC call with retry and circuit breaker.

        Args:
            stub_class: gRPC stub class
            method_name: Method name to call
            request: Request message
            timeout: Call timeout (overrides default)

        Returns:
            Response message

        Raises:
            grpc.RpcError: If call fails
            CircuitBreakerError: If circuit is open
        """
        if not self.connected:
            await self.connect()

        timeout = timeout or self.timeout

        try:
            stub = stub_class(self.channel)
            method = getattr(stub, method_name)

            logger.debug(
                "grpc_call_start",
                service=self.service_name,
                method=method_name,
                timeout=timeout,
            )

            response = await method(request, timeout=timeout)

            logger.debug(
                "grpc_call_success",
                service=self.service_name,
                method=method_name,
            )

            return response

        except grpc.RpcError as e:
            logger.error(
                "grpc_call_failed",
                service=self.service_name,
                method=method_name,
                code=e.code(),
                details=e.details(),
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.connected:
                await self.connect()
            return True
        except Exception:
            return False


class GRPCClientManager:
    """Manager for all gRPC clients."""

    def __init__(self):
        """Initialize gRPC client manager."""
        self.clients: Dict[str, GRPCClient] = {}

    async def initialize(self):
        """Initialize all gRPC clients."""
        # Voice services
        self.clients["stt"] = GRPCClient(
            "speech-to-text",
            settings.VOICE_STT_GRPC_URL,
            settings.STT_TIMEOUT,
        )

        self.clients["tts"] = GRPCClient(
            "text-to-speech",
            settings.VOICE_TTS_GRPC_URL,
            settings.TTS_TIMEOUT,
        )

        # Agent core
        self.clients["intent"] = GRPCClient(
            "intent-recognition",
            settings.INTENT_GRPC_URL,
            settings.INTENT_TIMEOUT,
        )

        self.clients["planner"] = GRPCClient(
            "action-planner",
            settings.PLANNER_GRPC_URL,
            settings.PLANNER_TIMEOUT,
        )

        self.clients["safety"] = GRPCClient(
            "safety-validator",
            settings.SAFETY_GRPC_URL,
            settings.SAFETY_TIMEOUT,
        )

        # Executors
        self.clients["browser"] = GRPCClient(
            "browser-executor",
            settings.BROWSER_GRPC_URL,
            settings.EXECUTOR_TIMEOUT,
        )

        self.clients["os"] = GRPCClient(
            "os-executor",
            settings.OS_GRPC_URL,
            settings.EXECUTOR_TIMEOUT,
        )

        self.clients["search"] = GRPCClient(
            "search-executor",
            settings.SEARCH_GRPC_URL,
            settings.EXECUTOR_TIMEOUT,
        )

        # Memory
        self.clients["memory"] = GRPCClient(
            "memory-manager",
            settings.MEMORY_GRPC_URL,
            settings.MEMORY_TIMEOUT,
        )

        # Connect all clients
        connect_tasks = [client.connect() for client in self.clients.values()]
        results = await asyncio.gather(*connect_tasks, return_exceptions=True)

        # Log connection results
        successful = sum(1 for r in results if not isinstance(r, Exception))
        logger.info(
            "grpc_clients_initialized",
            total=len(self.clients),
            successful=successful,
            failed=len(self.clients) - successful,
        )

    async def close_all(self):
        """Close all gRPC client connections."""
        close_tasks = [client.close() for client in self.clients.values()]
        await asyncio.gather(*close_tasks, return_exceptions=True)

        logger.info("all_grpc_clients_closed", count=len(self.clients))

    def get_client(self, service_name: str) -> Optional[GRPCClient]:
        """
        Get gRPC client by service name.

        Args:
            service_name: Service name (stt, tts, intent, etc.)

        Returns:
            GRPCClient instance or None
        """
        return self.clients.get(service_name)

    def list_services(self) -> list[str]:
        """
        List all registered services.

        Returns:
            List of service names
        """
        return list(self.clients.keys())

    async def health_check_all(self) -> Dict[str, bool]:
        """
        Health check all services.

        Returns:
            Dictionary mapping service names to health status
        """
        health_tasks = {name: client.health_check() for name, client in self.clients.items()}

        results = await asyncio.gather(*health_tasks.values(), return_exceptions=True)

        health_status = {}
        for name, result in zip(health_tasks.keys(), results):
            health_status[name] = result if isinstance(result, bool) else False

        return health_status

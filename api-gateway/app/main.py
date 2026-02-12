"""
API Gateway - Main Application (Module 11)

Central entry point for all client requests to the Jarvis Voice Agent system.
Routes requests to appropriate downstream services via gRPC.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Dict, Any
import structlog

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from app.config import settings
from app.auth import AuthMiddleware
from app.rate_limiter import RateLimiter
from app.routers import (
    voice_router,
    agent_router,
    executor_router,
    memory_router,
    health_router,
)
from app import websocket
from app.grpc_clients import GRPCClientManager

# Configure structured logging
logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter(
    "api_gateway_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)
REQUEST_DURATION = Histogram(
    "api_gateway_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)
GRPC_CALL_COUNT = Counter(
    "api_gateway_grpc_calls_total",
    "Total number of gRPC calls",
    ["service", "method", "status"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Check if this is a test environment
    import os

    if os.getenv("TESTING") == "true":
        # Skip actual initialization in test mode
        logger.info("test_mode_detected", message="Skipping Redis and gRPC initialization")
        yield
        return

    # Startup
    logger.info("api_gateway_starting", version=settings.VERSION)

    # Initialize gRPC clients
    app.state.grpc_manager = GRPCClientManager()
    await app.state.grpc_manager.initialize()

    # Initialize rate limiter
    app.state.rate_limiter = RateLimiter(
        redis_url=settings.REDIS_URL,
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window_seconds=settings.RATE_LIMIT_WINDOW,
    )
    await app.state.rate_limiter.initialize()

    logger.info("api_gateway_started", services=app.state.grpc_manager.list_services())

    yield

    # Shutdown
    logger.info("api_gateway_shutting_down")

    # Close gRPC connections
    await app.state.grpc_manager.close_all()

    # Close rate limiter
    await app.state.rate_limiter.close()

    logger.info("api_gateway_shutdown_complete")


# Create FastAPI application
app = FastAPI(
    title="Jarvis API Gateway",
    description="Central API Gateway for Jarvis Voice Agent System",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add authentication middleware
app.add_middleware(AuthMiddleware)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add request processing time to response headers and collect metrics."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Add header
    response.headers["X-Process-Time"] = f"{duration:.4f}"

    # Collect metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware."""
    # Skip rate limiting for health checks and metrics
    if request.url.path in ["/health", "/metrics", "/ready"]:
        return await call_next(request)

    # Skip rate limiting if rate_limiter not initialized (e.g., TESTING mode)
    if not hasattr(request.app.state, "rate_limiter"):
        return await call_next(request)

    # Get client identifier (IP or user ID from JWT)
    client_id = request.client.host if request.client else "unknown"
    if hasattr(request.state, "user_id"):
        client_id = f"user:{request.state.user_id}"

    # Check rate limit
    rate_limiter = request.app.state.rate_limiter
    is_allowed, limit_info = await rate_limiter.check_rate_limit(client_id)

    if not is_allowed:
        logger.warning(
            "rate_limit_exceeded",
            client_id=client_id,
            limit=limit_info["limit"],
            remaining=limit_info["remaining"],
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "limit": limit_info["limit"],
                "remaining": limit_info["remaining"],
                "reset_at": limit_info["reset_at"],
            },
        )

    # Add rate limit headers
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit_info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(limit_info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(limit_info["reset_at"])

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "path": request.url.path,
        },
    )


# Include routers
app.include_router(health_router.router, tags=["Health"])
app.include_router(voice_router.router, prefix="/api/v1/voice", tags=["Voice"])
app.include_router(agent_router.router, prefix="/api/v1/agent", tags=["Agent"])
app.include_router(executor_router.router, prefix="/api/v1/executor", tags=["Executor"])
app.include_router(memory_router.router, prefix="/api/v1/memory", tags=["Memory"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint."""
    return {
        "service": "Jarvis API Gateway",
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs" if settings.DEBUG else None,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )

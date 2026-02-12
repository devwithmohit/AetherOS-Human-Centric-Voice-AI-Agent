"""
Health Check Router

Provides health, readiness, and liveness endpoints for monitoring.
"""

from typing import Dict, Any
import structlog

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.config import settings

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": settings.VERSION,
    }


@router.get("/ready")
async def readiness_check(request: Request) -> JSONResponse:
    """
    Readiness check - verifies all dependencies are ready.

    Checks:
    - gRPC clients connectivity
    - Redis connectivity (rate limiter)

    Returns:
        200 if ready, 503 if not ready
    """
    checks = {}
    all_ready = True

    # Check gRPC clients
    try:
        grpc_manager = request.app.state.grpc_manager
        grpc_health = await grpc_manager.health_check_all()
        checks["grpc_services"] = grpc_health

        # Count healthy services
        healthy_count = sum(1 for v in grpc_health.values() if v)
        total_count = len(grpc_health)
        checks["grpc_healthy"] = f"{healthy_count}/{total_count}"

        # Require at least 50% of services to be healthy
        if healthy_count < total_count * 0.5:
            all_ready = False

    except Exception as e:
        logger.error("readiness_check_grpc_failed", error=str(e))
        checks["grpc_services"] = {"error": str(e)}
        all_ready = False

    # Check Redis
    try:
        rate_limiter = request.app.state.rate_limiter
        redis_healthy = await rate_limiter.health_check()
        checks["redis"] = "healthy" if redis_healthy else "unhealthy"

        if not redis_healthy:
            all_ready = False

    except Exception as e:
        logger.error("readiness_check_redis_failed", error=str(e))
        checks["redis"] = {"error": str(e)}
        all_ready = False

    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ready,
            "checks": checks,
        },
    )


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness check - indicates if the service is alive.

    Returns:
        Status indicating service is alive
    """
    return {"status": "alive"}

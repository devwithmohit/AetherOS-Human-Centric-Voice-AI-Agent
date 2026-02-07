"""FastAPI application for Memory Service."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.config import settings
from app.database import init_db, close_db
from app.stores.short_term import short_term_memory
from app.stores.episodic import episodic_memory
from app.routers import short_term_router, long_term_router, episodic_router
from app.routers.dashboard_router import router as dashboard_router
from app.retention import retention_policy
from app.schemas import HealthResponse

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(
        f"Starting {settings.service_name} on {settings.service_host}:{settings.service_port}"
    )

    try:
        # Initialize PostgreSQL
        await init_db()
        logger.info("PostgreSQL initialized")

        # Connect to Redis
        await short_term_memory.connect()
        logger.info("Redis connected")

        # Connect to ChromaDB
        await episodic_memory.connect()
        logger.info("ChromaDB connected")

        # Start retention policy enforcement
        asyncio.create_task(retention_policy.start())
        logger.info("Retention policy enforcement started")

        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down services...")

    try:
        await retention_policy.stop()
        await short_term_memory.disconnect()
        await episodic_memory.disconnect()
        await close_db()
        logger.info("✅ All services shut down gracefully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app
app = FastAPI(
    title="AetherOS Memory Service",
    description=(
        "Multi-tier memory management service for AetherOS voice agent. "
        "Provides short-term (Redis), long-term (PostgreSQL), and episodic (ChromaDB) memory "
        "with retention policies, dashboard analytics, and comprehensive API."
    ),
    version="0.2.0",
    lifespan=lifespan,
    contact={
        "name": "AetherOS Development Team",
        "url": "https://github.com/yourusername/Jarvis-voice-agent",
    },
    license_info={
        "name": "MIT",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Check service health."""
    services = {}

    # Check Redis
    try:
        await short_term_memory.redis.ping() if short_term_memory.redis else None
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    # Check ChromaDB
    try:
        services["chromadb"] = "healthy" if episodic_memory.client else "unhealthy"
    except Exception:
        services["chromadb"] = "unhealthy"

    # Check PostgreSQL (implicitly healthy if app started)
    services["postgresql"] = "healthy"

    overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running",
        "environment": settings.environment,
    }


# Register routers
app.include_router(short_term_router, tags=["Short-term Memory"])
app.include_router(long_term_router, tags=["Long-term Memory"])
app.include_router(episodic_router, tags=["Episodic Memory"])
app.include_router(dashboard_router, tags=["Dashboard & Analytics"])


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )

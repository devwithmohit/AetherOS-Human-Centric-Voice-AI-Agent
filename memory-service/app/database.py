"""Database connection and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config import settings
from app.models import Base
import logging

logger = logging.getLogger(__name__)

# Create async engine
# SQLite doesn't support pool_size/max_overflow, only use them for PostgreSQL
engine_args = {
    "echo": settings.log_level == "DEBUG",
    "pool_pre_ping": True,
}

# Add pooling args only for non-SQLite databases
if "sqlite" not in settings.database_url.lower():
    engine_args.update(
        {
            "pool_size": settings.pool_size,
            "max_overflow": settings.max_overflow,
            "poolclass": NullPool if settings.environment == "test" else None,
        }
    )
else:
    engine_args["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **engine_args)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

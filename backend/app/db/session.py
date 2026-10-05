"""
Database engine and async session configuration for CareerLens.
"""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

pool_kwargs: dict[str, Any] = {}
if settings.ENVIRONMENT == "test":
    pool_kwargs["poolclass"] = NullPool
else:
    pool_kwargs["pool_size"] = 10
    pool_kwargs["max_overflow"] = 20

engine = create_async_engine(
    settings.effective_database_url,
    echo=settings.DEBUG and settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    **pool_kwargs,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an asynchronous database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> dict[str, Any]:
    """
    Verify database connectivity and pgvector extension availability.
    Returns a dictionary of health check status and pgvector extension details.
    """
    async with async_session_factory() as session:
        # Check basic connectivity
        await session.execute(text("SELECT 1"))

        # Check pgvector extension status
        result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        pgvector_version = result.scalar()

        # Check pgvector distance math execution
        vector_math = None
        if pgvector_version:
            math_result = await session.execute(
                text("SELECT '[1,2,3]'::vector <-> '[3,2,1]'::vector AS dist")
            )
            vector_math = math_result.scalar()

        return {
            "database": "connected",
            "pgvector_installed": pgvector_version is not None,
            "pgvector_version": pgvector_version,
            "pgvector_operational": vector_math is not None,
        }

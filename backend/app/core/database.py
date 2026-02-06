"""
Database connection and session management for PostgreSQL with asyncpg.
"""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries in debug mode
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory for creating database sessions
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Use with FastAPI's Depends() for automatic session management.
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> dict:
    """
    Check if database connection is healthy.
    Returns status dict with connection info.
    """
    try:
        # Reuse the existing SQLAlchemy engine pool for health checks.
        async with engine.connect() as connection:
            version = await connection.scalar(text("SELECT version()"))

        return {
            "status": "connected",
            "database": settings.database_name,
            "host": settings.database_host,
            "version": version.split(",")[0] if version else "unknown",
        }
    except Exception as e:
        error_response = {
            "status": "disconnected",
            "database": settings.database_name,
            "host": settings.database_host,
        }
        if settings.debug:
            error_response["error"] = str(e)
        return error_response

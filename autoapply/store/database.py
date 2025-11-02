"""Database configuration and session management.

Uses SQLAlchemy 2.0 with async support for PostgreSQL.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from autoapply.config.env import get_database_url
from autoapply.util.logger import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Global engine and session factory
_engine = None
_async_session_factory = None


def get_engine():
    """Get or create the async database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        logger.info(f"Creating database engine for: {database_url.split('@')[-1]}")  # Hide credentials

        _engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debug logging
            pool_pre_ping=True,  # Verify connections before use
            pool_size=10,
            max_overflow=20,
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _async_session_factory


async def get_session() -> AsyncSession:
    """Get a new async database session.

    Usage:
        async with get_session() as session:
            # Use session for queries
            pass
    """
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Initialize database - create all tables.

    NOTE: In production, use Alembic migrations instead.
    This is for development/testing only.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models so they're registered
        from autoapply.store import models  # noqa

        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")


async def close_db():
    """Close database connections."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
    logger.info("Database connections closed")

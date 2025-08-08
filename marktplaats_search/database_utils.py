"""
Database utilities and session management helpers.
Provides decorators and context managers to reduce boilerplate database operations.
"""

import functools
import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal

logger = logging.getLogger(__name__)

T = TypeVar("T")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Standard database session context manager.

    Provides a consistent way to create and manage database sessions
    across the application with proper error handling and cleanup.

    Yields:
        AsyncSession: A database session

    Example:
        async with get_db_session() as db:
            result = await db.execute(select(User))
            await db.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise


def with_db_session(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that provides a database session as the first argument.

    The decorated function should accept 'db: AsyncSession' as its first parameter.

    Args:
        func: The function to decorate

    Returns:
        The decorated function with automatic session management

    Example:
        @with_db_session
        async def get_user_count(db: AsyncSession) -> int:
            result = await db.execute(select(func.count(User.id)))
            return result.scalar()
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        async with get_db_session() as db:
            return await func(db, *args, **kwargs)

    return wrapper


async def execute_with_session(operation: Callable[[AsyncSession], Any]) -> Any:
    """
    Execute a database operation with automatic session management.

    Args:
        operation: A callable that takes an AsyncSession and returns a result

    Returns:
        The result of the operation

    Example:
        async def get_users(db: AsyncSession):
            result = await db.execute(select(User))
            return result.scalars().all()

        users = await execute_with_session(get_users)
    """
    async with get_db_session() as db:
        return await operation(db)


class DatabaseService:
    """
    Base service class that provides database session management.

    Services can inherit from this class to get consistent database access
    without managing sessions manually.
    """

    @staticmethod
    @asynccontextmanager
    async def session() -> AsyncGenerator[AsyncSession, None]:
        """Get a database session."""
        async with get_db_session() as db:
            yield db

    @classmethod
    async def with_session(cls, operation: Callable[[AsyncSession], Any]) -> Any:
        """Execute an operation with a database session."""
        async with cls.session() as db:
            return await operation(db)

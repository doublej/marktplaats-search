"""User Management Service

Centralized business logic for user operations including creation, activation,
token management, and statistics. This eliminates duplication between scripts
and API endpoints.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import generate_secure_token, generate_user_identifier, hash_token
from ..database import AsyncSessionLocal
from ..models import User


class UserManagementService:
    """Service for managing user operations."""

    def __init__(self, db_session: AsyncSession | None = None):
        """Initialize service with optional database session."""
        self._db_session = db_session

    async def _get_db_session(self) -> AsyncSession:
        """Get database session, either provided or create new one."""
        if self._db_session:
            return self._db_session
        return AsyncSessionLocal()

    async def create_user(self, username: str | None = None) -> tuple[str, str]:
        """Create a new user with secure token.

        Args:
            username: Optional username (auto-generated if not provided)

        Returns:
            Tuple of (username, token)

        Raises:
            ValueError: If username already exists
        """
        # Generate or use provided username
        if not username:
            username = generate_user_identifier()

        async with await self._get_db_session() as db:
            # Check if username exists
            result = await db.execute(select(User).where(User.user_identifier == username))
            if result.scalars().first():
                raise ValueError(f"User '{username}' already exists")

            # Generate secure token
            token = generate_secure_token()
            token_hash = hash_token(token)

            # Create user
            user = User(
                user_identifier=username,
                api_token_hash=token_hash,
                is_active=True,
                token_created_at=datetime.now(UTC),
            )

            db.add(user)
            await db.commit()

            return username, token

    async def get_all_users(self, include_inactive: bool = True) -> list[User]:
        """Get all users in the system.

        Args:
            include_inactive: Whether to include inactive users

        Returns:
            List of User objects
        """
        async with await self._get_db_session() as db:
            query = select(User).order_by(User.created_at.desc())
            if not include_inactive:
                query = query.where(User.is_active.is_(True))

            result = await db.execute(query)
            return list(result.scalars().all())

    async def get_user_by_username(self, username: str) -> User | None:
        """Get user by username.

        Args:
            username: Username to search for

        Returns:
            User object or None if not found
        """
        async with await self._get_db_session() as db:
            result = await db.execute(select(User).where(User.user_identifier == username))
            return result.scalars().first()

    async def activate_user(self, username: str, activate: bool = True) -> bool:
        """Activate or deactivate a user.

        Args:
            username: Username to modify
            activate: True to activate, False to deactivate

        Returns:
            True if user was found and modified, False if not found
        """
        async with await self._get_db_session() as db:
            result = await db.execute(select(User).where(User.user_identifier == username))
            user = result.scalars().first()

            if not user:
                return False

            user.is_active = activate
            await db.commit()
            return True

    async def reset_user_token(self, username: str) -> str | None:
        """Reset a user's API token.

        Args:
            username: Username whose token to reset

        Returns:
            New token string, or None if user not found
        """
        async with await self._get_db_session() as db:
            result = await db.execute(select(User).where(User.user_identifier == username))
            user = result.scalars().first()

            if not user:
                return None

            # Generate new token
            new_token = generate_secure_token()
            new_token_hash = hash_token(new_token)

            user.api_token_hash = new_token_hash
            user.token_created_at = datetime.now(UTC)

            await db.commit()
            return new_token

    async def delete_user(self, username: str) -> bool:
        """Delete a user and all their data.

        Args:
            username: Username to delete

        Returns:
            True if user was found and deleted, False if not found
        """
        async with await self._get_db_session() as db:
            result = await db.execute(select(User).where(User.user_identifier == username))
            user = result.scalars().first()

            if not user:
                return False

            # This will cascade delete all searches and listings
            await db.delete(user)
            await db.commit()
            return True

    async def get_user_statistics(self, recent_days: int = 7) -> dict[str, Any]:
        """Get user statistics.

        Args:
            recent_days: Number of days to consider for recent activity

        Returns:
            Dictionary with user statistics
        """
        async with await self._get_db_session() as db:
            # Total users
            total_result = await db.execute(select(func.count(User.id)))
            total_users = total_result.scalar()

            # Active users
            active_result = await db.execute(
                select(func.count(User.id)).where(User.is_active.is_(True))
            )
            active_users = active_result.scalar()

            # Users with recent activity
            recent_date = datetime.now(UTC) - timedelta(days=recent_days)
            recent_result = await db.execute(
                select(func.count(User.id)).where(User.last_activity > recent_date)
            )
            recent_users = recent_result.scalar()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": total_users - active_users,
                "recent_users": recent_users,
                "recent_days": recent_days,
            }

    async def validate_user_exists(self, username: str) -> bool:
        """Check if a user exists.

        Args:
            username: Username to check

        Returns:
            True if user exists, False otherwise
        """
        user = await self.get_user_by_username(username)
        return user is not None

    async def update_last_activity(self, username: str) -> bool:
        """Update user's last activity timestamp.

        Args:
            username: Username to update

        Returns:
            True if user was found and updated, False otherwise
        """
        async with await self._get_db_session() as db:
            result = await db.execute(select(User).where(User.user_identifier == username))
            user = result.scalars().first()

            if not user:
                return False

            user.last_activity = datetime.now(UTC)
            await db.commit()
            return True

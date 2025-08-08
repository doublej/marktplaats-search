"""
Shared test fixtures and utilities for MarktplaatsSearch tests.
Provides common database setup, user creation, and cleanup patterns.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from marktplaats_search.auth import generate_secure_token, generate_user_identifier, hash_token
from marktplaats_search.database import AsyncSessionLocal, Base, engine
from marktplaats_search.models import Listing, Search, SearchStatus, User


@pytest.fixture
async def db_session():
    """
    Create a clean test database session.

    Sets up a fresh database for each test and cleans up afterwards.
    This ensures tests don't interfere with each other.

    Yields:
        AsyncSession: A database session for the test
    """
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with AsyncSessionLocal() as session:
        yield session

    # Clean up after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """
    Create a test user with secure token.

    Args:
        db_session: Database session fixture

    Returns:
        dict: User data with token for testing authentication
    """
    # Generate test user data
    username = generate_user_identifier("test")
    token = generate_secure_token()
    token_hash = hash_token(token)

    # Create user in database
    user = User(
        user_identifier=username,
        api_token_hash=token_hash,
        is_active=True,
        token_created_at=datetime.now(UTC),
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return {
        "user": user,
        "username": username,
        "token": token,
        "user_id": user.id,
    }


@pytest.fixture
async def test_search(db_session: AsyncSession, test_user):
    """
    Create a test search for the test user.

    Args:
        db_session: Database session fixture
        test_user: Test user fixture

    Returns:
        Search: A test search instance
    """
    search = Search(
        user_id=test_user["user_id"],
        query="test search",
        zip_code="1000AA",
        distance=25,
        price_from=100,
        price_to=1000,
        interval=3600,
        status=SearchStatus.ACTIVE,
        limit=20,
    )

    db_session.add(search)
    await db_session.commit()
    await db_session.refresh(search)

    return search


@pytest.fixture
async def test_listing(db_session: AsyncSession, test_search):
    """
    Create a test listing for the test search.

    Args:
        db_session: Database session fixture
        test_search: Test search fixture

    Returns:
        Listing: A test listing instance
    """
    listing = Listing(
        search_id=test_search.id,
        title="Test Listing",
        price="€ 500,00",
        price_numeric=50000,
        url="https://example.com/test-listing",
        description_snippet="Test description",
        is_new=True,
    )

    db_session.add(listing)
    await db_session.commit()
    await db_session.refresh(listing)

    return listing


@pytest.fixture
async def multiple_users(db_session: AsyncSession):
    """
    Create multiple test users for cross-user testing.

    Args:
        db_session: Database session fixture

    Returns:
        list[dict]: List of user data dictionaries
    """
    users = []

    for i in range(3):
        username = generate_user_identifier(f"test_{i}")
        token = generate_secure_token()
        token_hash = hash_token(token)

        user = User(
            user_identifier=username,
            api_token_hash=token_hash,
            is_active=True,
            token_created_at=datetime.now(UTC),
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        users.append(
            {
                "user": user,
                "username": username,
                "token": token,
                "user_id": user.id,
            }
        )

    return users


class DatabaseTestHelper:
    """
    Helper class for common database test operations.

    Provides convenience methods for creating test data
    and verifying database state in tests.
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_search_for_user(self, user_id: int, **kwargs) -> Search:
        """Create a search with default or custom parameters."""
        search_data = {
            "user_id": user_id,
            "query": "default test query",
            "interval": 3600,
            "status": SearchStatus.ACTIVE,
            "limit": 20,
            **kwargs,  # Override defaults with provided values
        }

        search = Search(**search_data)
        self.db.add(search)
        await self.db.commit()
        await self.db.refresh(search)

        return search

    async def create_listing_for_search(self, search_id, **kwargs) -> Listing:
        """Create a listing with default or custom parameters."""
        listing_data = {
            "search_id": search_id,
            "title": "Default Test Listing",
            "price": "€ 100,00",
            "price_numeric": 10000,
            "url": f"https://example.com/listing-{search_id}",
            "is_new": True,
            **kwargs,
        }

        listing = Listing(**listing_data)
        self.db.add(listing)
        await self.db.commit()
        await self.db.refresh(listing)

        return listing

    async def count_table_rows(self, model_class) -> int:
        """Count rows in a table."""
        from sqlalchemy import func, select

        result = await self.db.execute(select(func.count(model_class.id)))
        return result.scalar()


@pytest.fixture
async def db_helper(db_session: AsyncSession):
    """
    Provide database helper for tests.

    Args:
        db_session: Database session fixture

    Returns:
        DatabaseTestHelper: Helper instance for database operations
    """
    return DatabaseTestHelper(db_session)

"""Tests for database configuration and connectivity."""

import pytest

from marktplaats_search.database import DATABASE_URL, get_db


class TestDatabaseConfiguration:
    """Test database configuration management."""

    def test_database_url_from_settings(self):
        """Test that DATABASE_URL is loaded from settings."""
        # DATABASE_URL should be loaded from config.settings
        assert DATABASE_URL is not None
        assert isinstance(DATABASE_URL, str)
        assert "sqlite" in DATABASE_URL or "postgresql" in DATABASE_URL

    def test_database_url_consistency(self):
        """Test that database URL is consistent between runtime and settings."""
        from marktplaats_search.config import settings

        # Runtime DATABASE_URL should match settings
        assert settings.database_url == DATABASE_URL

    @pytest.mark.asyncio
    async def test_get_db_session(self):
        """Test database session factory."""
        # This tests that we can create a session without errors
        async for db in get_db():
            assert db is not None
            # Session should have basic SQLAlchemy session properties
            assert hasattr(db, "execute")
            assert hasattr(db, "commit")
            assert hasattr(db, "rollback")
            break  # Only test first iteration

    def test_sync_url_conversion(self):
        """Test conversion of async URL to sync URL for migrations."""
        from marktplaats_search.config import settings

        sync_url = settings.get_sync_database_url()

        # If original URL contains aiosqlite, it should be removed
        if "+aiosqlite" in settings.database_url:
            assert "+aiosqlite" not in sync_url

        # Sync URL should be a valid database URL
        assert isinstance(sync_url, str)
        assert len(sync_url) > 0

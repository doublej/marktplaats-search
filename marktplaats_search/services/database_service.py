"""Database Management Service

Centralized database operations including schema management, migrations,
and maintenance utilities. Provides both sync and async interfaces.
"""

from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from ..config import settings
from ..database import AsyncSessionLocal, Base
from ..models import Listing, Search, User


class DatabaseService:
    """Service for database management operations."""

    def __init__(self) -> None:
        """Initialize database service."""
        # Create sync engine for Alembic and other sync operations
        sync_url = settings.database_url.replace("+aiosqlite", "")
        self.sync_engine = create_engine(sync_url, echo=False)

        # Keep reference to async engine
        async_url = settings.database_url
        self.async_engine = create_async_engine(async_url, echo=False)

    def create_all_tables(self) -> None:
        """Create all database tables (sync operation for compatibility)."""
        Base.metadata.create_all(bind=self.sync_engine)

    def drop_all_tables(self) -> None:
        """Drop all database tables (sync operation)."""
        Base.metadata.drop_all(bind=self.sync_engine)

    def get_table_info(self) -> dict[str, Any]:
        """Get information about database tables."""
        with self.sync_engine.connect() as conn:
            # Get table names
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
            tables = [row[0] for row in result.fetchall()]

            table_info = {}
            for table in tables:
                if not table.startswith("sqlite_"):
                    # Get row count
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    table_info[table] = {"row_count": count}

            return table_info

    def verify_database_integrity(self) -> dict[str, Any]:
        """Verify database integrity and return status."""
        with self.sync_engine.connect() as conn:
            # Run SQLite integrity check
            result = conn.execute(text("PRAGMA integrity_check;"))
            integrity_result = result.scalar()

            # Get table info
            table_info = self.get_table_info()

            return {
                "integrity_check": integrity_result,
                "tables": table_info,
                "status": "ok" if integrity_result == "ok" else "error",
            }

    def optimize_database(self) -> dict[str, Any]:
        """Optimize database performance."""
        results = {}

        with self.sync_engine.connect() as conn:
            # Run VACUUM to compact database
            conn.execute(text("VACUUM;"))
            results["vacuum"] = "completed"

            # Run ANALYZE to update statistics
            conn.execute(text("ANALYZE;"))
            results["analyze"] = "completed"

            # Check if indexes exist and create if needed
            self._ensure_indexes(conn)
            results["indexes"] = "verified"

            conn.commit()

        return results

    def _ensure_indexes(self, conn: Any) -> None:
        """Ensure all necessary indexes exist."""
        indexes = [
            # User table indexes
            "CREATE INDEX IF NOT EXISTS idx_users_identifier ON users(user_identifier)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            # Search table indexes
            "CREATE INDEX IF NOT EXISTS idx_searches_user ON searches(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_searches_status ON searches(status)",
            "CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at)",
            # Listing table indexes
            "CREATE INDEX IF NOT EXISTS idx_listings_search ON listings(search_id)",
            "CREATE INDEX IF NOT EXISTS idx_listings_url ON listings(url)",
            "CREATE INDEX IF NOT EXISTS idx_listings_price ON listings(price_numeric)",
            "CREATE INDEX IF NOT EXISTS idx_listings_discovered ON listings(discovered_at)",
            "CREATE INDEX IF NOT EXISTS idx_listings_new ON listings(is_new)",
            "CREATE INDEX IF NOT EXISTS idx_listings_composite ON listings(search_id, url)",
        ]

        for index_sql in indexes:
            conn.execute(text(index_sql))

    def backup_database(self, backup_path: Path) -> dict[str, Any]:
        """Create a backup of the database."""
        import shutil

        # For SQLite, we can simply copy the file
        db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))

        try:
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(db_path, backup_path)

            return {
                "success": True,
                "backup_path": str(backup_path),
                "original_size": db_path.stat().st_size,
                "backup_size": backup_path.stat().st_size,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def restore_database(self, backup_path: Path) -> dict[str, Any]:
        """Restore database from backup."""
        import shutil

        db_path = Path(settings.database_url.replace("sqlite+aiosqlite:///", ""))

        try:
            if not backup_path.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Close any existing connections
            self.sync_engine.dispose()

            # Replace database file
            shutil.copy2(backup_path, db_path)

            # Recreate engine
            sync_url = settings.database_url.replace("+aiosqlite", "")
            self.sync_engine = create_engine(sync_url, echo=False)

            return {
                "success": True,
                "restored_from": str(backup_path),
                "database_size": db_path.stat().st_size,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def get_database_statistics(self) -> dict[str, Any]:
        """Get comprehensive database statistics (async)."""
        async with AsyncSessionLocal() as db:
            # Get counts for each model
            from sqlalchemy import func, select

            # User statistics
            user_count_result = await db.execute(select(func.count(User.id)))
            user_count = user_count_result.scalar()

            active_user_result = await db.execute(
                select(func.count(User.id)).where(User.is_active.is_(True))
            )
            active_users = active_user_result.scalar()

            # Search statistics
            search_count_result = await db.execute(select(func.count(Search.id)))
            search_count = search_count_result.scalar()

            active_search_result = await db.execute(
                select(func.count(Search.id)).where(Search.status == "active")
            )
            active_searches = active_search_result.scalar()

            # Listing statistics
            listing_count_result = await db.execute(select(func.count(Listing.id)))
            listing_count = listing_count_result.scalar()

            new_listing_result = await db.execute(
                select(func.count(Listing.id)).where(Listing.is_new.is_(True))
            )
            new_listings = new_listing_result.scalar()

            return {
                "users": {
                    "total": user_count or 0,
                    "active": active_users or 0,
                    "inactive": (user_count or 0) - (active_users or 0),
                },
                "searches": {
                    "total": search_count or 0,
                    "active": active_searches or 0,
                    "inactive": (search_count or 0) - (active_searches or 0),
                },
                "listings": {
                    "total": listing_count or 0,
                    "new": new_listings or 0,
                    "seen": (listing_count or 0) - (new_listings or 0),
                },
            }

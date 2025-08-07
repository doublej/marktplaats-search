#!/usr/bin/env python3
"""
Database migration script to add raw_html column to listings table.
This script will:
1. Back up existing data
2. Add raw_html column to listings table
"""

import asyncio
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marktplaats_search.database import DATABASE_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backup_database():
    """Create a backup of the database before migration."""
    # Look for database in both locations
    possible_paths = [
        Path("marktplaats_api.db"),
        Path("data/marktplaats_api.db"),
    ]

    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break

    if db_path:
        backup_name = f"{db_path.name}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = db_path.parent / backup_name
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    else:
        logger.warning("No database file found to backup")
    return None


async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    columns = result.fetchall()
    return any(col[1] == column_name for col in columns)


async def add_raw_html_column():
    """Add raw_html column to the listings table."""

    # Create a new engine for migration
    migration_engine = create_async_engine(DATABASE_URL, echo=True)

    async with migration_engine.begin() as conn:
        logger.info("Starting raw_html column migration...")

        # Check if raw_html column already exists
        has_raw_html = await check_column_exists(conn, "listings", "raw_html")

        if has_raw_html:
            logger.info("raw_html column already exists in listings table")
            return

        logger.info("Adding raw_html column to listings table...")

        # Add the raw_html column
        await conn.execute(text("ALTER TABLE listings ADD COLUMN raw_html TEXT"))

        logger.info("raw_html column added successfully!")

        # Check how many listings exist
        result = await conn.execute(text("SELECT COUNT(*) FROM listings"))
        count = result.scalar()
        logger.info(
            f"Found {count} existing listings (they will have NULL raw_html until next scrape)"
        )


async def main():
    """Main migration function."""
    logger.info("Starting raw_html column migration...")

    # Backup database
    backup_path = await backup_database()
    if backup_path:
        logger.info(f"Backup created at: {backup_path}")

    # Run migration
    try:
        await add_raw_html_column()
        logger.info("Migration completed successfully!")
        logger.info("New listings will now store original HTML content")
        logger.info("Existing listings will get HTML content on their next update")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if backup_path:
            logger.info(f"You can restore from backup: {backup_path}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

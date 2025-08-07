#!/usr/bin/env python3
"""
Database migration script to implement per-search listing management.

This migration:
1. Removes the global unique constraint on the URL field
2. Adds composite constraint to prevent duplicates within same search
3. Creates new indexes for optimal query performance
4. Handles existing data migration safely
5. Updates duplicate detection to be per-search based

Run with: python scripts/per_search_listing_migration.py
"""

import asyncio
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from marktplaats_search.database import DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def backup_database() -> str | None:
    """Create a backup of the database before migration."""
    db_path = Path("data/marktplaats_api.db")
    if not db_path.exists():
        # Try alternative location
        db_path = Path("marktplaats_api.db")

    if db_path.exists():
        backup_name = f"marktplaats_api_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = db_path.parent / backup_name
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return str(backup_path)

    logger.warning("Database file not found, skipping backup")
    return None


async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    columns = result.fetchall()
    return any(col[1] == column_name for col in columns)


async def check_index_exists(conn, index_name: str) -> bool:
    """Check if an index exists."""
    result = await conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND name=:name"),
        {"name": index_name},
    )
    return result.fetchone() is not None


async def get_current_schema_info(conn) -> dict[str, Any]:
    """Get current schema information for listings table."""
    result = await conn.execute(text("PRAGMA table_info(listings)"))
    columns = result.fetchall()

    # Check for unique constraints
    result = await conn.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name='listings'")
    )
    table_sql = result.fetchone()

    return {
        "columns": {col[1]: {"type": col[2], "nullable": not col[3]} for col in columns},
        "table_sql": table_sql[0] if table_sql else None,
        "has_url_unique": "UNIQUE" in (table_sql[0] if table_sql else ""),
    }


async def analyze_duplicate_data(conn) -> dict[str, Any]:
    """Analyze existing data for potential duplicates."""
    # Find URLs that appear multiple times
    result = await conn.execute(
        text("""
        SELECT url, COUNT(*) as count, GROUP_CONCAT(search_id) as search_ids
        FROM listings 
        GROUP BY url 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    )
    duplicates = result.fetchall()

    # Find same URL in different searches (legitimate cross-search duplicates)
    result = await conn.execute(
        text("""
        SELECT url, COUNT(DISTINCT search_id) as search_count, COUNT(*) as total_count
        FROM listings 
        GROUP BY url 
        HAVING COUNT(DISTINCT search_id) > 1
        ORDER BY search_count DESC
    """)
    )
    cross_search = result.fetchall()

    # Find true duplicates (same URL, same search)
    result = await conn.execute(
        text("""
        SELECT search_id, url, COUNT(*) as count
        FROM listings 
        GROUP BY search_id, url 
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    )
    true_duplicates = result.fetchall()

    return {
        "url_duplicates": duplicates,
        "cross_search_duplicates": cross_search,
        "true_duplicates": true_duplicates,
        "total_listings": (await conn.execute(text("SELECT COUNT(*) FROM listings"))).scalar(),
    }


async def remove_true_duplicates(conn) -> int:
    """Remove true duplicates (same search_id + url) keeping the earliest entry."""
    logger.info("Identifying and removing true duplicates...")

    # Find duplicate groups
    result = await conn.execute(
        text("""
        SELECT search_id, url, GROUP_CONCAT(id) as ids, MIN(discovered_at) as earliest
        FROM listings 
        GROUP BY search_id, url 
        HAVING COUNT(*) > 1
    """)
    )
    duplicate_groups = result.fetchall()

    removed_count = 0
    for search_id, url, ids_str, earliest in duplicate_groups:
        ids = ids_str.split(",")

        # Find the ID with the earliest discovered_at time
        result = await conn.execute(
            text("""
            SELECT id FROM listings 
            WHERE search_id = :search_id AND url = :url 
            ORDER BY discovered_at ASC 
            LIMIT 1
        """),
            {"search_id": search_id, "url": url},
        )
        keep_id = result.scalar()

        # Remove all others
        ids_to_remove = [id for id in ids if id != keep_id]
        for id_to_remove in ids_to_remove:
            await conn.execute(text("DELETE FROM listings WHERE id = :id"), {"id": id_to_remove})
            removed_count += 1

        logger.info(
            f"Removed {len(ids_to_remove)} duplicates for search {search_id}, URL: {url[:50]}..."
        )

    return removed_count


async def create_new_listings_table(conn) -> None:
    """Create new listings table with updated schema."""
    logger.info("Creating new listings table with per-search constraints...")

    await conn.execute(
        text("""
        CREATE TABLE listings_new (
            id CHAR(36) PRIMARY KEY,
            search_id CHAR(36) NOT NULL,
            source_listing_id VARCHAR,
            title VARCHAR,
            price VARCHAR,
            price_numeric INTEGER,
            url VARCHAR NOT NULL,  -- Removed UNIQUE constraint
            description_snippet TEXT,
            image_url VARCHAR,
            location VARCHAR,
            seller VARCHAR,
            views INTEGER,
            condition VARCHAR,
            date_posted DATETIME,
            raw_data JSON,
            raw_html TEXT,
            is_new BOOLEAN NOT NULL DEFAULT 1,
            discovered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            
            -- Foreign key constraint
            FOREIGN KEY (search_id) REFERENCES searches (id),
            
            -- Composite unique constraint to prevent same URL within same search
            UNIQUE (search_id, url)
        )
    """)
    )


async def migrate_data(conn) -> int:
    """Migrate data from old table to new table."""
    logger.info("Migrating data to new table structure...")

    # Copy all data to new table
    await conn.execute(
        text("""
        INSERT INTO listings_new (
            id, search_id, source_listing_id, title, price, price_numeric, 
            url, description_snippet, image_url, location, seller, views, 
            condition, date_posted, raw_data, raw_html, is_new, discovered_at
        )
        SELECT 
            id, search_id, source_listing_id, title, price, price_numeric, 
            url, description_snippet, image_url, location, seller, views, 
            condition, date_posted, raw_data, raw_html, is_new, discovered_at
        FROM listings
    """)
    )

    # Count migrated records
    result = await conn.execute(text("SELECT COUNT(*) FROM listings_new"))
    migrated_count = result.scalar()

    return migrated_count


async def create_optimized_indexes(conn) -> None:
    """Create optimized indexes for the new schema."""
    logger.info("Creating optimized indexes...")

    indexes = [
        # Primary lookup indexes
        (
            "idx_listings_search_id",
            "CREATE INDEX idx_listings_search_id ON listings_new (search_id)",
        ),
        ("idx_listings_url", "CREATE INDEX idx_listings_url ON listings_new (url)"),
        # Composite index for duplicate detection (search_id, url)
        (
            "idx_listings_search_url",
            "CREATE INDEX idx_listings_search_url ON listings_new (search_id, url)",
        ),
        # Query optimization indexes
        ("idx_listings_is_new", "CREATE INDEX idx_listings_is_new ON listings_new (is_new)"),
        (
            "idx_listings_discovered_at",
            "CREATE INDEX idx_listings_discovered_at ON listings_new (discovered_at)",
        ),
        (
            "idx_listings_price_numeric",
            "CREATE INDEX idx_listings_price_numeric ON listings_new (price_numeric)",
        ),
        # Compound indexes for common queries
        (
            "idx_listings_search_new",
            "CREATE INDEX idx_listings_search_new ON listings_new (search_id, is_new)",
        ),
        (
            "idx_listings_search_discovered",
            "CREATE INDEX idx_listings_search_discovered ON listings_new (search_id, discovered_at)",
        ),
    ]

    for index_name, sql in indexes:
        try:
            await conn.execute(text(sql))
            logger.info(f"Created index: {index_name}")
        except Exception as e:
            logger.warning(f"Failed to create index {index_name}: {e}")


async def swap_tables(conn) -> None:
    """Swap old and new tables."""
    logger.info("Swapping old and new tables...")

    # Drop old table
    await conn.execute(text("DROP TABLE listings"))

    # Rename new table
    await conn.execute(text("ALTER TABLE listings_new RENAME TO listings"))


async def verify_migration(conn) -> dict[str, Any]:
    """Verify migration was successful."""
    logger.info("Verifying migration results...")

    # Check table structure
    result = await conn.execute(text("PRAGMA table_info(listings)"))
    columns = result.fetchall()

    # Check constraints
    result = await conn.execute(
        text("SELECT sql FROM sqlite_master WHERE type='table' AND name='listings'")
    )
    table_sql = result.fetchone()

    # Count records
    result = await conn.execute(text("SELECT COUNT(*) FROM listings"))
    total_count = result.scalar()

    # Check for remaining duplicates
    result = await conn.execute(
        text("""
        SELECT COUNT(*) FROM (
            SELECT search_id, url, COUNT(*) as count
            FROM listings 
            GROUP BY search_id, url 
            HAVING COUNT(*) > 1
        )
    """)
    )
    remaining_duplicates = result.scalar()

    # Check indexes
    result = await conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='listings'")
    )
    indexes = [row[0] for row in result.fetchall()]

    return {
        "total_records": total_count,
        "remaining_duplicates": remaining_duplicates,
        "has_composite_constraint": "UNIQUE (search_id, url)"
        in (table_sql[0] if table_sql else ""),
        "no_global_url_unique": "url VARCHAR NOT NULL," in (table_sql[0] if table_sql else ""),
        "indexes": indexes,
    }


async def main() -> None:
    """Main migration function."""
    logger.info("Starting per-search listing management migration...")

    # Backup database
    backup_path = await backup_database()
    if backup_path:
        logger.info(f"Backup created at: {backup_path}")

    # Create migration engine
    migration_engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        async with migration_engine.begin() as conn:
            # Analyze current state
            logger.info("Analyzing current database state...")
            schema_info = await get_current_schema_info(conn)
            duplicate_analysis = await analyze_duplicate_data(conn)

            logger.info("Current state:")
            logger.info(f"- Total listings: {duplicate_analysis['total_listings']}")
            logger.info(f"- URLs with duplicates: {len(duplicate_analysis['url_duplicates'])}")
            logger.info(
                f"- Cross-search duplicates: {len(duplicate_analysis['cross_search_duplicates'])}"
            )
            logger.info(f"- True duplicates: {len(duplicate_analysis['true_duplicates'])}")
            logger.info(f"- Has global URL unique constraint: {schema_info['has_url_unique']}")

            # Ask for confirmation
            if duplicate_analysis["true_duplicates"]:
                logger.warning(
                    f"Found {len(duplicate_analysis['true_duplicates'])} true duplicates that will be removed"
                )

            print("\nMigration will:")
            print("1. Remove global URL unique constraint")
            print("2. Add composite constraint (search_id, url)")
            print("3. Remove true duplicates within same search")
            print("4. Create optimized indexes")
            print("5. Allow same listing in multiple searches")

            response = input("\nProceed with migration? (y/N): ")
            if response.lower() != "y":
                logger.info("Migration cancelled")
                return

            # Step 1: Remove true duplicates
            removed_count = await remove_true_duplicates(conn)
            if removed_count > 0:
                logger.info(f"Removed {removed_count} true duplicates")

            # Step 2: Create new table structure
            await create_new_listings_table(conn)

            # Step 3: Migrate data
            migrated_count = await migrate_data(conn)
            logger.info(f"Migrated {migrated_count} listings")

            # Step 4: Create indexes
            await create_optimized_indexes(conn)

            # Step 5: Swap tables
            await swap_tables(conn)

            # Step 6: Verify migration
            verification = await verify_migration(conn)

            logger.info("Migration completed successfully!")
            logger.info("Results:")
            logger.info(f"- Total records after migration: {verification['total_records']}")
            logger.info(f"- Remaining duplicates: {verification['remaining_duplicates']}")
            logger.info(f"- Has composite constraint: {verification['has_composite_constraint']}")
            logger.info(f"- No global URL constraint: {verification['no_global_url_unique']}")
            logger.info(f"- Indexes created: {len(verification['indexes'])}")

            if verification["remaining_duplicates"] > 0:
                logger.warning(f"WARNING: {verification['remaining_duplicates']} duplicates remain")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if backup_path:
            logger.info(f"You can restore from backup: {backup_path}")
        raise
    finally:
        await migration_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Database migration script to update existing users to the new secure schema.
This script will:
1. Back up existing data
2. Update the User table schema
3. Hash existing plaintext tokens
"""

import asyncio
import logging
from pathlib import Path
import shutil
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from database import DATABASE_URL, Base, engine
from models import User
from auth import hash_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backup_database():
    """Create a backup of the database before migration."""
    db_path = Path("marktplaats_api.db")
    if db_path.exists():
        backup_name = f"marktplaats_api.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(db_path, backup_name)
        logger.info(f"Database backed up to {backup_name}")
        return backup_name
    return None


async def check_column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    result = await conn.execute(
        text(f"PRAGMA table_info({table_name})")
    )
    columns = result.fetchall()
    return any(col[1] == column_name for col in columns)


async def migrate_users():
    """Migrate the User table to use hashed tokens."""
    
    # Create a new engine for migration
    migration_engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with migration_engine.begin() as conn:
        logger.info("Starting user table migration...")
        
        # Check current schema
        has_api_token = await check_column_exists(conn, "users", "api_token")
        has_api_token_hash = await check_column_exists(conn, "users", "api_token_hash")
        
        if has_api_token and not has_api_token_hash:
            logger.info("Migrating from plaintext tokens to hashed tokens...")
            
            # Step 1: Add new columns
            logger.info("Adding new columns...")
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN api_token_hash VARCHAR"
            ))
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"
            ))
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN token_created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            ))
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN last_activity DATETIME"
            ))
            
            # Step 2: Get all existing users
            result = await conn.execute(text(
                "SELECT id, api_token FROM users"
            ))
            users = result.fetchall()
            
            # Step 3: Hash existing tokens
            for user_id, plaintext_token in users:
                if plaintext_token:
                    hashed = hash_token(plaintext_token)
                    await conn.execute(
                        text("UPDATE users SET api_token_hash = :hash WHERE id = :id"),
                        {"hash": hashed, "id": user_id}
                    )
                    logger.info(f"Hashed token for user ID {user_id}")
            
            # Step 4: Create a new table with the correct schema
            logger.info("Creating new users table with updated schema...")
            await conn.execute(text("""
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY,
                    user_identifier VARCHAR NOT NULL UNIQUE,
                    api_token_hash VARCHAR NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    token_created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Step 5: Copy data to new table
            await conn.execute(text("""
                INSERT INTO users_new (id, user_identifier, api_token_hash, is_active, token_created_at, created_at)
                SELECT id, user_identifier, api_token_hash, is_active, token_created_at, created_at
                FROM users
            """))
            
            # Step 6: Drop old table and rename new one
            await conn.execute(text("DROP TABLE users"))
            await conn.execute(text("ALTER TABLE users_new RENAME TO users"))
            
            # Step 7: Create indexes
            await conn.execute(text(
                "CREATE UNIQUE INDEX ix_users_user_identifier ON users (user_identifier)"
            ))
            await conn.execute(text(
                "CREATE UNIQUE INDEX ix_users_api_token_hash ON users (api_token_hash)"
            ))
            await conn.execute(text(
                "CREATE INDEX ix_users_id ON users (id)"
            ))
            
            logger.info("Migration completed successfully!")
            logger.warning("IMPORTANT: Existing tokens have been hashed. Users must use their original tokens to authenticate.")
            
        elif has_api_token_hash:
            logger.info("Database already migrated to secure schema")
        else:
            logger.info("Creating fresh database with secure schema...")
            # Create all tables with the new schema
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created with secure schema")


async def main():
    """Main migration function."""
    logger.info("Starting database migration...")
    
    # Backup database
    backup_path = await backup_database()
    if backup_path:
        logger.info(f"Backup created at: {backup_path}")
    
    # Run migration
    try:
        await migrate_users()
        logger.info("Migration completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if backup_path:
            logger.info(f"You can restore from backup: {backup_path}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
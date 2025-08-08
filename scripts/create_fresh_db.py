#!/usr/bin/env python3
"""
Create a fresh database with the new marktplaats-py integrated schema.
This replaces the migration approach when no important data needs to be preserved.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from marktplaats_search.database import Base, engine


async def create_fresh_database():
    """Create all tables with the new schema."""
    print("Creating fresh database with marktplaats-py schema...")

    async with engine.begin() as conn:
        # Drop all existing tables if they exist
        print("Dropping any existing tables...")
        await conn.run_sync(Base.metadata.drop_all)

        # Create all tables with the new schema
        print("Creating new tables with enhanced schema...")
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Fresh database created successfully!")
    print("📊 New schema includes:")
    print("   - Enhanced listing fields from marktplaats-py")
    print("   - Per-search uniqueness constraint")
    print("   - Performance indexes")
    print("   - Seller, location, and category data")


if __name__ == "__main__":
    asyncio.run(create_fresh_database())

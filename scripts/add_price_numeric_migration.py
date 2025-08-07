#!/usr/bin/env python3
"""
Database migration script to add price_numeric field to listings table.

This migration:
1. Adds a price_numeric column to the listings table
2. Populates the column with numeric values extracted from existing price strings
3. Handles various price formats (€ 123,45, Price on request, etc.)

Run with: python scripts/add_price_numeric_migration.py
"""

import re
import sqlite3
import sys
from pathlib import Path


def extract_numeric_price(price_str: str) -> int | None:
    """Extract numeric price in cents from price string."""
    if not price_str:
        return None
        
    price_str = price_str.strip().lower()
    
    # Handle special cases
    if any(phrase in price_str for phrase in ["price on request", "vraagprijs", "v.o.n"]):
        return None
    elif "gratis" in price_str:
        return 0
    
    # Extract numeric value
    numeric_match = re.search(r"[\d.,]+", price_str.replace(",", "."))
    if numeric_match:
        try:
            # Convert to cents for precise integer storage
            return int(float(numeric_match.group().replace(",", ".")) * 100)
        except ValueError:
            return None
    
    return None


def migrate_database(db_path: str):
    """Run the migration on the specified database."""
    print(f"Starting migration for database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if price_numeric column already exists
        cursor.execute("PRAGMA table_info(listings)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "price_numeric" in columns:
            print("price_numeric column already exists. Skipping migration.")
            conn.close()
            return
        
        # Add the price_numeric column
        print("Adding price_numeric column...")
        cursor.execute("ALTER TABLE listings ADD COLUMN price_numeric INTEGER")
        
        # Get all existing listings with their prices
        print("Fetching existing listings...")
        cursor.execute("SELECT id, price FROM listings WHERE price IS NOT NULL")
        listings = cursor.fetchall()
        
        print(f"Processing {len(listings)} listings...")
        updated_count = 0
        
        # Process each listing
        for listing_id, price_str in listings:
            if price_str:
                numeric_price = extract_numeric_price(price_str)
                if numeric_price is not None:
                    cursor.execute(
                        "UPDATE listings SET price_numeric = ? WHERE id = ?",
                        (numeric_price, listing_id)
                    )
                    updated_count += 1
        
        # Commit the changes
        conn.commit()
        print(f"Migration completed successfully!")
        print(f"- Added price_numeric column")
        print(f"- Updated {updated_count} listings with numeric prices")
        print(f"- {len(listings) - updated_count} listings had no extractable numeric price")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    """Main migration function."""
    # Find the database file
    project_root = Path(__file__).parent.parent
    
    # Try multiple possible database locations
    possible_db_paths = [
        project_root / "marktplaats_api.db",
        project_root / "data" / "marktplaats_api.db",
    ]
    
    db_path = None
    for path in possible_db_paths:
        if path.exists():
            db_path = str(path)
            break
    
    if not db_path:
        print("ERROR: Could not find database file.")
        print("Tried:")
        for path in possible_db_paths:
            print(f"  - {path}")
        sys.exit(1)
    
    print(f"Found database at: {db_path}")
    
    # Confirm before proceeding
    response = input("Do you want to proceed with the migration? (y/N): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run the migration
    migrate_database(db_path)


if __name__ == "__main__":
    main()
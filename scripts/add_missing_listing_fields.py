#!/usr/bin/env python3
"""
Add Missing Listing Fields Migration

This script adds the missing structured fields to the listings table and updates
the scraping logic to properly extract and store this data.

Missing fields identified:
- location (String) - Location/city where item is offered
- seller (String) - Seller username/name
- views (Integer) - Number of views the listing has
- condition (String) - Condition of the item (new, used, etc.)
- date_posted (DateTime) - When the listing was originally posted (vs discovered_at)

Usage:
    python scripts/add_missing_listing_fields.py [--dry-run]
"""

import argparse
import sqlite3
import sys
from pathlib import Path


def check_missing_fields(db_path: str):
    """Check which fields are missing from the listings table."""
    print(f"Checking listings table schema: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get current columns
        cursor.execute("PRAGMA table_info(listings)")
        columns = cursor.fetchall()
        current_columns = [col[1] for col in columns]

        print(f"Current columns: {current_columns}")

        # Fields that should exist
        expected_fields = [
            "location",  # Location/city
            "seller",  # Seller name/username
            "views",  # Number of views
            "condition",  # Item condition
            "date_posted",  # Original post date
        ]

        missing_fields = []
        for field in expected_fields:
            if field not in current_columns:
                missing_fields.append(field)
                print(f"❌ Missing field: {field}")
            else:
                print(f"✅ Field exists: {field}")

        conn.close()
        return missing_fields

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return []


def add_missing_fields(db_path: str, missing_fields: list, dry_run: bool = False):
    """Add the missing fields to the listings table."""
    if not missing_fields:
        print("✅ All fields already exist!")
        return True

    if dry_run:
        print(f"DRY RUN: Would add {len(missing_fields)} missing fields:")
        for field in missing_fields:
            print(f"  - ALTER TABLE listings ADD COLUMN {field}")
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Field definitions
        field_definitions = {
            "location": "location TEXT",
            "seller": "seller TEXT",
            "views": "views INTEGER",
            "condition": "condition TEXT",
            "date_posted": "date_posted DATETIME",
        }

        for field in missing_fields:
            if field in field_definitions:
                sql = f"ALTER TABLE listings ADD COLUMN {field_definitions[field]}"
                print(f"Adding field: {sql}")
                cursor.execute(sql)

        conn.commit()
        conn.close()

        print(f"✅ Successfully added {len(missing_fields)} fields!")
        return True

    except Exception as e:
        print(f"❌ Error adding fields: {e}")
        return False


def update_models_file():
    """Show the user what needs to be updated in the models file."""
    print("\n" + "=" * 60)
    print("MANUAL UPDATES REQUIRED")
    print("=" * 60)
    print("\n1. Update marktplaats_search/models.py")
    print("Add these lines to the Listing class after line 77:")
    print("""
    # Additional listing metadata
    location = Column(String, nullable=True)           # Location/city
    seller = Column(String, nullable=True)             # Seller name/username
    views = Column(Integer, nullable=True)             # Number of views
    condition = Column(String, nullable=True)          # Item condition
    date_posted = Column(DateTime(timezone=True), nullable=True)  # Original post date
""")

    print("\n2. Update marktplaats_search/client.py")
    print("Add these lines to the ListingItem class:")
    print("""
    location: str | None = None
    seller: str | None = None  
    views: int | None = None
    condition: str | None = None
    date_posted: datetime | None = None
""")

    print("\n3. Update marktplaats_search/api.py")
    print("Add these lines to the ListingResponse class:")
    print("""
    location: str | None = None
    seller: str | None = None
    views: int | None = None 
    condition: str | None = None
    date_posted: datetime | None = None
""")

    print("\n4. Update scraping logic in marktplaats_search/client.py")
    print("Add extraction logic in _parse_single_listing method:")
    print("""
    # Extract location
    location = None
    location_elem = container.find(class_=re.compile(r"location|city", re.I))
    if location_elem:
        location = self._clean_text(location_elem.get_text())
    
    # Extract seller info  
    seller = None
    seller_elem = container.find(class_=re.compile(r"seller|username", re.I))
    if seller_elem:
        seller = self._clean_text(seller_elem.get_text())
        
    # Extract views
    views = None
    views_elem = container.find(string=re.compile(r"\\d+.*views?", re.I))
    if views_elem:
        views_match = re.search(r"(\\d+)", views_elem)
        if views_match:
            views = int(views_match.group(1))
            
    # Extract condition
    condition = None
    condition_elem = container.find(class_=re.compile(r"condition|state", re.I))
    if condition_elem:
        condition = self._clean_text(condition_elem.get_text())
        
    # Extract post date
    date_posted = None
    date_elem = container.find(class_=re.compile(r"date|posted", re.I))
    if date_elem:
        # Parse date string to datetime object
        date_text = self._clean_text(date_elem.get_text())
        # Add date parsing logic here
""")

    print("\n5. Update marktplaats_search/scheduler.py")
    print("Add these fields when creating new listings:")
    print("""
    location=listing_data.location,
    seller=listing_data.seller, 
    views=listing_data.views,
    condition=listing_data.condition,
    date_posted=listing_data.date_posted,
""")

    print("\n" + "=" * 60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Add missing structured fields to listings table")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    args = parser.parse_args()

    # Find database
    project_root = Path(__file__).parent.parent
    possible_paths = [
        project_root / "marktplaats_api.db",
        project_root / "data" / "marktplaats_api.db",
    ]

    db_path = None
    for path in possible_paths:
        if path.exists() and path.stat().st_size > 0:
            db_path = str(path)
            break

    if not db_path:
        print("❌ Could not find database file")
        sys.exit(1)

    print("=" * 60)
    print("ADD MISSING LISTING FIELDS")
    print("=" * 60)

    # Check what's missing
    missing_fields = check_missing_fields(db_path)

    if not missing_fields:
        print("\n✅ All required fields already exist!")
        return

    print(f"\n🔧 Found {len(missing_fields)} missing fields")

    if not args.dry_run:
        response = input(f"\nAdd {len(missing_fields)} missing fields to database? (y/N): ")
        if response.lower() != "y":
            print("Operation cancelled.")
            return

    # Add missing fields
    success = add_missing_fields(db_path, missing_fields, args.dry_run)

    if success and not args.dry_run:
        # Show manual updates needed
        update_models_file()
        print("\nAfter making the manual updates:")
        print("1. Restart your application server")
        print("2. The new fields will be populated as new listings are scraped")
        print("3. Existing listings will have NULL values for these fields")

    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Check and Fix Database Schema

This script checks if the database has the required schema and fixes any issues.
Specifically checks for the price_numeric column that was recently added.

Usage:
    python scripts/check_and_fix_database.py
"""

import sqlite3
import sys
from pathlib import Path


def check_database_schema(db_path: str):
    """Check the current database schema."""
    print(f"Checking database schema: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        print(f"Found tables: {table_names}")
        
        if not table_names:
            print("❌ Database is empty - no tables found")
            conn.close()
            return False
        
        # Check listings table schema if it exists
        if 'listings' in table_names:
            cursor.execute("PRAGMA table_info(listings)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            print(f"Listings table columns: {column_names}")
            
            if 'price_numeric' not in column_names:
                print("❌ Missing 'price_numeric' column in listings table")
                conn.close()
                return False
            else:
                print("✅ Schema looks correct - price_numeric column exists")
        else:
            print("❌ Missing 'listings' table")
            conn.close()
            return False
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


def fix_database_schema(db_path: str):
    """Fix database schema issues."""
    print(f"Fixing database schema: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if listings table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='listings'")
        if not cursor.fetchone():
            print("Listings table doesn't exist - database needs full initialization")
            conn.close()
            return False
        
        # Check if price_numeric column exists
        cursor.execute("PRAGMA table_info(listings)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'price_numeric' not in column_names:
            print("Adding price_numeric column...")
            cursor.execute("ALTER TABLE listings ADD COLUMN price_numeric INTEGER")
            
            # Update existing records with numeric prices
            cursor.execute("SELECT id, price FROM listings WHERE price IS NOT NULL")
            listings = cursor.fetchall()
            
            updated_count = 0
            for listing_id, price_str in listings:
                if price_str:
                    # Extract numeric value from price string
                    import re
                    numeric_match = re.search(r"[\d.,]+", price_str.replace(",", "."))
                    if numeric_match:
                        try:
                            numeric_value = int(float(numeric_match.group().replace(",", ".")) * 100)
                            cursor.execute(
                                "UPDATE listings SET price_numeric = ? WHERE id = ?",
                                (numeric_value, listing_id)
                            )
                            updated_count += 1
                        except ValueError:
                            pass
            
            conn.commit()
            print(f"✅ Added price_numeric column and updated {updated_count} records")
        else:
            print("✅ price_numeric column already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        return False


def backup_database(db_path: str):
    """Create a backup of the database."""
    from datetime import datetime
    
    db_file = Path(db_path)
    if not db_file.exists():
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_file.parent / f"{db_file.stem}_backup_{timestamp}{db_file.suffix}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return None


def main():
    """Main function."""
    # Find the database file
    project_root = Path(__file__).parent.parent
    
    possible_db_paths = [
        project_root / "marktplaats_api.db",
        project_root / "data" / "marktplaats_api.db",
    ]
    
    db_path = None
    for path in possible_db_paths:
        if path.exists() and path.stat().st_size > 0:  # File exists and is not empty
            db_path = str(path)
            break
    
    if not db_path:
        print("❌ Could not find a valid database file.")
        print("Tried:")
        for path in possible_db_paths:
            status = "exists but empty" if path.exists() else "not found"
            print(f"  - {path} ({status})")
        print("\n💡 If you haven't started the application yet, run 'python main.py' first to initialize the database.")
        sys.exit(1)
    
    print("=" * 60)
    print("DATABASE SCHEMA CHECK AND FIX")
    print("=" * 60)
    
    # Check current schema
    schema_ok = check_database_schema(db_path)
    
    if schema_ok:
        print("\n✅ Database schema is correct!")
        print("The 500 error might be caused by something else. Check the server logs for more details.")
        return
    
    print("\n🔧 Database schema needs fixing...")
    
    # Ask for confirmation
    response = input("\nDo you want to fix the database schema? This will modify your database. (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        sys.exit(0)
    
    # Create backup
    backup_path = backup_database(db_path)
    if backup_path:
        print("✅ Backup created successfully")
    else:
        response = input("❌ Could not create backup. Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            sys.exit(0)
    
    # Fix schema
    if fix_database_schema(db_path):
        print("\n✅ Database schema fixed successfully!")
        print("\nNext steps:")
        print("1. Restart your application server")
        print("2. Try loading search results again")
        print("3. If you still get errors, check the server logs")
    else:
        print("\n❌ Could not fix database schema.")
        print("You may need to:")
        print("1. Stop your application server")
        print("2. Delete the database file to start fresh")
        print("3. Restart the application to recreate the database")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
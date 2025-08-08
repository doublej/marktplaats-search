#!/usr/bin/env python3
"""
Create a fresh database with the current schema.
This replaces the migration approach when no important data needs to be preserved.

Usage:
    python scripts/create_fresh_db.py [--drop-existing] [--backup]

Options:
    --drop-existing: Drop existing tables before creating new ones
    --backup: Create a backup before dropping existing data
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from marktplaats_search.cli.database_cli import DatabaseCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Create a fresh database with current schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--drop-existing", action="store_true", help="Drop existing tables before creating new ones"
    )

    parser.add_argument(
        "--backup", action="store_true", help="Create a backup before dropping existing data"
    )

    args = parser.parse_args()

    try:
        cli = DatabaseCLI()

        # Create backup if requested and dropping existing data
        if args.backup and args.drop_existing:
            print("Creating database backup...")
            backup_result = cli.backup_database()
            if backup_result["success"]:
                print(cli.format_backup_results(backup_result))
            else:
                print(f"Backup failed: {backup_result['error']}")
                sys.exit(1)
            print()

        # Create fresh database
        print(
            f"Creating fresh database{' (dropping existing data)' if args.drop_existing else ''}..."
        )

        create_result = cli.create_fresh_database(drop_existing=args.drop_existing)

        if create_result["success"]:
            print("✅ Fresh database created successfully!")
            print("📊 New schema includes:")
            print("   - Enhanced listing fields from marktplaats-py")
            print("   - Per-search uniqueness constraint")
            print("   - Performance indexes")
            print("   - Optimized database structure")

            if create_result.get("optimization"):
                print("\n🔧 Database optimizations applied:")
                for operation, status in create_result["optimization"].items():
                    print(f"   - {operation.capitalize()}: {status}")
        else:
            print(f"❌ Failed to create database: {create_result['message']}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during database creation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Check and Fix Database Schema

This script checks database integrity, verifies schema, and performs maintenance operations.

Usage:
    python scripts/check_and_fix_database.py [--info-only] [--backup]

Options:
    --info-only: Only show database information without performing maintenance
    --backup: Create a backup before performing any fixes
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.database_cli import DatabaseCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Check and fix database schema and integrity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Only show database information without performing maintenance",
    )

    parser.add_argument(
        "--backup", action="store_true", help="Create a backup before performing any fixes"
    )

    args = parser.parse_args()

    try:
        cli = DatabaseCLI()

        # Create backup if requested
        if args.backup:
            print("Creating database backup...")
            backup_result = cli.backup_database()
            if backup_result["success"]:
                print(cli.format_backup_results(backup_result))
            else:
                print(f"Backup failed: {backup_result['error']}")
                sys.exit(1)
            print()

        if args.info_only:
            # Show database information only
            info_result = asyncio.run(cli.show_database_info())
            if info_result["success"]:
                print(cli.format_database_info(info_result))
            else:
                print(f"Error: {info_result['message']}")
                sys.exit(1)
        else:
            # Perform full check and maintenance
            check_result = cli.check_and_fix_database()
            if check_result["success"]:
                print(cli.format_check_results(check_result))
            else:
                print(f"Error: {check_result['message']}")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during database check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

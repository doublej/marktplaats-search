#!/usr/bin/env python3
"""
Refresh All Searches Script

This script will:
1. Export all current searches to a backup file
2. Delete all searches and their results
3. Re-create all searches with their original parameters

This is useful for:
- Clearing accumulated results while keeping search configurations
- Resetting search states after schema changes
- Clean slate with same search parameters

Usage:
    python scripts/refresh_all_searches.py [--dry-run] [--backup-file path] [--user-id id]

Options:
    --dry-run: Show what would be done without actually doing it
    --backup-file: Specify custom backup file path (default: data/searches_backup_YYYYMMDD_HHMMSS.json)
    --user-id: Limit operations to specific user (default: all users)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.search_cli import SearchCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Refresh all searches by deleting and recreating them",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )

    parser.add_argument(
        "--backup-file",
        type=Path,
        help="Custom backup file path (default: data/searches_backup_YYYYMMDD_HHMMSS.json)",
    )

    parser.add_argument(
        "--user-id",
        help="Limit operations to specific user ID (default: all users)",
    )

    args = parser.parse_args()

    try:
        cli = SearchCLI()
        results = asyncio.run(cli.refresh_searches(args.backup_file, args.user_id, args.dry_run))

        if results["success"]:
            print(cli.format_refresh_results(results, verbose=True))
        else:
            print(f"Error: {results['message']}")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during refresh: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

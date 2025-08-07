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
    python scripts/refresh_all_searches.py [--dry-run] [--backup-file path]

Options:
    --dry-run: Show what would be done without actually doing it
    --backup-file: Specify custom backup file path (default: data/searches_backup_YYYYMMDD_HHMMSS.json)
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.future import select

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.database import AsyncSessionLocal
from marktplaats_search.models import Listing, Search, SearchStatus


async def export_searches_to_backup(backup_file: Path, dry_run: bool = False) -> list[dict]:
    """Export all searches to a backup file and return the search data."""
    searches_data = []

    async with AsyncSessionLocal() as db:
        # Get all searches
        result = await db.execute(select(Search))
        searches = result.scalars().all()

        if not searches:
            print("No searches found to backup.")
            return []

        print(f"Found {len(searches)} searches to backup.")

        for search in searches:
            search_data = {
                "user_id": search.user_id,
                "query": search.query,
                "zip_code": search.zip_code,
                "distance": search.distance,
                "price_from": search.price_from,
                "price_to": search.price_to,
                "limit": search.limit,
                "sort_by": search.sort_by,
                "sort_order": search.sort_order,
                "interval": search.interval,
                "status": search.status.value,
                "original_id": str(search.id),
                "created_at": search.created_at.isoformat(),
                "updated_at": search.updated_at.isoformat() if search.updated_at else None,
            }
            searches_data.append(search_data)

            if dry_run:
                print(f"  Would backup: '{search.query}' (ID: {search.id})")
            else:
                print(f"  Backing up: '{search.query}' (ID: {search.id})")

        if not dry_run:
            # Save to backup file
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "export_date": datetime.now().isoformat(),
                        "total_searches": len(searches_data),
                        "searches": searches_data,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            print(f"Backup saved to: {backup_file}")

    return searches_data


async def delete_all_searches(dry_run: bool = False):
    """Delete all searches and their results."""
    async with AsyncSessionLocal() as db:
        # Get count for reporting
        search_result = await db.execute(select(Search))
        searches = search_result.scalars().all()
        search_count = len(searches)

        listing_result = await db.execute(select(Listing))
        listings = listing_result.scalars().all()
        listing_count = len(listings)

        if search_count == 0:
            print("No searches to delete.")
            return

        if dry_run:
            print(f"Would delete {search_count} searches and {listing_count} listings.")
            return

        print(f"Deleting {listing_count} listings...")
        await db.execute(delete(Listing))

        print(f"Deleting {search_count} searches...")
        await db.execute(delete(Search))

        await db.commit()
        print("All searches and listings deleted successfully.")


async def recreate_searches_from_backup(searches_data: list[dict], dry_run: bool = False):
    """Recreate searches from backup data."""
    if not searches_data:
        print("No search data to recreate.")
        return

    if dry_run:
        print(f"Would recreate {len(searches_data)} searches.")
        for search_data in searches_data:
            print(f"  Would recreate: '{search_data['query']}'")
        return

    async with AsyncSessionLocal() as db:
        created_count = 0

        for search_data in searches_data:
            try:
                # Create new search with original parameters but new ID
                new_search = Search(
                    user_id=search_data["user_id"],
                    query=search_data["query"],
                    zip_code=search_data.get("zip_code"),
                    distance=search_data.get("distance"),
                    price_from=search_data.get("price_from"),
                    price_to=search_data.get("price_to"),
                    limit=search_data.get("limit", 25),
                    sort_by=search_data.get("sort_by"),
                    sort_order=search_data.get("sort_order"),
                    interval=search_data["interval"],
                    status=SearchStatus(search_data.get("status", "active")),
                )

                db.add(new_search)
                created_count += 1
                print(f"  Recreated: '{search_data['query']}' (new ID will be assigned)")

            except Exception as e:
                print(f"  Failed to recreate search '{search_data['query']}': {e}")

        await db.commit()
        print(f"Successfully recreated {created_count}/{len(searches_data)} searches.")


async def refresh_all_searches(backup_file: Path, dry_run: bool = False):
    """Main function to refresh all searches."""
    print(f"{'DRY RUN: ' if dry_run else ''}Refreshing all searches...")
    print("=" * 50)

    # Step 1: Backup current searches
    print("Step 1: Backing up current searches...")
    searches_data = await export_searches_to_backup(backup_file, dry_run)

    if not searches_data:
        print("No searches to refresh. Exiting.")
        return

    print()

    # Step 2: Delete all searches and results
    print("Step 2: Deleting all searches and results...")
    await delete_all_searches(dry_run)
    print()

    # Step 3: Recreate searches
    print("Step 3: Recreating searches from backup...")
    await recreate_searches_from_backup(searches_data, dry_run)
    print()

    print("=" * 50)
    if dry_run:
        print("DRY RUN COMPLETE - No changes were made.")
        print("Run without --dry-run to execute the refresh.")
    else:
        print("REFRESH COMPLETE!")
        print(f"Backup saved to: {backup_file}")
        print("All searches have been refreshed with clean result sets.")
    print("=" * 50)


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

    args = parser.parse_args()

    # Generate default backup file name if not provided
    if not args.backup_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = project_root / "data"
        args.backup_file = data_dir / f"searches_backup_{timestamp}.json"

    try:
        asyncio.run(refresh_all_searches(args.backup_file, args.dry_run))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error during refresh: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

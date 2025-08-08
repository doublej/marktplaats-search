"""Search Management Service

Centralized business logic for search operations including backup, refresh,
and recreation operations. This eliminates duplication between scripts and
API endpoints.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import AsyncSessionLocal
from ..models import Listing, Search, SearchStatus


class SearchManagementService:
    """Service for managing search operations like backup, refresh, and recreation."""

    def __init__(self, db_session: AsyncSession | None = None):
        """Initialize service with optional database session."""
        self._db_session = db_session

    async def _get_db_session(self) -> AsyncSession:
        """Get database session, either provided or create new one."""
        if self._db_session:
            return self._db_session
        return AsyncSessionLocal()

    async def export_searches_to_backup(
        self, backup_file: Path, user_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Export searches to backup file and return search data.

        Args:
            backup_file: Path to save backup file
            user_id: Optional user ID to filter searches (None for all searches)

        Returns:
            List of search data dictionaries
        """
        searches_data = []

        async with await self._get_db_session() as db:
            # Build query with optional user filter
            query = select(Search)
            if user_id:
                query = query.where(Search.user_id == user_id)

            result = await db.execute(query)
            searches = result.scalars().all()

            if not searches:
                return []

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

            # Save to backup file
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "export_date": datetime.now().isoformat(),
                        "total_searches": len(searches_data),
                        "user_filter": user_id,
                        "searches": searches_data,
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

        return searches_data

    async def delete_searches_and_listings(self, user_id: str | None = None) -> tuple[int, int]:
        """Delete searches and their associated listings.

        Args:
            user_id: Optional user ID to filter deletions (None for all searches)

        Returns:
            Tuple of (deleted_searches_count, deleted_listings_count)
        """
        async with await self._get_db_session() as db:
            # Count searches and listings before deletion
            search_query = select(Search)
            if user_id:
                search_query = search_query.where(Search.user_id == user_id)

            search_result = await db.execute(search_query)
            searches = search_result.scalars().all()
            search_count = len(searches)

            # Count listings for these searches
            if user_id:
                # Get search IDs for this user
                search_ids = [search.id for search in searches]
                if search_ids:
                    listing_result = await db.execute(
                        select(Listing).where(Listing.search_id.in_(search_ids))
                    )
                else:
                    listing_result = None
            else:
                listing_result = await db.execute(select(Listing))

            listing_count = len(listing_result.scalars().all()) if listing_result else 0

            if search_count == 0:
                return 0, 0

            # Delete listings first (foreign key constraints)
            if user_id and search_ids:
                await db.execute(delete(Listing).where(Listing.search_id.in_(search_ids)))
            elif not user_id:
                await db.execute(delete(Listing))

            # Delete searches
            delete_query = delete(Search)
            if user_id:
                delete_query = delete_query.where(Search.user_id == user_id)

            await db.execute(delete_query)
            await db.commit()

            return search_count, listing_count

    async def recreate_searches_from_backup(
        self, searches_data: list[dict[str, Any]]
    ) -> tuple[int, list[str]]:
        """Recreate searches from backup data.

        Args:
            searches_data: List of search data dictionaries

        Returns:
            Tuple of (created_count, error_messages)
        """
        if not searches_data:
            return 0, []

        async with await self._get_db_session() as db:
            created_count = 0
            error_messages = []

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

                except Exception as e:
                    error_messages.append(
                        f"Failed to recreate search '{search_data['query']}': {e}"
                    )

            await db.commit()
            return created_count, error_messages

    async def refresh_searches(
        self, backup_file: Path, user_id: str | None = None
    ) -> dict[str, Any]:
        """Complete refresh operation: backup, delete, and recreate searches.

        Args:
            backup_file: Path to save backup file
            user_id: Optional user ID to filter operations (None for all searches)

        Returns:
            Dictionary with operation results and statistics
        """
        # Step 1: Backup current searches
        searches_data = await self.export_searches_to_backup(backup_file, user_id)

        if not searches_data:
            return {
                "success": False,
                "message": "No searches found to refresh",
                "backup_file": None,
                "deleted_searches": 0,
                "deleted_listings": 0,
                "recreated_searches": 0,
                "errors": [],
            }

        # Step 2: Delete searches and listings
        deleted_searches, deleted_listings = await self.delete_searches_and_listings(user_id)

        # Step 3: Recreate searches
        recreated_count, errors = await self.recreate_searches_from_backup(searches_data)

        return {
            "success": True,
            "message": "Refresh completed successfully",
            "backup_file": str(backup_file),
            "deleted_searches": deleted_searches,
            "deleted_listings": deleted_listings,
            "recreated_searches": recreated_count,
            "errors": errors,
        }

    async def get_search_counts(self, user_id: str | None = None) -> dict[str, int]:
        """Get counts of searches and listings.

        Args:
            user_id: Optional user ID to filter counts (None for all)

        Returns:
            Dictionary with search and listing counts
        """
        async with await self._get_db_session() as db:
            # Count searches
            search_query = select(Search)
            if user_id:
                search_query = search_query.where(Search.user_id == user_id)

            search_result = await db.execute(search_query)
            search_count = len(search_result.scalars().all())

            # Count listings
            if user_id:
                # Get search IDs for this user first
                searches = search_result.scalars().all()
                search_ids = [search.id for search in searches]
                if search_ids:
                    listing_result = await db.execute(
                        select(Listing).where(Listing.search_id.in_(search_ids))
                    )
                    listing_count = len(listing_result.scalars().all())
                else:
                    listing_count = 0
            else:
                listing_result = await db.execute(select(Listing))
                listing_count = len(listing_result.scalars().all())

            return {
                "searches": search_count,
                "listings": listing_count,
            }

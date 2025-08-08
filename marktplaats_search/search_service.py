"""
Search service using CRUD base patterns.
Provides business logic for search management operations.
"""

import uuid
from typing import Any

from fastapi import HTTPException
from fastapi import status as http_status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .crud_base import CRUDBase
from .models import Search, SearchStatus
from .scheduler import remove_search_job, schedule_search_job


class SearchCreateData(BaseModel):
    """Data class for search creation."""

    user_id: int
    query: str
    zip_code: str | None = None
    distance: int | None = None
    price_from: int | None = None
    price_to: int | None = None
    interval: int
    limit: int = 25
    sort_by: str | None = None
    sort_order: str | None = None
    status: SearchStatus = SearchStatus.ACTIVE

    class Config:
        use_enum_values = True


class SearchUpdateData(BaseModel):
    """Data class for search updates."""

    query: str | None = None
    zip_code: str | None = None
    distance: int | None = None
    price_from: int | None = None
    price_to: int | None = None
    interval: int | None = None
    limit: int | None = None
    sort_by: str | None = None
    sort_order: str | None = None
    status: SearchStatus | None = None

    class Config:
        use_enum_values = True


class SearchCRUD(CRUDBase[Search, SearchCreateData, SearchUpdateData]):
    """CRUD operations for Search model."""

    def __init__(self) -> None:
        super().__init__(Search)

    async def update_status(
        self, db: AsyncSession, search_id: uuid.UUID, new_status: SearchStatus
    ) -> Search:
        """Update search status and handle scheduler integration."""
        search = await self.get_or_404(db, search_id)

        # Update the status
        search.status = new_status
        db.add(search)
        await db.commit()
        await db.refresh(search)

        # Update scheduler based on new status
        if new_status == SearchStatus.ACTIVE:
            schedule_search_job(search)
        else:
            remove_search_job(search)

        return search


class SearchService:
    """
    High-level search service with business logic.

    Combines CRUD operations with search-specific business rules
    and scheduler integration.
    """

    def __init__(self) -> None:
        self.crud = SearchCRUD()

    async def create_search(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        query: str,
        zip_code: str | None = None,
        distance: int | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        interval: int = 3600,
        limit: int = 25,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> Search:
        """Create a new search with validation and scheduler integration."""

        # Validate price range
        if price_from is not None and price_from < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="price_from must be non-negative",
            )

        if price_to is not None and price_to < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail="price_to must be non-negative"
            )

        if price_from is not None and price_to is not None and price_from > price_to:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="price_from must be less than or equal to price_to",
            )

        # Validate interval
        if interval < 300:  # Minimum 5 minutes
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="interval must be at least 300 seconds (5 minutes)",
            )

        # Create search data
        search_data = SearchCreateData(
            user_id=user_id,
            query=query.strip(),
            zip_code=zip_code.strip() if zip_code else None,
            distance=distance,
            price_from=price_from,
            price_to=price_to,
            interval=interval,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            status=SearchStatus.ACTIVE,
        )

        # Create the search
        search = await self.crud.create(db, obj_in=search_data)

        # Schedule the search job
        schedule_search_job(search)

        return search

    async def get_search(self, db: AsyncSession, search_id: uuid.UUID, user_id: int) -> Search:
        """Get a search by ID that belongs to the user."""
        return await self.crud.get_by_owner_and_id_or_404(db, id=search_id, owner_id=user_id)

    async def get_user_searches(
        self, db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Search]:
        """Get all searches for a user."""
        return await self.crud.get_by_owner(db, owner_id=user_id, skip=skip, limit=limit)

    async def update_search(
        self,
        db: AsyncSession,
        *,
        search_id: uuid.UUID,
        user_id: int,
        query: str | None = None,
        zip_code: str | None = None,
        distance: int | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        interval: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
        status: SearchStatus | None = None,
    ) -> Search:
        """Update search with validation."""

        # Get existing search
        search = await self.get_search(db, search_id, user_id)

        # Validate updates
        if price_from is not None and price_from < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="price_from must be non-negative",
            )

        if price_to is not None and price_to < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST, detail="price_to must be non-negative"
            )

        # Check price range consistency
        final_price_from = price_from if price_from is not None else search.price_from
        final_price_to = price_to if price_to is not None else search.price_to

        if (
            final_price_from is not None
            and final_price_to is not None
            and final_price_from > final_price_to
        ):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="price_from must be less than or equal to price_to",
            )

        if interval is not None and interval < 300:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="interval must be at least 300 seconds (5 minutes)",
            )

        # Create update data with only non-None values
        update_data: dict[str, Any] = {}
        if query is not None:
            update_data["query"] = query.strip()
        if zip_code is not None:
            update_data["zip_code"] = zip_code.strip() if zip_code else None
        if distance is not None:
            update_data["distance"] = distance
        if price_from is not None:
            update_data["price_from"] = price_from
        if price_to is not None:
            update_data["price_to"] = price_to
        if interval is not None:
            update_data["interval"] = interval
        if limit is not None:
            update_data["limit"] = limit
        if sort_by is not None:
            update_data["sort_by"] = sort_by
        if sort_order is not None:
            update_data["sort_order"] = sort_order
        if status is not None:
            update_data["status"] = status

        # Update the search
        if update_data:
            search = await self.crud.update(db, db_obj=search, obj_in=update_data)

            # Update scheduler if status changed
            if "status" in update_data:
                if update_data["status"] == SearchStatus.ACTIVE:
                    schedule_search_job(search)
                else:
                    remove_search_job(search)
            elif search.status == SearchStatus.ACTIVE:
                # Reschedule if search is active and other parameters changed
                schedule_search_job(search)

        return search

    async def delete_search(self, db: AsyncSession, search_id: uuid.UUID, user_id: int) -> None:
        """Delete a search and remove from scheduler."""
        search = await self.get_search(db, search_id, user_id)

        # Remove from scheduler
        remove_search_job(search)

        # Delete from database
        await self.crud.delete(db, id=search_id)

    async def pause_search(self, db: AsyncSession, search_id: uuid.UUID, user_id: int) -> Search:
        """Pause a search."""
        await self.get_search(db, search_id, user_id)
        return await self.crud.update_status(db, search_id, SearchStatus.INACTIVE)

    async def resume_search(self, db: AsyncSession, search_id: uuid.UUID, user_id: int) -> Search:
        """Resume a paused search."""
        await self.get_search(db, search_id, user_id)
        return await self.crud.update_status(db, search_id, SearchStatus.ACTIVE)


# Global service instance
search_service = SearchService()

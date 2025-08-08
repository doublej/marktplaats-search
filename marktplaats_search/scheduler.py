import logging
import uuid
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .client import ListingItem, fetch_listings
from .database import AsyncSessionLocal  # Use the session factory directly for background tasks
from .models import Listing, Search, SearchStatus

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(
    timezone="UTC",
    executors={"default": {"type": "asyncio"}},
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 30},
)


async def run_single_search(search_id: uuid.UUID) -> None:
    """
    Executes a single search, fetches listings, and stores new ones.
    """
    logger.info(f"SCHEDULER: Running search {search_id} at {datetime.now(UTC)}")

    # Create a fresh async session for this job
    try:
        async with AsyncSessionLocal() as db:
            # Fetch the search instance, eager load existing listings to check URLs
            result = await db.execute(
                select(Search).options(selectinload(Search.listings)).where(Search.id == search_id)
            )
            search_instance = result.scalars().first()

            if not search_instance:
                logger.warning(f"SCHEDULER: Search {search_id} not found. Removing job if exists.")
                if scheduler.get_job(str(search_id)):
                    scheduler.remove_job(str(search_id))
                return

            if search_instance.status != SearchStatus.ACTIVE:
                logger.info(
                    f"SCHEDULER: Search {search_id} is not active ({search_instance.status}). Skipping run."
                )
                # Job should be removed/paused by API logic that changes status
                return

            new_listings_data: list[ListingItem] = await fetch_listings(
                query=search_instance.query,
                zip_code=search_instance.zip_code,
                distance=search_instance.distance,
                price_from=search_instance.price_from,
                price_to=search_instance.price_to,
                limit=search_instance.limit,
                sort_by=search_instance.sort_by,
                sort_order=search_instance.sort_order,
            )

            added_count = 0

            # Process all listings in a single transaction for better performance
            new_listings_to_add = []
            for listing_data in new_listings_data:
                try:
                    # Check if listing already exists FOR THIS SEARCH (per-search duplicate detection)
                    existing_listing = await db.execute(
                        select(Listing).where(
                            Listing.search_id == search_instance.id,
                            Listing.url == str(listing_data.url),
                        )
                    )
                    if existing_listing.scalars().first() is None:
                        # Listing doesn't exist for this search, create new one
                        # Convert price_numeric from cents to euros for Float field
                        price_float = (
                            listing_data.price_numeric / 100.0
                            if listing_data.price_numeric is not None
                            else None
                        )

                        new_db_listing = Listing(
                            search_id=search_instance.id,
                            source_listing_id=listing_data.source_listing_id,
                            title=listing_data.title,
                            price=price_float,
                            price_numeric=listing_data.price_numeric,
                            url=str(listing_data.url),
                            description_snippet=listing_data.description_snippet,
                            image_url=str(listing_data.image_url)
                            if listing_data.image_url
                            else None,
                            raw_html=listing_data.raw_html,
                            is_new=True,  # Always new for this specific search
                            # Additional listing metadata
                            location=listing_data.location,
                            seller=listing_data.seller,
                            views=listing_data.views,
                            condition=listing_data.condition,
                            date_posted=listing_data.date_posted,
                        )
                        new_listings_to_add.append(new_db_listing)
                        added_count += 1
                    else:
                        logger.debug(
                            f"SCHEDULER: Listing {listing_data.url} already exists for search {search_instance.id}"
                        )

                except Exception as listing_error:
                    # Log individual listing errors but continue with others
                    logger.warning(f"Failed to add listing {listing_data.url}: {listing_error}")

            # Add all new listings in batch
            if new_listings_to_add:
                for listing in new_listings_to_add:
                    db.add(listing)

            search_instance.last_run_at = datetime.now(UTC)
            search_instance.last_error = None
            if added_count > 0:
                logger.info(f"SCHEDULER: Added {added_count} new listings for search {search_id}.")

            await db.commit()

    except Exception as e:
        logger.error(f"SCHEDULER: Error running search {search_id}: {e}", exc_info=True)
        # Update search with error status and message in a new session
        try:
            async with AsyncSessionLocal() as error_db:
                error_search_instance = await error_db.get(Search, search_id)
                if error_search_instance:
                    error_search_instance.last_run_at = datetime.now(UTC)
                    error_search_instance.last_error = str(e)
                    # Optionally change status to ERROR, or just log and retry next interval
                    # error_search_instance.status = SearchStatus.ERROR
                    await error_db.commit()
        except Exception as error_handling_error:
            logger.error(f"SCHEDULER: Error updating search error status: {error_handling_error}")


def schedule_search_job(search: Search) -> None:
    """Schedule, modify, or remove a search job based on search status and interval."""
    job_id = str(search.id)

    try:
        if search.status == SearchStatus.ACTIVE and search.interval > 0:
            # Create proper trigger instance
            trigger = IntervalTrigger(seconds=search.interval)

            job_details = {
                "func": run_single_search,
                "trigger": trigger,
                "args": [search.id],
                "next_run_time": datetime.now(UTC),  # Run immediately then interval
            }

            existing_job = scheduler.get_job(job_id)
            if existing_job:
                # When modifying, job_id is the first arg, other changes in **job_details
                scheduler.modify_job(job_id, **job_details)
                logger.info(
                    f"SCHEDULER: Modified/Rescheduled search {job_id} to run every {search.interval}s"
                )
            else:
                # When adding, id is part of job_details
                scheduler.add_job(id=job_id, **job_details)
                logger.info(f"SCHEDULER: Scheduled search {job_id} to run every {search.interval}s")
        else:
            # Remove job if search is inactive or has invalid interval
            existing_job = scheduler.get_job(job_id)
            if existing_job:
                scheduler.remove_job(job_id)
                logger.info(
                    f"SCHEDULER: Removed job for search {job_id} (status: {search.status}, interval: {search.interval})."
                )

    except Exception as e:
        logger.error(f"SCHEDULER: Error scheduling job for search {job_id}: {e}", exc_info=True)
        raise


def remove_search_job(search: Search) -> None:
    """Remove a search job from the scheduler."""
    job_id = str(search.id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"SCHEDULER: Removed job for search {job_id}")


async def initialize_scheduler() -> None:
    logger.info("SCHEDULER: Initializing and loading active searches...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Search).where(Search.status == SearchStatus.ACTIVE))
        active_searches: list[Search] = list(result.scalars().all())

    for search_item in active_searches:
        schedule_search_job(search_item)

    if not scheduler.running:
        scheduler.start()
        logger.info("SCHEDULER: Started.")
    else:
        logger.info("SCHEDULER: Already running.")


async def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=True)  # Wait for jobs to complete
        logger.info("SCHEDULER: Shutdown.")

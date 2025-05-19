import asyncio
import uuid
from datetime import datetime, timezone
from typing import List
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import AsyncSessionLocal # Use the session factory directly for background tasks
from models import Search, SearchStatus, Listing
from marktplaats_client import fetch_listings, MockListingItem

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler(timezone="UTC")

async def run_single_search(search_id: uuid.UUID):
    """
    Executes a single search, fetches listings, and stores new ones.
    """
    logger.info(f"SCHEDULER: Running search {search_id} at {datetime.now(timezone.utc)}")
    async with AsyncSessionLocal() as db:
        try:
            # Fetch the search instance, eager load existing listings to check URLs
            result = await db.execute(
                select(Search)
                .options(selectinload(Search.listings))
                .where(Search.id == search_id)
            )
            search_instance = result.scalars().first()

            if not search_instance:
                logger.warning(f"SCHEDULER: Search {search_id} not found. Removing job if exists.")
                if scheduler.get_job(str(search_id)):
                     scheduler.remove_job(str(search_id))
                return

            if search_instance.status != SearchStatus.ACTIVE:
                logger.info(f"SCHEDULER: Search {search_id} is not active ({search_instance.status}). Skipping run.")
                # Job should be removed/paused by API logic that changes status
                return

            new_listings_data: List[MockListingItem] = await fetch_listings(
                query=search_instance.query,
                zip_code=search_instance.zip_code,
                distance=search_instance.distance,
                price_from=search_instance.price_from,
                price_to=search_instance.price_to,
                limit=search_instance.limit,
                sort_by=search_instance.sort_by,
                sort_order=search_instance.sort_order,
            )

            existing_listing_urls = {lst.url for lst in search_instance.listings}
            added_count = 0

            for listing_data in new_listings_data:
                if str(listing_data.url) not in existing_listing_urls: # Compare as strings
                    new_db_listing = Listing(
                        search_id=search_instance.id,
                        source_listing_id=listing_data.source_listing_id,
                        title=listing_data.title,
                        price=listing_data.price,
                        url=str(listing_data.url), # Ensure URL is string
                        description_snippet=listing_data.description_snippet,
                        image_url=str(listing_data.image_url) if listing_data.image_url else None,
                        is_new=True
                    )
                    db.add(new_db_listing)
                    existing_listing_urls.add(str(listing_data.url)) # Add to set to prevent duplicates in same run
                    added_count += 1
            
            search_instance.last_run_at = datetime.now(timezone.utc)
            search_instance.last_error = None
            if added_count > 0:
                logger.info(f"SCHEDULER: Added {added_count} new listings for search {search_id}.")
            
            await db.commit()

        except Exception as e:
            logger.error(f"SCHEDULER: Error running search {search_id}: {e}", exc_info=True)
            await db.rollback()
            # Update search with error status and message in a new session
            async with AsyncSessionLocal() as error_db:
                error_search_instance = await error_db.get(Search, search_id)
                if error_search_instance:
                    error_search_instance.last_run_at = datetime.now(timezone.utc)
                    error_search_instance.last_error = str(e)
                    # Optionally change status to ERROR, or just log and retry next interval
                    # error_search_instance.status = SearchStatus.ERROR 
                    await error_db.commit()
        finally:
            # Session is automatically closed by 'async with'
            pass


def schedule_search_job(search: Search):
    job_id = str(search.id)
    if search.status == SearchStatus.ACTIVE and search.interval > 0:
        job_details = {
            'func': run_single_search,
            'trigger': 'interval',
            'seconds': search.interval,
            'args': [search.id],
            'next_run_time': datetime.now(timezone.utc) # Run immediately then interval
        }
        if scheduler.get_job(job_id):
            # When modifying, job_id is the first arg, other changes in **job_details
            scheduler.modify_job(job_id, **job_details)
            logger.info(f"SCHEDULER: Modified/Rescheduled search {job_id} to run every {search.interval}s")
        else:
            # When adding, id is part of job_details
            scheduler.add_job(id=job_id, **job_details)
            logger.info(f"SCHEDULER: Scheduled search {job_id} to run every {search.interval}s")
    elif scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"SCHEDULER: Removed job for search {job_id} (status: {search.status}, interval: {search.interval}).")


async def initialize_scheduler():
    logger.info("SCHEDULER: Initializing and loading active searches...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Search).where(Search.status == SearchStatus.ACTIVE))
        active_searches: List[Search] = result.scalars().all()
    
    for search_item in active_searches:
        schedule_search_job(search_item)
    
    if not scheduler.running:
        scheduler.start()
        logger.info("SCHEDULER: Started.")
    else:
        logger.info("SCHEDULER: Already running.")

async def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=True) # Wait for jobs to complete
        logger.info("SCHEDULER: Shutdown.")

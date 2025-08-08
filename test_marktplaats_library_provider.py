#!/usr/bin/env python3
"""Simple test script for the MarktplaatsLibraryProvider."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from marktplaats_search.providers import (
    MarktplaatsLibraryProvider,
    MarktplaatsLibraryProviderConfig,
)
from marktplaats_search.providers.base import SearchContext

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_marktplaats_library_provider():
    """Test the MarktplaatsLibraryProvider functionality."""
    logger.info("Testing MarktplaatsLibraryProvider...")

    # Create provider configuration
    config = MarktplaatsLibraryProviderConfig(
        enabled=True,
        priority=50,
        timeout_seconds=30,
        rate_limit_requests_per_minute=20,  # Conservative for testing
    )

    # Create provider instance
    provider = MarktplaatsLibraryProvider(config)

    logger.info(f"Provider created: {provider}")
    logger.info(f"Provider type: {provider.provider_type}")
    logger.info(f"Provider status: {provider.status}")
    logger.info(f"Provider is healthy: {provider.is_healthy}")

    # Test provider info
    provider_info = await provider.get_provider_info()
    logger.info(f"Provider info: {provider_info}")

    # Create search context for testing
    search_context = SearchContext(
        search_id="test_search_1",
        query="gazelle fiets",  # Dutch bicycle brand
        zip_code="1016LV",  # Amsterdam postcode
        distance=50,  # 50km radius
        price_from=50,  # Minimum price 50 euros
        price_to=500,  # Maximum price 500 euros
        limit=5,  # Get 5 results
        sort_by="price",
        sort_order="asc",
    )

    logger.info(f"Search context: {search_context}")

    # Test health check first
    logger.info("Testing health check...")
    health_result = await provider.health_check()
    logger.info(f"Health check result: {health_result}")

    if not health_result:
        logger.error("Health check failed - aborting search test")
        return

    # Test search functionality
    logger.info("Testing search functionality...")
    try:
        result = await provider.search_listings(search_context)

        logger.info(f"Search completed successfully: {result.success}")
        logger.info(f"Execution time: {result.execution_time_ms}ms")
        logger.info(f"Number of listings found: {len(result.listings)}")

        if result.error_message:
            logger.error(f"Search error: {result.error_message}")

        if result.source_metadata:
            logger.info(f"Source metadata: {result.source_metadata}")

        # Display some listing details
        for i, listing in enumerate(result.listings[:3]):  # Show first 3 listings
            logger.info(f"Listing {i+1}:")
            logger.info(f"  ID: {listing.source_listing_id}")
            logger.info(f"  Title: {listing.title}")
            logger.info(f"  Price: {listing.price}")
            logger.info(f"  URL: {listing.url}")
            if listing.description_snippet:
                logger.info(f"  Description: {listing.description_snippet[:100]}...")
            if listing.location:
                logger.info(f"  Location: {listing.location}")
            if listing.date_posted:
                logger.info(f"  Posted: {listing.date_posted}")
            logger.info(f"  Image URL: {listing.image_url}")
            logger.info("")

    except Exception as e:
        logger.error(f"Search failed with exception: {e}")
        import traceback

        traceback.print_exc()

    # Test a second search to verify rate limiting and caching
    logger.info("Testing second search for rate limiting...")
    try:
        search_context_2 = SearchContext(search_id="test_search_2", query="macbook", limit=2)

        result_2 = await provider.search_listings(search_context_2)
        logger.info(f"Second search completed: {result_2.success}")
        logger.info(f"Second search execution time: {result_2.execution_time_ms}ms")
        logger.info(f"Second search listings count: {len(result_2.listings)}")

    except Exception as e:
        logger.error(f"Second search failed: {e}")

    # Final provider status
    final_info = await provider.get_provider_info()
    logger.info(f"Final provider info: {final_info}")

    logger.info("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_marktplaats_library_provider())

#!/usr/bin/env python3
"""Example usage of the MarktplaatsLibraryProvider."""

import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to Python path for direct execution
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.providers import (
    MarktplaatsLibraryProvider,
    MarktplaatsLibraryProviderConfig,
    SearchContext,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def example_usage():
    """Demonstrate MarktplaatsLibraryProvider usage."""

    # Create provider with custom configuration
    config = MarktplaatsLibraryProviderConfig(
        enabled=True,
        priority=100,
        timeout_seconds=30,
        rate_limit_requests_per_minute=30,  # 30 requests per minute
        max_retries=3,
        # Library-specific configuration
        provider_specific_config={
            "default_distance": 1_000_000,  # 1000km search radius
            "max_limit_per_request": 50,  # Max 50 listings per request
        },
    )

    provider = MarktplaatsLibraryProvider(config)

    logger.info(f"Created provider: {provider}")

    # Example 1: Basic search
    search_context = SearchContext(
        search_id="example_search_1",
        query="macbook pro",
        limit=10,
    )

    logger.info("=== Example 1: Basic search ===")
    result = await provider.search_listings(search_context)

    logger.info(f"Search successful: {result.success}")
    logger.info(f"Found {len(result.listings)} listings in {result.execution_time_ms}ms")

    if result.listings:
        first_listing = result.listings[0]
        logger.info(f"First result: {first_listing.title} - {first_listing.price}")

    # Example 2: Location-based search
    search_context_location = SearchContext(
        search_id="example_search_2",
        query="fiets gazelle",
        zip_code="1012AB",  # Amsterdam
        distance=25,  # 25km radius
        price_from=100,
        price_to=300,
        limit=5,
        sort_by="price",
        sort_order="asc",
    )

    logger.info("=== Example 2: Location-based search ===")
    result2 = await provider.search_listings(search_context_location)

    logger.info(f"Location search successful: {result2.success}")
    logger.info(f"Found {len(result2.listings)} listings in {result2.execution_time_ms}ms")

    for i, listing in enumerate(result2.listings[:3]):
        logger.info(
            f"  {i + 1}. {listing.title} - {listing.price} - {listing.location or 'Unknown location'}"
        )

    # Example 3: Health check
    logger.info("=== Example 3: Health check ===")
    is_healthy = await provider.health_check()
    logger.info(f"Provider health: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

    # Example 4: Provider information
    logger.info("=== Example 4: Provider information ===")
    provider_info = await provider.get_provider_info()
    logger.info(f"Provider info: {provider_info}")


if __name__ == "__main__":
    asyncio.run(example_usage())

#!/usr/bin/env python3
"""
Example script demonstrating how to use the HTML scraping provider.

This script shows how to:
1. Configure and initialize the HTML scraping provider
2. Perform searches using the provider
3. Handle errors and monitor metrics
4. Use the provider manager for better abstraction
"""

import asyncio
import logging
import uuid

from marktplaats_search.client import MarktplaatsScrapingError
from marktplaats_search.providers import (
    HtmlScrapingProvider,
    ListingProviderManager,
    ProviderConfig,
    ProviderManagerConfig,
    ProviderType,
    SearchContext,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def example_basic_provider_usage():
    """Example of using the HTML scraping provider directly."""
    logger.info("=== Basic HTML Provider Usage ===")

    # Configure the provider
    config = ProviderConfig(
        provider_type=ProviderType.HTML_SCRAPER,
        enabled=True,
        timeout_seconds=30,
        max_retries=3,
        rate_limit_requests_per_minute=30,
    )

    # Create provider instance
    provider = HtmlScrapingProvider(config)

    try:
        # Create search context
        search_context = SearchContext(
            search_id=str(uuid.uuid4()),
            query="iphone 15",
            zip_code="1012AB",  # Amsterdam
            distance=25,  # 25km radius
            price_from=500,
            price_to=1000,
            limit=10,
            timeout_seconds=30,
        )

        # Check provider health first
        is_healthy = await provider.health_check()
        logger.info(f"Provider health check: {'✓' if is_healthy else '✗'}")

        if is_healthy:
            logger.info(f"Searching with provider: {provider.provider_type.value}")
            result = await provider.search_listings(search_context)

            if result.success:
                logger.info(f"Found {len(result.listings)} listings")

                # Display first few listings
                for i, listing in enumerate(result.listings[:3]):
                    logger.info(
                        f"  {i + 1}. {listing.title} - {listing.price} "
                        f"({listing.source_listing_id})"
                    )

                # Show result metadata
                logger.info(f"Search completed in {result.execution_time_ms}ms")
                if result.source_metadata:
                    logger.info(f"Source metadata: {result.source_metadata}")

            else:
                logger.error(f"Search failed: {result.error_message}")

        else:
            logger.error("Provider is unhealthy, skipping search")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    finally:
        # Cleanup provider resources
        await provider.cleanup()


async def example_provider_manager_usage():
    """Example of using the provider manager with multiple providers."""
    logger.info("\n=== Provider Manager Usage ===")

    # Configure manager
    manager_config = ProviderManagerConfig(
        primary_provider=ProviderType.HTML_SCRAPER,
        fallback_providers=[],  # No fallbacks for this example
        enable_provider_switching=False,
        health_check_interval_seconds=300,  # 5 minutes
        global_timeout_seconds=60,
    )

    # Create manager
    manager = ListingProviderManager(manager_config)

    # Register HTML scraping provider
    html_config = ProviderConfig(
        provider_type=ProviderType.HTML_SCRAPER,
        enabled=True,
        timeout_seconds=30,
        max_retries=2,
        rate_limit_requests_per_minute=40,
    )

    html_provider = HtmlScrapingProvider(html_config)
    manager.register_provider(html_provider)

    try:
        # Use manager as async context manager
        async with manager:
            # Check all providers' health
            health_status = await manager.health_check_all_providers()
            logger.info(f"Provider health status: {health_status}")

            # Create search context
            search_context = SearchContext(
                search_id=str(uuid.uuid4()),
                query="macbook pro",
                zip_code="2000AA",  # Haarlem area
                distance=50,
                price_from=800,
                price_to=2000,
                limit=5,
            )

            # Search using manager (will use primary provider)
            logger.info("Searching using provider manager...")
            result = await manager.search_listings(search_context)

            if result.success:
                logger.info(f"Manager found {len(result.listings)} listings")

                # Display listings with more details
                for i, listing in enumerate(result.listings):
                    logger.info(f"  {i + 1}. {listing.title}")
                    logger.info(f"     Price: {listing.price}")
                    logger.info(f"     Location: {listing.location}")
                    logger.info(f"     URL: {listing.url}")
                    logger.info("")
            else:
                logger.error(f"Manager search failed: {result.error_message}")

            # Show manager metrics
            manager_metrics = manager.get_manager_metrics()
            logger.info("Manager metrics:")
            logger.info(f"  - Total searches: {manager_metrics['total_searches']}")
            logger.info(f"  - Successful: {manager_metrics['successful_searches']}")
            logger.info(f"  - Failed: {manager_metrics['failed_searches']}")
            logger.info(f"  - Success rate: {manager_metrics['success_rate']:.2%}")

            # Show individual provider stats
            for provider_type, stats in manager_metrics["provider_stats"].items():
                logger.info(
                    f"  - {provider_type.value}: {stats['successes']} successes, {stats['errors']} errors"
                )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")


async def example_error_handling():
    """Example of comprehensive error handling with providers."""
    logger.info("\n=== Error Handling Example ===")

    # Create a provider with aggressive settings to trigger errors
    config = ProviderConfig(
        provider_type=ProviderType.HTML_SCRAPER,
        timeout_seconds=5,  # Very short timeout
        max_retries=1,  # Few retries
        rate_limit_requests_per_minute=600,  # Aggressive rate limiting
    )

    provider = HtmlScrapingProvider(config)

    # Test various error scenarios
    error_scenarios = [
        {
            "name": "Invalid search",
            "context": SearchContext(
                search_id=str(uuid.uuid4()),
                query="",  # Empty query
                limit=1,
            ),
        },
        {
            "name": "Normal search (should work)",
            "context": SearchContext(search_id=str(uuid.uuid4()), query="test", limit=1),
        },
    ]

    try:
        for scenario in error_scenarios:
            try:
                logger.info(f"Testing scenario: {scenario['name']}")
                result = await provider.search_listings(scenario["context"])
                if result.success:
                    logger.info(f"  ✓ Success: {len(result.listings)} listings found")
                else:
                    logger.warning(f"  ✗ Provider failed: {result.error_message}")

            except MarktplaatsScrapingError as e:
                logger.warning(f"  ✗ Provider error: {e}")
                logger.warning(f"    Error type: {type(e).__name__}")

            except Exception as e:
                logger.error(f"  ✗ Unexpected error: {e}")

    finally:
        # Cleanup provider resources
        await provider.cleanup()


async def main():
    """Run all examples."""
    logger.info("Starting HTML scraping provider examples...\n")

    try:
        # Run examples
        await example_basic_provider_usage()
        await example_provider_manager_usage()
        await example_error_handling()

    except KeyboardInterrupt:
        logger.info("Examples interrupted by user")
    except Exception as e:
        logger.error(f"Error running examples: {e}")

    logger.info("\nExamples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

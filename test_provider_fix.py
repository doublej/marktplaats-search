#!/usr/bin/env python3
"""Test script to verify provider initialization fix."""

import asyncio
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_provider_initialization():
    """Test that provider manager initializes correctly."""
    from marktplaats_search.scheduler import provider_manager

    print("Testing provider initialization...")

    # Initialize the provider manager
    await provider_manager.initialize()
    print("Provider manager initialized successfully!")

    # Check available providers
    from marktplaats_search.providers.base import SearchContext

    # Create a test search context
    context = SearchContext(query="test", search_id="test-search-123", limit=5)

    # Try to search with the provider manager
    try:
        result = await provider_manager.search_listings(context)
        if result.success:
            provider_value = (
                result.provider_type.value
                if hasattr(result.provider_type, "value")
                else result.provider_type
            )
            print(f"Search successful! Provider used: {provider_value}")
            print(f"Number of listings found: {len(result.listings)}")
        else:
            print(f"Search failed: {result.error_message}")
    except Exception as e:
        import traceback

        print(f"Error during search: {e}")
        traceback.print_exc()

    # Shutdown the provider manager
    await provider_manager.shutdown()
    print("Provider manager shutdown complete.")


if __name__ == "__main__":
    asyncio.run(test_provider_initialization())

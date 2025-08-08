"""Enhanced client with provider abstraction integration.

This module provides an enhanced client interface that uses the provider manager
for reliable listing retrieval with fallback support.
"""

import logging
import uuid
from typing import TYPE_CHECKING, Any

from .client import ListingItem
from .providers import (
    ListingProviderManager,
    ProviderConfig,
    ProviderManagerConfig,
    ProviderType,
    SearchContext,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProviderManager:
    """Singleton provider manager for the application."""

    _instance: ListingProviderManager | None = None
    _initialized: bool = False

    @classmethod
    async def get_instance(
        cls, config: ProviderManagerConfig | None = None
    ) -> ListingProviderManager:
        """Get or create the provider manager instance.

        Args:
            config: Optional configuration for initialization

        Returns:
            ListingProviderManager instance
        """
        if cls._instance is None:
            if config is None:
                config = cls._get_default_config()

            cls._instance = ListingProviderManager(config)

        if not cls._initialized:
            await cls._instance.initialize()
            cls._initialized = True

        return cls._instance

    @classmethod
    def _get_default_config(cls) -> ProviderManagerConfig:
        """Get default provider manager configuration.

        Returns:
            Default ProviderManagerConfig
        """
        # HTML scraper configuration (primary)
        html_scraper_config = ProviderConfig(
            provider_type=ProviderType.HTML_SCRAPER,
            enabled=True,
            priority=50,  # Lower priority = higher preference
            timeout_seconds=30,
            max_retries=2,
            retry_delay_seconds=1.0,
            rate_limit_requests_per_minute=30,
            rate_limit_burst_size=5,
            health_check_interval_seconds=300,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout_seconds=60,
        )

        # Library provider configuration (fallback)
        library_provider_config = ProviderConfig(
            provider_type=ProviderType.MARKTPLAATS_LIBRARY,
            enabled=True,
            priority=100,  # Higher priority number = lower preference
            timeout_seconds=45,
            max_retries=1,
            retry_delay_seconds=2.0,
            rate_limit_requests_per_minute=15,  # More conservative for API
            rate_limit_burst_size=3,
            health_check_interval_seconds=300,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout_seconds=120,
        )

        return ProviderManagerConfig(
            primary_provider=ProviderType.HTML_SCRAPER,
            fallback_providers=[ProviderType.MARKTPLAATS_LIBRARY],
            max_concurrent_requests=3,
            global_timeout_seconds=60,
            enable_provider_switching=True,
            health_check_interval_seconds=300,
            metrics_collection_enabled=True,
            retry_failed_providers=True,
            provider_configs={
                ProviderType.HTML_SCRAPER.value: html_scraper_config,
                ProviderType.MARKTPLAATS_LIBRARY.value: library_provider_config,
            },
        )


async def fetch_listings_with_providers(
    query: str,
    zip_code: str | None = None,
    distance: int | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    limit: int = 10,
    sort_by: str | None = None,
    sort_order: str | None = None,
    preferred_provider: ProviderType | None = None,
    provider_config: ProviderManagerConfig | None = None,
) -> list[ListingItem]:
    """
    Fetch listings using the provider abstraction system with fallback support.

    This function provides enterprise-grade reliability with automatic failover
    between providers, rate limiting, circuit breaker protection, and metrics collection.

    Args:
        query: Search query string
        zip_code: Dutch postal code (e.g., "1012AB")
        distance: Search radius in kilometers
        price_from: Minimum price in euros
        price_to: Maximum price in euros
        limit: Maximum number of listings to return
        sort_by: Sort criteria ("price", "date", "relevance")
        sort_order: Sort order ("asc", "desc")
        preferred_provider: Override default provider selection
        provider_config: Custom provider configuration

    Returns:
        List of ListingItem objects

    Raises:
        Exception: If all providers fail
    """
    logger.info(
        f"Fetching listings with providers: query='{query}', zip='{zip_code}', "
        f"distance={distance}km, price={price_from}-{price_to}, limit={limit}, "
        f"preferred_provider={preferred_provider.value if preferred_provider else 'auto'}"
    )

    # Get provider manager instance
    provider_manager = await ProviderManager.get_instance(provider_config)

    # Create search context
    search_context = SearchContext(
        search_id=str(uuid.uuid4()),
        query=query,
        zip_code=zip_code,
        distance=distance,
        price_from=price_from,
        price_to=price_to,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        timeout_seconds=30,
    )

    # Execute search with provider manager
    result = await provider_manager.search_listings(
        context=search_context,
        preferred_provider=preferred_provider,
    )

    if not result.success:
        logger.error(f"Provider search failed: {result.error_message}")
        raise Exception(f"Failed to fetch listings: {result.error_message}")

    logger.info(
        f"Successfully retrieved {len(result.listings)} listings "
        f"using provider {result.provider_type.value} "
        f"in {result.execution_time_ms}ms"
    )

    return result.listings


async def get_provider_status() -> dict[str, Any]:
    """Get comprehensive status of all providers.

    Returns:
        Dictionary containing provider status and metrics
    """
    try:
        provider_manager = await ProviderManager.get_instance()
        return await provider_manager.get_provider_status()
    except Exception as e:
        logger.error(f"Failed to get provider status: {e}")
        return {
            "error": f"Failed to get provider status: {e}",
            "providers": {},
            "metrics": None,
        }


async def shutdown_providers() -> None:
    """Shutdown all providers and cleanup resources."""
    if ProviderManager._instance and ProviderManager._initialized:
        await ProviderManager._instance.shutdown()
        ProviderManager._instance = None
        ProviderManager._initialized = False
        logger.info("Provider manager shutdown completed")


# Backward compatibility function that uses providers
async def fetch_listings(
    query: str,
    zip_code: str | None = None,
    distance: int | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    limit: int = 10,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> list[ListingItem]:
    """
    Fetch listings with backward compatibility for existing code.

    This function maintains the same signature as the original fetch_listings
    but now uses the provider abstraction system for improved reliability.

    Args:
        query: Search query string
        zip_code: Dutch postal code (e.g., "1012AB")
        distance: Search radius in kilometers
        price_from: Minimum price in euros
        price_to: Maximum price in euros
        limit: Maximum number of listings to return
        sort_by: Sort criteria ("price", "date", "relevance")
        sort_order: Sort order ("asc", "desc")

    Returns:
        List of ListingItem objects

    Raises:
        Exception: If all providers fail
    """
    return await fetch_listings_with_providers(
        query=query,
        zip_code=zip_code,
        distance=distance,
        price_from=price_from,
        price_to=price_to,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

"""DEPRECATED: Enhanced client with provider abstraction integration.

This module is deprecated. All functionality has been moved to:
- marktplaats_search.providers.manager

Please update imports to use the new location.
"""

import warnings

from .client import ListingItem
from .providers import (
    ProviderManager,
    fetch_listings_with_providers,
    get_provider_status,
)

# Issue deprecation warning
warnings.warn(
    "marktplaats_search.provider_client is deprecated. Use marktplaats_search.providers instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export for backward compatibility
__all__ = [
    "ProviderManager",
    "fetch_listings_with_providers",
    "fetch_listings",
    "get_provider_status",
    "shutdown_providers",
]


async def shutdown_providers() -> None:
    """Shutdown all providers and cleanup resources."""
    await ProviderManager.shutdown()


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
    """Backward compatibility function that uses the new provider system."""
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

"""Marktplaats provider abstraction package."""

from .base import (
    MarktplaatsProvider,
    ProviderConfig,
    ProviderResult,
    ProviderStatus,
    ProviderType,
    SearchContext,
)
from .html_scraper import HtmlScrapingProvider
from .manager import ListingProviderManager, ProviderManagerConfig

# Conditional import of marktplaats library provider
try:
    from .marktplaats_library_provider import (
        MarktplaatsLibraryProvider,
        MarktplaatsLibraryProviderConfig,
    )

    _MARKTPLAATS_LIBRARY_AVAILABLE = True
except ImportError:
    MarktplaatsLibraryProvider = None
    MarktplaatsLibraryProviderConfig = None
    _MARKTPLAATS_LIBRARY_AVAILABLE = False

__all__ = [
    # Base classes and interfaces
    "MarktplaatsProvider",
    "ProviderConfig",
    "ProviderResult",
    "ProviderType",
    "ProviderStatus",
    "SearchContext",
    # Concrete providers
    "HtmlScrapingProvider",
]

# Conditionally add library provider to exports
if _MARKTPLAATS_LIBRARY_AVAILABLE:
    __all__.extend(["MarktplaatsLibraryProvider", "MarktplaatsLibraryProviderConfig"])

__all__.extend(
    [
        # Provider management
        "ListingProviderManager",
        "ProviderManagerConfig",
    ]
)

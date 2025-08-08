"""HTML scraper provider implementation that wraps the existing client.py functionality."""

from ..client import fetch_listings
from .base import MarktplaatsProvider, ProviderConfig, ProviderResult, ProviderType, SearchContext


class HtmlScrapingProvider(MarktplaatsProvider):
    """Provider that uses the existing HTML scraper from client.py."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)

    async def search_listings(self, context: SearchContext) -> ProviderResult:
        """Execute search using HTML scraping via the existing client.py implementation."""
        try:
            # Use the existing fetch_listings function
            listings = await fetch_listings(
                query=context.query,
                zip_code=context.zip_code,
                distance=context.distance,
                price_from=context.price_from,
                price_to=context.price_to,
                limit=context.limit,
                sort_by=context.sort_by,
                sort_order=context.sort_order,
            )

            return ProviderResult(
                listings=listings,
                provider_type=ProviderType.HTML_SCRAPER,
                success=True,
                execution_time_ms=None,  # Will be set by manager
                source_metadata={
                    "source": "html_scraper",
                    "query": context.query,
                    "limit": context.limit,
                },
            )

        except Exception as e:
            return ProviderResult(
                listings=[],
                provider_type=ProviderType.HTML_SCRAPER,
                success=False,
                error_message=str(e),
                execution_time_ms=None,
            )

    async def health_check(self) -> bool:
        """Simple health check - always return True since we use the existing client."""
        return True

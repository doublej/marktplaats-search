"""Marktplaats library-based provider for listing searches."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from marktplaats import SearchQuery
from marktplaats.models import Listing as MarktplaatsListing
from marktplaats.query import BadStatusCodeError, JSONDecodeError

from .base import (
    MarktplaatsProvider,
    ProviderConfig,
    ProviderResult,
    ProviderType,
    SearchContext,
)
from .data_mappers import MarktplaatsLibraryDataMapper

logger = logging.getLogger(__name__)


class MarktplaatsLibraryProviderConfig(ProviderConfig):
    """Configuration for the Marktplaats library provider."""

    def __init__(self, **kwargs: Any) -> None:
        # Set provider type and defaults
        kwargs.setdefault("provider_type", ProviderType.MARKTPLAATS_LIBRARY)
        kwargs.setdefault("rate_limit_requests_per_minute", 30)  # Conservative for API usage
        kwargs.setdefault("timeout_seconds", 30)

        # Library-specific settings in provider_specific_config
        provider_specific_config = kwargs.setdefault("provider_specific_config", {})
        provider_specific_config.setdefault("default_distance", 1_000_000)  # 1000km in meters
        provider_specific_config.setdefault("max_limit_per_request", 100)

        super().__init__(**kwargs)


class MarktplaatsLibraryProvider(MarktplaatsProvider):
    """Provider using the official marktplaats Python library."""

    def __init__(self, config: MarktplaatsLibraryProviderConfig | None = None):
        if config is None:
            config = MarktplaatsLibraryProviderConfig()
        super().__init__(config)
        self.config: MarktplaatsLibraryProviderConfig = config

    async def search_listings(self, context: SearchContext) -> ProviderResult:
        """
        Search for listings using the marktplaats library.

        Args:
            context: Search context containing query parameters and metadata

        Returns:
            ProviderResult containing listings and metadata
        """
        start_time = datetime.now()

        async def _search_operation() -> ProviderResult:
            self.logger.info(
                f"Starting search with marktplaats library: query='{context.query}', "
                f"zip_code='{context.zip_code}', distance={context.distance}km, "
                f"price={context.price_from}-{context.price_to}, limit={context.limit}"
            )

            # Apply rate limiting - simple delay for now
            await asyncio.sleep(60.0 / self.config.rate_limit_requests_per_minute)

            # Convert parameters to library format
            library_params = MarktplaatsLibraryDataMapper.convert_search_params(
                context, self.config.provider_specific_config
            )

            # Execute search using the library
            # Note: The library performs synchronous requests, so we run it in a thread
            listings = await asyncio.to_thread(self._execute_library_search, library_params)

            # Convert library listings to our ListingItem format
            converted_listings = []
            for library_listing in listings:
                try:
                    listing_item = MarktplaatsLibraryDataMapper.convert_listing_to_listing_item(
                        library_listing
                    )
                    if listing_item:
                        converted_listings.append(listing_item)
                except Exception as e:
                    self.logger.warning(f"Failed to convert listing {library_listing.id}: {e}")
                    continue

            # Calculate execution time
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            self.logger.info(
                f"Successfully retrieved {len(converted_listings)} listings "
                f"from marktplaats library in {execution_time_ms}ms"
            )

            return ProviderResult(
                listings=converted_listings,
                provider_type=self.provider_type,
                success=True,
                error_message=None,
                execution_time_ms=execution_time_ms,
                source_metadata={
                    "library_params": library_params,
                    "raw_count": len(listings),
                    "converted_count": len(converted_listings),
                },
            )

        # Use circuit breaker protection
        try:
            return await self._execute_with_circuit_breaker("search_listings", _search_operation)
        except BadStatusCodeError as e:
            error_msg = f"Bad status code from Marktplaats API: {e}"
            self.logger.error(error_msg)
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProviderResult(
                listings=[],
                provider_type=self.provider_type,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
            )
        except JSONDecodeError as e:
            error_msg = f"Failed to decode JSON response from Marktplaats API: {e}"
            self.logger.error(error_msg)
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProviderResult(
                listings=[],
                provider_type=self.provider_type,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            error_msg = f"Unexpected error during Marktplaats library search: {e}"
            self.logger.error(error_msg)
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

            return ProviderResult(
                listings=[],
                provider_type=self.provider_type,
                success=False,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
            )

    def _execute_library_search(self, params: dict[str, Any]) -> list[MarktplaatsListing]:
        """Execute the actual search using the marktplaats library."""
        search = SearchQuery(**params)
        return search.get_listings()

    async def health_check(self) -> bool:
        """
        Perform a health check for the Marktplaats library provider.

        Returns:
            True if the provider is healthy, False otherwise
        """
        try:
            # Perform a minimal search to test connectivity
            test_context = SearchContext(
                search_id="health_check",
                query="test",
                limit=1,
            )

            # Use a shorter timeout for health checks
            start_time = datetime.now()

            # Execute a simple search
            result = await self.search_listings(test_context)

            response_time = (datetime.now() - start_time).total_seconds()

            # Consider healthy if we can get a response within reasonable time and it was successful
            is_healthy = result.success and response_time < 10.0  # 10 second threshold

            self.logger.info(
                f"Health check {'passed' if is_healthy else 'failed'}: "
                f"response_time={response_time:.2f}s, success={result.success}, "
                f"listings_count={len(result.listings)}"
            )

            self._last_health_check = datetime.now()
            return is_healthy

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            self._last_health_check = datetime.now()
            return False

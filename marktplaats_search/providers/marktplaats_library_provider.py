"""Marktplaats library-based provider for listing searches."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from marktplaats import SearchQuery, SortBy, SortOrder
from marktplaats.models import Listing as MarktplaatsListing
from marktplaats.query import BadStatusCodeError, JSONDecodeError
from pydantic import HttpUrl, ValidationError

from ..client import ListingItem
from .base import (
    MarktplaatsProvider,
    ProviderConfig,
    ProviderResult,
    ProviderType,
    SearchContext,
)

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
            library_params = self._convert_search_params(context)

            # Execute search using the library
            # Note: The library performs synchronous requests, so we run it in a thread
            listings = await asyncio.to_thread(self._execute_library_search, library_params)

            # Convert library listings to our ListingItem format
            converted_listings = []
            for library_listing in listings:
                try:
                    listing_item = self._convert_library_listing_to_listing_item(library_listing)
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

    def _convert_search_params(self, context: SearchContext) -> dict:
        """Convert SearchContext parameters to marktplaats library format."""
        provider_config = self.config.provider_specific_config

        params = {
            "query": context.query or "",
            "limit": min(context.limit, provider_config.get("max_limit_per_request", 100)),
        }

        # Add location parameters
        if context.zip_code:
            params["zip_code"] = context.zip_code

        if context.distance:
            # Convert km to meters for the library
            params["distance"] = context.distance * 1000
        else:
            params["distance"] = provider_config.get("default_distance", 1_000_000)

        # Add price filters
        if context.price_from is not None:
            params["price_from"] = context.price_from
        if context.price_to is not None:
            params["price_to"] = context.price_to

        # Convert sorting parameters
        if context.sort_by:
            sort_by_mapping = {
                "price": SortBy.PRICE,
                "date": SortBy.DATE,
                "location": SortBy.LOCATION,
                "relevance": SortBy.OPTIMIZED,
            }
            params["sort_by"] = sort_by_mapping.get(context.sort_by, SortBy.OPTIMIZED)

        if context.sort_order:
            sort_order_mapping = {
                "asc": SortOrder.ASC,
                "desc": SortOrder.DESC,
            }
            params["sort_order"] = sort_order_mapping.get(context.sort_order, SortOrder.DESC)

        return params

    def _execute_library_search(self, params: dict) -> list[MarktplaatsListing]:
        """Execute the actual search using the marktplaats library."""
        search = SearchQuery(**params)
        return search.get_listings()

    def _convert_library_listing_to_listing_item(
        self, library_listing: MarktplaatsListing
    ) -> ListingItem | None:
        """
        Convert a marktplaats library Listing to our ListingItem format.

        Args:
            library_listing: Listing object from the marktplaats library

        Returns:
            ListingItem object or None if conversion fails
        """
        try:
            # Extract and validate URL
            url_str = library_listing.link
            if not url_str:
                self.logger.warning(f"Listing {library_listing.id} has no URL")
                return None

            # Ensure URL is absolute
            if url_str.startswith("/"):
                url_str = f"https://www.marktplaats.nl{url_str}"
            elif not url_str.startswith("http"):
                url_str = f"https://www.marktplaats.nl/{url_str}"

            try:
                url = HttpUrl(url_str)
            except ValidationError:
                self.logger.warning(f"Invalid URL for listing {library_listing.id}: {url_str}")
                return None

            # Extract price information
            price_str = "Price on request"
            price_numeric = None

            if library_listing.price is not None and library_listing.price > 0:
                price_numeric = int(library_listing.price * 100)  # Convert to cents
                if library_listing.price_type:
                    price_str = library_listing.price_as_string(euro_sign=True, lang="nl")
                else:
                    price_str = f"€ {library_listing.price:.2f}"

            # Extract image URL
            image_url = None
            if library_listing.first_image:
                try:
                    # Try different image sizes, preferring larger ones
                    img_urls = [
                        library_listing.first_image.large,
                        library_listing.first_image.medium,
                        library_listing.first_image.extra_large,
                        library_listing.first_image.extra_small,
                    ]
                    
                    for img_url_str in img_urls:
                        if img_url_str and img_url_str.strip():
                            try:
                                image_url = HttpUrl(img_url_str)
                                break
                            except ValidationError:
                                continue
                                
                except (AttributeError, ValidationError):
                    self.logger.debug(f"Failed to extract image URL for listing {library_listing.id}")
                    image_url = None

            # Handle date conversion
            date_posted = None
            if library_listing.date:
                try:
                    # Convert date to datetime for consistency with existing code
                    date_posted = datetime.combine(
                        library_listing.date, datetime.min.time().replace(hour=12)
                    )
                except (ValueError, TypeError):
                    self.logger.debug(f"Invalid date for listing {library_listing.id}")
                    date_posted = None

            # Create ListingItem with both legacy and new fields populated
            listing_item = ListingItem(
                # Core fields
                source_listing_id=library_listing.id,
                title=library_listing.title or "No title",
                price=price_str,
                price_numeric=price_numeric,
                url=url,
                description_snippet=library_listing.description[:500]
                if library_listing.description
                else None,
                image_url=image_url,
                raw_html=None,  # Not available from library
                # Location data
                location=(
                    library_listing.location.city
                    if library_listing.location and library_listing.location.city
                    else None
                ),
                # Seller data
                seller=(
                    library_listing.seller.name
                    if library_listing.seller and library_listing.seller.name
                    else None
                ),
                # Other metadata
                views=None,  # Not available from library
                condition=None,  # Would need to be extracted from attributes
                date_posted=date_posted,
            )

            return listing_item

        except Exception as e:
            self.logger.error(f"Failed to convert library listing {library_listing.id}: {e}")
            return None

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

"""Marktplaats library provider for listing retrieval.

This provider uses the marktplaats>=0.3.1 Python library to fetch listings
through the official API, providing a more reliable data source.
"""

import contextlib
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import HttpUrl, ValidationError

from ..client import ListingItem
from ..models import PriceTypeEnum
from .base import MarktplaatsProvider, ProviderConfig, ProviderResult, ProviderType, SearchContext

logger = logging.getLogger(__name__)

# Import marktplaats library with proper error handling
try:
    from marktplaats import Condition, SearchQuery, SortBy, SortOrder

    MARKTPLAATS_LIBRARY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Marktplaats library not available: {e}")
    MARKTPLAATS_LIBRARY_AVAILABLE = False

    if TYPE_CHECKING:
        from marktplaats import Condition, SearchQuery, SortBy, SortOrder
    else:
        SearchQuery = None  # type: ignore
        SortBy = None  # type: ignore
        SortOrder = None  # type: ignore
        Condition = None  # type: ignore


class MarktplaatsLibraryProvider(MarktplaatsProvider):
    """Provider implementation using the marktplaats Python library."""

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the marktplaats library provider.

        Args:
            config: Provider configuration

        Raises:
            ImportError: If marktplaats library is not available
        """
        if not MARKTPLAATS_LIBRARY_AVAILABLE:
            raise ImportError(
                "marktplaats library is required for MarktplaatsLibraryProvider. "
                "Install with: uv add marktplaats>=0.3.1"
            )

        super().__init__(config)
        self._last_request_time: datetime | None = None

    async def search_listings(self, context: SearchContext) -> ProviderResult:
        """Search for listings using the marktplaats library.

        Args:
            context: Search parameters and context information

        Returns:
            ProviderResult containing library-retrieved listings and metadata

        Raises:
            Exception: If library search fails
        """
        start_time = datetime.now()

        try:
            return await self._execute_with_circuit_breaker(
                "library_search", lambda: self._perform_search(context, start_time)
            )
        except (ValueError, AttributeError, ImportError, httpx.HTTPError) as e:
            self.logger.error(f"Marktplaats library search failed for query '{context.query}': {e}")
            return ProviderResult(
                listings=[],
                provider_type=ProviderType.MARKTPLAATS_LIBRARY,
                success=False,
                error_message=str(e),
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

    async def _perform_search(self, context: SearchContext, start_time: datetime) -> ProviderResult:
        """Perform the actual library-based search.

        Args:
            context: Search context
            start_time: When the search started

        Returns:
            ProviderResult with library data
        """
        # Apply rate limiting
        await self._apply_rate_limiting()

        # Build search query using marktplaats library
        search_query = self._build_search_query(context)

        self.logger.debug(f"Marktplaats library executing search: {search_query}")

        # Execute search using the library
        # Note: The marktplaats library's get_listings() is synchronous
        import asyncio

        raw_listings = await asyncio.get_event_loop().run_in_executor(
            None, search_query.get_listings
        )

        self._last_request_time = datetime.now()

        # Convert library listings to our ListingItem format
        converted_listings = self._convert_listings(raw_listings, context)

        execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        self.logger.info(
            f"Marktplaats library found {len(converted_listings)} listings "
            f"for query '{context.query}' in {execution_time_ms}ms"
        )

        return ProviderResult(
            listings=converted_listings,
            provider_type=ProviderType.MARKTPLAATS_LIBRARY,
            success=True,
            execution_time_ms=execution_time_ms,
            source_metadata={
                "library_version": self._get_library_version(),
                "search_parameters": self._extract_search_params(search_query),
                "data_source": "marktplaats_api",
                "total_found": len(raw_listings),
            },
        )

    async def health_check(self) -> bool:
        """Perform health check by testing library functionality.

        Returns:
            True if provider is healthy, False otherwise
        """
        try:
            # Create a minimal search query to test library functionality
            test_query = SearchQuery(
                query="test",
                limit=1,
                zip_code="1012AB",  # Amsterdam center
                distance=10000,  # 10km
            )

            # Test the library with a very quick search
            import asyncio

            await asyncio.get_event_loop().run_in_executor(None, test_query.get_listings)

            # If we get here without exception, the library is working
            self._last_health_check = datetime.now()
            return True

        except Exception as e:
            self.logger.debug(f"Marktplaats library health check failed: {e}")
            return False

    def _build_search_query(self, context: SearchContext) -> "SearchQuery":
        """Build a SearchQuery object from search context.

        Args:
            context: Search parameters

        Returns:
            Configured SearchQuery object
        """
        # Base parameters
        query_params: dict[str, Any] = {
            "limit": min(context.limit or 25, 100),  # Library max is 100
        }

        # Add query if provided
        if context.query:
            query_params["query"] = context.query

        # Add location parameters
        if context.zip_code:
            query_params["zip_code"] = context.zip_code
        if context.distance:
            query_params["distance"] = context.distance * 1000  # Convert km to meters

        # Add price range
        if context.price_from is not None:
            query_params["price_from"] = context.price_from
        if context.price_to is not None:
            query_params["price_to"] = context.price_to

        # Map sort parameters
        if context.sort_by:
            sort_by = self._map_sort_by(context.sort_by)
            if sort_by:
                query_params["sort_by"] = sort_by

        if context.sort_order:
            sort_order = self._map_sort_order(context.sort_order)
            if sort_order:
                query_params["sort_order"] = sort_order

        # Add provider-specific configuration
        provider_config = self.config.provider_specific_config
        if "condition" in provider_config:
            condition = self._map_condition(provider_config["condition"])
            if condition:
                query_params["condition"] = condition

        if "category" in provider_config:
            query_params["category"] = provider_config["category"]

        return SearchQuery(**query_params)

    def _convert_listings(
        self, raw_listings: list[Any], context: SearchContext
    ) -> list[ListingItem]:
        """Convert marktplaats library listings to ListingItem format.

        Args:
            raw_listings: Raw listings from marktplaats library
            context: Search context for reference

        Returns:
            List of converted ListingItem objects
        """
        converted_listings = []

        for raw_listing in raw_listings:
            try:
                converted_listing = self._convert_single_listing(raw_listing)
                if converted_listing:
                    converted_listings.append(converted_listing)
            except Exception as e:
                self.logger.warning(f"Failed to convert listing: {e}")
                continue

        return converted_listings

    def _convert_single_listing(self, raw_listing: Any) -> ListingItem | None:
        """Convert a single raw listing to ListingItem format.

        Args:
            raw_listing: Raw listing from marktplaats library

        Returns:
            Converted ListingItem or None if conversion fails
        """
        try:
            # Extract basic information
            listing_id = getattr(raw_listing, "id", None)
            title = getattr(raw_listing, "title", "Unknown Title")
            description = getattr(raw_listing, "description", None)

            # Handle price and price type
            price_obj = getattr(raw_listing, "price", None)
            price_str = "Price on request"
            price_numeric = None

            if price_obj:
                if hasattr(price_obj, "price_type"):
                    # Price type mapping available but not used in current ListingItem
                    pass

                if hasattr(price_obj, "amount") and price_obj.amount is not None:
                    price_numeric = int(float(price_obj.amount) * 100)  # Convert to cents
                    price_str = f"€ {price_obj.amount:.2f}"
                elif hasattr(price_obj, "price_type_text"):
                    price_str = price_obj.price_type_text

            # Extract URL
            url_str = getattr(raw_listing, "link", "")
            try:
                url = HttpUrl(url_str)
            except ValidationError:
                self.logger.warning(f"Invalid URL for listing {listing_id}: {url_str}")
                return None

            # Extract location information
            location_obj = getattr(raw_listing, "location", None)
            location_city = None

            if location_obj:
                location_city = getattr(location_obj, "city", None)
                # Additional location data available: distance, latitude, longitude
                # but not used in current ListingItem structure

            # Extract seller information
            seller_obj = getattr(raw_listing, "seller", None)
            seller_name = None

            if seller_obj:
                # Seller ID and verification status available but not used
                seller_name = getattr(seller_obj, "name", None)

            # Extract images
            image_url = None

            if hasattr(raw_listing, "first_image") and raw_listing.first_image:
                with contextlib.suppress(ValidationError):
                    image_url = HttpUrl(raw_listing.first_image)

            # Additional image sizes available but not used in current ListingItem
            if hasattr(raw_listing, "images") and raw_listing.images:
                # Multiple image sizes and data available for future enhancement
                pass

            # Category information available but not used in current ListingItem
            if hasattr(raw_listing, "category") and raw_listing.category:
                # Category ID available for future enhancement
                pass

            # Extract date posted
            date_posted = None
            if hasattr(raw_listing, "date") and raw_listing.date:
                date_posted = raw_listing.date

            # Create ListingItem with comprehensive mapping to database fields
            return ListingItem(
                # Core fields
                source_listing_id=str(listing_id) if listing_id else f"lib_{hash(url_str)}",
                title=title,
                price=price_str,
                price_numeric=price_numeric,
                url=url,
                description_snippet=description,
                image_url=image_url,
                raw_html=None,  # Not available from library
                # Additional metadata from existing model
                location=location_city,
                seller=seller_name,
                views=None,  # Not available from library
                condition=None,  # Would need mapping from attributes
                date_posted=date_posted,
            )

        except Exception as e:
            self.logger.error(f"Error converting listing: {e}")
            return None

    def _map_sort_by(self, sort_by: str) -> "SortBy | None":
        """Map sort_by parameter to library SortBy enum.

        Args:
            sort_by: Sort criteria string

        Returns:
            Mapped SortBy enum value or None
        """
        mapping = {
            "date": SortBy.DATE,
            "price": SortBy.PRICE,
            "location": SortBy.LOCATION,
            "optimized": SortBy.OPTIMIZED,
            "relevance": SortBy.OPTIMIZED,  # Default to optimized for relevance
        }
        return mapping.get(sort_by.lower())

    def _map_sort_order(self, sort_order: str) -> "SortOrder | None":
        """Map sort_order parameter to library SortOrder enum.

        Args:
            sort_order: Sort order string

        Returns:
            Mapped SortOrder enum value or None
        """
        mapping = {
            "asc": SortOrder.ASC,
            "desc": SortOrder.DESC,
        }
        return mapping.get(sort_order.lower())

    def _map_condition(self, condition: str) -> "Condition | None":
        """Map condition parameter to library Condition enum.

        Args:
            condition: Condition string

        Returns:
            Mapped Condition enum value or None
        """
        mapping = {
            "new": Condition.NEW,
            "used": Condition.USED,
        }
        return mapping.get(condition.lower())

    def _map_price_type(self, price_type: str) -> PriceTypeEnum | None:
        """Map library price type to our PriceTypeEnum.

        Args:
            price_type: Price type from library

        Returns:
            Mapped PriceTypeEnum value or None
        """
        # This would need to be updated based on actual library price types
        mapping = {
            "FIXED": PriceTypeEnum.FIXED,
            "FREE": PriceTypeEnum.FREE,
            "FAST_BID": PriceTypeEnum.BID,
            "RESERVED": PriceTypeEnum.RESERVED,
            "SEE_DESCRIPTION": PriceTypeEnum.SEE_DESCRIPTION,
            "NOTK": PriceTypeEnum.TO_BE_AGREED_UPON,
            "ON_REQUEST": PriceTypeEnum.ON_REQUEST,
            "EXCHANGE": PriceTypeEnum.EXCHANGE,
            "MIN_BID": PriceTypeEnum.BID_FROM,
        }
        return mapping.get(price_type, PriceTypeEnum.UNKNOWN)

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting between requests."""
        if self._last_request_time:
            time_since_last = (datetime.now() - self._last_request_time).total_seconds()
            min_interval = 60.0 / self.config.rate_limit_requests_per_minute

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                import asyncio

                await asyncio.sleep(sleep_time)

    def _get_library_version(self) -> str:
        """Get the version of the marktplaats library.

        Returns:
            Library version string
        """
        try:
            import marktplaats

            return getattr(marktplaats, "__version__", "unknown")
        except Exception:
            return "unknown"

    def _extract_search_params(self, search_query: "SearchQuery") -> dict[str, Any]:
        """Extract search parameters from SearchQuery for metadata.

        Args:
            search_query: The SearchQuery object used

        Returns:
            Dictionary of search parameters
        """
        params = {}

        # Extract common parameters
        for attr in ["query", "zip_code", "distance", "price_from", "price_to", "limit"]:
            if hasattr(search_query, attr):
                value = getattr(search_query, attr)
                if value is not None:
                    params[attr] = value

        return params

    async def get_provider_info(self) -> dict[str, Any]:
        """Get marktplaats library provider information.

        Returns:
            Dictionary containing provider metadata
        """
        base_info = await super().get_provider_info()

        # Add library-specific information
        library_info = {
            "library_available": MARKTPLAATS_LIBRARY_AVAILABLE,
            "library_version": self._get_library_version(),
            "data_source": "marktplaats_api",
            "supports_parameters": [
                "query",
                "zip_code",
                "distance",
                "price_from",
                "price_to",
                "sort_by",
                "sort_order",
                "condition",
                "category",
            ],
            "max_limit": 100,
            "requires_session": False,
            "last_request_time": self._last_request_time.isoformat()
            if self._last_request_time
            else None,
        }

        base_info.update(library_info)
        return base_info

    def __repr__(self) -> str:
        """Return string representation of the library provider."""
        return (
            f"MarktplaatsLibraryProvider("
            f"status={self.status.value}, "
            f"library_available={MARKTPLAATS_LIBRARY_AVAILABLE}, "
            f"priority={self.config.priority})"
        )

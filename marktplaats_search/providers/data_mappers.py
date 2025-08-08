"""Data mapping utilities for converting between different data formats in providers."""

import logging
from datetime import datetime
from typing import Any

from marktplaats import SortBy, SortOrder
from marktplaats.models import Listing as MarktplaatsListing
from pydantic import HttpUrl, ValidationError

from ..client import ListingItem
from ..models import PriceTypeEnum

logger = logging.getLogger(__name__)


class MarktplaatsLibraryDataMapper:
    """Maps data between marktplaats library objects and application models."""

    @staticmethod
    def convert_listing_to_listing_item(
        library_listing: MarktplaatsListing,
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
                logger.warning(f"Listing {library_listing.id} has no URL")
                return None

            # Ensure URL is absolute
            if url_str.startswith("/"):
                url_str = f"https://www.marktplaats.nl{url_str}"
            elif not url_str.startswith("http"):
                url_str = f"https://www.marktplaats.nl/{url_str}"

            try:
                url = HttpUrl(url_str)
            except ValidationError:
                logger.warning(f"Invalid URL for listing {library_listing.id}: {url_str}")
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
                    logger.debug(f"Failed to extract image URL for listing {library_listing.id}")
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
                    logger.debug(f"Invalid date for listing {library_listing.id}")
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
            logger.error(f"Failed to convert library listing {library_listing.id}: {e}")
            return None

    @staticmethod
    def create_database_listing_data(
        library_listing: MarktplaatsListing,
        search_id: str,
    ) -> dict[str, Any] | None:
        """
        Convert a marktplaats library Listing to database Listing model format.

        Args:
            library_listing: Listing object from the marktplaats library
            search_id: ID of the search this listing belongs to

        Returns:
            Dictionary with fields for the database Listing model, or None if conversion fails
        """
        try:
            # Basic ListingItem conversion first
            listing_item = MarktplaatsLibraryDataMapper.convert_listing_to_listing_item(
                library_listing
            )
            if not listing_item:
                return None

            # Map price type
            price_type = None
            if library_listing.price_type:
                # Try to map library price type to our enum
                price_type_mapping = {
                    "FREE": PriceTypeEnum.FREE,
                    "FAST_BID": PriceTypeEnum.BID,
                    "RESERVED": PriceTypeEnum.RESERVED,
                    "SEE_DESCRIPTION": PriceTypeEnum.SEE_DESCRIPTION,
                    "NOTK": PriceTypeEnum.TO_BE_AGREED_UPON,
                    "ON_REQUEST": PriceTypeEnum.ON_REQUEST,
                    "EXCHANGE": PriceTypeEnum.EXCHANGE,
                    "FIXED": PriceTypeEnum.FIXED,
                    "MIN_BID": PriceTypeEnum.BID_FROM,
                }
                price_type = price_type_mapping.get(
                    str(library_listing.price_type), PriceTypeEnum.UNKNOWN
                )

            # Collect all available images
            images_data = []
            if library_listing.first_image:
                images_data.append(
                    {
                        "extra_small": library_listing.first_image.extra_small,
                        "medium": library_listing.first_image.medium,
                        "large": library_listing.first_image.large,
                        "extra_large": library_listing.first_image.extra_large,
                    }
                )

            # Create database model data
            database_data = {
                # Core fields from marktplaats library
                "marktplaats_id": library_listing.id,
                "title": library_listing.title or "No title",
                "description": library_listing.description,
                "price": float(library_listing.price) if library_listing.price else None,
                "price_type": price_type,
                "url": str(listing_item.url),
                "date_posted": library_listing.date,
                # Legacy fields for backward compatibility
                "source_listing_id": library_listing.id,
                "price_numeric": listing_item.price_numeric,
                "description_snippet": library_listing.description[:500]
                if library_listing.description
                else None,
                "image_url": str(listing_item.image_url) if listing_item.image_url else None,
                # Location data
                "location_city": library_listing.location.city
                if library_listing.location
                else None,
                "location_country": library_listing.location.country
                if library_listing.location
                else None,
                "location_country_short": library_listing.location.country_short
                if library_listing.location
                else None,
                "location_latitude": library_listing.location.latitude
                if library_listing.location
                else None,
                "location_longitude": library_listing.location.longitude
                if library_listing.location
                else None,
                "location_distance": library_listing.location.distance
                if library_listing.location
                else None,
                # Seller data
                "seller_id": library_listing.seller.id if library_listing.seller else None,
                "seller_name": library_listing.seller.name if library_listing.seller else None,
                "seller_is_verified": library_listing.seller.is_verified
                if library_listing.seller
                else None,
                # Category and attributes
                "category_id": library_listing.category_id,
                "attributes": [
                    {"name": attr.name, "value": attr.value}
                    for attr in (library_listing.attributes or [])
                ]
                if library_listing.attributes
                else None,
                "extended_attributes": [
                    {"name": attr.name, "value": attr.value}
                    for attr in (library_listing.extended_attributes or [])
                ]
                if library_listing.extended_attributes
                else None,
                # Image data
                "image_extra_small": library_listing.first_image.extra_small
                if library_listing.first_image
                else None,
                "image_medium": library_listing.first_image.medium
                if library_listing.first_image
                else None,
                "image_large": library_listing.first_image.large
                if library_listing.first_image
                else None,
                "image_extra_large": library_listing.first_image.extra_large
                if library_listing.first_image
                else None,
                "images": images_data if images_data else None,
                # Legacy fields maintained for compatibility
                "condition": None,  # Could be extracted from attributes
                "views": None,  # Not available from library
                "location": library_listing.location.city if library_listing.location else None,
                "seller": library_listing.seller.name if library_listing.seller else None,
                # Metadata
                "raw_data": {
                    "id": library_listing.id,
                    "title": library_listing.title,
                    "description": library_listing.description,
                    "price": library_listing.price,
                    "price_type": str(library_listing.price_type)
                    if library_listing.price_type
                    else None,
                    "category_id": library_listing.category_id,
                    "date": library_listing.date.isoformat() if library_listing.date else None,
                    "link": library_listing.link,
                },
                "raw_html": None,  # Not available from library
                "is_new": True,
                # Search relationship
                "search_id": search_id,
                "discovered_at": datetime.now(),
            }

            return database_data

        except Exception as e:
            logger.error(f"Failed to create database data for listing {library_listing.id}: {e}")
            return None

    @staticmethod
    def convert_search_params(
        search_context, provider_config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Convert SearchContext parameters to marktplaats library format.

        Args:
            search_context: SearchContext object with search parameters
            provider_config: Optional provider-specific configuration

        Returns:
            Dictionary of parameters for SearchQuery
        """
        config = provider_config or {}

        params = {
            "query": search_context.query or "",
            "limit": min(search_context.limit, config.get("max_limit_per_request", 100)),
        }

        # Add location parameters
        if search_context.zip_code:
            params["zip_code"] = search_context.zip_code

        if search_context.distance:
            # Convert km to meters for the library
            params["distance"] = search_context.distance * 1000
        else:
            # Use default distance from config
            params["distance"] = config.get("default_distance", 1_000_000)

        # Add price filters
        if search_context.price_from is not None:
            params["price_from"] = search_context.price_from
        if search_context.price_to is not None:
            params["price_to"] = search_context.price_to

        # Convert sorting parameters
        if search_context.sort_by:
            sort_by_mapping = {
                "price": SortBy.PRICE,
                "date": SortBy.DATE,
                "location": SortBy.LOCATION,
                "relevance": SortBy.OPTIMIZED,
            }
            params["sort_by"] = sort_by_mapping.get(search_context.sort_by, SortBy.OPTIMIZED)

        if search_context.sort_order:
            sort_order_mapping = {
                "asc": SortOrder.ASC,
                "desc": SortOrder.DESC,
            }
            params["sort_order"] = sort_order_mapping.get(search_context.sort_order, SortOrder.DESC)

        return params

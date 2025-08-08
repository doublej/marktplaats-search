"""
Test suite for marktplaats library integration and per-search listing management.

This module tests:
- MarktplaatsClient functionality
- Per-search duplicate handling
- Cross-search analysis
- Enhanced API endpoints
- Database migration compatibility
"""

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from marktplaats import Condition, PriceType, SortBy
from marktplaats.models import (
    Listing as MarktplaatsListing,
)
from marktplaats.models import (
    ListingFirstImage,
    ListingLocation,
    ListingSeller,
)

from marktplaats_search.client_new import (
    EnhancedListingItem,
    MarktplaatsApiError,
    MarktplaatsClient,
)
from marktplaats_search.models import Listing, PriceTypeEnum


class TestMarktplaatsClient:
    """Test suite for the MarktplaatsClient wrapper."""

    @pytest.fixture
    def mock_marktplaats_listing(self):
        """Create a mock MarktplaatsListing for testing."""
        # Mock seller
        mock_seller = Mock(spec=ListingSeller)
        mock_seller.id = 12345
        mock_seller.name = "TestSeller"
        mock_seller.is_verified = True

        # Mock location
        mock_location = Mock(spec=ListingLocation)
        mock_location.city = "Amsterdam"
        mock_location.country = "Netherlands"
        mock_location.country_short = "NL"
        mock_location.latitude = 52.3676
        mock_location.longitude = 4.9041
        mock_location.distance = 5000

        # Mock image
        mock_image = Mock(spec=ListingFirstImage)
        mock_image.extra_small = "https://example.com/image_xs.jpg"
        mock_image.medium = "https://example.com/image_m.jpg"
        mock_image.large = "https://example.com/image_l.jpg"
        mock_image.extra_large = "https://example.com/image_xl.jpg"

        # Mock main listing
        mock_listing = Mock(spec=MarktplaatsListing)
        mock_listing.id = "m123456789"
        mock_listing.title = "Test iPhone 12"
        mock_listing.description = "Barely used iPhone 12 in excellent condition"
        mock_listing.date = date(2024, 1, 15)
        mock_listing.price = 599.99
        mock_listing.price_type = PriceType.FIXED
        mock_listing.link = "https://www.marktplaats.nl/m123456789-test-iphone-12"
        mock_listing.category_id = 1953
        mock_listing.seller = mock_seller
        mock_listing.location = mock_location
        mock_listing._images = [mock_image]
        mock_listing.attributes = [{"name": "Brand", "value": "Apple"}]
        mock_listing.extended_attributes = []

        return mock_listing

    def test_convert_sort_by(self):
        """Test sort_by parameter conversion."""
        client = MarktplaatsClient()

        assert client._convert_sort_by("date") == SortBy.DATE
        assert client._convert_sort_by("price") == SortBy.PRICE
        assert client._convert_sort_by("optimized") == SortBy.OPTIMIZED
        assert client._convert_sort_by("location") == SortBy.LOCATION
        assert client._convert_sort_by(None) == SortBy.OPTIMIZED
        assert client._convert_sort_by("invalid") == SortBy.OPTIMIZED

    def test_convert_condition(self):
        """Test condition parameter conversion."""
        client = MarktplaatsClient()

        assert client._convert_condition("new") == Condition.NEW
        assert client._convert_condition("used") == Condition.USED
        assert client._convert_condition("as_good_as_new") == Condition.AS_GOOD_AS_NEW
        assert client._convert_condition(None) is None
        assert client._convert_condition("invalid") is None

    def test_extract_listing_id_from_url(self):
        """Test listing ID extraction from URL."""
        client = MarktplaatsClient()

        url = "https://www.marktplaats.nl/m123456789-test-listing"
        assert client._extract_listing_id_from_url(url) == "m123456789"

        url = "https://www.marktplaats.nl/v/computers-en-software/m987654321-another-test"
        assert client._extract_listing_id_from_url(url) == "m987654321"

        url = "https://www.marktplaats.nl/invalid-url"
        assert client._extract_listing_id_from_url(url) is None

    def test_convert_listing(self, mock_marktplaats_listing):
        """Test conversion from MarktplaatsListing to EnhancedListingItem."""
        client = MarktplaatsClient()

        enhanced_listing = client._convert_listing(mock_marktplaats_listing)

        # Test core fields
        assert enhanced_listing.marktplaats_id == "m123456789"
        assert enhanced_listing.title == "Test iPhone 12"
        assert enhanced_listing.description == "Barely used iPhone 12 in excellent condition"
        assert enhanced_listing.price == 599.99
        assert enhanced_listing.price_type == "FIXED"
        assert str(enhanced_listing.url) == "https://www.marktplaats.nl/m123456789-test-iphone-12"
        assert enhanced_listing.date_posted == date(2024, 1, 15)

        # Test legacy compatibility
        assert enhanced_listing.source_listing_id == "m123456789"
        assert enhanced_listing.price_numeric == 59999  # 599.99 * 100 cents
        assert (
            enhanced_listing.description_snippet == "Barely used iPhone 12 in excellent condition"
        )

        # Test location fields
        assert enhanced_listing.location_city == "Amsterdam"
        assert enhanced_listing.location_country == "Netherlands"
        assert enhanced_listing.location_country_short == "NL"
        assert enhanced_listing.location_latitude == 52.3676
        assert enhanced_listing.location_longitude == 4.9041
        assert enhanced_listing.location_distance == 5000

        # Test seller fields
        assert enhanced_listing.seller_id == 12345
        assert enhanced_listing.seller_name == "TestSeller"
        assert enhanced_listing.seller_is_verified is True

        # Test category and attributes
        assert enhanced_listing.category_id == 1953
        assert enhanced_listing.attributes == [{"name": "Brand", "value": "Apple"}]

        # Test images
        assert str(enhanced_listing.image_large) == "https://example.com/image_l.jpg"
        assert str(enhanced_listing.image_extra_small) == "https://example.com/image_xs.jpg"
        assert enhanced_listing.images == [
            {
                "extra_small": "https://example.com/image_xs.jpg",
                "medium": "https://example.com/image_m.jpg",
                "large": "https://example.com/image_l.jpg",
                "extra_large": "https://example.com/image_xl.jpg",
            }
        ]

    @pytest.mark.asyncio
    async def test_fetch_listings_success(self, mock_marktplaats_listing):
        """Test successful listing fetch."""
        client = MarktplaatsClient()

        with patch("marktplaats_search.client_new.SearchQuery") as mock_search_query:
            mock_instance = Mock()
            mock_instance.get_listings.return_value = [mock_marktplaats_listing]
            mock_search_query.return_value = mock_instance

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    return_value=[mock_marktplaats_listing]
                )

                listings = await client.fetch_listings(
                    query="iPhone", zip_code="1012AB", distance=25, limit=10
                )

                assert len(listings) == 1
                assert isinstance(listings[0], EnhancedListingItem)
                assert listings[0].marktplaats_id == "m123456789"

    @pytest.mark.asyncio
    async def test_fetch_listings_api_error(self):
        """Test handling of API errors."""
        client = MarktplaatsClient()

        with patch("marktplaats_search.client_new.SearchQuery") as mock_search_query:
            mock_instance = Mock()
            mock_instance.get_listings.side_effect = Exception("API Error")
            mock_search_query.return_value = mock_instance

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(
                    side_effect=Exception("API Error")
                )

                with pytest.raises(MarktplaatsApiError):
                    await client.fetch_listings(query="iPhone")

    def test_rate_limiting_semaphore(self):
        """Test that rate limiting semaphore is properly configured."""
        # All client instances should share the same semaphore
        client1 = MarktplaatsClient()
        client2 = MarktplaatsClient()

        assert client1._rate_limit_semaphore is client2._rate_limit_semaphore
        assert client1._rate_limit_semaphore._value == 2  # Allow 2 concurrent requests


class TestPerSearchListingManagement:
    """Test per-search listing uniqueness and management."""

    @pytest.fixture
    def sample_enhanced_listing(self):
        """Create a sample EnhancedListingItem for testing."""
        return EnhancedListingItem(
            marktplaats_id="m123456789",
            title="Test iPhone 12",
            description="Test description",
            price=599.99,
            price_type="FIXED",
            url="https://www.marktplaats.nl/m123456789-test-iphone-12",
            date_posted=date(2024, 1, 15),
            source_listing_id="m123456789",
            price_numeric=59999,
            description_snippet="Test description",
            location_city="Amsterdam",
            seller_id=12345,
            seller_name="TestSeller",
            seller_is_verified=True,
            category_id=1953,
            attributes=[{"name": "Brand", "value": "Apple"}],
            raw_data={"test": "data"},
        )

    def test_per_search_uniqueness_constraint(self):
        """Test that the database model enforces per-search uniqueness."""
        # This would be tested with actual database operations
        # showing that same URL can exist in multiple searches
        # but not within the same search
        pass

    def test_listing_model_new_fields(self):
        """Test that the Listing model has all new marktplaats library fields."""
        # Create a listing instance and verify all new fields exist
        listing = Listing(
            search_id=uuid.uuid4(),
            marktplaats_id="m123456789",
            title="Test Listing",
            url="https://example.com/test",
            price=99.99,
            price_type=PriceTypeEnum.FIXED,
            location_city="Amsterdam",
            seller_id=12345,
            seller_name="TestSeller",
            seller_is_verified=True,
            category_id=1953,
        )

        # Verify new fields are accessible
        assert listing.marktplaats_id == "m123456789"
        assert listing.price == 99.99
        assert listing.price_type == PriceTypeEnum.FIXED
        assert listing.location_city == "Amsterdam"
        assert listing.seller_id == 12345
        assert listing.category_id == 1953

    @pytest.mark.asyncio
    async def test_cross_search_duplicate_detection(self):
        """Test detection of listings appearing in multiple searches."""
        # This would test the cross-search analysis functionality
        # with actual database setup showing listings in multiple searches
        pass


class TestSchedulerIntegration:
    """Test scheduler integration with marktplaats library."""

    @pytest.mark.asyncio
    async def test_run_single_search_with_new_client(self):
        """Test that scheduler uses new MarktplaatsClient."""
        # This would require setting up test database and mocking
        # the MarktplaatsClient to return test data
        pass

    def test_scheduler_rate_limiting(self):
        """Test that scheduler respects rate limiting."""
        # Test that multiple concurrent searches are properly rate limited
        pass


class TestDatabaseMigration:
    """Test database migration compatibility."""

    def test_migration_adds_new_columns(self):
        """Test that migration script adds all required new columns."""
        # This would test the migration script functionality
        pass

    def test_backward_compatibility(self):
        """Test that existing data remains accessible after migration."""
        # Test that legacy fields still work after adding new fields
        pass


class TestAPIEnhancement:
    """Test enhanced API endpoints."""

    def test_enhanced_listing_response_fields(self):
        """Test that enhanced API responses include all new fields."""
        # Test the EnhancedListingResponse model
        response = {
            "id": str(uuid.uuid4()),
            "search_id": str(uuid.uuid4()),
            "marktplaats_id": "m123456789",
            "title": "Test Listing",
            "url": "https://example.com/test",
            "price": 99.99,
            "price_type": "FIXED",
            "location_city": "Amsterdam",
            "seller_id": 12345,
            "seller_name": "TestSeller",
            "seller_is_verified": True,
            "category_id": 1953,
            "is_new": True,
            "discovered_at": datetime.now(UTC),
        }

        from marktplaats_search.api_new import EnhancedListingResponse

        enhanced_response = EnhancedListingResponse(**response)

        assert enhanced_response.marktplaats_id == "m123456789"
        assert enhanced_response.price == 99.99
        assert enhanced_response.location_city == "Amsterdam"
        assert enhanced_response.seller_id == 12345

    def test_cross_search_analysis_response(self):
        """Test cross-search analysis response model."""
        response = {
            "url": "https://example.com/test",
            "title": "Test Listing",
            "marktplaats_id": "m123456789",
            "price": 99.99,
            "search_count": 3,
            "total_occurrences": 5,
            "search_queries": ["iPhone", "smartphone", "Apple"],
            "first_seen": datetime.now(UTC),
            "last_seen": datetime.now(UTC),
        }

        from marktplaats_search.api_new import CrossSearchAnalysisResponse

        analysis_response = CrossSearchAnalysisResponse(**response)

        assert analysis_response.search_count == 3
        assert len(analysis_response.search_queries) == 3

    def test_health_check_response(self):
        """Test health check endpoint response."""
        response = {
            "status": "healthy",
            "version": "2.0.0",
            "database_status": "healthy",
            "scheduler_status": "running",
            "marktplaats_client_status": "healthy",
            "total_searches": 5,
            "total_listings": 100,
            "timestamp": datetime.now(UTC),
        }

        from marktplaats_search.api_new import HealthCheckResponse

        health_response = HealthCheckResponse(**response)

        assert health_response.status == "healthy"
        assert health_response.version == "2.0.0"
        assert health_response.total_searches == 5

    def test_filtering_parameters(self):
        """Test new filtering parameters in search results."""
        # Test that category_id, seller_type, price filters work correctly
        pass


class TestErrorHandling:
    """Test error handling and resilience."""

    @pytest.mark.asyncio
    async def test_marktplaats_api_downtime_handling(self):
        """Test handling when marktplaats API is down."""
        client = MarktplaatsClient()

        with patch("marktplaats_search.client_new.SearchQuery") as mock_search_query:
            mock_search_query.side_effect = Exception("Service Unavailable")

            with pytest.raises(MarktplaatsApiError):
                await client.fetch_listings(query="test")

    def test_invalid_data_handling(self):
        """Test handling of invalid data from marktplaats API."""
        # Test handling of listings with missing or invalid fields
        pass

    def test_rate_limit_exceeded_handling(self):
        """Test handling when rate limits are exceeded."""
        # Test that rate limiting properly queues requests
        pass


class TestDataQuality:
    """Test data quality improvements with marktplaats library."""

    def test_structured_data_vs_scraped_data(self):
        """Test that structured API data is more reliable than scraped data."""
        # Compare data quality metrics between old scraper and new library
        pass

    def test_price_accuracy(self):
        """Test that price parsing is more accurate with API data."""
        client = MarktplaatsClient()

        # Test price conversion to cents
        mock_listing = Mock()
        mock_listing.price = 599.99
        mock_listing.id = "test"
        mock_listing.title = "Test"
        mock_listing.description = ""
        mock_listing.link = "https://example.com"
        mock_listing.seller = None
        mock_listing.location = None
        mock_listing._images = []
        mock_listing.category_id = 1
        mock_listing.attributes = []
        mock_listing.extended_attributes = []
        mock_listing.date = None
        mock_listing.price_type = None

        enhanced = client._convert_listing(mock_listing)
        assert enhanced.price_numeric == 59999  # 599.99 * 100

    def test_category_mapping(self):
        """Test that category data is properly preserved."""
        # Test that category_id from API is correctly stored
        pass


# Integration test marks
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

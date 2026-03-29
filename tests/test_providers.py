"""Tests for provider management and integration."""

from unittest.mock import AsyncMock, patch

import pytest

from marktplaats_search.client import ListingItem
from marktplaats_search.providers import (
    ProviderManager,
    ProviderManagerConfig,
    ProviderType,
    SearchContext,
    fetch_listings_with_providers,
)
from marktplaats_search.providers.base import ProviderResult


class TestProviderManager:
    """Test provider manager singleton functionality."""

    def teardown_method(self):
        """Clean up singleton state between tests."""
        ProviderManager._instance = None
        ProviderManager._initialized = False

    @pytest.mark.asyncio
    async def test_singleton_behavior(self):
        """Test that ProviderManager maintains singleton behavior."""
        manager1 = await ProviderManager.get_instance()
        manager2 = await ProviderManager.get_instance()

        assert manager1 is manager2
        assert ProviderManager._initialized is True

    @pytest.mark.asyncio
    async def test_custom_configuration(self):
        """Test ProviderManager with custom configuration."""
        custom_config = ProviderManagerConfig(
            primary_provider=ProviderType.MARKTPLAATS_LIBRARY, max_concurrent_requests=5
        )

        manager = await ProviderManager.get_instance(custom_config)

        assert manager.config.primary_provider == ProviderType.MARKTPLAATS_LIBRARY
        assert manager.config.max_concurrent_requests == 5

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test proper shutdown of provider manager."""
        await ProviderManager.get_instance()
        assert ProviderManager._instance is not None

        await ProviderManager.shutdown()

        assert ProviderManager._instance is None
        assert ProviderManager._initialized is False

    def test_default_configuration(self):
        """Test default configuration generation."""
        config = ProviderManager._get_default_config()

        assert config.primary_provider == ProviderType.HTML_SCRAPER
        assert ProviderType.MARKTPLAATS_LIBRARY in config.fallback_providers
        assert config.max_concurrent_requests > 0
        assert config.global_timeout_seconds > 0


@pytest.mark.asyncio
class TestFetchListingsWithProviders:
    """Test the high-level listing fetch function."""

    def teardown_method(self):
        """Clean up singleton state between tests."""
        ProviderManager._instance = None
        ProviderManager._initialized = False

    async def test_successful_fetch(self):
        """Test successful listing fetch with mock provider."""
        # Create mock listing
        mock_listing = ListingItem(
            source_listing_id="test123",
            title="Test iPhone",
            price="€ 500,00",
            price_numeric=50000,
            url="https://www.marktplaats.nl/test",
        )

        # Create mock result
        mock_result = ProviderResult(
            success=True,
            listings=[mock_listing],
            provider_type=ProviderType.HTML_SCRAPER,
            execution_time_ms=100,
        )

        # Mock the provider manager
        mock_manager = AsyncMock()
        mock_manager.search_listings = AsyncMock(return_value=mock_result)

        with patch.object(ProviderManager, "get_instance", return_value=mock_manager):
            result = await fetch_listings_with_providers(query="iPhone", limit=10)

        assert len(result) == 1
        assert result[0].title == "Test iPhone"
        assert result[0].source_listing_id == "test123"

        # Verify search context was created properly
        mock_manager.search_listings.assert_called_once()
        call_args = mock_manager.search_listings.call_args
        search_context = call_args.kwargs["context"]

        assert search_context.query == "iPhone"
        assert search_context.limit == 10

    async def test_failed_fetch(self):
        """Test handling of failed listing fetch."""
        # Create mock failed result
        mock_result = ProviderResult(
            success=False,
            listings=[],
            provider_type=ProviderType.HTML_SCRAPER,
            error_message="Provider failed",
            execution_time_ms=50,
        )

        mock_manager = AsyncMock()
        mock_manager.search_listings = AsyncMock(return_value=mock_result)

        with (
            patch.object(ProviderManager, "get_instance", return_value=mock_manager),
            pytest.raises(Exception, match="Failed to fetch listings"),
        ):
            await fetch_listings_with_providers(query="test")

    async def test_search_context_creation(self):
        """Test proper search context creation with all parameters."""
        mock_result = ProviderResult(
            success=True,
            listings=[],
            provider_type=ProviderType.HTML_SCRAPER,
            execution_time_ms=100,
        )

        mock_manager = AsyncMock()
        mock_manager.search_listings = AsyncMock(return_value=mock_result)

        with patch.object(ProviderManager, "get_instance", return_value=mock_manager):
            await fetch_listings_with_providers(
                query="MacBook Pro",
                zip_code="1012AB",
                distance=25,
                price_from=800,
                price_to=2000,
                limit=20,
                sort_by="price",
                sort_order="asc",
                preferred_provider=ProviderType.MARKTPLAATS_LIBRARY,
            )

        # Verify all parameters were passed correctly
        call_args = mock_manager.search_listings.call_args
        search_context = call_args.kwargs["context"]
        preferred_provider = call_args.kwargs["preferred_provider"]

        assert search_context.query == "MacBook Pro"
        assert search_context.zip_code == "1012AB"
        assert search_context.distance == 25
        assert search_context.price_from == 800
        assert search_context.price_to == 2000
        assert search_context.limit == 20
        assert search_context.sort_by == "price"
        assert search_context.sort_order == "asc"
        assert preferred_provider == ProviderType.MARKTPLAATS_LIBRARY


class TestSearchContext:
    """Test search context functionality."""

    def test_search_context_creation(self):
        """Test basic search context creation."""
        context = SearchContext(search_id="test-123", query="test query", timeout_seconds=30)

        assert context.search_id == "test-123"
        assert context.query == "test query"
        assert context.timeout_seconds == 30

    def test_search_context_with_all_fields(self):
        """Test search context with all optional fields."""
        context = SearchContext(
            search_id="test-456",
            query="iPhone 15",
            zip_code="1012AB",
            distance=50,
            price_from=500,
            price_to=1500,
            limit=25,
            sort_by="date",
            sort_order="desc",
            timeout_seconds=45,
        )

        assert context.query == "iPhone 15"
        assert context.zip_code == "1012AB"
        assert context.distance == 50
        assert context.price_from == 500
        assert context.price_to == 1500
        assert context.limit == 25
        assert context.sort_by == "date"
        assert context.sort_order == "desc"
        assert context.timeout_seconds == 45


class TestProviderResult:
    """Test provider result functionality."""

    def test_successful_result(self):
        """Test successful provider result."""
        mock_listing = ListingItem(
            source_listing_id="test123", title="Test Item", price="€ 100,00", url="https://test.com"
        )

        result = ProviderResult(
            success=True,
            listings=[mock_listing],
            provider_type=ProviderType.HTML_SCRAPER,
            execution_time_ms=150,
        )

        assert result.success is True
        assert len(result.listings) == 1
        assert result.listings[0].title == "Test Item"
        assert result.provider_type == ProviderType.HTML_SCRAPER
        assert result.execution_time_ms == 150

    def test_failed_result(self):
        """Test failed provider result."""
        result = ProviderResult(
            success=False,
            listings=[],
            provider_type=ProviderType.HTML_SCRAPER,
            error_message="Connection timeout",
            execution_time_ms=30000,
        )

        assert result.success is False
        assert len(result.listings) == 0
        assert result.error_message == "Connection timeout"
        assert result.execution_time_ms == 30000

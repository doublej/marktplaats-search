"""pytest configuration and fixtures for MarktplaatsSearch tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_database_session():
    """Mock database session for testing."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_search_context():
    """Mock search context for provider testing."""
    from marktplaats_search.providers.base import SearchContext

    return SearchContext(search_id="test-search-123", query="test query", timeout_seconds=30)


@pytest.fixture
def mock_listing_item():
    """Mock listing item for testing."""

    # This fixture will only work if dependencies are installed
    # For now, we'll return a mock object that mimics the interface
    mock_listing = MagicMock()
    mock_listing.source_listing_id = "test123"
    mock_listing.title = "Test Listing"
    mock_listing.price = "€ 100,00"
    mock_listing.price_numeric = 10000
    mock_listing.url = "https://test.example.com"
    return mock_listing


@pytest.fixture
def sample_html_content():
    """Sample HTML content for scraping tests."""
    return """
    <html>
        <body>
            <div class="listing">
                <h2>iPhone 15 128GB</h2>
                <span class="price">€ 950,00</span>
                <p class="description">Excellent condition iPhone</p>
                <span class="location">Amsterdam</span>
            </div>
        </body>
    </html>
    """


# Configure asyncio for pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

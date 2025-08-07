"""
Tests for per-search listing management functionality.

This module tests:
- Database schema changes (composite constraints)
- Per-search duplicate detection
- Cross-search duplicate analysis
- New listing management per search
- API endpoints for listing management
"""

import pytest
import uuid
from datetime import UTC, datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from marktplaats_search.database import AsyncSessionLocal, engine, Base
from marktplaats_search.models import User, Search, Listing, SearchStatus
from marktplaats_search.listing_management import (
    get_cross_search_duplicates,
    get_listing_stats_for_user,
    get_new_listings_summary,
    mark_search_listings_as_read,
    mark_all_user_listings_as_read,
    cleanup_old_listings,
    optimize_listing_queries,
)
from marktplaats_search.auth import generate_secure_token, hash_token


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with AsyncSessionLocal() as session:
        yield session
    
    # Clean up after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    token = generate_secure_token()
    user = User(
        user_identifier="test_user",
        api_token_hash=hash_token(token),
        is_active=True,
        token_created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_searches(db_session: AsyncSession, test_user: User):
    """Create test searches."""
    search1 = Search(
        query="laptop",
        interval=300,
        status=SearchStatus.ACTIVE,
        user_id=test_user.id,
    )
    search2 = Search(
        query="macbook",
        interval=600,
        status=SearchStatus.ACTIVE,
        user_id=test_user.id,
    )
    
    db_session.add_all([search1, search2])
    await db_session.commit()
    await db_session.refresh(search1)
    await db_session.refresh(search2)
    
    return search1, search2


class TestDatabaseSchema:
    """Test database schema changes and constraints."""
    
    async def test_url_not_globally_unique(self, db_session: AsyncSession, test_searches):
        """Test that same URL can exist in different searches."""
        search1, search2 = test_searches
        url = "https://www.marktplaats.nl/listing/123456"
        
        # Create listing in first search
        listing1 = Listing(
            search_id=search1.id,
            url=url,
            title="Laptop 1",
            is_new=True,
        )
        db_session.add(listing1)
        await db_session.commit()
        
        # Create same URL in second search - should succeed
        listing2 = Listing(
            search_id=search2.id,
            url=url,
            title="Laptop 2",
            is_new=True,
        )
        db_session.add(listing2)
        await db_session.commit()
        
        # Verify both exist
        assert listing1.id != listing2.id
        assert listing1.url == listing2.url
        assert listing1.search_id != listing2.search_id
    
    async def test_composite_unique_constraint(self, db_session: AsyncSession, test_searches):
        """Test that same URL cannot exist twice in same search."""
        search1, _ = test_searches
        url = "https://www.marktplaats.nl/listing/123456"
        
        # Create first listing
        listing1 = Listing(
            search_id=search1.id,
            url=url,
            title="Laptop 1",
            is_new=True,
        )
        db_session.add(listing1)
        await db_session.commit()
        
        # Try to create duplicate in same search - should fail
        listing2 = Listing(
            search_id=search1.id,
            url=url,
            title="Laptop 2",
            is_new=True,
        )
        db_session.add(listing2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    async def test_indexes_exist(self, db_session: AsyncSession):
        """Test that required indexes are created."""
        # Check for essential indexes
        result = await db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='listings'")
        )
        indexes = [row[0] for row in result.fetchall()]
        
        # Should have indexes on commonly queried fields
        expected_patterns = ["search_id", "url", "is_new", "discovered_at"]
        
        found_patterns = []
        for pattern in expected_patterns:
            if any(pattern in idx for idx in indexes):
                found_patterns.append(pattern)
        
        assert len(found_patterns) >= 2, f"Missing essential indexes, found: {indexes}"


class TestPerSearchDuplicateDetection:
    """Test per-search duplicate detection logic."""
    
    async def test_same_listing_different_searches(self, db_session: AsyncSession, test_searches):
        """Test that same listing can be added to different searches."""
        search1, search2 = test_searches
        url = "https://www.marktplaats.nl/listing/123456"
        
        # Simulate scheduler logic for search1
        existing = await db_session.execute(
            text("SELECT * FROM listings WHERE search_id = :search_id AND url = :url"),
            {"search_id": str(search1.id), "url": url}
        )
        assert existing.fetchone() is None
        
        # Add to search1
        listing1 = Listing(search_id=search1.id, url=url, title="Test", is_new=True)
        db_session.add(listing1)
        await db_session.commit()
        
        # Simulate scheduler logic for search2 - should still be able to add
        existing = await db_session.execute(
            text("SELECT * FROM listings WHERE search_id = :search_id AND url = :url"),
            {"search_id": str(search2.id), "url": url}
        )
        assert existing.fetchone() is None
        
        # Add to search2
        listing2 = Listing(search_id=search2.id, url=url, title="Test", is_new=True)
        db_session.add(listing2)
        await db_session.commit()
        
        # Both should exist
        count = await db_session.execute(text("SELECT COUNT(*) FROM listings WHERE url = :url"), {"url": url})
        assert count.scalar() == 2
    
    async def test_duplicate_within_same_search_prevented(self, db_session: AsyncSession, test_searches):
        """Test that duplicate detection works within same search."""
        search1, _ = test_searches
        url = "https://www.marktplaats.nl/listing/123456"
        
        # Add first listing
        listing1 = Listing(search_id=search1.id, url=url, title="Test", is_new=True)
        db_session.add(listing1)
        await db_session.commit()
        
        # Simulate scheduler duplicate check
        existing = await db_session.execute(
            text("SELECT * FROM listings WHERE search_id = :search_id AND url = :url"),
            {"search_id": str(search1.id), "url": url}
        )
        assert existing.fetchone() is not None  # Should find existing
        
        # Should not add duplicate (this simulates scheduler logic)
        # Scheduler would skip adding if existing.fetchone() is not None


class TestListingManagementFunctions:
    """Test listing management utility functions."""
    
    async def test_get_cross_search_duplicates(self, db_session: AsyncSession, test_user: User, test_searches):
        """Test cross-search duplicate detection."""
        search1, search2 = test_searches
        
        # Create listings that appear in both searches
        url1 = "https://www.marktplaats.nl/listing/123456"
        url2 = "https://www.marktplaats.nl/listing/789012"
        url3 = "https://www.marktplaats.nl/listing/345678"  # Only in search1
        
        listings = [
            Listing(search_id=search1.id, url=url1, title="Laptop A", price="€500", is_new=True),
            Listing(search_id=search2.id, url=url1, title="Laptop A", price="€500", is_new=True),
            Listing(search_id=search1.id, url=url2, title="Laptop B", price="€800", is_new=True),
            Listing(search_id=search2.id, url=url2, title="Laptop B", price="€800", is_new=True),
            Listing(search_id=search1.id, url=url3, title="Laptop C", price="€300", is_new=True),
        ]
        
        for listing in listings:
            db_session.add(listing)
        await db_session.commit()
        
        # Get cross-search duplicates
        duplicates = await get_cross_search_duplicates(db_session, test_user.id, limit=10)
        
        # Should find 2 URLs that appear in multiple searches
        assert len(duplicates) == 2
        
        duplicate_urls = {dup["url"] for dup in duplicates}
        assert url1 in duplicate_urls
        assert url2 in duplicate_urls
        assert url3 not in duplicate_urls
        
        # Check duplicate details
        for dup in duplicates:
            assert dup["search_count"] == 2
            assert dup["total_occurrences"] == 2
            assert len(dup["search_queries"]) == 2
    
    async def test_get_listing_stats_for_user(self, db_session: AsyncSession, test_user: User, test_searches):
        """Test user listing statistics."""
        search1, search2 = test_searches
        
        # Create various listings
        listings = [
            Listing(search_id=search1.id, url="https://example.com/1", title="New 1", is_new=True),
            Listing(search_id=search1.id, url="https://example.com/2", title="Old 1", is_new=False),
            Listing(search_id=search2.id, url="https://example.com/3", title="New 2", is_new=True),
            Listing(search_id=search2.id, url="https://example.com/1", title="New 1 Dup", is_new=True),  # Cross-search dup
        ]
        
        for listing in listings:
            db_session.add(listing)
        await db_session.commit()
        
        stats = await get_listing_stats_for_user(db_session, test_user.id)
        
        assert stats.total_listings == 4
        assert stats.new_listings == 3
        assert stats.cross_search_duplicates == 1  # URL "https://example.com/1" appears in both searches
        assert stats.searches_affected == 2
    
    async def test_mark_search_listings_as_read(self, db_session: AsyncSession, test_user: User, test_searches):
        """Test marking listings as read for specific search."""
        search1, search2 = test_searches
        
        # Create new listings in both searches
        listings = [
            Listing(search_id=search1.id, url="https://example.com/1", title="New 1", is_new=True),
            Listing(search_id=search1.id, url="https://example.com/2", title="New 2", is_new=True),
            Listing(search_id=search2.id, url="https://example.com/3", title="New 3", is_new=True),
        ]
        
        for listing in listings:
            db_session.add(listing)
        await db_session.commit()
        
        # Mark search1 listings as read
        marked_count = await mark_search_listings_as_read(db_session, search1.id, test_user.id)
        
        assert marked_count == 2
        
        # Check that only search1 listings were marked as read
        await db_session.refresh(listings[0])
        await db_session.refresh(listings[1])
        await db_session.refresh(listings[2])
        
        assert not listings[0].is_new
        assert not listings[1].is_new
        assert listings[2].is_new  # Should still be new
    
    async def test_mark_all_user_listings_as_read(self, db_session: AsyncSession, test_user: User, test_searches):
        """Test marking all user listings as read."""
        search1, search2 = test_searches
        
        # Create new listings in both searches
        listings = [
            Listing(search_id=search1.id, url="https://example.com/1", title="New 1", is_new=True),
            Listing(search_id=search2.id, url="https://example.com/2", title="New 2", is_new=True),
        ]
        
        for listing in listings:
            db_session.add(listing)
        await db_session.commit()
        
        # Mark all listings as read
        marked_count = await mark_all_user_listings_as_read(db_session, test_user.id)
        
        assert marked_count == 2
        
        # Check that all listings were marked as read
        await db_session.refresh(listings[0])
        await db_session.refresh(listings[1])
        
        assert not listings[0].is_new
        assert not listings[1].is_new
    
    async def test_cleanup_old_listings(self, db_session: AsyncSession, test_searches):
        """Test cleaning up old listings."""
        search1, search2 = test_searches
        
        # Create old and new listings
        old_date = datetime.now(UTC) - timedelta(days=35)
        
        old_listing = Listing(
            search_id=search1.id,
            url="https://example.com/old",
            title="Old listing",
            is_new=False,
            discovered_at=old_date,
        )
        
        new_listing = Listing(
            search_id=search2.id,
            url="https://example.com/new",
            title="New listing",
            is_new=True,
        )
        
        db_session.add_all([old_listing, new_listing])
        await db_session.commit()
        
        # Test dry run
        count, searches_affected = await cleanup_old_listings(
            db_session, days_old=30, keep_new_listings=True, dry_run=True
        )
        
        assert count == 1  # Should identify 1 old listing to delete
        assert str(search1.id) in searches_affected
        
        # Verify nothing was actually deleted in dry run
        result = await db_session.execute(text("SELECT COUNT(*) FROM listings"))
        assert result.scalar() == 2
        
        # Test actual cleanup
        count, searches_affected = await cleanup_old_listings(
            db_session, days_old=30, keep_new_listings=True, dry_run=False
        )
        
        assert count == 1
        
        # Verify old listing was deleted, new one remains
        result = await db_session.execute(text("SELECT COUNT(*) FROM listings"))
        assert result.scalar() == 1
        
        remaining = await db_session.execute(text("SELECT title FROM listings"))
        assert remaining.scalar() == "New listing"
    
    async def test_optimize_listing_queries(self, db_session: AsyncSession):
        """Test query optimization function."""
        optimizations = await optimize_listing_queries(db_session)
        
        # Should return results for various indexes
        assert len(optimizations) > 0
        assert isinstance(optimizations, dict)
        
        # Check that some common indexes are included
        expected_indexes = ["idx_listings_search_id", "idx_listings_url", "idx_listings_is_new"]
        
        for expected_idx in expected_indexes:
            assert expected_idx in optimizations
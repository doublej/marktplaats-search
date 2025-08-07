"""
Listing management utilities for per-search listing operations.

This module provides utilities for:
- Cross-search listing analysis
- Duplicate detection and management
- Per-search notification management
- Performance optimization for listing queries
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .models import Listing, Search

logger = logging.getLogger(__name__)


class ListingStats:
    """Statistics for listing management."""
    
    def __init__(
        self,
        total_listings: int = 0,
        new_listings: int = 0,
        cross_search_duplicates: int = 0,
        searches_affected: int = 0,
    ):
        self.total_listings = total_listings
        self.new_listings = new_listings
        self.cross_search_duplicates = cross_search_duplicates
        self.searches_affected = searches_affected


async def get_cross_search_duplicates(
    db: AsyncSession, user_id: int, limit: int = 50
) -> List[Dict]:
    """
    Find listings that appear across multiple searches for a user.
    
    Args:
        db: Database session
        user_id: User ID to filter searches
        limit: Maximum number of duplicate groups to return
        
    Returns:
        List of dictionaries with duplicate information
    """
    query = text("""
        SELECT 
            l.url,
            l.title,
            l.price,
            COUNT(DISTINCT l.search_id) as search_count,
            COUNT(l.id) as total_occurrences,
            GROUP_CONCAT(DISTINCT s.query) as search_queries,
            MIN(l.discovered_at) as first_seen,
            MAX(l.discovered_at) as last_seen
        FROM listings l
        JOIN searches s ON l.search_id = s.id
        WHERE s.user_id = :user_id
        GROUP BY l.url
        HAVING COUNT(DISTINCT l.search_id) > 1
        ORDER BY search_count DESC, total_occurrences DESC
        LIMIT :limit
    """)
    
    result = await db.execute(query, {"user_id": user_id, "limit": limit})
    
    duplicates = []
    for row in result.fetchall():
        duplicates.append({
            "url": row[0],
            "title": row[1],
            "price": row[2],
            "search_count": row[3],
            "total_occurrences": row[4],
            "search_queries": row[5].split(",") if row[5] else [],
            "first_seen": row[6],
            "last_seen": row[7],
        })
    
    return duplicates


async def get_listing_stats_for_user(db: AsyncSession, user_id: int) -> ListingStats:
    """
    Get comprehensive listing statistics for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        ListingStats object with comprehensive statistics
    """
    # Total listings for user's searches
    total_result = await db.execute(
        text("""
            SELECT COUNT(l.id)
            FROM listings l
            JOIN searches s ON l.search_id = s.id
            WHERE s.user_id = :user_id
        """),
        {"user_id": user_id}
    )
    total_listings = total_result.scalar() or 0
    
    # New listings count
    new_result = await db.execute(
        text("""
            SELECT COUNT(l.id)
            FROM listings l
            JOIN searches s ON l.search_id = s.id
            WHERE s.user_id = :user_id AND l.is_new = 1
        """),
        {"user_id": user_id}
    )
    new_listings = new_result.scalar() or 0
    
    # Cross-search duplicates
    duplicate_result = await db.execute(
        text("""
            SELECT COUNT(DISTINCT l.url)
            FROM listings l
            JOIN searches s ON l.search_id = s.id
            WHERE s.user_id = :user_id
            GROUP BY l.url
            HAVING COUNT(DISTINCT l.search_id) > 1
        """),
        {"user_id": user_id}
    )
    cross_search_duplicates = len(duplicate_result.fetchall())
    
    # Searches with listings
    searches_result = await db.execute(
        text("""
            SELECT COUNT(DISTINCT s.id)
            FROM searches s
            JOIN listings l ON s.id = l.search_id
            WHERE s.user_id = :user_id
        """),
        {"user_id": user_id}
    )
    searches_affected = searches_result.scalar() or 0
    
    return ListingStats(
        total_listings=total_listings,
        new_listings=new_listings,
        cross_search_duplicates=cross_search_duplicates,
        searches_affected=searches_affected,
    )


async def mark_search_listings_as_read(
    db: AsyncSession, search_id: uuid.UUID, user_id: int
) -> int:
    """
    Mark all new listings for a specific search as read.
    
    Args:
        db: Database session
        search_id: Search ID
        user_id: User ID (for authorization)
        
    Returns:
        Number of listings marked as read
        
    Raises:
        ValueError: If search doesn't belong to user
    """
    # Verify search ownership
    search_result = await db.execute(
        select(Search).where(Search.id == search_id, Search.user_id == user_id)
    )
    if not search_result.scalars().first():
        raise ValueError("Search not found or access denied")
    
    # Update listings
    update_result = await db.execute(
        text("""
            UPDATE listings 
            SET is_new = 0 
            WHERE search_id = :search_id AND is_new = 1
        """),
        {"search_id": str(search_id)}
    )
    
    await db.commit()
    return update_result.rowcount


async def mark_all_user_listings_as_read(db: AsyncSession, user_id: int) -> int:
    """
    Mark all new listings for all user's searches as read.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Number of listings marked as read
    """
    update_result = await db.execute(
        text("""
            UPDATE listings 
            SET is_new = 0 
            WHERE is_new = 1 AND search_id IN (
                SELECT id FROM searches WHERE user_id = :user_id
            )
        """),
        {"user_id": user_id}
    )
    
    await db.commit()
    return update_result.rowcount


async def get_new_listings_summary(
    db: AsyncSession, user_id: int
) -> Dict[str, int]:
    """
    Get summary of new listings per search for a user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        Dictionary mapping search_id to new listing count
    """
    result = await db.execute(
        text("""
            SELECT s.id, s.query, COUNT(l.id) as new_count
            FROM searches s
            LEFT JOIN listings l ON s.id = l.search_id AND l.is_new = 1
            WHERE s.user_id = :user_id
            GROUP BY s.id, s.query
            HAVING new_count > 0
            ORDER BY new_count DESC
        """),
        {"user_id": user_id}
    )
    
    summary = {}
    for row in result.fetchall():
        summary[row[0]] = {
            "search_query": row[1],
            "new_count": row[2]
        }
    
    return summary


async def cleanup_old_listings(
    db: AsyncSession,
    days_old: int = 30,
    keep_new_listings: bool = True,
    dry_run: bool = True
) -> Tuple[int, List[str]]:
    """
    Clean up old listings to manage database size.
    
    Args:
        db: Database session
        days_old: Delete listings older than this many days
        keep_new_listings: If True, never delete listings marked as new
        dry_run: If True, only count what would be deleted
        
    Returns:
        Tuple of (count_deleted, list_of_search_ids_affected)
    """
    cutoff_date = datetime.now(UTC).date() - timedelta(days=days_old)
    
    # Build query conditions
    conditions = ["DATE(l.discovered_at) < :cutoff_date"]
    params = {"cutoff_date": cutoff_date}
    
    if keep_new_listings:
        conditions.append("l.is_new = 0")
    
    where_clause = " AND ".join(conditions)
    
    if dry_run:
        # Count what would be deleted
        count_query = text(f"""
            SELECT COUNT(l.id), GROUP_CONCAT(DISTINCT l.search_id)
            FROM listings l
            WHERE {where_clause}
        """)
        
        result = await db.execute(count_query, params)
        row = result.fetchone()
        count = row[0] if row else 0
        search_ids = row[1].split(",") if row and row[1] else []
        
        return count, search_ids
    else:
        # Get affected searches before deletion
        search_query = text(f"""
            SELECT DISTINCT l.search_id
            FROM listings l
            WHERE {where_clause}
        """)
        
        search_result = await db.execute(search_query, params)
        search_ids = [row[0] for row in search_result.fetchall()]
        
        # Delete listings
        delete_query = text(f"""
            DELETE FROM listings
            WHERE {where_clause}
        """)
        
        delete_result = await db.execute(delete_query, params)
        await db.commit()
        
        return delete_result.rowcount, search_ids


async def optimize_listing_queries(db: AsyncSession) -> Dict[str, bool]:
    """
    Check and create missing indexes for optimal query performance.
    
    Args:
        db: Database session
        
    Returns:
        Dictionary of optimization results
    """
    optimizations = {}
    
    # Check for essential indexes
    index_checks = [
        ("idx_listings_search_id", "CREATE INDEX IF NOT EXISTS idx_listings_search_id ON listings (search_id)"),
        ("idx_listings_url", "CREATE INDEX IF NOT EXISTS idx_listings_url ON listings (url)"),
        ("idx_listings_is_new", "CREATE INDEX IF NOT EXISTS idx_listings_is_new ON listings (is_new)"),
        ("idx_listings_discovered_at", "CREATE INDEX IF NOT EXISTS idx_listings_discovered_at ON listings (discovered_at)"),
        ("idx_listings_search_new", "CREATE INDEX IF NOT EXISTS idx_listings_search_new ON listings (search_id, is_new)"),
        ("idx_listings_search_discovered", "CREATE INDEX IF NOT EXISTS idx_listings_search_discovered ON listings (search_id, discovered_at)"),
    ]
    
    for index_name, create_sql in index_checks:
        try:
            await db.execute(text(create_sql))
            optimizations[index_name] = True
            logger.info(f"Created/verified index: {index_name}")
        except Exception as e:
            optimizations[index_name] = False
            logger.error(f"Failed to create index {index_name}: {e}")
    
    await db.commit()
    return optimizations
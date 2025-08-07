# Per-Search Listing Management Architecture

## Overview

This document describes the architectural changes implemented to support per-search listing management, allowing the same listing to appear in multiple searches while maintaining proper duplicate detection within each search.

## Problem Statement

**Original Issues:**
- Global unique constraint on URL field prevented same listing from appearing in multiple searches
- Only first search to find a URL could store it; subsequent searches missed relevant results
- `is_new` flag was global rather than per-search
- Users missed notifications for listings matching their specific searches

**Business Impact:**
- Incomplete search results for overlapping queries
- Missing notifications for relevant listings
- Poor user experience for users with multiple related searches

## Solution Architecture

### 1. Database Schema Changes

#### Before (Original Schema)
```sql
CREATE TABLE listings (
    id CHAR(36) PRIMARY KEY,
    search_id CHAR(36) NOT NULL,
    url VARCHAR UNIQUE NOT NULL,  -- GLOBAL UNIQUE CONSTRAINT
    -- ... other fields
);
```

#### After (New Schema)
```sql
CREATE TABLE listings (
    id CHAR(36) PRIMARY KEY,
    search_id CHAR(36) NOT NULL,
    url VARCHAR NOT NULL,  -- Removed global unique constraint
    -- ... other fields
    
    -- Composite unique constraint: prevent same URL within same search
    UNIQUE (search_id, url)
);
```

### 2. Key Architectural Changes

#### A. Constraint Strategy
- **Removed:** Global unique constraint on `url` field
- **Added:** Composite unique constraint on `(search_id, url)`
- **Result:** Same URL can exist across different searches but not within the same search

#### B. Duplicate Detection Logic
- **Before:** `SELECT * FROM listings WHERE url = ?`
- **After:** `SELECT * FROM listings WHERE search_id = ? AND url = ?`
- **Result:** Per-search duplicate detection instead of global

#### C. "New" Flag Management
- **Before:** Global `is_new` status across all searches
- **After:** Per-search `is_new` status - same listing can be "new" for different searches
- **Result:** Each search tracks its own notification state

#### D. Performance Optimization
- **Added:** Composite index on `(search_id, url)` for efficient duplicate checking
- **Added:** Compound indexes for common query patterns
- **Added:** Individual indexes on frequently queried fields

## Implementation Details

### 1. Database Migration

The migration process is implemented in `/scripts/per_search_listing_migration.py`:

```python
# Key migration steps:
1. Backup database
2. Analyze existing data for duplicates
3. Remove true duplicates (same search_id + url)
4. Create new table with updated schema
5. Migrate data to new table
6. Create optimized indexes
7. Swap tables
8. Verify migration success
```

### 2. Model Changes

Updated SQLAlchemy model in `/marktplaats_search/models.py`:

```python
class Listing(Base):
    # ... fields
    url = Column(String, nullable=False, index=True)  # Removed unique=True
    
    # Composite constraint
    __table_args__ = (
        UniqueConstraint("search_id", "url", name="uq_listing_search_url"),
    )
```

### 3. Scheduler Updates

Updated duplicate detection logic in `/marktplaats_search/scheduler.py`:

```python
# Before: Global check
existing = await db.execute(
    select(Listing).where(Listing.url == str(listing_data.url))
)

# After: Per-search check
existing = await db.execute(
    select(Listing).where(
        Listing.search_id == search_instance.id,
        Listing.url == str(listing_data.url)
    )
)
```

### 4. New API Endpoints

Added comprehensive listing management endpoints:

- `GET /api/listings/stats` - User listing statistics
- `GET /api/listings/cross-search-duplicates` - Find listings across searches
- `GET /api/listings/new-summary` - New listings per search
- `POST /api/searches/{search_id}/mark-read` - Mark search listings as read
- `POST /api/listings/mark-all-read` - Mark all user listings as read
- `POST /api/admin/cleanup-listings` - Clean up old listings
- `POST /api/admin/optimize-queries` - Database optimization

## Performance Considerations

### 1. Index Strategy
```sql
-- Essential indexes for performance
CREATE INDEX idx_listings_search_id ON listings (search_id);
CREATE INDEX idx_listings_url ON listings (url);
CREATE INDEX idx_listings_search_url ON listings (search_id, url);
CREATE INDEX idx_listings_is_new ON listings (is_new);
CREATE INDEX idx_listings_discovered_at ON listings (discovered_at);
CREATE INDEX idx_listings_search_new ON listings (search_id, is_new);
CREATE INDEX idx_listings_search_discovered ON listings (search_id, discovered_at);
```

### 2. Query Optimization
- Composite index on `(search_id, url)` enables efficient duplicate detection
- Compound indexes support common query patterns without table scans
- Strategic individual indexes for filtering and sorting operations

### 3. Database Size Management
- Cleanup utilities to remove old listings
- Configurable retention policies
- Dry-run capabilities for safe testing

## Risk Analysis and Mitigation

### 1. Migration Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during migration | High | Automatic backup before migration |
| Migration failure | High | Rollback procedures and verification |
| Constraint violations | Medium | Pre-migration duplicate analysis and cleanup |
| Performance degradation | Medium | Optimized indexes and query patterns |
| Extended downtime | Low | Fast migration process with minimal steps |

### 2. Operational Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database growth | Medium | Cleanup utilities and retention policies |
| Query performance | Medium | Comprehensive indexing strategy |
| Memory usage | Low | Efficient query patterns and pagination |
| Storage requirements | Medium | Regular cleanup and archival processes |

## Rollback Procedures

### 1. Emergency Rollback (Database Level)

If critical issues occur immediately after migration:

```bash
# 1. Stop application
systemctl stop marktplaats-search

# 2. Restore from backup
cp marktplaats_api_backup_YYYYMMDD_HHMMSS.db data/marktplaats_api.db

# 3. Restart application
systemctl start marktplaats-search
```

### 2. Planned Rollback (Code Level)

If issues are discovered later but database is stable:

```bash
# 1. Revert code changes
git revert <migration-commit-hash>

# 2. Update models to original schema
# 3. Deploy reverted version
# 4. Run reverse migration if needed
```

### 3. Data Integrity Verification

After any rollback:

```sql
-- Check for duplicate URLs (should exist if rollback was needed)
SELECT url, COUNT(*) FROM listings GROUP BY url HAVING COUNT(*) > 1;

-- Verify search functionality
SELECT COUNT(*) FROM listings WHERE search_id = '<test-search-id>';

-- Check constraint violations
PRAGMA foreign_key_check;
PRAGMA integrity_check;
```

## Testing Strategy

### 1. Unit Tests
- Database schema validation
- Constraint behavior verification
- Duplicate detection logic
- API endpoint functionality

### 2. Integration Tests
- End-to-end search workflow
- Cross-search duplicate scenarios
- Migration process validation
- Performance benchmarking

### 3. Load Testing
- Concurrent search execution
- Large dataset handling
- Memory and CPU usage monitoring
- Database performance under load

## Monitoring and Observability

### 1. Key Metrics
- Duplicate detection rate per search
- Cross-search duplicate percentage
- New listing notification accuracy
- Query performance metrics
- Database size growth

### 2. Health Checks
```python
# Database health
await db.execute(text("SELECT COUNT(*) FROM listings"))

# Constraint validation  
await db.execute(text("PRAGMA integrity_check"))

# Performance monitoring
await db.execute(text("EXPLAIN QUERY PLAN SELECT ..."))
```

### 3. Alerting Thresholds
- Database size > 1GB (cleanup needed)
- Query response time > 500ms
- Error rate > 1% for listing operations
- Failed duplicate detection > 0.1%

## Deployment Checklist

### Pre-Deployment
- [ ] Database backup verified
- [ ] Migration script tested on copy of production data
- [ ] Performance benchmarks established
- [ ] Rollback procedures documented and tested
- [ ] Monitoring alerts configured

### During Deployment
- [ ] Application stopped gracefully
- [ ] Database backup created
- [ ] Migration script executed successfully
- [ ] Data integrity verified
- [ ] Indexes created and verified
- [ ] Application restarted

### Post-Deployment
- [ ] Health checks passing
- [ ] Search functionality verified
- [ ] Duplicate detection working correctly
- [ ] New listing notifications accurate
- [ ] Performance metrics within acceptable range
- [ ] No error rate increase

## Future Enhancements

### 1. Advanced Analytics
- Cross-search recommendation engine
- Search overlap analysis
- User behavior insights
- Market trend detection

### 2. Performance Optimizations
- Query result caching
- Async background processing
- Database partitioning
- Archive old data to separate tables

### 3. User Experience
- Unified notification management
- Advanced filtering options
- Search result deduplication UI
- Personalized recommendations

## Conclusion

The per-search listing management architecture provides:

1. **Complete Search Results**: Users see all relevant listings for each search
2. **Proper Notifications**: Each search maintains its own "new" status
3. **Data Integrity**: Prevents true duplicates within searches
4. **Scalable Design**: Supports growth in users and searches
5. **Maintainable Code**: Clean separation of concerns and comprehensive testing

This architecture solves the original limitations while maintaining data consistency, performance, and user experience quality expected in an enterprise-grade application.
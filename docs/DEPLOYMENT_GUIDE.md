# Per-Search Listing Management Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the per-search listing management feature safely in a production environment.

## Prerequisites

- Python 3.11+ environment with uv
- Access to production database
- Backup storage space (at least 2x current database size)
- Administrative access to application server
- Testing environment that mirrors production

## Pre-Deployment Preparation

### 1. Environment Validation

```bash
# Check Python version
python --version  # Should be 3.11+

# Verify uv is available
uv --version

# Check database accessibility
sqlite3 data/marktplaats_api.db ".tables"

# Verify disk space (need 2x database size for backup)
df -h data/
```

### 2. Code Preparation

```bash
# Ensure you're on the correct branch
git checkout main
git pull origin main

# Install dependencies
uv sync --dev

# Run type checking
mypy .

# Run linting
ruff check .
ruff format .

# Run tests
pytest tests/test_per_search_listing_management.py -v
```

### 3. Database Analysis

```bash
# Run pre-migration analysis
python scripts/per_search_listing_migration.py --analyze-only

# Check current database size
ls -lh data/marktplaats_api.db

# Verify application can connect to database
python -c "
import asyncio
from marktplaats_search.database import AsyncSessionLocal
async def test():
    async with AsyncSessionLocal() as db:
        print('Database connection successful')
asyncio.run(test())
"
```

## Deployment Process

### Phase 1: Backup and Preparation

#### Step 1.1: Stop Application Services

```bash
# Stop the FastAPI application
sudo systemctl stop marktplaats-search

# Verify application is stopped
sudo systemctl status marktplaats-search
```

#### Step 1.2: Create Database Backup

```bash
# Create timestamped backup
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp data/marktplaats_api.db "data/marktplaats_api_backup_${TIMESTAMP}.db"

# Verify backup integrity
sqlite3 "data/marktplaats_api_backup_${TIMESTAMP}.db" "PRAGMA integrity_check;"

# Store backup location for rollback
echo "BACKUP_PATH=data/marktplaats_api_backup_${TIMESTAMP}.db" > .migration_backup
```

#### Step 1.3: Pre-Migration Validation

```bash
# Test migration script in dry-run mode
python scripts/per_search_listing_migration.py --dry-run

# Verify no critical issues reported
# Check estimated migration time and resource usage
```

### Phase 2: Migration Execution

#### Step 2.1: Run Migration

```bash
# Execute migration with logging
python scripts/per_search_listing_migration.py 2>&1 | tee migration_${TIMESTAMP}.log

# Monitor migration progress
# Expected duration: 5-15 minutes depending on database size
```

#### Step 2.2: Verify Migration Success

```bash
# Check migration log for errors
grep -i error migration_${TIMESTAMP}.log

# Verify database integrity
sqlite3 data/marktplaats_api.db "PRAGMA integrity_check;"

# Check new schema is in place
sqlite3 data/marktplaats_api.db "
.schema listings
SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='listings';
"

# Verify constraint behavior
sqlite3 data/marktplaats_api.db "
SELECT sql FROM sqlite_master WHERE name='uq_listing_search_url';
"
```

### Phase 3: Application Update and Testing

#### Step 3.1: Deploy New Code

```bash
# Install updated dependencies if needed
uv sync

# Update application configuration if needed
# (No config changes required for this migration)

# Verify code deployment
python -c "
from marktplaats_search.models import Listing
print('New model imported successfully')
print(Listing.__table_args__)
"
```

#### Step 3.2: Start Application

```bash
# Start application services
sudo systemctl start marktplaats-search

# Check application status
sudo systemctl status marktplaats-search

# Monitor application logs for startup issues
sudo journalctl -u marktplaats-search -f --lines=50
```

#### Step 3.3: Functional Testing

```bash
# Test database connection
curl -X GET "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"user_identifier": "test_migration_user"}'

# Extract token from response and test search creation
TOKEN="your_test_token_here"

# Create test search
curl -X POST "http://localhost:8000/api/searches" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "test migration",
    "interval": 300,
    "limit": 10
  }'

# Verify search was created and scheduler is working
curl -X GET "http://localhost:8000/api/searches" \
  -H "Authorization: Bearer $TOKEN"
```

### Phase 4: Post-Deployment Validation

#### Step 4.1: Monitor Application Health

```bash
# Check API endpoints
curl -X GET "http://localhost:8000/api/listings/stats" \
  -H "Authorization: Bearer $TOKEN"

# Verify new endpoints work
curl -X GET "http://localhost:8000/api/listings/cross-search-duplicates" \
  -H "Authorization: Bearer $TOKEN"

# Check scheduler is running
curl -X GET "http://localhost:8000/api/searches" \
  -H "Authorization: Bearer $TOKEN"
```

#### Step 4.2: Performance Validation

```bash
# Check database performance
python -c "
import asyncio
import time
from marktplaats_search.database import AsyncSessionLocal
from marktplaats_search.models import Listing
from sqlalchemy.future import select

async def perf_test():
    start = time.time()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Listing).limit(100))
        listings = result.scalars().all()
    end = time.time()
    print(f'Query completed in {end-start:.3f}s, returned {len(listings)} results')

asyncio.run(perf_test())
"

# Monitor system resources
top -n 1 | head -20
df -h
```

#### Step 4.3: Data Integrity Verification

```bash
# Verify no duplicate (search_id, url) combinations exist
sqlite3 data/marktplaats_api.db "
SELECT search_id, url, COUNT(*) as count 
FROM listings 
GROUP BY search_id, url 
HAVING count > 1;
"
# Should return no results

# Check that cross-search duplicates are allowed
sqlite3 data/marktplaats_api.db "
SELECT url, COUNT(DISTINCT search_id) as search_count 
FROM listings 
GROUP BY url 
HAVING search_count > 1 
LIMIT 5;
"
# Should return results if successful

# Verify foreign key constraints
sqlite3 data/marktplaats_api.db "PRAGMA foreign_key_check;"
# Should return no results
```

### Phase 5: Cleanup and Documentation

#### Step 5.1: Clean Up Test Data

```bash
# Remove test user and searches if created
# (Optional - can be left for ongoing testing)
```

#### Step 5.2: Update Monitoring

```bash
# Update monitoring dashboards to include new metrics
# Add alerts for new functionality
# Update health check endpoints
```

#### Step 5.3: Document Deployment

```bash
# Record deployment details
echo "
Deployment completed: $(date)
Migration backup: $(cat .migration_backup)
Database size before: $(stat -f%z data/marktplaats_api_backup_${TIMESTAMP}.db 2>/dev/null || stat -c%s data/marktplaats_api_backup_${TIMESTAMP}.db)
Database size after: $(stat -f%z data/marktplaats_api.db 2>/dev/null || stat -c%s data/marktplaats_api.db)
Migration log: migration_${TIMESTAMP}.log
" >> deployment_history.txt
```

## Rollback Procedures

### Emergency Rollback (Database Issues)

If critical database issues are discovered:

```bash
# 1. Stop application immediately
sudo systemctl stop marktplaats-search

# 2. Restore from backup
source .migration_backup
cp "$BACKUP_PATH" data/marktplaats_api.db

# 3. Verify backup restoration
sqlite3 data/marktplaats_api.db "PRAGMA integrity_check;"

# 4. Restart application with old code
git checkout <previous-commit-hash>
uv sync
sudo systemctl start marktplaats-search

# 5. Verify functionality
curl -X GET "http://localhost:8000/api/searches" \
  -H "Authorization: Bearer $TOKEN"
```

### Planned Rollback (Code Issues)

If application-level issues are discovered but database is healthy:

```bash
# 1. Revert code changes only
git revert <migration-commit-hash>

# 2. Update models to use old schema
# Edit marktplaats_search/models.py to restore unique=True on url field

# 3. Deploy reverted version
uv sync
sudo systemctl restart marktplaats-search

# 4. Consider running reverse migration if needed
python scripts/reverse_migration.py  # If created
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: Migration script fails with "UNIQUE constraint failed"

**Solution:**
```bash
# Check for pre-existing duplicates
sqlite3 data/marktplaats_api.db "
SELECT search_id, url, COUNT(*) as count 
FROM listings 
GROUP BY search_id, url 
HAVING count > 1;
"

# Clean up duplicates before re-running migration
python scripts/cleanup_duplicates.py
```

#### Issue: Application fails to start after migration

**Solution:**
```bash
# Check application logs
sudo journalctl -u marktplaats-search -n 50

# Verify database schema
sqlite3 data/marktplaats_api.db ".schema listings"

# Check Python imports
python -c "from marktplaats_search.models import Listing; print('OK')"
```

#### Issue: Poor performance after migration

**Solution:**
```bash
# Run index optimization
python -c "
import asyncio
from marktplaats_search.listing_management import optimize_listing_queries
from marktplaats_search.database import AsyncSessionLocal

async def optimize():
    async with AsyncSessionLocal() as db:
        result = await optimize_listing_queries(db)
        print('Optimization result:', result)

asyncio.run(optimize())
"

# Check query execution plans
sqlite3 data/marktplaats_api.db "
EXPLAIN QUERY PLAN 
SELECT * FROM listings 
WHERE search_id = 'test-id' AND url = 'test-url';
"
```

#### Issue: Cross-search duplicates not showing

**Solution:**
```bash
# Verify data exists
sqlite3 data/marktplaats_api.db "
SELECT url, COUNT(DISTINCT search_id) 
FROM listings 
GROUP BY url 
HAVING COUNT(DISTINCT search_id) > 1 
LIMIT 5;
"

# Test API endpoint directly
curl -X GET "http://localhost:8000/api/listings/cross-search-duplicates" \
  -H "Authorization: Bearer $TOKEN"
```

## Success Criteria

Deployment is considered successful when:

- [ ] Migration completes without errors
- [ ] Database integrity check passes
- [ ] Application starts and responds to health checks
- [ ] Search functionality works correctly
- [ ] New API endpoints respond correctly
- [ ] Performance is within acceptable range (< 500ms for typical queries)
- [ ] No error rate increase in logs
- [ ] Cross-search duplicates are properly identified
- [ ] Per-search "new" flags work correctly

## Monitoring Post-Deployment

Monitor these metrics for the first 24-48 hours:

### Application Metrics
- Response times for search endpoints
- Error rates for listing operations
- Memory and CPU usage
- Database connection pool usage

### Business Metrics
- Search result completeness
- New listing notification accuracy
- User engagement with cross-search features
- Database growth rate

### Performance Metrics
- Query execution times
- Index usage statistics
- Disk I/O patterns
- Cache hit rates (if applicable)

## Support and Escalation

If issues arise during or after deployment:

1. **Immediate Issues**: Follow emergency rollback procedures
2. **Performance Issues**: Run optimization scripts and check indexes
3. **Data Issues**: Verify database integrity and constraints
4. **Application Issues**: Check logs and restart services if needed

For complex issues, gather:
- Migration logs
- Application logs
- Database query plans
- System resource usage
- Error reproductions steps

This comprehensive deployment guide ensures a safe, monitored rollout of the per-search listing management feature.
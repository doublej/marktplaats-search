# MarktplaatsSearch v2.0 Deployment Guide

This guide covers deploying the upgraded MarktplaatsSearch application with marktplaats-py library integration and per-search listing management.

## ✅ What's New in v2.0

### 🔄 Core Improvements
- **Marktplaats Library Integration**: Replaced brittle HTML scraping with the maintained `marktplaats-py` library
- **Per-Search Uniqueness**: Same listing can now appear in multiple searches (fixes "one listing in one search only" limitation)
- **Rich Data**: Enhanced listing data including seller info, categories, verified status, location details
- **Better Performance**: Optimized duplicate checking and rate limiting
- **Cross-Search Analysis**: New insights into listings appearing across multiple searches

### 📊 New Features
- **Enhanced API Endpoints**: Support for category filtering, seller type filtering, price ranges
- **Health Check Endpoint**: Real-time system status monitoring
- **Cross-Search Analysis**: Find listings appearing in multiple searches
- **Enhanced Frontend**: Three view modes (Standard, Enhanced, Cross-Search Analysis)
- **Comprehensive Monitoring**: System health indicators and performance metrics

## 🚀 Deployment Steps

### 1. Pre-Deployment Checklist

```bash
# Backup your current database
cp data/marktplaats_api.db data/marktplaats_api.db.backup.$(date +%Y%m%d_%H%M%S)

# Verify marktplaats-py library is available
uv run python -c "import marktplaats; print('Library available')"

# Run tests to verify functionality
uv run pytest tests/ -v

# Check code quality
ruff check . && ruff format . && mypy .
```

### 2. Database Migration

The application includes an automatic database migration script:

```bash
# Run migration (with backup)
uv run python scripts/marktplaats_library_migration.py

# Or dry-run first to see what changes will be made
uv run python scripts/marktplaats_library_migration.py --dry-run
```

**Migration adds these new fields:**
- `marktplaats_id` - Official Marktplaats listing ID
- `price_type` - Price type (FIXED, BID, etc.)
- `location_city`, `location_country`, etc. - Detailed location data
- `seller_id`, `seller_name`, `seller_is_verified` - Seller information
- `category_id` - Marktplaats category ID
- `attributes`, `extended_attributes` - Structured listing attributes
- Enhanced image fields with multiple sizes

### 3. Update Code References

The migration maintains backward compatibility, but you can gradually adopt new patterns:

#### Old Pattern (Still Works)
```python
# Using legacy fields
listing.source_listing_id  # Still works
listing.price_numeric     # Still works (price in cents)
listing.description_snippet  # Still works
```

#### New Pattern (Recommended)
```python
# Using marktplaats library fields
listing.marktplaats_id    # Official API ID
listing.price            # Float price from API
listing.description      # Full description
listing.seller_name      # Structured seller data
listing.category_id      # Marktplaats category
```

### 4. Switch to New Components

#### Scheduler
```python
# Replace old scheduler import
# from marktplaats_search import scheduler
from marktplaats_search import scheduler_new as scheduler
```

#### Client
```python
# Replace old client import
# from marktplaats_search.client import fetch_listings
from marktplaats_search.client_new import MarktplaatsClient

# New usage
client = MarktplaatsClient()
listings = await client.fetch_listings(query="iPhone")
```

#### API
```python
# Replace old API import
# from marktplaats_search import api
from marktplaats_search import api_new as api
```

### 5. Configuration Updates

Update your environment variables if needed:

```bash
# .env file
DATABASE_URL=sqlite+aiosqlite:///./data/marktplaats_api.db
API_HOST=0.0.0.0
API_PORT=8000

# Optional: Enable development features
DEV_MODE=true
CREATE_DEFAULT_USER=false

# Rate limiting (recommended)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60
```

### 6. Start the Application

```bash
# Install dependencies
uv sync

# Start the server
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🔧 New API Endpoints

### Enhanced Search Results
```bash
# Get enhanced listings with new fields
GET /api/searches/{search_id}/results
# Supports new filters:
# - category_id: Filter by Marktplaats category
# - seller_type: verified/unverified
# - min_price/max_price: Price range filtering
```

### Cross-Search Analysis
```bash
# Find listings appearing in multiple searches
GET /api/cross-search-analysis?min_searches=2&limit=50

# Response includes:
# - marktplaats_id, seller info, category data
# - Which searches found the listing
# - Time range analysis
```

### Health Check
```bash
# System health and metrics
GET /health

# Response includes:
# - Database status
# - Scheduler status
# - Marktplaats client status
# - System metrics (search/listing counts)
```

## 💻 Frontend Updates

The frontend now supports three view modes:

### 1. Standard View
- Original functionality maintained
- Backward compatible with existing workflows

### 2. Enhanced View
- Rich listing data display
- Seller verification badges
- Category information
- Location details with distance
- Multiple image sizes

### 3. Cross-Search Analysis
- Interactive analysis of duplicate listings
- Filter by minimum search appearances
- Detailed metadata comparison
- Search query correlation

### Access Views
Visit your application URL and use the view toggle buttons in the header:
- **Standard View**: Classic interface
- **Enhanced View**: Rich data display
- **Cross-Search Analysis**: Duplicate analysis

## 📊 Monitoring & Health

### Health Check Dashboard
The `/health` endpoint provides real-time system status:
- Green: All systems operational
- Yellow: Some systems degraded
- Red: System errors detected

### Performance Monitoring
- Rate limiting prevents API overuse
- Efficient duplicate detection using pre-loaded URL sets
- Database indexes for optimized queries
- Connection pooling for better performance

### Logging
Enhanced logging covers:
- Marktplaats API interactions
- Rate limiting events
- Database migration status
- Search execution performance
- Error tracking and recovery

## 🔍 Troubleshooting

### Migration Issues
```bash
# If migration fails, restore from backup
cp data/marktplaats_api.db.backup.TIMESTAMP data/marktplaats_api.db

# Re-run migration with more verbose output
uv run python scripts/marktplaats_library_migration.py --database ./data/marktplaats_api.db
```

### API Issues
```bash
# Test marktplaats library directly
uv run python -c "
from marktplaats import SearchQuery
query = SearchQuery(query='test', limit=1)
results = query.get_listings()
print(f'Found {len(results)} listings')
"
```

### Performance Issues
```bash
# Check database indexes
uv run python -c "
import sqlite3
conn = sqlite3.connect('data/marktplaats_api.db')
cursor = conn.cursor()
cursor.execute('PRAGMA index_list(listings)')
indexes = cursor.fetchall()
print('Indexes:', [idx[1] for idx in indexes])
"
```

## 📈 Performance Improvements

### Before (v1.0)
- ❌ HTML scraping with 450+ lines of fragile parsing
- ❌ Global uniqueness preventing cross-search duplicates
- ❌ No structured data (categories, seller info, etc.)
- ❌ Frequent parsing failures on HTML changes

### After (v2.0)
- ✅ Stable API integration with structured data
- ✅ Per-search uniqueness allowing cross-search analysis
- ✅ Rich metadata (seller verification, categories, locations)
- ✅ Rate limiting and connection pooling
- ✅ Optimized duplicate detection with O(1) lookups
- ✅ Comprehensive error handling and recovery

## 🔄 Rollback Plan

If issues occur, you can rollback:

```bash
# 1. Stop the application
pkill -f uvicorn

# 2. Restore database backup
cp data/marktplaats_api.db.backup.TIMESTAMP data/marktplaats_api.db

# 3. Switch back to old modules (temporarily)
# Edit imports in main.py:
# from marktplaats_search import scheduler  # Old version
# from marktplaats_search import api        # Old version

# 4. Restart application
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📚 Additional Resources

- [Marktplaats-py Documentation](https://github.com/jensjeflensje/marktplaats-py)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Project Architecture Documentation](./docs/PER_SEARCH_LISTING_ARCHITECTURE.md)

## 🎯 Success Metrics

After deployment, monitor these metrics:

- **Data Quality**: Higher percentage of listings with structured data
- **Reliability**: Reduced scraping failures and error rates
- **User Experience**: Enhanced search insights and cross-search analysis
- **Performance**: Faster duplicate detection and query responses
- **Maintenance**: Reduced need for HTML parsing updates

---

**Deployment Status: ✅ Ready for Production**

The v2.0 upgrade provides significant improvements in reliability, data quality, and user insights while maintaining full backward compatibility.

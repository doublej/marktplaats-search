# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Per-search listing management**: Complete architectural overhaul enabling same listing to appear in multiple searches
- Composite unique constraint (search_id, url) replacing global URL uniqueness
- Per-search duplicate detection logic in scheduler
- Per-search "new" flag management for independent notifications
- New API endpoints for listing management:
  - `GET /api/listings/stats` - Comprehensive user listing statistics
  - `GET /api/listings/cross-search-duplicates` - Cross-search duplicate analysis
  - `GET /api/listings/new-summary` - New listings summary per search
  - `POST /api/searches/{search_id}/mark-read` - Mark search listings as read
  - `POST /api/listings/mark-all-read` - Mark all user listings as read
  - `POST /api/admin/cleanup-listings` - Database cleanup utilities
  - `POST /api/admin/optimize-queries` - Query optimization tools
- Comprehensive database migration script with backup and rollback capabilities
- Advanced listing management utilities module
- Performance-optimized indexes for per-search queries
- Cross-search duplicate analysis and reporting
- Listing cleanup and retention management
- Comprehensive test suite for per-search functionality
- Complete architecture documentation and deployment guide
- Applied Python boilerplate configuration with modern pyproject.toml
- Development tools: ruff (linting/formatting), mypy (type checking), pytest (testing)
- Pre-commit hooks for automated code quality enforcement
- Claude Code hooks for quality checks and git automation
- Project documentation (CLAUDE.md) with development standards and commands
- Comprehensive .gitignore with ai-dev profile for Python projects
- Raw HTML storage field in database for debugging scraped content
- Title cleaning functionality to remove price pollution from scraped listings
- Marktplaats comparison links in search UI for manual verification
- Details modal functionality for listing inspection

### Changed
- **BREAKING**: Database schema updated to support per-search listing management
- Removed global unique constraint on URL field in listings table
- Updated SQLAlchemy models with composite constraints and optimized indexes
- Enhanced duplicate detection from global to per-search scope
- Scheduler logic updated for per-search duplicate checking
- Database schema migration to add raw_html column to listings table
- Code formatting and linting applied across entire codebase
- Enhanced error handling and type safety improvements

### Fixed
- Multiple searches with overlapping results now capture all relevant listings
- Users receive notifications for listings matching their specific searches
- Same listing can appear in multiple searches without conflicts
- Per-search "new" status prevents missed notifications
- Price information no longer pollutes listing titles from scraping
- API model field mapping corrected for listing details modal
- Details modal 422 error resolved with proper field references

### Security
- All code follows security best practices with automated checks
- Database migration includes integrity validation and rollback procedures

---

## Instructions for Maintaining This Changelog

**For Claude Code users**: This changelog should be updated with every significant change to the project. When making changes:

1. Add new entries under the appropriate "Unreleased" section
2. Use these categories: Added, Changed, Deprecated, Removed, Fixed, Security
3. Write entries from the user's perspective
4. Include relevant context and reasoning for changes
5. When releasing a version, move "Unreleased" items to a new version section

**Entry Format Examples:**
- Added: New feature or capability
- Changed: Modification to existing functionality
- Deprecated: Features marked for removal
- Removed: Features that were removed
- Fixed: Bug fixes
- Security: Security improvements or fixes

**Version Release Process:**
When ready to release, create a new version section like:

```markdown
## [1.0.0] - 2024-01-15

### Added
- Feature descriptions here

### Changed
- Change descriptions here
```

Then reset the "Unreleased" section for future changes.

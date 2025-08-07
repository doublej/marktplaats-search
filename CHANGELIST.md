# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Database schema migration to add raw_html column to listings table
- Code formatting and linting applied across entire codebase
- Enhanced error handling and type safety improvements

### Fixed
- Price information no longer pollutes listing titles from scraping
- API model field mapping corrected for listing details modal
- Details modal 422 error resolved with proper field references

### Security
- All code follows security best practices with automated checks

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

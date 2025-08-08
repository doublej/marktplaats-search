# MarktplaatsSearch

A Python application for monitoring Marktplaats.nl listings with automated search scheduling and web dashboard.

## Features

- **Automated Search Monitoring**: Schedule searches to run at regular intervals
- **Web Dashboard**: Modern React-based frontend for managing searches and viewing results
- **REST API**: Complete API for programmatic access
- **User Management**: Multi-user support with API tokens
- **Data Management**: Structured listing data with metadata extraction
- **CLI Tools**: Command-line utilities for administration

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync --dev
   ```

2. **Run the application:**
   ```bash
   python main.py
   ```

3. **Access the web interface:**
   Open http://localhost:8000 in your browser

## Development

See [CLAUDE.md](CLAUDE.md) for development instructions and project standards.

## Architecture

The application follows a layered architecture:

- **API Layer**: FastAPI-based REST endpoints
- **Service Layer**: Business logic and operations
- **Repository Layer**: Data access patterns
- **CLI Layer**: Command-line interfaces

This design eliminates code duplication and ensures consistency between different interfaces.

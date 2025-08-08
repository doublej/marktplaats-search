"""CLI interface for database management operations."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from ..services.database_service import DatabaseService


class DatabaseCLI:
    """Command-line interface for database management operations."""

    def __init__(self) -> None:
        """Initialize CLI with database service."""
        self.service = DatabaseService()

    def create_fresh_database(self, drop_existing: bool = False) -> dict[str, Any]:
        """Create a fresh database, optionally dropping existing tables.

        Args:
            drop_existing: Whether to drop existing tables first

        Returns:
            Dictionary with operation results
        """
        try:
            if drop_existing:
                self.service.drop_all_tables()

            self.service.create_all_tables()

            # Optimize the new database
            optimization_results = self.service.optimize_database()

            return {
                "success": True,
                "message": "Database created successfully",
                "tables_dropped": drop_existing,
                "optimization": optimization_results,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to create database: {e}",
            }

    def check_and_fix_database(self) -> dict[str, Any]:
        """Check database integrity and perform maintenance.

        Returns:
            Dictionary with check and fix results
        """
        try:
            # Verify integrity
            integrity_results = self.service.verify_database_integrity()

            # Optimize database
            optimization_results = self.service.optimize_database()

            # Get statistics
            statistics = asyncio.run(self.service.get_database_statistics())

            return {
                "success": True,
                "integrity": integrity_results,
                "optimization": optimization_results,
                "statistics": statistics,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Database check failed: {e}",
            }

    def backup_database(self, backup_path: Path | None = None) -> dict[str, Any]:
        """Create a database backup.

        Args:
            backup_path: Optional backup file path (auto-generated if None)

        Returns:
            Dictionary with backup results
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path("data/backups")
            backup_path = data_dir / f"database_backup_{timestamp}.db"

        return self.service.backup_database(backup_path)

    def restore_database(self, backup_path: Path) -> dict[str, Any]:
        """Restore database from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            Dictionary with restore results
        """
        return self.service.restore_database(backup_path)

    async def show_database_info(self) -> dict[str, Any]:
        """Show comprehensive database information.

        Returns:
            Dictionary with database information
        """
        try:
            # Get sync info
            table_info = self.service.get_table_info()
            integrity = self.service.verify_database_integrity()

            # Get async statistics
            statistics = await self.service.get_database_statistics()

            return {
                "success": True,
                "tables": table_info,
                "integrity": integrity,
                "statistics": statistics,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to get database info: {e}",
            }

    def format_database_info(self, info_data: dict[str, Any]) -> str:
        """Format database information for console output.

        Args:
            info_data: Dictionary from show_database_info method

        Returns:
            Formatted string for console output
        """
        if not info_data["success"]:
            return f"Error: {info_data['message']}"

        lines = []
        lines.append("=" * 50)
        lines.append("DATABASE INFORMATION")
        lines.append("=" * 50)

        # Integrity status
        integrity = info_data["integrity"]
        lines.append(f"Database Status: {integrity['status'].upper()}")
        lines.append(f"Integrity Check: {integrity['integrity_check']}")
        lines.append("")

        # Table information
        lines.append("TABLES:")
        for table_name, table_data in info_data["tables"].items():
            lines.append(f"  {table_name:<20} {table_data['row_count']:>8} rows")
        lines.append("")

        # Statistics
        stats = info_data["statistics"]
        lines.append("STATISTICS:")

        # User stats
        user_stats = stats["users"]
        lines.append(
            f"  Users:      {user_stats['total']:>6} total, {user_stats['active']:>6} active"
        )

        # Search stats
        search_stats = stats["searches"]
        lines.append(
            f"  Searches:   {search_stats['total']:>6} total, {search_stats['active']:>6} active"
        )

        # Listing stats
        listing_stats = stats["listings"]
        lines.append(
            f"  Listings:   {listing_stats['total']:>6} total, {listing_stats['new']:>6} new"
        )

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_backup_results(self, results: dict[str, Any]) -> str:
        """Format backup results for console output.

        Args:
            results: Results dictionary from backup operation

        Returns:
            Formatted string for console output
        """
        if results["success"]:
            lines = []
            lines.append("Database backup completed successfully!")
            lines.append(f"Backup saved to: {results['backup_path']}")
            lines.append(f"Original size: {results['original_size']:,} bytes")
            lines.append(f"Backup size:   {results['backup_size']:,} bytes")
            return "\n".join(lines)
        else:
            return f"Backup failed: {results['error']}"

    def format_check_results(self, results: dict[str, Any]) -> str:
        """Format database check results for console output.

        Args:
            results: Results dictionary from check operation

        Returns:
            Formatted string for console output
        """
        if not results["success"]:
            return f"Database check failed: {results['message']}"

        lines = []
        lines.append("=" * 50)
        lines.append("DATABASE CHECK AND MAINTENANCE")
        lines.append("=" * 50)

        # Integrity results
        integrity = results["integrity"]
        lines.append(f"Integrity Check: {integrity['integrity_check']}")
        lines.append(f"Database Status: {integrity['status'].upper()}")
        lines.append("")

        # Optimization results
        optimization = results["optimization"]
        lines.append("Maintenance Operations:")
        for operation, status in optimization.items():
            lines.append(f"  {operation.capitalize()}: {status}")
        lines.append("")

        # Statistics
        stats = results["statistics"]
        lines.append("Current Statistics:")

        user_stats = stats["users"]
        lines.append(f"  Users:      {user_stats['total']} total ({user_stats['active']} active)")

        search_stats = stats["searches"]
        lines.append(
            f"  Searches:   {search_stats['total']} total ({search_stats['active']} active)"
        )

        listing_stats = stats["listings"]
        lines.append(f"  Listings:   {listing_stats['total']} total ({listing_stats['new']} new)")

        lines.append("=" * 50)
        return "\n".join(lines)

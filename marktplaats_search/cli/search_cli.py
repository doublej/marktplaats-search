"""CLI interface for search management operations."""

from datetime import datetime
from pathlib import Path
from typing import Any

from ..services.search_management_service import SearchManagementService


class SearchCLI:
    """Command-line interface for search management operations."""

    def __init__(self) -> None:
        """Initialize CLI with search management service."""
        self.service = SearchManagementService()

    async def refresh_searches(
        self, backup_file: Path | None = None, user_id: str | None = None, dry_run: bool = False
    ) -> dict[str, Any]:
        """Refresh all searches by backing up, deleting, and recreating them.

        Args:
            backup_file: Path for backup file (auto-generated if None)
            user_id: Optional user ID filter (None for all users)
            dry_run: If True, show what would be done without making changes

        Returns:
            Dictionary with operation results
        """
        # Generate default backup file name if not provided
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path("data")
            suffix = f"_user_{user_id}" if user_id else ""
            backup_file = data_dir / f"searches_backup_{timestamp}{suffix}.json"

        if dry_run:
            return await self._dry_run_refresh(backup_file, user_id)
        else:
            return await self.service.refresh_searches(backup_file, user_id)

    async def _dry_run_refresh(
        self, backup_file: Path, user_id: str | None = None
    ) -> dict[str, Any]:
        """Perform dry run of refresh operation."""
        # Get current counts
        counts = await self.service.get_search_counts(user_id)

        return {
            "success": True,
            "message": "DRY RUN - No changes were made",
            "backup_file": str(backup_file),
            "would_delete_searches": counts["searches"],
            "would_delete_listings": counts["listings"],
            "would_recreate_searches": counts["searches"],
            "dry_run": True,
        }

    async def export_searches(
        self, backup_file: Path, user_id: str | None = None
    ) -> dict[str, Any]:
        """Export searches to backup file.

        Args:
            backup_file: Path to save backup file
            user_id: Optional user ID filter

        Returns:
            Dictionary with export results
        """
        searches_data = await self.service.export_searches_to_backup(backup_file, user_id)

        return {
            "success": True,
            "message": f"Exported {len(searches_data)} searches",
            "backup_file": str(backup_file),
            "exported_count": len(searches_data),
        }

    async def get_search_statistics(self, user_id: str | None = None) -> dict[str, Any]:
        """Get search and listing statistics.

        Args:
            user_id: Optional user ID filter

        Returns:
            Dictionary with statistics
        """
        counts = await self.service.get_search_counts(user_id)

        return {
            "success": True,
            "searches": counts["searches"],
            "listings": counts["listings"],
            "user_filter": user_id,
        }

    def format_refresh_results(self, results: dict[str, Any], verbose: bool = False) -> str:
        """Format refresh operation results for console output.

        Args:
            results: Results dictionary from refresh operation
            verbose: Whether to include detailed information

        Returns:
            Formatted string for console output
        """
        lines = []

        if results.get("dry_run"):
            lines.append("=" * 50)
            lines.append("DRY RUN RESULTS")
            lines.append("=" * 50)
            lines.append(f"Would backup searches to: {results['backup_file']}")
            lines.append(f"Would delete {results['would_delete_searches']} searches")
            lines.append(f"Would delete {results['would_delete_listings']} listings")
            lines.append(f"Would recreate {results['would_recreate_searches']} searches")
            lines.append("")
            lines.append("Run without --dry-run to execute the refresh.")
        else:
            lines.append("=" * 50)
            lines.append("REFRESH COMPLETE")
            lines.append("=" * 50)
            lines.append(f"Backup saved to: {results['backup_file']}")
            lines.append(f"Deleted {results['deleted_searches']} searches")
            lines.append(f"Deleted {results['deleted_listings']} listings")
            lines.append(f"Recreated {results['recreated_searches']} searches")

            if results.get("errors"):
                lines.append("")
                lines.append("Errors encountered:")
                for error in results["errors"]:
                    lines.append(f"  - {error}")

        lines.append("=" * 50)
        return "\n".join(lines)

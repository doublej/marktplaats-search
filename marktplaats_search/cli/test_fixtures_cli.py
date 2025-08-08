"""CLI interface for test fixtures management operations."""

from pathlib import Path
from typing import Any

from ..services.test_fixtures_service import TestFixturesService


class TestFixturesCLI:
    """Command-line interface for test fixtures management operations."""

    def __init__(self, project_root: Path | None = None):
        """Initialize CLI with test fixtures service."""
        self.service = TestFixturesService(project_root)

    def show_fixtures_status(self) -> dict[str, Any]:
        """Show current status of test fixtures.

        Returns:
            Dictionary with fixtures status information
        """
        return self.service.get_fixtures_status()

    def validate_fixtures(self) -> dict[str, Any]:
        """Validate test fixtures structure and imports.

        Returns:
            Dictionary with validation results
        """
        return self.service.validate_fixtures_structure()

    def export_fixtures(self, output_path: Path | None = None) -> dict[str, Any]:
        """Export test fixtures to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            Dictionary with export results
        """
        return self.service.export_test_fixtures_json(output_path)

    def create_test_data_preview(self) -> dict[str, Any]:
        """Create preview of test data that will be generated.

        Returns:
            Dictionary with sample test data
        """
        try:
            search_scenarios = self.service.create_multiple_search_scenarios(3)
            listing_variations = self.service.create_listing_variations(3)

            return {
                "success": True,
                "preview": {
                    "search_scenarios": search_scenarios,
                    "listing_variations": listing_variations,
                },
                "counts": {
                    "search_scenarios": len(search_scenarios),
                    "listing_variations": len(listing_variations),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"Preview generation failed: {e}"}

    def format_fixtures_status(self, status_data: dict[str, Any]) -> str:
        """Format fixtures status for console output.

        Args:
            status_data: Status data from show_fixtures_status method

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("=== TEST FIXTURES STATUS ===")
        lines.append("")

        # Basic info
        lines.append(f"Fixtures Directory: {status_data['fixtures_dir']}")
        lines.append(f"Directory Exists: {'✅' if status_data['fixtures_exist'] else '❌'}")
        lines.append("")

        # Validation results
        validation = status_data["validation"]
        lines.append("VALIDATION RESULTS:")
        lines.append(f"Overall Status: {'✅ PASSED' if validation['success'] else '❌ FAILED'}")

        if validation["missing_files"]:
            lines.append(f"Missing Files: {len(validation['missing_files'])}")
            for file_name in validation["missing_files"]:
                lines.append(f"  ❌ {file_name}")

        if validation["structure_issues"]:
            lines.append(f"Structure Issues: {len(validation['structure_issues'])}")
            for issue in validation["structure_issues"]:
                lines.append(f"  ⚠️  {issue}")

        lines.append(f"Files Checked: {len(validation['files_checked'])}")
        lines.append("")

        # File statistics
        if status_data["file_stats"]:
            lines.append("FILE STATISTICS:")
            for file_name, stats in status_data["file_stats"].items():
                if "error" in stats:
                    lines.append(f"  ❌ {file_name}: {stats['error']}")
                else:
                    lines.append(f"  📄 {file_name}: {stats['lines']} lines, {stats['size']} bytes")

        lines.append("=" * 30)
        return "\\n".join(lines)

    def format_validation_results(self, validation_data: dict[str, Any]) -> str:
        """Format validation results for console output.

        Args:
            validation_data: Validation data from validate_fixtures method

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("=== FIXTURES VALIDATION ===")
        lines.append("")

        if validation_data["success"]:
            lines.append("✅ All fixtures validation passed!")
        else:
            lines.append("❌ Fixtures validation failed!")

        lines.append("")
        lines.append(f"Files Checked: {len(validation_data['files_checked'])}")

        if validation_data["missing_files"]:
            lines.append("")
            lines.append("MISSING FILES:")
            for file_name in validation_data["missing_files"]:
                lines.append(f"  ❌ {file_name}")

        if validation_data["structure_issues"]:
            lines.append("")
            lines.append("STRUCTURE ISSUES:")
            for issue in validation_data["structure_issues"]:
                lines.append(f"  ⚠️  {issue}")

        if not validation_data["missing_files"] and not validation_data["structure_issues"]:
            lines.append("")
            lines.append("🎉 No issues found!")

        lines.append("=" * 30)
        return "\\n".join(lines)

    def format_export_results(self, export_data: dict[str, Any]) -> str:
        """Format export results for console output.

        Args:
            export_data: Export data from export_fixtures method

        Returns:
            Formatted string for console output
        """
        if not export_data["success"]:
            return f"❌ Export failed: {export_data['error']}"

        lines = []
        lines.append("✅ Test fixtures exported successfully!")
        lines.append("")
        lines.append(f"Output File: {export_data['output_path']}")
        lines.append(f"Fixtures Count: {export_data['fixtures_count']}")
        lines.append("")
        lines.append("The exported JSON file contains:")
        lines.append("  • All test constants and configuration")
        lines.append("  • Mock API response templates")
        lines.append("  • Generated test scenarios")
        lines.append("  • Sample test data variations")

        return "\\n".join(lines)

    def format_test_data_preview(self, preview_data: dict[str, Any]) -> str:
        """Format test data preview for console output.

        Args:
            preview_data: Preview data from create_test_data_preview method

        Returns:
            Formatted string for console output
        """
        if not preview_data["success"]:
            return f"❌ Preview generation failed: {preview_data['error']}"

        lines = []
        lines.append("=== TEST DATA PREVIEW ===")
        lines.append("")

        counts = preview_data["counts"]
        lines.append(f"Search Scenarios: {counts['search_scenarios']}")
        lines.append(f"Listing Variations: {counts['listing_variations']}")
        lines.append("")

        # Show sample search scenario
        if preview_data["preview"]["search_scenarios"]:
            lines.append("SAMPLE SEARCH SCENARIO:")
            sample_search = preview_data["preview"]["search_scenarios"][0]
            lines.append(f"  Query: {sample_search['query']}")
            lines.append(f"  Location: {sample_search['zip_code']}")
            lines.append(
                f"  Price Range: €{sample_search['price_from']} - €{sample_search['price_to']}"
            )
            lines.append(f"  Distance: {sample_search['distance']}m")
            lines.append("")

        # Show sample listing variation
        if preview_data["preview"]["listing_variations"]:
            lines.append("SAMPLE LISTING VARIATION:")
            sample_listing = preview_data["preview"]["listing_variations"][0]
            lines.append(f"  Title: {sample_listing['title']}")
            lines.append(f"  Price: {sample_listing['price']}")
            lines.append(f"  Condition: {sample_listing['condition']}")
            lines.append(f"  New Item: {sample_listing['is_new']}")

        lines.append("=" * 30)
        return "\\n".join(lines)

    def show_fixtures_help(self) -> str:
        """Show help information for test fixtures management.

        Returns:
            Help text for console output
        """
        return """
🧪 TEST FIXTURES MANAGEMENT HELP

The test fixtures system centralizes all test data, mock objects, and test
utilities to eliminate duplication and provide consistent testing patterns.

WHAT IT PROVIDES:
  • Centralized test constants and configuration
  • Reusable mock data for external services (Marktplaats API)
  • Test data templates with variations
  • API test clients with authentication
  • Database test helpers with cleanup
  • Error response templates for testing edge cases

FIXTURES STRUCTURE:
  tests/fixtures/
  ├── __init__.py           # Package initialization
  ├── constants.py          # Test constants and templates
  ├── mock_data.py         # Mock objects and factories
  └── test_helpers.py      # Test utilities and clients

KEY FEATURES:
  • MockFactory for creating test data variations
  • APITestClient for authenticated API testing
  • DatabaseTestHelper for complex test scenarios
  • Centralized error response templates
  • Consistent test data patterns

USAGE IN TESTS:
  from tests.fixtures.constants import SEARCH_DATA_TEMPLATE
  from tests.fixtures.mock_data import MockFactory
  from tests.fixtures.test_helpers import APITestClient

  # Create test data with variations
  search_data = MockFactory.create_search_data(query="custom query")

  # Use authenticated API client
  async with APITestClient() as client:
      await client.create_user()
      response = await client.create_search(search_data)

BEST PRACTICES:
  • Use MockFactory for generating test data with variations
  • Reuse fixtures across multiple test modules
  • Validate fixtures structure before running tests
  • Export fixtures to JSON for external testing tools
  • Keep fixtures updated when models change
        """.strip()

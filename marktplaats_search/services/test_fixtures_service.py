"""Test Fixtures Management Service

Service for managing test fixtures, mock data, and test utilities.
Provides centralized access to test data and mock objects.
"""

import json
from pathlib import Path
from typing import Any


class TestFixturesService:
    """Service for managing centralized test fixtures and mock data."""

    def __init__(self, project_root: Path | None = None):
        """Initialize service with project root path."""
        self.project_root = project_root or Path.cwd()
        self.fixtures_dir = self.project_root / "tests" / "fixtures"

    def get_test_constants(self) -> dict[str, Any]:
        """Get all test constants and configuration values.

        Returns:
            Dictionary with all test constants
        """
        try:
            # Import constants dynamically to avoid import issues
            import sys

            fixtures_path = str(self.fixtures_dir)
            if fixtures_path not in sys.path:
                sys.path.insert(0, fixtures_path)

            from tests.fixtures.constants import (
                API_ERROR_RESPONSES,
                API_TIMEOUT,
                BASE_URL,
                LISTING_DATA_TEMPLATE,
                MOCK_LISTING_RESPONSE,
                MOCK_SEARCH_RESPONSE,
                MOCK_USER_RESPONSE,
                SEARCH_DATA_TEMPLATE,
                SEARCH_UPDATE_TEMPLATE,
                TEST_DATABASE_URL,
                TEST_DISTANCES,
                TEST_PRICES,
                TEST_QUERIES,
                TEST_USERNAME,
                TEST_ZIP_CODES,
                USER_DATA_TEMPLATE,
            )

            return {
                "api": {
                    "base_url": BASE_URL,
                    "test_username": TEST_USERNAME,
                    "timeout": API_TIMEOUT,
                },
                "templates": {
                    "search_data": SEARCH_DATA_TEMPLATE,
                    "search_update": SEARCH_UPDATE_TEMPLATE,
                    "listing_data": LISTING_DATA_TEMPLATE,
                    "user_data": USER_DATA_TEMPLATE,
                },
                "mock_responses": {
                    "user": MOCK_USER_RESPONSE,
                    "search": MOCK_SEARCH_RESPONSE,
                    "listing": MOCK_LISTING_RESPONSE,
                },
                "test_data": {
                    "zip_codes": TEST_ZIP_CODES,
                    "queries": TEST_QUERIES,
                    "prices": TEST_PRICES,
                    "distances": TEST_DISTANCES,
                },
                "error_responses": API_ERROR_RESPONSES,
                "database_url": TEST_DATABASE_URL,
            }
        except ImportError as e:
            return {"error": f"Failed to load test constants: {e}"}

    def create_test_search_data(self, **overrides: Any) -> dict[str, Any]:
        """Create test search data with optional overrides.

        Args:
            **overrides: Fields to override in the default template

        Returns:
            Dictionary with search data
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        template = constants["templates"]["search_data"].copy()
        template.update(overrides)
        return template

    def create_test_listing_data(self, **overrides: Any) -> dict[str, Any]:
        """Create test listing data with optional overrides.

        Args:
            **overrides: Fields to override in the default template

        Returns:
            Dictionary with listing data
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        template = constants["templates"]["listing_data"].copy()
        template.update(overrides)
        return template

    def create_test_user_data(self, **overrides: Any) -> dict[str, Any]:
        """Create test user data with optional overrides.

        Args:
            **overrides: Fields to override in the default template

        Returns:
            Dictionary with user data
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        template = constants["templates"]["user_data"].copy()
        template.update(overrides)
        return template

    def get_mock_api_response(self, response_type: str) -> dict[str, Any]:
        """Get mock API response by type.

        Args:
            response_type: Type of response ('user', 'search', 'listing')

        Returns:
            Dictionary with mock response data
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        return constants["mock_responses"].get(response_type, {})

    def get_error_response(self, error_type: str) -> dict[str, Any]:
        """Get mock error response by type.

        Args:
            error_type: Type of error ('auth_failed', 'not_found', etc.)

        Returns:
            Dictionary with error response data
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        return constants["error_responses"].get(error_type, {})

    def create_multiple_search_scenarios(self, count: int = 3) -> list[dict[str, Any]]:
        """Create multiple search scenarios with variations.

        Args:
            count: Number of scenarios to create

        Returns:
            List of search data dictionaries
        """
        constants = self.get_test_constants()
        if "error" in constants:
            raise RuntimeError(constants["error"])

        scenarios = []
        test_data = constants["test_data"]

        for i in range(count):
            scenario = self.create_test_search_data(
                query=test_data["queries"][i % len(test_data["queries"])],
                zip_code=test_data["zip_codes"][i % len(test_data["zip_codes"])],
                distance=test_data["distances"][i % len(test_data["distances"])],
                price_from=test_data["prices"][i % len(test_data["prices"])][0],
                price_to=test_data["prices"][i % len(test_data["prices"])][1],
                interval=300 + (i * 300),  # Vary intervals
            )
            scenarios.append(scenario)

        return scenarios

    def create_listing_variations(self, count: int = 5) -> list[dict[str, Any]]:
        """Create multiple listing variations.

        Args:
            count: Number of listings to create

        Returns:
            List of listing data dictionaries
        """
        listings = []
        for i in range(count):
            listing = self.create_test_listing_data(
                title=f"Test Product {i + 1}",
                url=f"https://www.marktplaats.nl/listing/test{i + 1:03d}",
                price_numeric=(i + 1) * 10000,
                price=f"€ {(i + 1) * 100},00",
                is_new=i % 2 == 0,  # Alternate new/existing
                condition="new" if i % 2 == 0 else "used",
            )
            listings.append(listing)

        return listings

    def export_test_fixtures_json(self, output_path: Path | None = None) -> dict[str, Any]:
        """Export all test fixtures to JSON file.

        Args:
            output_path: Path to output JSON file

        Returns:
            Dictionary with export results
        """
        if not output_path:
            output_path = self.fixtures_dir / "exported_fixtures.json"

        try:
            constants = self.get_test_constants()
            if "error" in constants:
                return {"success": False, "error": constants["error"]}

            # Add generated scenarios
            search_scenarios = self.create_multiple_search_scenarios(5)
            listing_variations = self.create_listing_variations(10)
            fixtures_data: dict[str, Any] = {
                "constants": constants,
                "scenarios": {
                    "search_scenarios": search_scenarios,
                    "listing_variations": listing_variations,
                },
                "generated_at": str(Path(__file__).stat().st_mtime),
            }

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fixtures_data, f, indent=2, ensure_ascii=False)

            return {
                "success": True,
                "output_path": str(output_path),
                "fixtures_count": len(search_scenarios) + len(listing_variations),
            }

        except Exception as e:
            return {"success": False, "error": f"Export failed: {e}"}

    def validate_fixtures_structure(self) -> dict[str, Any]:
        """Validate that all fixture files are properly structured.

        Returns:
            Dictionary with validation results
        """
        results: dict[str, Any] = {
            "success": True,
            "files_checked": [],
            "missing_files": [],
            "structure_issues": [],
        }

        # Check required fixture files
        required_files = [
            "constants.py",
            "mock_data.py",
            "test_helpers.py",
            "__init__.py",
        ]

        for file_name in required_files:
            file_path = self.fixtures_dir / file_name
            results["files_checked"].append(file_name)

            if not file_path.exists():
                results["missing_files"].append(file_name)
                results["success"] = False
            else:
                # Basic structure validation
                try:
                    content = file_path.read_text(encoding="utf-8")
                    if len(content.strip()) == 0:
                        results["structure_issues"].append(f"{file_name}: Empty file")
                        results["success"] = False
                    elif file_name.endswith(".py") and "import" not in content:
                        results["structure_issues"].append(f"{file_name}: No imports found")

                except Exception as e:
                    results["structure_issues"].append(f"{file_name}: Read error - {e}")
                    results["success"] = False

        # Try to import constants
        try:
            constants = self.get_test_constants()
            if "error" in constants:
                results["structure_issues"].append(f"Constants import failed: {constants['error']}")
                results["success"] = False
        except Exception as e:
            results["structure_issues"].append(f"Constants validation failed: {e}")
            results["success"] = False

        return results

    def get_fixtures_status(self) -> dict[str, Any]:
        """Get current status of test fixtures system.

        Returns:
            Dictionary with fixtures status information
        """
        validation = self.validate_fixtures_structure()

        status: dict[str, Any] = {
            "fixtures_dir": str(self.fixtures_dir),
            "fixtures_exist": self.fixtures_dir.exists(),
            "validation": validation,
            "file_stats": {},
        }

        if self.fixtures_dir.exists():
            fixture_files = list(self.fixtures_dir.glob("*.py"))
            for file_path in fixture_files:
                try:
                    stat = file_path.stat()
                    status["file_stats"][file_path.name] = {
                        "size": stat.st_size,
                        "lines": len(file_path.read_text().splitlines()),
                        "modified": str(stat.st_mtime),
                    }
                except Exception as e:
                    status["file_stats"][file_path.name] = {"error": str(e)}

        return status

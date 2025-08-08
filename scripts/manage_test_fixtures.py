#!/usr/bin/env python3
"""
Manage Test Fixtures

This script manages the centralized test fixtures system,
validates fixture structure, and exports test data.

Usage:
    python scripts/manage_test_fixtures.py [--status] [--validate] [--export] [--preview] [--help-fixtures]

Options:
    --status: Show test fixtures system status
    --validate: Validate fixtures structure and imports
    --export: Export all fixtures to JSON file
    --preview: Show preview of generated test data
    --help-fixtures: Show detailed help about fixtures system
    --output: Output path for export (default: tests/fixtures/exported_fixtures.json)
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.test_fixtures_cli import TestFixturesCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Manage centralized test fixtures system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show test fixtures system status",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate fixtures structure and imports",
    )

    parser.add_argument(
        "--export",
        action="store_true",
        help="Export all fixtures to JSON file",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show preview of generated test data",
    )

    parser.add_argument(
        "--help-fixtures",
        action="store_true",
        help="Show detailed help about fixtures system",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output path for export (default: tests/fixtures/exported_fixtures.json)",
    )

    args = parser.parse_args()

    try:
        cli = TestFixturesCLI(project_root)

        # Show help if requested
        if args.help_fixtures:
            print(cli.show_fixtures_help())
            return

        # Default to status if no specific action
        if not any([args.status, args.validate, args.export, args.preview]):
            args.status = True

        print("🧪 Test Fixtures Management")
        print("=" * 50)

        # Show fixtures status
        if args.status:
            print("📊 Fixtures System Status:")
            status_result = cli.show_fixtures_status()
            print(cli.format_fixtures_status(status_result))
            print()

        # Validate fixtures
        if args.validate:
            print("🔍 Validating Fixtures Structure:")
            validation_result = cli.validate_fixtures()
            print(cli.format_validation_results(validation_result))
            print()

            if not validation_result["success"]:
                print("⚠️  Validation failed. Please fix issues before using fixtures.")
                return

        # Show test data preview
        if args.preview:
            print("👀 Test Data Preview:")
            preview_result = cli.create_test_data_preview()
            print(cli.format_test_data_preview(preview_result))
            print()

        # Export fixtures
        if args.export:
            print("📤 Exporting Test Fixtures:")
            export_result = cli.export_fixtures(args.output)
            print(cli.format_export_results(export_result))
            print()

            if not export_result["success"]:
                print("❌ Export failed. Check error details above.")
                sys.exit(1)

        print("🎉 Test fixtures management completed successfully!")

        # Show next steps
        print()
        print("📋 NEXT STEPS:")
        if not args.validate:
            print("   1. Run: python scripts/manage_test_fixtures.py --validate")
        if not args.export:
            print("   2. Run: python scripts/manage_test_fixtures.py --export")
        print("   3. Update existing tests to use centralized fixtures")
        print("   4. Run test suite to verify everything works")
        print()
        print("💡 TIP: Use --help-fixtures for detailed usage information")

    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Make sure you're in the project directory and dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during fixtures management: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

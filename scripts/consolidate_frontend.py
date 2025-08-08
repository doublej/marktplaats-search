#!/usr/bin/env python3
"""
Consolidate Frontend Assets

This script consolidates all frontend assets into a unified structure,
removes duplicates, and sets up a proper build system.

Usage:
    python scripts/consolidate_frontend.py [--build] [--clean] [--status] [--help-consolidation]

Options:
    --build: Build assets after consolidation
    --clean: Clean build artifacts before consolidation
    --status: Show build status after consolidation
    --help-consolidation: Show detailed help about consolidation
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.frontend_cli import FrontendCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Consolidate frontend assets into unified structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--build",
        action="store_true",
        help="Build assets after consolidation",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build artifacts before consolidation",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Show build status after consolidation",
    )

    parser.add_argument(
        "--help-consolidation",
        action="store_true",
        help="Show detailed help about consolidation process",
    )

    args = parser.parse_args()

    try:
        cli = FrontendCLI(project_root)

        # Show help if requested
        if args.help_consolidation:
            print(cli.show_consolidation_help())
            return

        print("🎨 Starting frontend asset consolidation...")
        print()

        # Clean build artifacts if requested
        if args.clean:
            print("🧹 Cleaning build artifacts...")
            cleanup_result = cli.clean_build()
            print(cli.format_cleanup_results(cleanup_result))
            print()

        # Perform consolidation
        print("📦 Consolidating frontend assets...")
        consolidation_result = cli.consolidate_assets()
        print(cli.format_consolidation_results(consolidation_result))
        print()

        if not consolidation_result["success"]:
            sys.exit(1)

        # Build assets if requested
        if args.build:
            print("🔨 Building frontend assets...")
            build_result = cli.build_assets()
            print(cli.format_build_results(build_result))
            print()

            if not build_result["success"]:
                sys.exit(1)

        # Show status if requested
        if args.status:
            print("📊 Build Status:")
            status_result = cli.show_build_status()
            print(cli.format_build_status(status_result))
            print()

        print("🎉 Frontend consolidation completed successfully!")
        print()

        # Show next steps
        print("📋 NEXT STEPS:")
        if not args.build:
            print("   1. Run: python scripts/consolidate_frontend.py --build")
            print("   2. Test the consolidated frontend")
        else:
            print("   1. Test the consolidated frontend")
            print("   2. Update API server to use consolidated assets")

        print("   3. Remove any remaining duplicate files")
        print()
        print("🔄 To rebuild assets after changes:")
        print(f"   python {project_root / 'frontend' / 'build.py'}")

    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Make sure you're in the project directory and dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during consolidation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

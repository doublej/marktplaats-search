#!/usr/bin/env python3
"""
Export OpenAPI Schema

This script exports the OpenAPI schema from the FastAPI application for frontend code generation.

Usage:
    python scripts/export_openapi_schema.py [--output path] [--format json|yaml] [--validate] [--preview-types]

Options:
    --output: Output file path (default: frontend/schema/openapi.json)
    --format: Export format - json or yaml (default: json)
    --validate: Validate schema before export
    --preview-types: Show TypeScript types preview
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.openapi_cli import OpenAPICLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Export OpenAPI schema for frontend code generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output file path (default: frontend/schema/openapi.json)",
    )

    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Export format (default: json)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate schema before export",
    )

    parser.add_argument(
        "--preview-types",
        action="store_true",
        help="Show TypeScript types preview",
    )

    parser.add_argument(
        "--info-only",
        action="store_true",
        help="Show schema information without exporting",
    )

    args = parser.parse_args()

    try:
        # Import the FastAPI app (this will initialize the full application)
        from marktplaats_search.api import app

        cli = OpenAPICLI(app)

        # Show schema information
        if args.info_only:
            info_result = cli.show_schema_info()
            print(cli.format_schema_info(info_result))
            return

        # Validate schema if requested
        if args.validate:
            print("Validating OpenAPI schema...")
            validation_result = cli.validate_schema()
            print(cli.format_validation_results(validation_result))

            if not validation_result["valid"]:
                print("\n❌ Schema validation failed. Fix issues before exporting.")
                sys.exit(1)
            print()

        # Show TypeScript preview if requested
        if args.preview_types:
            print("Generating TypeScript types preview...")
            preview_result = cli.preview_typescript_types()
            print(cli.format_typescript_preview(preview_result))
            print()

        # Set default output path if not provided
        if not args.output:
            args.output = project_root / "frontend" / "schema" / f"openapi.{args.format}"

        # Export schema
        print(f"Exporting OpenAPI schema to {args.output}...")
        export_result = cli.export_schema(args.output, args.format)

        if export_result["success"]:
            print(cli.format_export_results(export_result))
            print("\n🎉 Schema exported successfully!")
            print("Next steps:")
            print("  1. Use this schema to generate frontend API client")
            print("  2. Generate TypeScript types from the schema")
            print("  3. Update frontend code to use generated types")
        else:
            print(f"❌ Export failed: {export_result['error']}")
            sys.exit(1)

    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        print("Make sure you're in the project directory and dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during schema export: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

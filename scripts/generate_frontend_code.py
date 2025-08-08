#!/usr/bin/env python3
"""
Generate Frontend Code

This script generates TypeScript types and API client code from the OpenAPI schema,
eliminating manual duplication between frontend and backend.

Usage:
    python scripts/generate_frontend_code.py [--output path] [--clean] [--validate] [--help-integration]

Options:
    --output: Output directory for generated code (default: frontend/src/generated)
    --clean: Clean output directory before generation
    --validate: Validate generated code after creation
    --help-integration: Show integration help after generation
    --client-name: Name for the generated client class (default: ApiClient)
"""

import argparse
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.cli.codegen_cli import CodegenCLI


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate TypeScript types and API client from OpenAPI schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for generated code (default: frontend/src/generated)",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean output directory before generation",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated code after creation",
    )

    parser.add_argument(
        "--help-integration",
        action="store_true",
        help="Show integration help after generation",
    )

    parser.add_argument(
        "--client-name",
        default="ApiClient",
        help="Name for the generated client class (default: ApiClient)",
    )

    parser.add_argument(
        "--schema-path",
        type=Path,
        help="Path to OpenAPI schema file (will generate if not provided)",
    )

    parser.add_argument(
        "--show-help",
        action="store_true",
        help="Show detailed help about code generation",
    )

    args = parser.parse_args()

    try:
        # Import the FastAPI app for schema generation
        from marktplaats_search.api import app

        cli = CodegenCLI(app)

        # Show help if requested
        if args.show_help:
            print(cli.show_generation_help())
            return

        # Set default output directory
        if not args.output:
            args.output = project_root / "frontend" / "src" / "generated"

        print("🔧 Generating frontend code...")
        print(f"Output directory: {args.output}")
        print(f"Client name: {args.client_name}")
        print()

        # Clean output directory if requested
        if args.clean and args.output.exists():
            print("🧹 Cleaning output directory...")
            cleanup_result = cli.clean_generated_code(args.output)
            if cleanup_result["success"]:
                print(cli.format_cleanup_results(cleanup_result))
            else:
                print(f"❌ Cleanup failed: {cleanup_result['error']}")
                sys.exit(1)
            print()

        # Generate API client (this includes TypeScript types)
        print("🏗️  Generating TypeScript API client and types...")
        generation_result = cli.generate_client(
            output_dir=args.output, schema_path=args.schema_path, client_name=args.client_name
        )

        print(cli.format_generation_results(generation_result))

        if not generation_result["success"]:
            sys.exit(1)

        print()

        # Validate generated code if requested
        if args.validate:
            print("🔍 Validating generated code...")
            validation_result = cli.validate_generated_code(args.output)
            print(cli.format_validation_results(validation_result))

            if not validation_result["success"]:
                print("⚠️  Validation issues found, but generation completed.")

            print()

        # Show integration help if requested
        if args.help_integration:
            print(cli.show_next_steps(args.output))
            print()

        print("🎉 Frontend code generation completed!")
        print()
        print("📋 SUMMARY:")
        print(f"   Generated files: {generation_result.get('files_count', 'N/A')}")
        print(f"   Output directory: {args.output}")
        print(f"   API Client: {args.client_name}")
        print()
        print("🔄 To regenerate after API changes:")
        print(f"   python scripts/generate_frontend_code.py --clean --output {args.output}")

    except ImportError as e:
        print(f"❌ Failed to import FastAPI app: {e}")
        print("Make sure you're in the project directory and dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during code generation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

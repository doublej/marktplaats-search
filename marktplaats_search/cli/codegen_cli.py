"""CLI interface for code generation operations."""

from pathlib import Path
from typing import Any

from ..services.codegen_service import CodegenService


class CodegenCLI:
    """Command-line interface for code generation operations."""

    def __init__(self, app: Any = None) -> None:
        """Initialize CLI with optional FastAPI app instance."""
        self.app = app
        self.service = CodegenService(app)

    def generate_types(self, output_dir: Path, schema_path: Path | None = None) -> dict[str, Any]:
        """Generate TypeScript types.

        Args:
            output_dir: Directory to output generated types
            schema_path: Optional path to OpenAPI schema file

        Returns:
            Dictionary with generation results
        """
        return self.service.generate_typescript_types(output_dir, schema_path)

    def generate_client(
        self, output_dir: Path, schema_path: Path | None = None, client_name: str = "ApiClient"
    ) -> dict[str, Any]:
        """Generate API client.

        Args:
            output_dir: Directory to output generated client
            schema_path: Optional path to OpenAPI schema file
            client_name: Name for the generated client class

        Returns:
            Dictionary with generation results
        """
        return self.service.generate_api_client(output_dir, schema_path, client_name)

    def validate_generated_code(self, output_dir: Path) -> dict[str, Any]:
        """Validate generated code.

        Args:
            output_dir: Directory containing generated code

        Returns:
            Dictionary with validation results
        """
        return self.service.validate_generated_code(output_dir)

    def clean_generated_code(self, output_dir: Path) -> dict[str, Any]:
        """Clean generated code directory.

        Args:
            output_dir: Directory to clean

        Returns:
            Dictionary with cleanup results
        """
        return self.service.clean_generated_code(output_dir)

    def format_generation_results(self, results: dict[str, Any]) -> str:
        """Format generation results for console output.

        Args:
            results: Results dictionary from generation methods

        Returns:
            Formatted string for console output
        """
        if results["success"]:
            lines = []
            lines.append("✅ Code generation completed successfully!")
            lines.append(f"Output directory: {results['output_dir']}")

            if "files_count" in results:
                lines.append(f"Generated files: {results['files_count']}")

            if "generated_files" in results:
                lines.append("")
                lines.append("Generated files:")
                for file_path in results["generated_files"][:10]:  # Show first 10
                    lines.append(f"  - {file_path}")

                if len(results["generated_files"]) > 10:
                    remaining = len(results["generated_files"]) - 10
                    lines.append(f"  ... and {remaining} more files")

            if "client_file" in results:
                lines.append(f"API Client: {results['client_file']}")

            lines.append("")
            lines.append(results.get("message", "Generation completed"))

            return "\n".join(lines)
        else:
            lines = []
            lines.append("❌ Code generation failed!")
            lines.append(f"Error: {results['error']}")

            if "stdout" in results and results["stdout"]:
                lines.append("")
                lines.append("Additional output:")
                lines.append(results["stdout"])

            return "\n".join(lines)

    def format_validation_results(self, results: dict[str, Any]) -> str:
        """Format validation results for console output.

        Args:
            results: Results dictionary from validation method

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("=" * 50)
        lines.append("CODE VALIDATION RESULTS")
        lines.append("=" * 50)

        if results["success"]:
            lines.append("✅ Generated code validation passed!")
        else:
            lines.append("❌ Generated code has issues:")

            if "issues" in results:
                for issue in results["issues"]:
                    lines.append(f"  ERROR: {issue}")

        if "warnings" in results and results["warnings"]:
            lines.append("")
            lines.append("⚠️  Warnings:")
            for warning in results["warnings"]:
                lines.append(f"  WARNING: {warning}")

        if "summary" in results:
            lines.append("")
            lines.append("VALIDATION SUMMARY:")
            summary = results["summary"]
            lines.append(f"  Total files:    {summary.get('total_files', 0)}")
            lines.append(f"  Empty files:    {summary.get('empty_files', 0)}")
            lines.append(f"  Syntax issues:  {summary.get('syntax_issues', 0)}")

            if "found_patterns" in summary:
                lines.append("")
                lines.append("File patterns found:")
                for pattern, count in summary["found_patterns"].items():
                    lines.append(f"  {pattern}: {count} files")

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_cleanup_results(self, results: dict[str, Any]) -> str:
        """Format cleanup results for console output.

        Args:
            results: Results dictionary from cleanup method

        Returns:
            Formatted string for console output
        """
        if results["success"]:
            if "removed_files" in results and results["removed_files"] > 0:
                return f"✅ Cleanup completed: Removed {results['removed_files']} files"
            else:
                return f"✅ {results.get('message', 'Cleanup completed')}"
        else:
            return f"❌ Cleanup failed: {results['error']}"

    def show_generation_help(self) -> str:
        """Show help information for code generation.

        Returns:
            Help text for console output
        """
        return """
🔧 CODE GENERATION HELP

The code generation system creates TypeScript types and API client code
from your OpenAPI schema, eliminating manual duplication between frontend
and backend.

WORKFLOW:
  1. Export OpenAPI schema from FastAPI
  2. Generate TypeScript types and API client
  3. Use generated code in your frontend
  4. Regenerate when API changes

GENERATED FILES:
  - TypeScript interfaces for all API models
  - API client with methods for all endpoints
  - Request/response types
  - Error handling utilities

INTEGRATION:
  1. Import the generated ApiClient in your frontend
  2. Use TypeScript interfaces for type safety
  3. Replace manual API calls with generated methods
  4. Enjoy automatic synchronization with backend changes

BEST PRACTICES:
  - Regenerate after any API changes
  - Don't manually edit generated files
  - Validate generated code before using
  - Keep schema and generated code in version control
        """.strip()

    def show_next_steps(self, output_dir: Path) -> str:
        """Show next steps after code generation.

        Args:
            output_dir: Directory where code was generated

        Returns:
            Next steps text for console output
        """
        return f"""
🚀 NEXT STEPS

Your TypeScript API client has been generated in: {output_dir}

TO INTEGRATE WITH YOUR FRONTEND:

1. Install required dependencies:
   npm install axios

2. Import and use the API client:
   ```typescript
   import ApiClient from './{output_dir.name}/apiclient';

   const client = new ApiClient({{
     baseURL: 'http://localhost:8000',
     apiToken: 'your-api-token'
   }});

   // Use the client
   const searches = await client.getApi().getUserSearchesEndpoint();
   ```

3. Use generated types for type safety:
   ```typescript
   import {{ SearchResponse, ListingResponse }} from './{output_dir.name}/models';

   function handleSearches(searches: SearchResponse[]) {{
     // TypeScript will now provide full type checking
   }}
   ```

4. Replace manual API calls with generated methods
5. Regenerate when your API changes

🔄 TO REGENERATE AFTER API CHANGES:
   python scripts/generate_frontend_code.py --clean --output {output_dir}
        """.strip()

"""CLI interface for OpenAPI schema operations."""

from pathlib import Path
from typing import Any

from ..services.openapi_service import OpenAPIService


class OpenAPICLI:
    """Command-line interface for OpenAPI schema operations."""

    def __init__(self, app: Any = None) -> None:
        """Initialize CLI with optional FastAPI app instance."""
        self.app = app
        self.service: OpenAPIService | None
        if app:
            self.service = OpenAPIService(app)
        else:
            self.service = None

    def export_schema(self, output_path: Path, format_type: str = "json") -> dict[str, Any]:
        """Export OpenAPI schema to file.

        Args:
            output_path: Path to save schema file
            format_type: Export format ('json' or 'yaml')

        Returns:
            Dictionary with export results
        """
        if not self.service:
            return {"success": False, "error": "No FastAPI app provided"}

        return self.service.export_schema_to_file(output_path, format_type)

    def validate_schema(self) -> dict[str, Any]:
        """Validate OpenAPI schema.

        Returns:
            Dictionary with validation results
        """
        if not self.service:
            return {"success": False, "error": "No FastAPI app provided"}

        return self.service.validate_schema()

    def preview_typescript_types(self) -> dict[str, Any]:
        """Preview TypeScript types that would be generated.

        Returns:
            Dictionary with TypeScript previews
        """
        if not self.service:
            return {"success": False, "error": "No FastAPI app provided"}

        try:
            types = self.service.get_typescript_types_preview()
            return {"success": True, "types": types, "count": len(types)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def show_schema_info(self) -> dict[str, Any]:
        """Show OpenAPI schema information.

        Returns:
            Dictionary with schema information
        """
        if not self.service:
            return {"success": False, "error": "No FastAPI app provided"}

        try:
            schema = self.service.generate_openapi_schema()
            info = schema.get("info", {})
            paths = schema.get("paths", {})
            components = schema.get("components", {})

            return {
                "success": True,
                "info": {
                    "title": info.get("title"),
                    "version": info.get("version"),
                    "description": info.get("description"),
                },
                "statistics": {
                    "paths_count": len(paths),
                    "schemas_count": len(components.get("schemas", {})),
                    "security_schemes": len(components.get("securitySchemes", {})),
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def format_schema_info(self, info_data: dict[str, Any]) -> str:
        """Format schema information for console output.

        Args:
            info_data: Dictionary from show_schema_info method

        Returns:
            Formatted string for console output
        """
        if not info_data["success"]:
            return f"Error: {info_data['error']}"

        lines = []
        lines.append("=" * 50)
        lines.append("OPENAPI SCHEMA INFORMATION")
        lines.append("=" * 50)

        info = info_data["info"]
        lines.append(f"Title:       {info['title']}")
        lines.append(f"Version:     {info['version']}")
        lines.append(f"Description: {info['description']}")
        lines.append("")

        stats = info_data["statistics"]
        lines.append("STATISTICS:")
        lines.append(f"  API Endpoints:    {stats['paths_count']}")
        lines.append(f"  Data Schemas:     {stats['schemas_count']}")
        lines.append(f"  Security Schemes: {stats['security_schemes']}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_validation_results(self, validation_data: dict[str, Any]) -> str:
        """Format validation results for console output.

        Args:
            validation_data: Dictionary from validate_schema method

        Returns:
            Formatted string for console output
        """
        lines = []
        lines.append("=" * 50)
        lines.append("OPENAPI SCHEMA VALIDATION")
        lines.append("=" * 50)

        if validation_data["valid"]:
            lines.append("✅ Schema is valid!")
        else:
            lines.append("❌ Schema has issues:")
            for issue in validation_data["issues"]:
                lines.append(f"  - {issue}")

        lines.append("")
        summary = validation_data.get("summary", {})
        if summary:
            lines.append("SCHEMA SUMMARY:")
            lines.append(f"  Paths:      {summary.get('paths_count', 0)}")
            lines.append(f"  Components: {summary.get('components_count', 0)}")
            lines.append(f"  Security:   {summary.get('security_schemes', 0)}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def format_export_results(self, export_data: dict[str, Any]) -> str:
        """Format export results for console output.

        Args:
            export_data: Dictionary from export_schema method

        Returns:
            Formatted string for console output
        """
        if export_data["success"]:
            lines = []
            lines.append("✅ OpenAPI schema exported successfully!")
            lines.append(f"Output file: {export_data['output_path']}")
            lines.append(f"Format:      {export_data['format']}")

            schema_info = export_data.get("schema_info", {})
            if schema_info:
                lines.append("")
                lines.append("Schema Information:")
                lines.append(f"  Title:      {schema_info.get('title')}")
                lines.append(f"  Version:    {schema_info.get('version')}")
                lines.append(f"  Endpoints:  {schema_info.get('paths_count')}")
                lines.append(f"  Components: {schema_info.get('components_count')}")

            return "\n".join(lines)
        else:
            return f"❌ Export failed: {export_data['error']}"

    def format_typescript_preview(self, preview_data: dict[str, Any]) -> str:
        """Format TypeScript preview for console output.

        Args:
            preview_data: Dictionary from preview_typescript_types method

        Returns:
            Formatted string for console output
        """
        if not preview_data["success"]:
            return f"Error: {preview_data['error']}"

        lines = []
        lines.append("=" * 50)
        lines.append("TYPESCRIPT TYPES PREVIEW")
        lines.append("=" * 50)
        lines.append(f"Generated {preview_data['count']} TypeScript interfaces:")
        lines.append("")

        for i, type_def in enumerate(preview_data["types"][:5]):  # Show first 5
            lines.append(type_def)
            if i < len(preview_data["types"]) - 1:
                lines.append("")

        if len(preview_data["types"]) > 5:
            remaining = len(preview_data["types"]) - 5
            lines.append(f"... and {remaining} more interfaces")

        lines.append("")
        lines.append("=" * 50)
        return "\n".join(lines)

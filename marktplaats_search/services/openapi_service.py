"""OpenAPI Schema Service

Service for managing OpenAPI schema generation, export, and frontend integration.
Provides schema customization and export capabilities for code generation.
"""

import json
from pathlib import Path
from typing import Any

from fastapi.openapi.utils import get_openapi


class OpenAPIService:
    """Service for OpenAPI schema management and code generation."""

    def __init__(self, app):
        """Initialize service with FastAPI app instance."""
        self.app = app

    def generate_openapi_schema(
        self, customizations: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Generate OpenAPI schema with optional customizations.

        Args:
            customizations: Optional schema customizations

        Returns:
            OpenAPI schema dictionary
        """
        # Get the base schema from FastAPI
        schema = get_openapi(
            title=self.app.title,
            version=self.app.version,
            description=self.app.description,
            routes=self.app.routes,
            servers=[{"url": "/", "description": "Local server"}],
        )

        # Apply customizations if provided
        if customizations:
            schema.update(customizations)

        # Add additional frontend-friendly information
        self._enhance_schema_for_codegen(schema)

        return schema

    def _enhance_schema_for_codegen(self, schema: dict[str, Any]) -> None:
        """Enhance schema with frontend code generation information."""
        # Add operation IDs for better client generation
        for path_item in schema.get("paths", {}).values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "operationId" not in operation:
                    # Generate operationId from summary or tags
                    method = operation.get("summary", "").replace(" ", "")
                    tags = operation.get("tags", [])
                    if tags:
                        operation["operationId"] = f"{tags[0]}_{method}"

        # Skip adding examples to avoid validation issues during code generation

    def export_schema_to_file(self, output_path: Path, format_type: str = "json") -> dict[str, Any]:
        """Export OpenAPI schema to file.

        Args:
            output_path: Path to save schema file
            format_type: Export format ('json' or 'yaml')

        Returns:
            Dictionary with export results
        """
        try:
            schema = self.generate_openapi_schema()

            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format_type.lower() == "json":
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)
            elif format_type.lower() == "yaml":
                import yaml

                with open(output_path, "w", encoding="utf-8") as f:
                    yaml.dump(schema, f, default_flow_style=False, allow_unicode=True)
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            return {
                "success": True,
                "output_path": str(output_path),
                "format": format_type,
                "schema_info": {
                    "title": schema.get("info", {}).get("title"),
                    "version": schema.get("info", {}).get("version"),
                    "paths_count": len(schema.get("paths", {})),
                    "components_count": len(schema.get("components", {}).get("schemas", {})),
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_typescript_types_preview(self) -> list[str]:
        """Generate a preview of TypeScript types that would be generated.

        Returns:
            List of TypeScript interface previews
        """
        schema = self.generate_openapi_schema()
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        type_previews = []

        for name, schema_def in schemas.items():
            if schema_def.get("type") == "object":
                properties = schema_def.get("properties", {})

                # Generate TypeScript interface preview
                interface_lines = [f"interface {name} {{"]

                for prop_name, prop_def in properties.items():
                    prop_type = self._map_openapi_type_to_typescript(prop_def)
                    optional = "?" if prop_name not in schema_def.get("required", []) else ""
                    interface_lines.append(f"  {prop_name}{optional}: {prop_type};")

                interface_lines.append("}")
                type_previews.append("\n".join(interface_lines))

        return type_previews

    def _map_openapi_type_to_typescript(self, prop_def: dict[str, Any]) -> str:
        """Map OpenAPI property definition to TypeScript type."""
        openapi_type = prop_def.get("type", "any")
        format_type = prop_def.get("format")

        # Handle arrays
        if openapi_type == "array":
            item_type = self._map_openapi_type_to_typescript(prop_def.get("items", {}))
            return f"{item_type}[]"

        # Handle basic types
        type_mapping = {
            "string": "string",
            "integer": "number",
            "number": "number",
            "boolean": "boolean",
            "object": "Record<string, any>",
        }

        # Handle special formats
        if format_type == "date-time":
            return "string"  # ISO date string
        elif format_type == "uuid":
            return "string"

        return type_mapping.get(openapi_type, "any")

    def validate_schema(self) -> dict[str, Any]:
        """Validate the generated OpenAPI schema.

        Returns:
            Dictionary with validation results
        """
        try:
            schema = self.generate_openapi_schema()

            # Basic validation checks
            issues = []

            # Check required fields
            if not schema.get("info", {}).get("title"):
                issues.append("Missing API title")

            if not schema.get("info", {}).get("version"):
                issues.append("Missing API version")

            paths = schema.get("paths", {})
            if not paths:
                issues.append("No API paths defined")

            # Check for operation IDs
            missing_operation_ids = []
            for path, methods in paths.items():
                for method, operation in methods.items():
                    if isinstance(operation, dict) and not operation.get("operationId"):
                        missing_operation_ids.append(f"{method.upper()} {path}")

            if missing_operation_ids:
                issues.append(f"Missing operation IDs: {', '.join(missing_operation_ids)}")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "summary": {
                    "paths_count": len(paths),
                    "components_count": len(schema.get("components", {}).get("schemas", {})),
                    "security_schemes": len(
                        schema.get("components", {}).get("securitySchemes", {})
                    ),
                },
            }

        except Exception as e:
            return {"valid": False, "issues": [f"Schema generation error: {e}"], "summary": {}}

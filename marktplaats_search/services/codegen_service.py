"""Code Generation Service

Service for generating TypeScript types and API client code from OpenAPI schemas.
Integrates with frontend development workflow to eliminate manual API duplication.
"""

import subprocess
from pathlib import Path
from typing import Any

from .openapi_service import OpenAPIService


class CodegenService:
    """Service for generating frontend code from OpenAPI schemas."""

    def __init__(self, app: Any = None) -> None:
        """Initialize service with optional FastAPI app."""
        self.app = app
        self.openapi_service: OpenAPIService | None
        if app:
            self.openapi_service = OpenAPIService(app)
        else:
            self.openapi_service = None

    def generate_typescript_types(
        self, output_dir: Path, schema_path: Path | None = None
    ) -> dict[str, Any]:
        """Generate TypeScript types from OpenAPI schema.

        Args:
            output_dir: Directory to output generated types
            schema_path: Path to OpenAPI schema file (will generate if None)

        Returns:
            Dictionary with generation results
        """
        try:
            # Ensure we have a schema file
            if not schema_path:
                schema_path = output_dir.parent / "schema" / "openapi.json"
                if not schema_path.exists() and self.openapi_service:
                    # Generate schema if it doesn't exist
                    schema_result = self.openapi_service.export_schema_to_file(schema_path)
                    if not schema_result["success"]:
                        return {
                            "success": False,
                            "error": f"Failed to generate schema: {schema_result['error']}",
                        }

            if not schema_path.exists():
                return {"success": False, "error": f"Schema file not found: {schema_path}"}

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate TypeScript types using openapi-generator-cli
            cmd = [
                "npx",
                "@openapitools/openapi-generator-cli",
                "generate",
                "-g",
                "typescript-axios",  # TypeScript with Axios client
                "-i",
                str(schema_path),
                "-o",
                str(output_dir),
                "--skip-validate-spec",  # Skip OpenAPI spec validation to avoid issues
                "--additional-properties=typescriptThreePlus=true,withSeparateModelsAndApi=true,apiPackage=api,modelPackage=models",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Code generation failed: {result.stderr}",
                    "stdout": result.stdout,
                }

            # Check generated files
            generated_files = list(output_dir.rglob("*.ts"))

            return {
                "success": True,
                "output_dir": str(output_dir),
                "generated_files": [str(f.relative_to(output_dir)) for f in generated_files],
                "files_count": len(generated_files),
                "message": f"Generated {len(generated_files)} TypeScript files",
            }

        except Exception as e:
            return {"success": False, "error": f"Code generation error: {e}"}

    def generate_api_client(
        self, output_dir: Path, schema_path: Path | None = None, client_name: str = "ApiClient"
    ) -> dict[str, Any]:
        """Generate API client code from OpenAPI schema.

        Args:
            output_dir: Directory to output generated client
            schema_path: Path to OpenAPI schema file
            client_name: Name for the generated client class

        Returns:
            Dictionary with generation results
        """
        try:
            # First generate the base TypeScript files
            types_result = self.generate_typescript_types(output_dir, schema_path)
            if not types_result["success"]:
                return types_result

            # Create a custom API client wrapper
            client_content = self._generate_custom_client_wrapper(client_name)

            client_file = output_dir / f"{client_name.lower()}.ts"
            with open(client_file, "w", encoding="utf-8") as f:
                f.write(client_content)

            return {
                "success": True,
                "output_dir": str(output_dir),
                "client_file": str(client_file.relative_to(output_dir)),
                "base_files_count": types_result["files_count"],
                "message": f"Generated API client with {types_result['files_count']} supporting files",
            }

        except Exception as e:
            return {"success": False, "error": f"API client generation error: {e}"}

    def _generate_custom_client_wrapper(self, client_name: str) -> str:
        """Generate a custom API client wrapper with convenience methods."""
        return f"""/**
 * {client_name} - Custom API Client
 *
 * This file provides a convenient wrapper around the generated API client
 * with error handling, authentication, and utility methods.
 *
 * Generated automatically from OpenAPI schema - do not edit manually!
 */

import {{ Configuration, DefaultApi }} from './api';
import {{ AxiosRequestConfig, AxiosResponse }} from 'axios';

export interface ClientConfig {{
  baseURL?: string;
  apiToken?: string;
  timeout?: number;
}}

export class {client_name} {{
  private api: DefaultApi;
  private config: ClientConfig;

  constructor(config: ClientConfig = {{}}) {{
    this.config = {{
      baseURL: config.baseURL || window.location.origin,
      timeout: config.timeout || 30000,
      ...config
    }};

    const configuration = new Configuration({{
      basePath: this.config.baseURL,
      accessToken: this.config.apiToken
    }});

    this.api = new DefaultApi(configuration);
  }}

  /**
   * Update API token for authentication
   */
  setApiToken(token: string): void {{
    this.config.apiToken = token;
    const configuration = new Configuration({{
      basePath: this.config.baseURL,
      accessToken: token
    }});
    this.api = new DefaultApi(configuration);
  }}

  /**
   * Get current API token
   */
  getApiToken(): string | undefined {{
    return this.config.apiToken;
  }}

  /**
   * Check if client is authenticated
   */
  isAuthenticated(): boolean {{
    return !!this.config.apiToken;
  }}

  /**
   * Get the underlying API instance for direct access
   */
  getApi(): DefaultApi {{
    return this.api;
  }}

  /**
   * Handle API errors consistently
   */
  private handleApiError(error: any): never {{
    if (error.response) {{
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.statusText || 'API Error';

      if (status === 401) {{
        throw new Error('Authentication required or token expired');
      }} else if (status === 403) {{
        throw new Error('Access forbidden');
      }} else if (status === 404) {{
        throw new Error('Resource not found');
      }} else if (status >= 500) {{
        throw new Error('Server error - please try again later');
      }} else {{
        throw new Error(`API Error (${{status}}): ${{message}}`);
      }}
    }} else if (error.request) {{
      throw new Error('Network error - please check your connection');
    }} else {{
      throw new Error(`Request error: ${{error.message}}`);
    }}
  }}

  /**
   * Wrapper for API calls with consistent error handling
   */
  private async apiCall<T>(apiMethod: () => Promise<AxiosResponse<T>>): Promise<T> {{
    try {{
      const response = await apiMethod();
      return response.data;
    }} catch (error) {{
      this.handleApiError(error);
    }}
  }}

  // Add convenience methods here that wrap the generated API methods
  // Example:
  // async getSearches() {{
  //   return this.apiCall(() => this.api.getUserSearchesEndpoint());
  // }}
}}

// Export the client as default for easy importing
export default {client_name};

// Re-export types and models for convenience
export * from './models';
export * from './api';
"""

    def validate_generated_code(self, output_dir: Path) -> dict[str, Any]:
        """Validate generated TypeScript code.

        Args:
            output_dir: Directory containing generated code

        Returns:
            Dictionary with validation results
        """
        try:
            issues = []
            warnings = []

            # Check if output directory exists
            if not output_dir.exists():
                return {"success": False, "error": f"Output directory does not exist: {output_dir}"}

            # Check for required files
            required_patterns = ["*.ts", "models/*.ts", "api/*.ts"]
            found_files = {}

            for pattern in required_patterns:
                files = list(output_dir.glob(pattern))
                found_files[pattern] = len(files)
                if len(files) == 0:
                    issues.append(f"No files found matching pattern: {pattern}")

            # Check file sizes (basic sanity check)
            all_ts_files = list(output_dir.rglob("*.ts"))
            empty_files = [f for f in all_ts_files if f.stat().st_size == 0]
            if empty_files:
                warnings.append(f"Found {len(empty_files)} empty TypeScript files")

            # Check for syntax issues (basic check)
            syntax_issues = []
            for ts_file in all_ts_files[:10]:  # Check first 10 files
                try:
                    content = ts_file.read_text(encoding="utf-8")
                    # Very basic syntax checks
                    if content.count("{") != content.count("}"):
                        syntax_issues.append(f"Possible brace mismatch in {ts_file.name}")
                    if "export" not in content and ts_file.suffix == ".ts":
                        warnings.append(f"No exports found in {ts_file.name}")
                except Exception as e:
                    issues.append(f"Could not read {ts_file.name}: {e}")

            return {
                "success": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "summary": {
                    "total_files": len(all_ts_files),
                    "empty_files": len(empty_files),
                    "syntax_issues": len(syntax_issues),
                    "found_patterns": found_files,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Validation error: {e}"}

    def clean_generated_code(self, output_dir: Path) -> dict[str, Any]:
        """Clean up generated code directory.

        Args:
            output_dir: Directory to clean

        Returns:
            Dictionary with cleanup results
        """
        try:
            if not output_dir.exists():
                return {"success": True, "message": "Directory does not exist"}

            # Count files before cleanup
            files_before = list(output_dir.rglob("*"))
            file_count_before = len([f for f in files_before if f.is_file()])

            # Remove the directory and all its contents
            import shutil

            shutil.rmtree(output_dir)

            return {
                "success": True,
                "removed_files": file_count_before,
                "message": f"Cleaned up {file_count_before} generated files",
            }

        except Exception as e:
            return {"success": False, "error": f"Cleanup error: {e}"}

"""Frontend Asset Management Service

Service for managing frontend assets, builds, and consolidation.
Handles CSS/JS compilation, asset optimization, and deployment.
"""

import json
import shutil
from pathlib import Path
from typing import Any


class FrontendService:
    """Service for frontend asset management and consolidation."""

    def __init__(self, project_root: Path | None = None):
        """Initialize service with project root path."""
        self.project_root = project_root or Path.cwd()
        self.frontend_dir = self.project_root / "frontend"
        self.src_dir = self.frontend_dir / "src"
        self.dist_dir = self.frontend_dir / "dist"
        self.public_dir = self.frontend_dir / "public"
        self.static_dir = self.project_root / "static"

    def consolidate_frontend_assets(self) -> dict[str, Any]:
        """Consolidate all frontend assets into a unified structure.

        Returns:
            Dictionary with consolidation results
        """
        try:
            results: dict[str, Any] = {
                "success": True,
                "actions": [],
                "removed_duplicates": [],
                "created_build": False,
                "updated_structure": False,
            }

            # Step 1: Remove duplicate HTML files
            duplicate_files = [
                self.frontend_dir / "src" / "templates" / "index.html",  # Duplicate of public
                self.static_dir / "index.html",  # Old monolithic version
            ]

            for file_path in duplicate_files:
                if file_path.exists():
                    file_path.unlink()
                    results["removed_duplicates"].append(
                        str(file_path.relative_to(self.project_root))
                    )
                    results["actions"].append(
                        f"Removed duplicate: {file_path.relative_to(self.project_root)}"
                    )

            # Step 2: Ensure clean directory structure
            self._ensure_directory_structure()
            results["updated_structure"] = True
            results["actions"].append("Updated directory structure")

            # Step 3: Create build configuration
            self._create_build_configuration()
            results["created_build"] = True
            results["actions"].append("Created build configuration")

            # Step 4: Build assets from source
            build_result = self.build_assets()
            if build_result["success"]:
                results["actions"].extend(build_result.get("actions", []))

            # Step 5: Move old static assets to proper location
            self._migrate_static_assets()
            results["actions"].append("Migrated static assets")

            return results

        except (OSError, FileNotFoundError, PermissionError) as e:
            return {"success": False, "error": f"Frontend consolidation failed: {e}", "actions": []}

    def _ensure_directory_structure(self) -> None:
        """Ensure proper frontend directory structure exists."""
        directories = [
            self.frontend_dir,
            self.src_dir,
            self.src_dir / "js",
            self.src_dir / "css",
            self.src_dir / "assets",
            self.dist_dir,
            self.public_dir,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _create_build_configuration(self) -> None:
        """Create build configuration files."""
        # Create package.json for npm scripts
        package_json = {
            "name": "marktplaats-search-frontend",
            "version": "1.0.0",
            "description": "Frontend assets for MarktplaatsSearch application",
            "scripts": {
                "build": "npm run build:css && npm run build:js",
                "build:css": "cat src/css/utilities/reset.css src/css/utilities/variables.css src/css/layouts/*.css src/css/components/*.css src/css/utilities/responsive.css > dist/styles.css",
                "build:js": "cat src/js/config/*.js src/js/services/*.js src/js/components/*.js src/js/utils/*.js src/js/app.js > dist/app.js",
                "watch": "npm run build && echo 'Watching for changes...'",
                "clean": "rm -rf dist/* && mkdir -p dist",
            },
            "devDependencies": {"@openapitools/openapi-generator-cli": "^2.13.4"},
        }

        package_json_path = self.frontend_dir / "package.json"
        with open(package_json_path, "w", encoding="utf-8") as f:
            json.dump(package_json, f, indent=2, ensure_ascii=False)

        # Create build script
        build_script = self.frontend_dir / "build.py"
        build_script_content = '''#!/usr/bin/env python3
"""
Frontend Build Script

Builds CSS and JavaScript assets from source files.
Alternative to npm build for Python-only environments.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from marktplaats_search.services.frontend_service import FrontendService


def main():
    """Main build function."""
    service = FrontendService()
    result = service.build_assets()

    if result["success"]:
        print("✅ Frontend build completed successfully!")
        for action in result.get("actions", []):
            print(f"   {action}")
    else:
        print(f"❌ Frontend build failed: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

        with open(build_script, "w", encoding="utf-8") as f:
            f.write(build_script_content)
        build_script.chmod(0o755)

    def build_assets(self) -> dict[str, Any]:
        """Build CSS and JavaScript assets from source files.

        Returns:
            Dictionary with build results
        """
        try:
            actions = []

            # Ensure dist directory exists
            self.dist_dir.mkdir(parents=True, exist_ok=True)

            # Build CSS
            css_result = self._build_css()
            if css_result["success"]:
                actions.append(f"Built CSS: {css_result['output_file']}")
            else:
                return {"success": False, "error": f"CSS build failed: {css_result['error']}"}

            # Build JavaScript
            js_result = self._build_javascript()
            if js_result["success"]:
                actions.append(f"Built JavaScript: {js_result['output_file']}")
            else:
                return {"success": False, "error": f"JS build failed: {js_result['error']}"}

            # Copy static assets
            self._copy_static_assets()
            actions.append("Copied static assets")

            return {
                "success": True,
                "actions": actions,
                "css_file": css_result.get("output_file"),
                "js_file": js_result.get("output_file"),
            }

        except (OSError, FileNotFoundError, PermissionError) as e:
            return {"success": False, "error": f"Build failed: {e}", "actions": []}

    def _build_css(self) -> dict[str, Any]:
        """Build CSS from source files in correct order."""
        try:
            # Define CSS build order for proper cascade
            css_files = [
                "utilities/reset.css",
                "utilities/variables.css",
                "layouts/header.css",
                "layouts/main.css",
                "components/buttons.css",
                "components/forms.css",
                "components/tables.css",
                "components/cards.css",
                "components/modals.css",
                "utilities/responsive.css",
                "main.css",  # Main should come last
            ]

            css_content = []
            found_files = []

            for css_file in css_files:
                file_path = self.src_dir / "css" / css_file
                if file_path.exists():
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            css_content.append(f"/* {css_file} */")
                            css_content.append(content)
                            css_content.append("")  # Empty line between files
                            found_files.append(css_file)

            if not css_content:
                return {"success": False, "error": "No CSS files found"}

            # Write combined CSS
            output_file = self.dist_dir / "styles.css"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(css_content))

            return {
                "success": True,
                "output_file": str(output_file.relative_to(self.project_root)),
                "files_included": found_files,
            }

        except (OSError, FileNotFoundError, PermissionError) as e:
            return {"success": False, "error": f"CSS build error: {e}"}

    def _build_javascript(self) -> dict[str, Any]:
        """Build JavaScript from source files in correct order."""
        try:
            # Define JS build order for proper dependencies
            js_files = [
                "config/constants.js",
                "services/auth.js",
                "services/api.js",
                "services/theme.js",
                "components/search-form.js",
                "components/search-manager.js",
                "components/results-viewer.js",
                "utils/helpers.js",
                "app.js",  # Main app should come last
            ]

            js_content = []
            found_files = []

            # Add IIFE wrapper start to create isolated scope
            js_content.append("// MarktplaatsSearch Application Bundle")
            js_content.append("(function() {")
            js_content.append("'use strict';")
            js_content.append("")

            for js_file in js_files:
                file_path = self.src_dir / "js" / js_file
                if file_path.exists():
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            js_content.append(f"/* {js_file} */")

                            # Remove ES6 export statements and convert to browser-compatible code
                            content = self._convert_es6_to_browser(content)

                            js_content.append(content)
                            js_content.append("")  # Empty line between files
                            found_files.append(js_file)

            if not found_files:
                return {"success": False, "error": "No JavaScript files found"}

            # Close IIFE wrapper
            js_content.append("})();")

            # Write combined JavaScript
            output_file = self.dist_dir / "app.js"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\n".join(js_content))

            return {
                "success": True,
                "output_file": str(output_file.relative_to(self.project_root)),
                "files_included": found_files,
            }

        except (OSError, FileNotFoundError, PermissionError) as e:
            return {"success": False, "error": f"JavaScript build error: {e}"}

    def _convert_es6_to_browser(self, content: str) -> str:
        """Convert ES6 module syntax to browser-compatible code."""
        # Remove export statements and convert to global variables
        content = content.replace("export const ", "const ")
        content = content.replace("export class ", "class ")
        content = content.replace("export function ", "function ")
        content = content.replace("export default ", "")
        content = content.replace("export { ", "// export { ")
        content = content.replace("export * from ", "// export * from ")

        # Remove import statements (assuming dependencies are loaded in order)
        import_lines = []
        for line in content.split("\n"):
            if not (line.strip().startswith("import ") and " from " in line):
                import_lines.append(line)
        content = "\n".join(import_lines)

        return content

    def _copy_static_assets(self) -> None:
        """Copy static assets like images, fonts, etc."""
        assets_src = self.src_dir / "assets"
        if assets_src.exists():
            assets_dest = self.dist_dir / "assets"
            if assets_dest.exists():
                shutil.rmtree(assets_dest)
            shutil.copytree(assets_src, assets_dest)

    def _migrate_static_assets(self) -> None:
        """Migrate assets from old static directory."""
        if not self.static_dir.exists():
            return

        # Move enhanced_features.js to proper location
        enhanced_js = self.static_dir / "enhanced_features.js"
        if enhanced_js.exists():
            target = self.src_dir / "js" / "utils" / "enhanced_features.js"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(enhanced_js), str(target))

    def clean_build_artifacts(self) -> dict[str, Any]:
        """Clean all build artifacts and temp files.

        Returns:
            Dictionary with cleanup results
        """
        try:
            removed_files = []

            # Clean dist directory
            if self.dist_dir.exists():
                for file_path in self.dist_dir.rglob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                        removed_files.append(str(file_path.relative_to(self.project_root)))

            # Clean node_modules if exists
            node_modules = self.frontend_dir / "node_modules"
            if node_modules.exists():
                shutil.rmtree(node_modules)
                removed_files.append("frontend/node_modules/")

            return {
                "success": True,
                "removed_files": removed_files,
                "message": f"Cleaned {len(removed_files)} build artifacts",
            }

        except (OSError, PermissionError) as e:
            return {"success": False, "error": f"Cleanup failed: {e}", "removed_files": []}

    def get_build_status(self) -> dict[str, Any]:
        """Get current build status and file information.

        Returns:
            Dictionary with build status information
        """
        try:
            status = {
                "dist_exists": self.dist_dir.exists(),
                "css_exists": (self.dist_dir / "styles.css").exists(),
                "js_exists": (self.dist_dir / "app.js").exists(),
                "html_template": (self.public_dir / "index.html").exists(),
                "source_files": {},
                "build_artifacts": {},
            }

            # Count source files
            if self.src_dir.exists():
                css_files = list(self.src_dir.rglob("*.css"))
                js_files = list(self.src_dir.rglob("*.js"))

                status["source_files"] = {
                    "css_count": len(css_files),
                    "js_count": len(js_files),
                    "css_files": [str(f.relative_to(self.src_dir)) for f in css_files],
                    "js_files": [str(f.relative_to(self.src_dir)) for f in js_files],
                }

            # Get build artifact info
            if self.dist_dir.exists():
                artifacts = list(self.dist_dir.rglob("*"))
                artifact_files = [f for f in artifacts if f.is_file()]

                status["build_artifacts"] = {
                    "total_files": len(artifact_files),
                    "files": [str(f.relative_to(self.dist_dir)) for f in artifact_files],
                }

            return {"success": True, "status": status}

        except (OSError, FileNotFoundError) as e:
            return {"success": False, "error": f"Status check failed: {e}", "status": {}}

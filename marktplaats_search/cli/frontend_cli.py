"""CLI interface for frontend asset management operations."""

from pathlib import Path
from typing import Any

from ..services.frontend_service import FrontendService


class FrontendCLI:
    """Command-line interface for frontend asset management operations."""

    def __init__(self, project_root: Path | None = None):
        """Initialize CLI with frontend service."""
        self.service = FrontendService(project_root)

    def consolidate_assets(self) -> dict[str, Any]:
        """Consolidate frontend assets into unified structure.

        Returns:
            Dictionary with consolidation results
        """
        return self.service.consolidate_frontend_assets()

    def build_assets(self) -> dict[str, Any]:
        """Build frontend assets from source files.

        Returns:
            Dictionary with build results
        """
        return self.service.build_assets()

    def clean_build(self) -> dict[str, Any]:
        """Clean build artifacts and temporary files.

        Returns:
            Dictionary with cleanup results
        """
        return self.service.clean_build_artifacts()

    def show_build_status(self) -> dict[str, Any]:
        """Show current build status and file information.

        Returns:
            Dictionary with build status information
        """
        return self.service.get_build_status()

    def format_consolidation_results(self, results: dict[str, Any]) -> str:
        """Format consolidation results for console output.

        Args:
            results: Results dictionary from consolidation method

        Returns:
            Formatted string for console output
        """
        if not results["success"]:
            return f"❌ Frontend consolidation failed: {results['error']}"

        lines = []
        lines.append("✅ Frontend assets consolidated successfully!")
        lines.append("")

        # Show actions taken
        if results.get("actions"):
            lines.append("ACTIONS PERFORMED:")
            for action in results["actions"]:
                lines.append(f"  ✓ {action}")
            lines.append("")

        # Show removed duplicates
        if results.get("removed_duplicates"):
            lines.append("REMOVED DUPLICATES:")
            for file_path in results["removed_duplicates"]:
                lines.append(f"  🗑️  {file_path}")
            lines.append("")

        # Show status updates
        status_items = []
        if results.get("updated_structure"):
            status_items.append("Directory structure updated")
        if results.get("created_build"):
            status_items.append("Build configuration created")

        if status_items:
            lines.append("STATUS:")
            for item in status_items:
                lines.append(f"  ✅ {item}")

        return "\\n".join(lines)

    def format_build_results(self, results: dict[str, Any]) -> str:
        """Format build results for console output.

        Args:
            results: Results dictionary from build method

        Returns:
            Formatted string for console output
        """
        if not results["success"]:
            return f"❌ Frontend build failed: {results['error']}"

        lines = []
        lines.append("✅ Frontend build completed successfully!")
        lines.append("")

        if results.get("actions"):
            lines.append("BUILD RESULTS:")
            for action in results["actions"]:
                lines.append(f"  ✓ {action}")
            lines.append("")

        # Show output files
        if results.get("css_file"):
            lines.append(f"CSS Output:  {results['css_file']}")
        if results.get("js_file"):
            lines.append(f"JS Output:   {results['js_file']}")

        return "\\n".join(lines)

    def format_build_status(self, status_data: dict[str, Any]) -> str:
        """Format build status for console output.

        Args:
            status_data: Status data from show_build_status method

        Returns:
            Formatted string for console output
        """
        if not status_data["success"]:
            return f"❌ Status check failed: {status_data['error']}"

        status = status_data["status"]
        lines = []
        lines.append("=== FRONTEND BUILD STATUS ===")
        lines.append("")

        # Build artifacts status
        lines.append("BUILD ARTIFACTS:")
        lines.append(f"  Dist directory:  {'✅' if status['dist_exists'] else '❌'}")
        lines.append(f"  CSS compiled:    {'✅' if status['css_exists'] else '❌'}")
        lines.append(f"  JS compiled:     {'✅' if status['js_exists'] else '❌'}")
        lines.append(f"  HTML template:   {'✅' if status['html_template'] else '❌'}")
        lines.append("")

        # Source files
        source = status.get("source_files", {})
        if source:
            lines.append("SOURCE FILES:")
            lines.append(f"  CSS files:       {source.get('css_count', 0)}")
            lines.append(f"  JS files:        {source.get('js_count', 0)}")
            lines.append("")

            if source.get("css_files"):
                lines.append("  CSS Sources:")
                for css_file in source["css_files"]:
                    lines.append(f"    - {css_file}")
                lines.append("")

            if source.get("js_files"):
                lines.append("  JS Sources:")
                for js_file in source["js_files"]:
                    lines.append(f"    - {js_file}")
                lines.append("")

        # Build artifacts
        artifacts = status.get("build_artifacts", {})
        if artifacts and artifacts.get("files"):
            lines.append("BUILT FILES:")
            for artifact in artifacts["files"]:
                lines.append(f"  📦 {artifact}")

        lines.append("=" * 30)
        return "\\n".join(lines)

    def format_cleanup_results(self, results: dict[str, Any]) -> str:
        """Format cleanup results for console output.

        Args:
            results: Results dictionary from cleanup method

        Returns:
            Formatted string for console output
        """
        if not results["success"]:
            return f"❌ Cleanup failed: {results['error']}"

        lines = []
        lines.append("🧹 Frontend cleanup completed!")
        lines.append(f"Removed {len(results.get('removed_files', []))} files/directories")
        lines.append("")

        if results.get("removed_files"):
            lines.append("REMOVED FILES:")
            for file_path in results["removed_files"][:10]:  # Show first 10
                lines.append(f"  🗑️  {file_path}")

            if len(results["removed_files"]) > 10:
                remaining = len(results["removed_files"]) - 10
                lines.append(f"  ... and {remaining} more files")

        return "\\n".join(lines)

    def show_consolidation_help(self) -> str:
        """Show help information for frontend consolidation.

        Returns:
            Help text for console output
        """
        return """
🎨 FRONTEND CONSOLIDATION HELP

The frontend consolidation system organizes and optimizes your frontend assets
for better maintainability and performance.

WHAT IT DOES:
  • Removes duplicate HTML files
  • Consolidates CSS and JavaScript into optimized bundles
  • Creates proper source/build directory structure
  • Sets up build configuration and scripts
  • Migrates assets from legacy locations

DIRECTORY STRUCTURE:
  frontend/
  ├── src/                 # Source files
  │   ├── css/            # CSS modules
  │   │   ├── components/ # Component styles
  │   │   ├── layouts/    # Layout styles
  │   │   └── utilities/  # Utility styles
  │   ├── js/             # JavaScript modules
  │   │   ├── components/ # UI components
  │   │   ├── services/   # API services
  │   │   └── utils/      # Utility functions
  │   └── assets/         # Images, fonts, etc.
  ├── dist/               # Built files
  │   ├── styles.css      # Compiled CSS
  │   ├── app.js          # Compiled JavaScript
  │   └── assets/         # Copied assets
  └── public/             # HTML templates
      └── index.html      # Main template

BUILD PROCESS:
  1. CSS files are concatenated in dependency order
  2. JavaScript files are combined with proper dependencies
  3. Assets are copied to distribution directory
  4. Source maps and optimization can be added

BEST PRACTICES:
  • Keep source files modular and focused
  • Use semantic naming for CSS classes and JS functions
  • Test the build output before deploying
  • Run consolidation after structural changes
        """.strip()

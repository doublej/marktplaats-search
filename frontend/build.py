#!/usr/bin/env python3
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

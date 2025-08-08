#!/usr/bin/env python3
"""
Simple build system for MarktplaatsSearch frontend
Concatenates modular CSS and JS files into single files for production
"""

from pathlib import Path


def build_css():
    """Concatenate all CSS files in the correct order"""
    css_files = [
        "src/css/utilities/variables.css",
        "src/css/utilities/reset.css",
        "src/css/layouts/header.css",
        "src/css/layouts/main.css",
        "src/css/components/buttons.css",
        "src/css/components/forms.css",
        "src/css/components/cards.css",
        "src/css/components/modals.css",
        "src/css/components/tables.css",
        "src/css/utilities/responsive.css",
    ]

    output = []
    frontend_dir = Path(__file__).parent

    for css_file in css_files:
        file_path = frontend_dir / css_file
        if file_path.exists():
            with open(file_path) as f:
                output.append(f"/* {css_file} */\n")
                output.append(f.read())
                output.append("\n\n")
        else:
            print(f"Warning: {css_file} not found, skipping...")

    # Write concatenated CSS
    dist_dir = frontend_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    with open(dist_dir / "styles.css", "w") as f:
        f.write("".join(output))

    print("✅ CSS built successfully")


def build_js():
    """Concatenate all JS files in the correct order"""
    js_files = [
        "src/js/config/constants.js",
        "src/js/services/api.js",
        "src/js/services/auth.js",
        "src/js/services/theme.js",
        "src/js/utils/helpers.js",
        "src/js/components/search-manager.js",
        "src/js/components/results-viewer.js",
        "src/js/components/search-form.js",
        "src/js/app.js",
    ]

    output = []
    frontend_dir = Path(__file__).parent

    for js_file in js_files:
        file_path = frontend_dir / js_file
        if file_path.exists():
            with open(file_path) as f:
                output.append(f"/* {js_file} */\n")
                content = f.read()
                # Remove export statements for simple concatenation
                content = content.replace("export ", "")
                output.append(content)
                output.append("\n\n")
        else:
            print(f"Warning: {js_file} not found, skipping...")

    # Write concatenated JS
    dist_dir = frontend_dir / "dist"
    dist_dir.mkdir(exist_ok=True)

    with open(dist_dir / "app.js", "w") as f:
        f.write("".join(output))

    print("✅ JavaScript built successfully")


def copy_html():
    """Copy HTML template to public directory"""
    frontend_dir = Path(__file__).parent
    template_path = frontend_dir / "src/templates/index.html"

    if template_path.exists():
        public_dir = frontend_dir / "public"
        public_dir.mkdir(exist_ok=True)

        with open(template_path) as f:
            html_content = f.read()

        # Update CSS and JS paths for production
        html_content = html_content.replace(
            '<!-- CSS Imports -->\n    <link rel="stylesheet" href="../css/utilities/variables.css">\n    <link rel="stylesheet" href="../css/utilities/reset.css">\n    <link rel="stylesheet" href="../css/layouts/header.css">\n    <link rel="stylesheet" href="../css/layouts/main.css">\n    <link rel="stylesheet" href="../css/components/buttons.css">\n    <link rel="stylesheet" href="../css/components/forms.css">\n    <link rel="stylesheet" href="../css/components/cards.css">\n    <link rel="stylesheet" href="../css/components/modals.css">\n    <link rel="stylesheet" href="../css/components/tables.css">\n    <link rel="stylesheet" href="../css/utilities/responsive.css">',
            '<link rel="stylesheet" href="styles.css">',
        )

        html_content = html_content.replace(
            '<!-- JavaScript Imports -->\n    <script src="../js/config/constants.js"></script>\n    <script src="../js/services/api.js"></script>\n    <script src="../js/services/auth.js"></script>\n    <script src="../js/services/theme.js"></script>\n    <script src="../js/components/search-manager.js"></script>\n    <script src="../js/components/results-viewer.js"></script>\n    <script src="../js/components/search-form.js"></script>\n    <script src="../js/utils/helpers.js"></script>\n    <script src="../js/app.js"></script>',
            '<script src="app.js"></script>',
        )

        with open(public_dir / "index.html", "w") as f:
            f.write(html_content)

    print("✅ HTML built successfully")


def main():
    """Main build function"""
    print("🔨 Building MarktplaatsSearch Frontend...")

    build_css()
    build_js()
    copy_html()

    print("✅ Frontend build complete!")
    print("\n📁 Built files:")
    print("   - frontend/dist/styles.css")
    print("   - frontend/dist/app.js")
    print("   - frontend/public/index.html")


if __name__ == "__main__":
    main()

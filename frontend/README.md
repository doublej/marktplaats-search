# Frontend Documentation

This directory contains the JavaScript frontend for the MarktplaatsSearch application.

## Architecture

The frontend uses a **legacy JavaScript architecture** with global variables and script tags, rather than modern ES modules. This was designed for simplicity and direct integration with the Python backend.

### Structure

```
frontend/
├── src/
│   ├── js/
│   │   ├── config/
│   │   │   └── constants.js     # Application constants (exports CONFIG)
│   │   ├── services/
│   │   │   ├── api.js           # API service (creates global apiService)
│   │   │   ├── auth.js          # Authentication service (creates global authService)
│   │   │   └── theme.js         # Theme service (creates global themeService)
│   │   ├── components/
│   │   │   ├── search-form.js   # Search form component
│   │   │   ├── search-manager.js # Search management component
│   │   │   └── results-viewer.js # Results display component
│   │   ├── utils/
│   │   │   └── helpers.js       # Utility functions ($, $$, escapeHtml, etc.)
│   │   └── app.js               # Main application class
│   ├── css/                     # Stylesheets
│   └── templates/               # HTML templates
├── dist/                        # Built/compiled assets
└── public/
    └── index.html               # Main HTML file
```

## ESLint Configuration

The project uses ESLint for JavaScript code quality and consistency:

### Commands

```bash
# Run ESLint (check for issues)
npm run lint

# Run ESLint and auto-fix issues where possible
npm run lint:fix

# Run ESLint with zero tolerance for warnings
npm run lint:check
```

### Configuration

- **Config file**: `eslint.config.js` (flat config format)
- **Style**: Modern ESLint 9.x with flat configuration
- **Rules**: Configured for legacy JavaScript architecture with global variables
- **Prettier integration**: Automatic code formatting

### Global Variables

The ESLint configuration recognizes these global variables:

- **Application globals**: `CONFIG`, `apiService`, `authService`, `themeService`, `app`
- **Utility functions**: Defined in `helpers.js` but available globally
- **Components**: `SearchForm`, `SearchManager`, `ResultsViewer`

## Code Standards

### JavaScript Style
- **Quotes**: Single quotes preferred
- **Semicolons**: Required
- **Indentation**: 2 spaces
- **Variables**: Use `const`/`let`, avoid `var`
- **Templates**: Use template literals for string interpolation
- **Functions**: Prefer arrow functions for callbacks

### Legacy Considerations
- Global variables are acceptable due to the legacy architecture
- Functions may be attached to `window` for global access
- ES modules are used only in `constants.js`
- Most files use script-style JavaScript without imports/exports

## Development Workflow

1. **Make changes** to JavaScript files in `frontend/src/js/`
2. **Run linting**: `npm run lint:fix`
3. **Test in browser**: The files are served directly by the Python backend
4. **Build if needed**: `python frontend/build.py` (if build process exists)

## Future Modernization

This frontend could be modernized by:
- Converting to ES modules with proper import/export
- Adding a build step with bundling (webpack, vite, etc.)
- Implementing a modern framework (React, Vue, etc.)
- Adding TypeScript for better type safety
- Implementing component-based architecture

However, the current architecture is functional and serves the application's needs effectively.

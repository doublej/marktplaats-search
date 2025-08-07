# Claude Code Project Instructions

## Project Overview
A Python application for monitoring Marktplaats.nl listings with automated search scheduling and web dashboard.

**Status**: Existing project enhanced with boilerplate configuration.

**Gitignore Profile**: This project uses the "ai-dev" .gitignore profile, optimized for ai dev workflows.

## Changelog Maintenance
**IMPORTANT**: Update `CHANGELIST.md` with every significant change. This file tracks all project modifications and should be kept current. Add entries under "Unreleased" and move them to version sections when releasing.

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv sync --dev
```

### Code Quality
```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy .

# Run all quality checks
ruff check . && ruff format . && mypy .
```

### Testing
```bash
# Run tests
pytest

# Run specific test
pytest tests/test_example.py::test_function
```

### Dependencies
```bash
# Add dependency
uv add package_name

# Add dev dependency
uv add --dev package_name

# Update dependencies
uv sync
```

## Code Standards

- Use type hints for all functions and methods
- Follow PEP 8 style guide (enforced by ruff)
- Keep functions focused and single-purpose
- Use descriptive variable and function names
- Document public APIs with docstrings

## Before Committing

1. Update `CHANGELIST.md` with your changes
2. Run the full quality check suite:
```bash
ruff check . && ruff format . && mypy . && pytest
```

## Claude Code Hooks

This project includes Claude Code hooks configured in `.claude/settings.json` that provide:

### Automatic Quality Enforcement
- **PreToolUse**: Runs `ruff format` and `ruff check --fix` before Write/Edit operations
- **PostToolUse**: Runs `mypy` type checking after code modifications
- **Quality Gates**: Ensures code meets standards before and after changes

### Automatic Git Integration
- **UserPromptSubmit**: Creates commit before Claude Code starts working
- **Stop**: Creates commit after Claude Code completes changes
- **Professional Commit Messages**: Includes Claude Code attribution

### Session Management
- **SessionStart**: Shows project info and reminds about CLAUDE.md instructions
- **Changelog Reminders**: Prompts to update CHANGELIST.md when it's over 30 minutes old

### Hook Configuration
The hooks are defined in `.claude/settings.json` and run automatically when using Claude Code in this project directory. They provide deterministic control over the development workflow.

## Implementation Notes

This project was enhanced with boilerplate configuration including:
- Modern Python project configuration in pyproject.toml
- Comprehensive code quality tools (ruff, mypy, pre-commit)
- Claude Code hooks for automated workflow
- Professional .gitignore patterns

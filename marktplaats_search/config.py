"""
Configuration management for the MarktplaatsSearch API.
Loads settings from environment variables with secure defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self) -> None:
        # Database settings
        self.database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./marktplaats_api.db")

        # Security settings
        self.token_salt = os.getenv(
            "TOKEN_SALT",
            None,  # Will be generated if not set
        )

        # Token expiry in days (None = never expires)
        self.token_expiry_days = self._get_int_env(
            "TOKEN_EXPIRY_DAYS",
            None,  # Default: tokens never expire
        )

        # API settings
        self.api_host = os.getenv("API_HOST", "0.0.0.0")
        self.api_port = self._get_int_env("API_PORT", 8000)
        self.api_reload = self._get_bool_env("API_RELOAD", True)

        # CORS settings
        self.cors_origins = os.getenv(
            "CORS_ORIGINS",
            "*",  # In production, set specific origins
        ).split(",")

        # Development mode
        self.dev_mode = self._get_bool_env("DEV_MODE", True)

        # Default user creation (only in dev mode)
        self.create_default_user = self._get_bool_env(
            "CREATE_DEFAULT_USER",
            False,  # Disabled by default for security
        )
        self.default_user_token = os.getenv("DEFAULT_USER_TOKEN", None)
        self.default_user_name = os.getenv("DEFAULT_USER_NAME", None)

        # Rate limiting
        self.rate_limit_enabled = self._get_bool_env("RATE_LIMIT_ENABLED", True)
        self.rate_limit_requests = self._get_int_env("RATE_LIMIT_REQUESTS", 100)
        self.rate_limit_period = self._get_int_env("RATE_LIMIT_PERIOD", 60)  # seconds
        
        # API pagination defaults
        self.default_frontend_limit = self._get_int_env("DEFAULT_FRONTEND_LIMIT", 20)

        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Validate and generate missing required settings
        self._validate_settings()

    def _get_bool_env(self, key: str, default: bool) -> bool:
        """Parse boolean from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    def _get_int_env(self, key: str, default: int | None) -> int | None:
        """Parse integer from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _validate_settings(self) -> None:
        """Validate settings and generate missing security values."""
        # Generate token salt if not provided
        if not self.token_salt:
            import secrets

            self.token_salt = secrets.token_hex(32)
            self._save_generated_salt()

    def _save_generated_salt(self) -> None:
        """Save generated salt to .env file for persistence."""
        env_file = Path(".env")

        # Check if .env exists
        if env_file.exists():
            content = env_file.read_text()
            if "TOKEN_SALT" not in content:
                # Append to existing .env
                with open(env_file, "a") as f:
                    f.write("\n# Auto-generated security salt\n")
                    f.write(f"TOKEN_SALT={self.token_salt}\n")
        else:
            # Create new .env file
            with open(env_file, "w") as f:
                f.write("# MarktplaatsSearch API Configuration\n")
                f.write("# WARNING: Keep this file secret and never commit to version control\n\n")
                f.write("# Security Settings\n")
                f.write(f"TOKEN_SALT={self.token_salt}\n")
                f.write("# TOKEN_EXPIRY_DAYS=30  # Uncomment to enable token expiry\n\n")
                f.write("# API Settings\n")
                f.write("# API_HOST=0.0.0.0\n")
                f.write("# API_PORT=8000\n")
                f.write("# API_RELOAD=false  # Set to false in production\n\n")
                f.write("# CORS Settings\n")
                f.write("# CORS_ORIGINS=https://example.com,https://app.example.com\n\n")
                f.write("# Development Settings\n")
                f.write("DEV_MODE=false  # Set to false in production\n")
                f.write("CREATE_DEFAULT_USER=false  # Never enable in production\n\n")
                f.write("# Rate Limiting\n")
                f.write("# RATE_LIMIT_ENABLED=true\n")
                f.write("# RATE_LIMIT_REQUESTS=100\n")
                f.write("# RATE_LIMIT_PERIOD=60\n")


# Global settings instance
settings = Settings()

"""
Configuration management for the MarktplaatsSearch API.

This module provides comprehensive configuration for:
- Provider selection and management (HTML scraping vs Library API)
- Fallback logic and circuit breaker patterns
- Rate limiting and timeout settings
- Per-search provider overrides
- Health checks and monitoring
- Development and testing configurations

## Provider Configuration

### Provider Types
- HTML: Web scraping provider using BeautifulSoup and httpx
- LIBRARY: API-based provider using official libraries

### Environment Variables

#### Core Provider Settings:
- PRIMARY_PROVIDER: Main provider to use (html/library, default: html)
- SECONDARY_PROVIDER: Fallback provider (html/library, default: library)
- ALLOW_PROVIDER_OVERRIDE: Allow per-search overrides (true/false, default: true)

#### Fallback Configuration:
- FALLBACK_ENABLED: Enable provider fallback (true/false, default: true)
- FALLBACK_MAX_FAILURES: Max failures before fallback (int, default: 3)
- FALLBACK_FAILURE_WINDOW: Time window for failure counting in seconds (int, default: 300)
- FALLBACK_AUTO_RECOVERY: Enable automatic recovery (true/false, default: true)
- FALLBACK_RECOVERY_INTERVAL: Recovery check interval in seconds (int, default: 600)
- FALLBACK_PERFORMANCE_THRESHOLD: Performance threshold in ms (int, default: 5000)
- FALLBACK_CIRCUIT_BREAKER: Enable circuit breaker pattern (true/false, default: true)

#### HTML Provider Settings:
- HTML_PROVIDER_ENABLED: Enable HTML provider (true/false, default: true)
- HTML_PROVIDER_TIMEOUT: Request timeout in seconds (float, default: 30.0)
- HTML_PROVIDER_RATE_REQUESTS: Rate limit requests per period (int, default: 60)
- HTML_PROVIDER_RATE_PERIOD: Rate limit period in seconds (int, default: 60)
- HTML_PROVIDER_MAX_RETRIES: Maximum retry attempts (int, default: 3)
- HTML_PROVIDER_RETRY_DELAY: Delay between retries in seconds (float, default: 1.0)
- HTML_PROVIDER_CONCURRENT: Maximum concurrent requests (int, default: 5)
- HTML_PROVIDER_UA_ROTATION: Enable user agent rotation (true/false, default: true)
- HTML_PROVIDER_MIN_DELAY: Minimum delay between requests (float, default: 1.0)
- HTML_PROVIDER_MAX_DELAY: Maximum delay between requests (float, default: 3.0)
- HTML_PROVIDER_JAVASCRIPT: Enable JavaScript rendering (true/false, default: false)
- HTML_PROVIDER_PROXY: Enable proxy usage (true/false, default: false)
- HTML_PROVIDER_PROXY_ROTATION: Enable proxy rotation (true/false, default: false)

#### Library Provider Settings:
- LIBRARY_PROVIDER_ENABLED: Enable library provider (true/false, default: true)
- LIBRARY_PROVIDER_TIMEOUT: Request timeout in seconds (float, default: 15.0)
- LIBRARY_PROVIDER_RATE_REQUESTS: Rate limit requests per period (int, default: 120)
- LIBRARY_PROVIDER_RATE_PERIOD: Rate limit period in seconds (int, default: 60)
- LIBRARY_PROVIDER_MAX_RETRIES: Maximum retry attempts (int, default: 2)
- LIBRARY_PROVIDER_RETRY_DELAY: Delay between retries in seconds (float, default: 0.5)
- LIBRARY_PROVIDER_CONCURRENT: Maximum concurrent requests (int, default: 10)
- LIBRARY_PROVIDER_UA_ROTATION: Enable user agent rotation (true/false, default: false)
- LIBRARY_PROVIDER_API_KEY: API key for library provider
- LIBRARY_PROVIDER_API_SECRET: API secret for library provider
- LIBRARY_PROVIDER_CACHE: Enable response caching (true/false, default: true)
- LIBRARY_PROVIDER_CACHE_TTL: Cache TTL in seconds (int, default: 300)

#### Monitoring & Health Checks:
- PROVIDER_MONITORING_ENABLED: Enable monitoring (true/false, default: true)
- PROVIDER_METRICS_WINDOW: Metrics window size (int, default: 100)
- PROVIDER_PERFORMANCE_LOGGING: Enable performance logging (true/false, default: true)
- PROVIDER_HEALTH_CHECK: Enable health checks (true/false, default: true)
- PROVIDER_HEALTH_CHECK_INTERVAL: Health check interval in seconds (int, default: 300)
- PROVIDER_HEALTH_CHECK_TIMEOUT: Health check timeout in seconds (float, default: 10.0)

#### Development/Testing:
- FORCE_PROVIDER: Force specific provider for testing (html/library, optional)

## Usage Examples

### Basic Configuration
```python
from marktplaats_search.config import settings

# Get current provider configuration
primary_provider = settings.primary_provider
html_config = settings.html_provider
fallback_config = settings.fallback

# Check if provider is enabled
if settings.is_provider_enabled("html"):
    print("HTML provider is enabled")

# Get provider priority order
providers = settings.get_provider_priority_order()
```

### Provider Override Validation
```python
# Validate provider override
if settings.validate_provider_override("library"):
    effective_provider = settings.get_effective_provider("library")
else:
    effective_provider = settings.get_effective_provider()
```

### Configuration Export
```python
# Export safe configuration for logging
config_dict = settings.to_dict()
print(f"Configuration: {config_dict}")
```

## Security Considerations
- API keys and secrets are excluded from configuration exports
- Token salt is automatically generated if not provided
- Sensitive settings are not logged or exposed in debug output
- Environment variables are used for all configuration to avoid hardcoding secrets

## Production Recommendations
- Set DEV_MODE=false in production
- Configure appropriate rate limits for your use case
- Enable fallback and circuit breaker patterns
- Set reasonable timeouts (HTML: 30s, Library: 15s)
- Monitor provider performance and health
- Use environment-specific configuration files
"""

import os
from enum import Enum
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ProviderType(str, Enum):
    """Available provider types for search operations."""

    HTML = "html"
    LIBRARY = "library"


class ProviderConfig:
    """Configuration for individual providers."""

    def __init__(
        self,
        enabled: bool = True,
        timeout: float = 30.0,
        rate_limit_requests: int = 60,
        rate_limit_period: int = 60,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        concurrent_requests: int = 5,
        user_agent_rotation: bool = True,
        **kwargs: Any,
    ) -> None:
        self.enabled = enabled
        self.timeout = timeout
        self.rate_limit_requests = rate_limit_requests
        self.rate_limit_period = rate_limit_period
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.concurrent_requests = concurrent_requests
        self.user_agent_rotation = user_agent_rotation
        # Store any additional provider-specific settings
        self.extra_settings = kwargs


class FallbackConfig:
    """Configuration for provider fallback behavior."""

    def __init__(
        self,
        enabled: bool = True,
        max_failures: int = 3,
        failure_window_seconds: int = 300,
        auto_recovery: bool = True,
        recovery_check_interval: int = 600,
        performance_threshold_ms: int = 5000,
        enable_circuit_breaker: bool = True,
    ) -> None:
        self.enabled = enabled
        self.max_failures = max_failures
        self.failure_window_seconds = failure_window_seconds
        self.auto_recovery = auto_recovery
        self.recovery_check_interval = recovery_check_interval
        self.performance_threshold_ms = performance_threshold_ms
        self.enable_circuit_breaker = enable_circuit_breaker


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

        # ===================
        # PROVIDER SETTINGS
        # ===================

        # Primary provider selection
        self.primary_provider = ProviderType(
            os.getenv("PRIMARY_PROVIDER", ProviderType.HTML.value).lower()
        )
        self.secondary_provider = ProviderType(
            os.getenv("SECONDARY_PROVIDER", ProviderType.LIBRARY.value).lower()
        )

        # Allow per-search provider overrides
        self.allow_provider_override = self._get_bool_env("ALLOW_PROVIDER_OVERRIDE", True)

        # Fallback configuration
        self.fallback = FallbackConfig(
            enabled=self._get_bool_env("FALLBACK_ENABLED", True),
            max_failures=self._get_int_env("FALLBACK_MAX_FAILURES", 3) or 3,
            failure_window_seconds=self._get_int_env("FALLBACK_FAILURE_WINDOW", 300) or 300,
            auto_recovery=self._get_bool_env("FALLBACK_AUTO_RECOVERY", True),
            recovery_check_interval=self._get_int_env("FALLBACK_RECOVERY_INTERVAL", 600) or 600,
            performance_threshold_ms=self._get_int_env("FALLBACK_PERFORMANCE_THRESHOLD", 5000)
            or 5000,
            enable_circuit_breaker=self._get_bool_env("FALLBACK_CIRCUIT_BREAKER", True),
        )

        # HTML Provider configuration
        self.html_provider = ProviderConfig(
            enabled=self._get_bool_env("HTML_PROVIDER_ENABLED", True),
            timeout=self._get_float_env("HTML_PROVIDER_TIMEOUT", 30.0),
            rate_limit_requests=self._get_int_env("HTML_PROVIDER_RATE_REQUESTS", 60) or 60,
            rate_limit_period=self._get_int_env("HTML_PROVIDER_RATE_PERIOD", 60) or 60,
            max_retries=self._get_int_env("HTML_PROVIDER_MAX_RETRIES", 3) or 3,
            retry_delay=self._get_float_env("HTML_PROVIDER_RETRY_DELAY", 1.0),
            concurrent_requests=self._get_int_env("HTML_PROVIDER_CONCURRENT", 5) or 5,
            user_agent_rotation=self._get_bool_env("HTML_PROVIDER_UA_ROTATION", True),
            # HTML-specific settings
            min_request_delay=self._get_float_env("HTML_PROVIDER_MIN_DELAY", 1.0),
            max_request_delay=self._get_float_env("HTML_PROVIDER_MAX_DELAY", 3.0),
            javascript_enabled=self._get_bool_env("HTML_PROVIDER_JAVASCRIPT", False),
            proxy_enabled=self._get_bool_env("HTML_PROVIDER_PROXY", False),
            proxy_rotation=self._get_bool_env("HTML_PROVIDER_PROXY_ROTATION", False),
        )

        # Library Provider configuration
        self.library_provider = ProviderConfig(
            enabled=self._get_bool_env("LIBRARY_PROVIDER_ENABLED", True),
            timeout=self._get_float_env("LIBRARY_PROVIDER_TIMEOUT", 15.0),
            rate_limit_requests=self._get_int_env("LIBRARY_PROVIDER_RATE_REQUESTS", 120) or 120,
            rate_limit_period=self._get_int_env("LIBRARY_PROVIDER_RATE_PERIOD", 60) or 60,
            max_retries=self._get_int_env("LIBRARY_PROVIDER_MAX_RETRIES", 2) or 2,
            retry_delay=self._get_float_env("LIBRARY_PROVIDER_RETRY_DELAY", 0.5),
            concurrent_requests=self._get_int_env("LIBRARY_PROVIDER_CONCURRENT", 10) or 10,
            user_agent_rotation=self._get_bool_env("LIBRARY_PROVIDER_UA_ROTATION", False),
            # Library-specific settings
            api_key=os.getenv("LIBRARY_PROVIDER_API_KEY"),
            api_secret=os.getenv("LIBRARY_PROVIDER_API_SECRET"),
            cache_enabled=self._get_bool_env("LIBRARY_PROVIDER_CACHE", True),
            cache_ttl=self._get_int_env("LIBRARY_PROVIDER_CACHE_TTL", 300) or 300,
        )

        # Provider monitoring and metrics
        self.monitoring_enabled = self._get_bool_env("PROVIDER_MONITORING_ENABLED", True)
        self.metrics_window_size = self._get_int_env("PROVIDER_METRICS_WINDOW", 100) or 100
        self.performance_logging = self._get_bool_env("PROVIDER_PERFORMANCE_LOGGING", True)

        # Development/Testing overrides
        force_provider_str = os.getenv("FORCE_PROVIDER")  # Override for testing
        self.force_provider: ProviderType | None = None
        if force_provider_str:
            self.force_provider = ProviderType(force_provider_str.lower())

        # Provider health check settings
        self.health_check_enabled = self._get_bool_env("PROVIDER_HEALTH_CHECK", True)
        self.health_check_interval = self._get_int_env("PROVIDER_HEALTH_CHECK_INTERVAL", 300) or 300
        self.health_check_timeout = self._get_float_env("PROVIDER_HEALTH_CHECK_TIMEOUT", 10.0)

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

    def _get_float_env(self, key: str, default: float) -> float:
        """Parse float from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _validate_settings(self) -> None:
        """Validate settings and generate missing security values."""
        # Generate token salt if not provided
        if not self.token_salt:
            import secrets

            self.token_salt = secrets.token_hex(32)
            self._save_generated_salt()

        # Validate provider configuration
        self._validate_provider_config()

    def _validate_provider_config(self) -> None:
        """Validate provider-specific configuration."""
        # Ensure at least one provider is enabled
        if not (self.html_provider.enabled or self.library_provider.enabled):
            raise ValueError("At least one provider must be enabled")

        # Validate provider types are valid
        try:
            if self.primary_provider not in ProviderType:
                raise ValueError(f"Invalid primary provider: {self.primary_provider}")
            if self.secondary_provider not in ProviderType:
                raise ValueError(f"Invalid secondary provider: {self.secondary_provider}")
        except ValueError as e:
            raise ValueError(f"Provider type validation failed: {e}") from e

        # Validate that primary provider is enabled
        primary_config = self._get_provider_config(self.primary_provider)
        if not primary_config.enabled:
            raise ValueError(f"Primary provider '{self.primary_provider}' is disabled")

        # Validate timeout values are reasonable
        if self.html_provider.timeout <= 0 or self.html_provider.timeout > 300:
            raise ValueError("HTML provider timeout must be between 0 and 300 seconds")

        if self.library_provider.timeout <= 0 or self.library_provider.timeout > 300:
            raise ValueError("Library provider timeout must be between 0 and 300 seconds")

        # Validate rate limiting configuration
        for provider_name, provider_config in [
            ("HTML", self.html_provider),
            ("Library", self.library_provider),
        ]:
            if provider_config.rate_limit_requests <= 0:
                raise ValueError(f"{provider_name} provider rate limit requests must be positive")
            if provider_config.rate_limit_period <= 0:
                raise ValueError(f"{provider_name} provider rate limit period must be positive")
            if provider_config.max_retries < 0:
                raise ValueError(f"{provider_name} provider max retries cannot be negative")
            if provider_config.retry_delay < 0:
                raise ValueError(f"{provider_name} provider retry delay cannot be negative")
            if provider_config.concurrent_requests <= 0:
                raise ValueError(f"{provider_name} provider concurrent requests must be positive")

        # Validate fallback configuration
        if self.fallback.enabled:
            if self.fallback.max_failures <= 0:
                raise ValueError("Fallback max failures must be positive")
            if self.fallback.failure_window_seconds <= 0:
                raise ValueError("Fallback failure window must be positive")
            if self.fallback.recovery_check_interval <= 0:
                raise ValueError("Fallback recovery check interval must be positive")
            if self.fallback.performance_threshold_ms <= 0:
                raise ValueError("Fallback performance threshold must be positive")

    def _get_provider_config(self, provider_type: ProviderType) -> ProviderConfig:
        """Get configuration for a specific provider type."""
        if provider_type == ProviderType.HTML:
            return self.html_provider
        elif provider_type == ProviderType.LIBRARY:
            return self.library_provider
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def get_provider_config(self, provider_type: ProviderType | str) -> ProviderConfig:
        """Public method to get provider configuration."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())
        return self._get_provider_config(provider_type)

    def is_provider_enabled(self, provider_type: ProviderType | str) -> bool:
        """Check if a provider is enabled."""
        if isinstance(provider_type, str):
            provider_type = ProviderType(provider_type.lower())
        return self._get_provider_config(provider_type).enabled

    def get_enabled_providers(self) -> list[ProviderType]:
        """Get list of all enabled providers."""
        enabled = []
        if self.html_provider.enabled:
            enabled.append(ProviderType.HTML)
        if self.library_provider.enabled:
            enabled.append(ProviderType.LIBRARY)
        return enabled

    def should_use_fallback(self) -> bool:
        """Check if fallback is enabled and configured."""
        return self.fallback.enabled and len(self.get_enabled_providers()) > 1

    def get_provider_priority_order(self) -> list[ProviderType]:
        """Get providers in order of priority (primary first, then secondary)."""
        order = []
        enabled_providers = self.get_enabled_providers()

        # Add primary provider if enabled
        if self.primary_provider in enabled_providers:
            order.append(self.primary_provider)

        # Add secondary provider if enabled and different from primary
        if (
            self.secondary_provider in enabled_providers
            and self.secondary_provider != self.primary_provider
        ):
            order.append(self.secondary_provider)

        # Add any remaining enabled providers
        for provider in enabled_providers:
            if provider not in order:
                order.append(provider)

        return order

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
            # Create new .env file with comprehensive configuration template
            self._create_env_template(env_file)

    def _create_env_template(self, env_file: Path) -> None:
        """Create a comprehensive .env template file."""
        with open(env_file, "w") as f:
            f.write("# MarktplaatsSearch API Configuration\n")
            f.write("# WARNING: Keep this file secret and never commit to version control\n\n")

            f.write("# ==================\n")
            f.write("# SECURITY SETTINGS\n")
            f.write("# ==================\n")
            f.write(f"TOKEN_SALT={self.token_salt}\n")
            f.write("# TOKEN_EXPIRY_DAYS=30  # Uncomment to enable token expiry\n\n")

            f.write("# ==================\n")
            f.write("# API SETTINGS\n")
            f.write("# ==================\n")
            f.write("# API_HOST=0.0.0.0\n")
            f.write("# API_PORT=8000\n")
            f.write("# API_RELOAD=false  # Set to false in production\n\n")

            f.write("# ==================\n")
            f.write("# CORS SETTINGS\n")
            f.write("# ==================\n")
            f.write("# CORS_ORIGINS=https://example.com,https://app.example.com\n\n")

            f.write("# ==================\n")
            f.write("# DEVELOPMENT SETTINGS\n")
            f.write("# ==================\n")
            f.write("DEV_MODE=false  # Set to false in production\n")
            f.write("CREATE_DEFAULT_USER=false  # Never enable in production\n\n")

            f.write("# ==================\n")
            f.write("# RATE LIMITING\n")
            f.write("# ==================\n")
            f.write("# RATE_LIMIT_ENABLED=true\n")
            f.write("# RATE_LIMIT_REQUESTS=100\n")
            f.write("# RATE_LIMIT_PERIOD=60\n\n")

            f.write("# ==================\n")
            f.write("# PROVIDER SETTINGS\n")
            f.write("# ==================\n")
            f.write("# Primary provider: html or library (default: html)\n")
            f.write("# PRIMARY_PROVIDER=html\n")
            f.write("# Secondary provider for fallback: html or library (default: library)\n")
            f.write("# SECONDARY_PROVIDER=library\n")
            f.write("# Allow per-search provider overrides (default: true)\n")
            f.write("# ALLOW_PROVIDER_OVERRIDE=true\n\n")

            f.write("# ==================\n")
            f.write("# FALLBACK CONFIGURATION\n")
            f.write("# ==================\n")
            f.write("# Enable provider fallback (default: true)\n")
            f.write("# FALLBACK_ENABLED=true\n")
            f.write("# Max failures before fallback (default: 3)\n")
            f.write("# FALLBACK_MAX_FAILURES=3\n")
            f.write("# Time window for failure counting in seconds (default: 300)\n")
            f.write("# FALLBACK_FAILURE_WINDOW=300\n")
            f.write("# Enable automatic recovery (default: true)\n")
            f.write("# FALLBACK_AUTO_RECOVERY=true\n")
            f.write("# Recovery check interval in seconds (default: 600)\n")
            f.write("# FALLBACK_RECOVERY_INTERVAL=600\n")
            f.write("# Performance threshold in milliseconds (default: 5000)\n")
            f.write("# FALLBACK_PERFORMANCE_THRESHOLD=5000\n")
            f.write("# Enable circuit breaker pattern (default: true)\n")
            f.write("# FALLBACK_CIRCUIT_BREAKER=true\n\n")

            f.write("# ==================\n")
            f.write("# HTML PROVIDER SETTINGS\n")
            f.write("# ==================\n")
            f.write("# Enable HTML scraping provider (default: true)\n")
            f.write("# HTML_PROVIDER_ENABLED=true\n")
            f.write("# Request timeout in seconds (default: 30.0)\n")
            f.write("# HTML_PROVIDER_TIMEOUT=30.0\n")
            f.write("# Rate limit: requests per period (default: 60)\n")
            f.write("# HTML_PROVIDER_RATE_REQUESTS=60\n")
            f.write("# Rate limit period in seconds (default: 60)\n")
            f.write("# HTML_PROVIDER_RATE_PERIOD=60\n")
            f.write("# Maximum retry attempts (default: 3)\n")
            f.write("# HTML_PROVIDER_MAX_RETRIES=3\n")
            f.write("# Delay between retries in seconds (default: 1.0)\n")
            f.write("# HTML_PROVIDER_RETRY_DELAY=1.0\n")
            f.write("# Maximum concurrent requests (default: 5)\n")
            f.write("# HTML_PROVIDER_CONCURRENT=5\n")
            f.write("# Enable user agent rotation (default: true)\n")
            f.write("# HTML_PROVIDER_UA_ROTATION=true\n")
            f.write("# Minimum delay between requests in seconds (default: 1.0)\n")
            f.write("# HTML_PROVIDER_MIN_DELAY=1.0\n")
            f.write("# Maximum delay between requests in seconds (default: 3.0)\n")
            f.write("# HTML_PROVIDER_MAX_DELAY=3.0\n")
            f.write("# Enable JavaScript rendering (default: false)\n")
            f.write("# HTML_PROVIDER_JAVASCRIPT=false\n")
            f.write("# Enable proxy usage (default: false)\n")
            f.write("# HTML_PROVIDER_PROXY=false\n")
            f.write("# Enable proxy rotation (default: false)\n")
            f.write("# HTML_PROVIDER_PROXY_ROTATION=false\n\n")

            f.write("# ==================\n")
            f.write("# LIBRARY PROVIDER SETTINGS\n")
            f.write("# ==================\n")
            f.write("# Enable library-based provider (default: true)\n")
            f.write("# LIBRARY_PROVIDER_ENABLED=true\n")
            f.write("# Request timeout in seconds (default: 15.0)\n")
            f.write("# LIBRARY_PROVIDER_TIMEOUT=15.0\n")
            f.write("# Rate limit: requests per period (default: 120)\n")
            f.write("# LIBRARY_PROVIDER_RATE_REQUESTS=120\n")
            f.write("# Rate limit period in seconds (default: 60)\n")
            f.write("# LIBRARY_PROVIDER_RATE_PERIOD=60\n")
            f.write("# Maximum retry attempts (default: 2)\n")
            f.write("# LIBRARY_PROVIDER_MAX_RETRIES=2\n")
            f.write("# Delay between retries in seconds (default: 0.5)\n")
            f.write("# LIBRARY_PROVIDER_RETRY_DELAY=0.5\n")
            f.write("# Maximum concurrent requests (default: 10)\n")
            f.write("# LIBRARY_PROVIDER_CONCURRENT=10\n")
            f.write("# Enable user agent rotation (default: false)\n")
            f.write("# LIBRARY_PROVIDER_UA_ROTATION=false\n")
            f.write("# API key for library provider\n")
            f.write("# LIBRARY_PROVIDER_API_KEY=\n")
            f.write("# API secret for library provider\n")
            f.write("# LIBRARY_PROVIDER_API_SECRET=\n")
            f.write("# Enable response caching (default: true)\n")
            f.write("# LIBRARY_PROVIDER_CACHE=true\n")
            f.write("# Cache TTL in seconds (default: 300)\n")
            f.write("# LIBRARY_PROVIDER_CACHE_TTL=300\n\n")

            f.write("# ==================\n")
            f.write("# MONITORING & METRICS\n")
            f.write("# ==================\n")
            f.write("# Enable provider monitoring (default: true)\n")
            f.write("# PROVIDER_MONITORING_ENABLED=true\n")
            f.write("# Metrics window size for averaging (default: 100)\n")
            f.write("# PROVIDER_METRICS_WINDOW=100\n")
            f.write("# Enable performance logging (default: true)\n")
            f.write("# PROVIDER_PERFORMANCE_LOGGING=true\n\n")

            f.write("# ==================\n")
            f.write("# HEALTH CHECKS\n")
            f.write("# ==================\n")
            f.write("# Enable provider health checks (default: true)\n")
            f.write("# PROVIDER_HEALTH_CHECK=true\n")
            f.write("# Health check interval in seconds (default: 300)\n")
            f.write("# PROVIDER_HEALTH_CHECK_INTERVAL=300\n")
            f.write("# Health check timeout in seconds (default: 10.0)\n")
            f.write("# PROVIDER_HEALTH_CHECK_TIMEOUT=10.0\n\n")

            f.write("# ==================\n")
            f.write("# DEVELOPMENT/TESTING\n")
            f.write("# ==================\n")
            f.write("# Force use of specific provider (html or library)\n")
            f.write("# FORCE_PROVIDER=\n")
            f.write("# Uncomment to force a specific provider for testing\n")

    def to_dict(self) -> dict[str, Any]:
        """Export configuration as dictionary for debugging/logging."""
        config_dict: dict[str, Any] = {}

        # Basic settings
        config_dict.update(
            {
                "primary_provider": self.primary_provider.value,
                "secondary_provider": self.secondary_provider.value,
                "allow_provider_override": self.allow_provider_override,
                "dev_mode": self.dev_mode,
                "monitoring_enabled": self.monitoring_enabled,
                "force_provider": self.force_provider.value if self.force_provider else None,
            }
        )

        # Fallback config
        fallback_config: dict[str, Any] = {
            "enabled": self.fallback.enabled,
            "max_failures": self.fallback.max_failures,
            "failure_window_seconds": self.fallback.failure_window_seconds,
            "auto_recovery": self.fallback.auto_recovery,
            "performance_threshold_ms": self.fallback.performance_threshold_ms,
            "circuit_breaker": self.fallback.enable_circuit_breaker,
        }
        config_dict["fallback"] = fallback_config

        # Provider configs (excluding sensitive info)
        for provider_name, provider_config in [
            ("html", self.html_provider),
            ("library", self.library_provider),
        ]:
            provider_dict: dict[str, Any] = {
                "enabled": provider_config.enabled,
                "timeout": provider_config.timeout,
                "rate_limit_requests": provider_config.rate_limit_requests,
                "rate_limit_period": provider_config.rate_limit_period,
                "max_retries": provider_config.max_retries,
                "concurrent_requests": provider_config.concurrent_requests,
                "user_agent_rotation": provider_config.user_agent_rotation,
            }

            # Add non-sensitive extra settings
            safe_extra_settings = {
                k: v
                for k, v in provider_config.extra_settings.items()
                if k not in ["api_key", "api_secret", "password", "token"]
            }
            if safe_extra_settings:
                provider_dict["extra_settings"] = safe_extra_settings

            config_dict[f"{provider_name}_provider"] = provider_dict

        return config_dict

    def validate_provider_override(self, provider_type: str | ProviderType) -> bool:
        """
        Validate if a provider override is allowed and valid.

        Args:
            provider_type: Provider type to validate

        Returns:
            True if override is valid and allowed, False otherwise
        """
        if not self.allow_provider_override:
            return False

        if isinstance(provider_type, str):
            try:
                provider_type = ProviderType(provider_type.lower())
            except ValueError:
                return False

        return self.is_provider_enabled(provider_type)

    def get_effective_provider(
        self, override_provider: str | ProviderType | None = None
    ) -> ProviderType:
        """
        Get the effective provider to use, considering overrides and force settings.

        Args:
            override_provider: Optional provider override

        Returns:
            The provider type to use
        """
        # Force provider takes precedence (for testing)
        if self.force_provider:
            return self.force_provider

        # Check if override is valid and allowed
        if override_provider and self.validate_provider_override(override_provider):
            if isinstance(override_provider, str):
                return ProviderType(override_provider.lower())
            elif isinstance(override_provider, ProviderType):
                return override_provider
            # If override_provider is neither str nor ProviderType, ignore it and continue

        # Fall back to primary provider if enabled, then any enabled provider
        enabled_providers = self.get_enabled_providers()

        # Prefer primary provider if it's in the enabled list
        if self.primary_provider in enabled_providers:
            return self.primary_provider
        elif enabled_providers:
            return enabled_providers[0]
        else:
            # This should never happen due to validation, but just in case
            raise ValueError("No providers are enabled")


# Global settings instance
settings = Settings()

"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from marktplaats_search.config import Settings
from marktplaats_search.providers.base import ProviderType


class TestSettings:
    """Test configuration settings functionality."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.database_url == "sqlite+aiosqlite:///./data/marktplaats_api.db"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.dev_mode is True
        assert settings.primary_provider == ProviderType.HTML_SCRAPER
        assert settings.secondary_provider == ProviderType.MARKTPLAATS_LIBRARY

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://test:test@localhost/testdb",
                "API_PORT": "9000",
                "DEV_MODE": "false",
                "PRIMARY_PROVIDER": "library",
            },
        ):
            settings = Settings()

            assert settings.database_url == "postgresql://test:test@localhost/testdb"
            assert settings.api_port == 9000
            assert settings.dev_mode is False
            assert settings.primary_provider == ProviderType.MARKTPLAATS_LIBRARY

    def test_provider_validation(self):
        """Test provider configuration validation."""
        settings = Settings()

        # At least one provider should be enabled
        assert settings.html_provider.enabled or settings.library_provider.enabled

        # Primary provider should be enabled
        primary_config = settings._get_provider_config(settings.primary_provider)
        assert primary_config.enabled

    def test_invalid_provider_configuration(self):
        """Test validation of invalid provider configuration."""
        with (
            patch.dict(
                os.environ, {"HTML_PROVIDER_ENABLED": "false", "LIBRARY_PROVIDER_ENABLED": "false"}
            ),
            pytest.raises(ValueError, match="At least one provider must be enabled"),
        ):
            Settings()

    def test_get_sync_database_url(self):
        """Test synchronous database URL generation."""
        settings = Settings()

        # Test with aiosqlite URL
        settings.database_url = "sqlite+aiosqlite:///./test.db"
        sync_url = settings.get_sync_database_url()
        assert sync_url == "sqlite:///./test.db"

        # Test with regular URL (no change)
        settings.database_url = "postgresql://user:pass@localhost/db"
        sync_url = settings.get_sync_database_url()
        assert sync_url == "postgresql://user:pass@localhost/db"

    def test_provider_priority_order(self):
        """Test provider priority ordering."""
        settings = Settings()

        providers = settings.get_provider_priority_order()

        # Should have at least one provider
        assert len(providers) > 0

        # Primary should be first if enabled
        if settings.primary_provider in settings.get_enabled_providers():
            assert providers[0] == settings.primary_provider

    def test_boolean_environment_parsing(self):
        """Test boolean environment variable parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("invalid", False),
        ]

        Settings()

        for env_value, expected in test_cases:
            with patch.dict(os.environ, {"DEV_MODE": env_value}):
                # Create new instance to test parsing
                test_settings = Settings()
                assert test_settings.dev_mode == expected

    def test_rate_limiting_configuration(self):
        """Test rate limiting configuration validation."""
        settings = Settings()

        # Rate limits should be positive
        assert settings.html_provider.rate_limit_requests > 0
        assert settings.html_provider.rate_limit_period > 0
        assert settings.library_provider.rate_limit_requests > 0
        assert settings.library_provider.rate_limit_period > 0

    def test_timeout_validation(self):
        """Test timeout value validation."""
        settings = Settings()

        # Timeouts should be reasonable
        assert 0 < settings.html_provider.timeout <= 300
        assert 0 < settings.library_provider.timeout <= 300

    def test_fallback_configuration(self):
        """Test fallback configuration."""
        settings = Settings()

        if settings.fallback.enabled:
            assert settings.fallback.max_failures > 0
            assert settings.fallback.failure_window_seconds > 0
            assert settings.fallback.performance_threshold_ms > 0

"""Provider manager for coordinating multiple Marktplaats providers.

This module manages multiple providers with fallback logic, rate limiting coordination,
and intelligent provider selection for enterprise-grade reliability.
"""

import asyncio
import contextlib
import logging
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, validator

from .base import (
    MarktplaatsProvider,
    ProviderConfig,
    ProviderResult,
    ProviderType,
    SearchContext,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ProviderManagerConfig(BaseModel):
    """Configuration for the provider manager."""

    primary_provider: ProviderType = ProviderType.HTML_SCRAPER
    fallback_providers: list[ProviderType] = Field(
        default_factory=lambda: [ProviderType.MARKTPLAATS_LIBRARY]
    )
    max_concurrent_requests: int = Field(default=3, ge=1, le=10)
    global_timeout_seconds: int = Field(default=60, ge=10, le=300)
    enable_provider_switching: bool = True
    health_check_interval_seconds: int = Field(default=300, ge=60, le=3600)
    metrics_collection_enabled: bool = True
    retry_failed_providers: bool = True
    provider_configs: dict[str, ProviderConfig] = Field(default_factory=dict)

    @validator("fallback_providers")
    def validate_fallback_providers(
        cls, v: list[ProviderType], values: dict[str, Any]
    ) -> list[ProviderType]:
        """Ensure fallback providers don't include primary provider."""
        primary = values.get("primary_provider")
        if primary and primary in v:
            v = v.copy()  # Don't mutate the original list
            v.remove(primary)
        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class ListingProviderManager:
    """Manages multiple Marktplaats providers with intelligent failover and load balancing."""

    def __init__(self, config: ProviderManagerConfig) -> None:
        """Initialize the provider manager.

        Args:
            config: Manager configuration
        """
        self.config = config
        self.providers: dict[ProviderType, MarktplaatsProvider] = {}
        self.logger = logging.getLogger(f"{__name__}.manager")

        # Metrics tracking
        self._search_count = 0
        self._success_count = 0
        self._error_count = 0
        self._provider_stats: dict[ProviderType, dict[str, Any]] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "errors": 0, "avg_time_ms": 0.0}
        )

        # Health monitoring
        self._health_check_task: asyncio.Task[None] | None = None
        self._last_health_check: datetime | None = None

    def register_provider(
        self, provider: MarktplaatsProvider, provider_type: ProviderType | None = None
    ) -> None:
        """Register a provider with the manager.

        Args:
            provider: The provider instance to register
            provider_type: Optional provider type override
        """
        if provider_type is None:
            provider_type = provider.provider_type

        self.providers[provider_type] = provider
        provider_type_str = (
            provider_type.value if hasattr(provider_type, "value") else str(provider_type)
        )
        self.logger.info(f"Registered provider: {provider_type_str}")

    def unregister_provider(self, provider_type: ProviderType) -> None:
        """Unregister a provider from the manager.

        Args:
            provider_type: Type of provider to unregister
        """
        if provider_type in self.providers:
            del self.providers[provider_type]
            provider_type_str = (
                provider_type.value if hasattr(provider_type, "value") else str(provider_type)
            )
            self.logger.info(f"Unregistered provider: {provider_type_str}")

    async def initialize(self) -> None:
        """Initialize the provider manager and register providers."""
        # Register HTML scraper provider
        from .html_scraper import HtmlScrapingProvider

        html_config = self.config.provider_configs.get(ProviderType.HTML_SCRAPER.value)
        if html_config is None:
            html_config = ProviderConfig(provider_type=ProviderType.HTML_SCRAPER)

        html_provider = HtmlScrapingProvider(html_config)
        self.register_provider(html_provider)

        # Try to register library provider if available
        try:
            from .marktplaats_library_provider import (
                MarktplaatsLibraryProvider,
                MarktplaatsLibraryProviderConfig,
            )

            library_config = self.config.provider_configs.get(
                ProviderType.MARKTPLAATS_LIBRARY.value
            )
            if library_config is None:
                library_provider_config = MarktplaatsLibraryProviderConfig()
            else:
                # Convert generic config to library-specific config
                library_provider_config = MarktplaatsLibraryProviderConfig(
                    **library_config.model_dump()
                )

            library_provider = MarktplaatsLibraryProvider(library_provider_config)
            self.register_provider(library_provider)
        except ImportError:
            self.logger.info("Marktplaats library provider not available, skipping registration")

    async def shutdown(self) -> None:
        """Shutdown the provider manager and cleanup resources."""
        await self.cleanup()

    async def get_provider_status(self) -> dict[str, Any]:
        """Get comprehensive status of all providers."""
        provider_info = {}

        for provider_type, provider in self.providers.items():
            provider_info[provider_type.value] = await provider.get_provider_info()

        return {
            "providers": provider_info,
            "metrics": self.get_manager_metrics(),
            "health_check_status": await self.health_check_all_providers(),
        }

    async def search_listings(
        self, context: SearchContext, preferred_provider: ProviderType | None = None
    ) -> ProviderResult:
        """Search for listings using the configured provider strategy.

        Args:
            context: Search parameters and context
            preferred_provider: Optional preferred provider to try first

        Returns:
            ProviderResult with listings or error information
        """
        self._search_count += 1
        start_time = datetime.now()

        # Determine provider order: preferred first (if specified), then primary, then fallbacks
        provider_order = []
        if preferred_provider:
            provider_order.append(preferred_provider)

        # Add primary provider if not already in list
        if self.config.primary_provider not in provider_order:
            provider_order.append(self.config.primary_provider)

        # Add fallbacks if provider switching is enabled
        if self.config.enable_provider_switching:
            for fallback in self.config.fallback_providers:
                if fallback not in provider_order:
                    provider_order.append(fallback)

        # Filter to only registered and healthy providers
        available_providers = []
        for provider_type in provider_order:
            provider = self.providers.get(provider_type)
            if provider and provider.is_available:
                available_providers.append((provider_type, provider))

        if not available_providers:
            self._error_count += 1
            # Convert string to enum if needed for error response
            primary_type = (
                ProviderType(self.config.primary_provider)
                if isinstance(self.config.primary_provider, str)
                else self.config.primary_provider
            )
            return ProviderResult(
                listings=[],
                provider_type=primary_type,
                success=False,
                error_message="No available providers",
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
            )

        # Try each provider in order
        last_result = None
        for provider_type, provider in available_providers:
            try:
                self.logger.info(f"Attempting search with provider: {provider_type.value}")

                # Update provider stats
                self._provider_stats[provider_type]["attempts"] += 1

                # Perform search with timeout
                result = await asyncio.wait_for(
                    provider.search_listings(context), timeout=self.config.global_timeout_seconds
                )

                if result.success:
                    # Update success metrics
                    self._success_count += 1
                    self._provider_stats[provider_type]["successes"] += 1

                    # Update average time
                    stats = self._provider_stats[provider_type]
                    if result.execution_time_ms:
                        old_avg = stats["avg_time_ms"]
                        stats["avg_time_ms"] = (
                            old_avg * (stats["successes"] - 1) + result.execution_time_ms
                        ) / stats["successes"]

                    self.logger.info(
                        f"Search successful with provider {provider_type.value}: "
                        f"{len(result.listings)} listings found"
                    )

                    return result
                else:
                    # Provider returned unsuccessful result
                    self._provider_stats[provider_type]["errors"] += 1
                    self.logger.warning(
                        f"Provider {provider_type.value} returned unsuccessful result: "
                        f"{result.error_message}"
                    )
                    last_result = result

            except TimeoutError:
                self._provider_stats[provider_type]["errors"] += 1
                self.logger.warning(
                    f"Provider {provider_type.value} timed out after "
                    f"{self.config.global_timeout_seconds}s"
                )
                last_result = ProviderResult(
                    listings=[],
                    provider_type=provider_type,
                    success=False,
                    error_message=f"Provider timed out after {self.config.global_timeout_seconds}s",
                    execution_time_ms=self.config.global_timeout_seconds * 1000,
                )

            except Exception as e:
                self._provider_stats[provider_type]["errors"] += 1
                self.logger.error(f"Provider {provider_type.value} failed: {e}")
                last_result = ProviderResult(
                    listings=[],
                    provider_type=provider_type,
                    success=False,
                    error_message=str(e),
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                )

        # All providers failed
        self._error_count += 1
        self.logger.error("All providers failed for search")

        return last_result or ProviderResult(
            listings=[],
            provider_type=self.config.primary_provider,
            success=False,
            error_message="All providers failed",
            execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
        )

    async def health_check_all_providers(self) -> dict[ProviderType, bool]:
        """Perform health checks on all registered providers.

        Returns:
            Dictionary mapping provider type to health status
        """
        health_results = {}

        for provider_type, provider in self.providers.items():
            try:
                is_healthy = await provider.health_check()
                health_results[provider_type] = is_healthy

                if not is_healthy:
                    self.logger.warning(f"Provider {provider_type.value} failed health check")

            except Exception as e:
                self.logger.error(f"Health check error for provider {provider_type.value}: {e}")
                health_results[provider_type] = False

        self._last_health_check = datetime.now()

        healthy_count = sum(health_results.values())
        total_count = len(health_results)
        self.logger.info(f"Health check completed: {healthy_count}/{total_count} providers healthy")

        return health_results

    async def start_health_monitoring(self) -> None:
        """Start background health monitoring."""
        if self._health_check_task and not self._health_check_task.done():
            self.logger.warning("Health monitoring already running")
            return

        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        self.logger.info("Started health monitoring")

    async def stop_health_monitoring(self) -> None:
        """Stop background health monitoring."""
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_check_task
            self.logger.info("Stopped health monitoring")

    async def _health_monitor_loop(self) -> None:
        """Background health monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self.health_check_all_providers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")

    def get_manager_metrics(self) -> dict[str, Any]:
        """Get manager metrics and statistics.

        Returns:
            Dictionary containing manager metrics
        """
        return {
            "total_searches": self._search_count,
            "successful_searches": self._success_count,
            "failed_searches": self._error_count,
            "success_rate": self._success_count / max(self._search_count, 1),
            "registered_providers": list(self.providers.keys()),
            "provider_stats": dict(self._provider_stats),
            "last_health_check": self._last_health_check.isoformat()
            if self._last_health_check
            else None,
            "config": {
                "primary_provider": self.config.primary_provider.value,
                "fallback_providers": [p.value for p in self.config.fallback_providers],
                "max_concurrent_requests": self.config.max_concurrent_requests,
                "global_timeout_seconds": self.config.global_timeout_seconds,
            },
        }

    async def cleanup(self) -> None:
        """Cleanup manager and provider resources."""
        # Stop health monitoring
        await self.stop_health_monitoring()

        # Cleanup all providers
        for provider_type, provider in self.providers.items():
            try:
                if hasattr(provider, "cleanup"):
                    await provider.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up provider {provider_type.value}: {e}")

    async def __aenter__(self) -> "ListingProviderManager":
        """Async context manager entry."""
        await self.start_health_monitoring()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.cleanup()

    def __repr__(self) -> str:
        """Return string representation of the manager."""
        return (
            f"ListingProviderManager("
            f"providers={len(self.providers)}, "
            f"primary={self.config.primary_provider.value}, "
            f"searches={self._search_count})"
        )

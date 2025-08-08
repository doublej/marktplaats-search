"""Abstract base provider for Marktplaats listing retrieval.

This module defines the abstract interface that all Marktplaats providers must implement,
ensuring consistent behavior across different data sources (HTML scraping, API library).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ..client import ListingItem

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Available provider types for listing retrieval."""

    HTML_SCRAPER = "html_scraper"
    MARKTPLAATS_LIBRARY = "marktplaats_library"


class ProviderStatus(str, Enum):
    """Provider operational status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class SearchContext:
    """Context information for a search operation."""

    search_id: str
    query: str
    zip_code: str | None = None
    distance: int | None = None
    price_from: int | None = None
    price_to: int | None = None
    limit: int = 10
    sort_by: str | None = None
    sort_order: str | None = None
    search_timestamp: datetime = field(default_factory=datetime.now)
    user_agent: str | None = None
    timeout_seconds: int = 30


@dataclass
class ProviderResult:
    """Result from a provider search operation."""

    listings: list[ListingItem]
    provider_type: ProviderType
    success: bool
    error_message: str | None = None
    execution_time_ms: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: datetime | None = None
    source_metadata: dict[str, Any] | None = None


class ProviderConfig(BaseModel):
    """Configuration for a Marktplaats provider."""

    provider_type: ProviderType
    enabled: bool = True
    priority: int = Field(default=100, ge=1, le=1000, description="Lower numbers = higher priority")
    timeout_seconds: int = Field(default=30, ge=5, le=300)
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_delay_seconds: float = Field(default=1.0, ge=0.1, le=60.0)
    rate_limit_requests_per_minute: int = Field(default=30, ge=1, le=300)
    rate_limit_burst_size: int = Field(default=5, ge=1, le=50)
    health_check_interval_seconds: int = Field(default=300, ge=60, le=3600)
    circuit_breaker_threshold: int = Field(default=5, ge=1, le=20)
    circuit_breaker_timeout_seconds: int = Field(default=60, ge=10, le=3600)
    provider_specific_config: dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""

        use_enum_values = True


class MarktplaatsProvider(ABC):
    """Abstract base class for all Marktplaats providers.

    This class defines the common interface that all providers must implement
    to ensure consistent behavior and interoperability within the system.
    """

    def __init__(self, config: ProviderConfig) -> None:
        """Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._status = ProviderStatus.HEALTHY
        self._last_error: Exception | None = None
        self._consecutive_errors = 0
        self._last_health_check: datetime | None = None

    @property
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        return self.config.provider_type

    @property
    def status(self) -> ProviderStatus:
        """Return current provider status."""
        return self._status

    @property
    def is_healthy(self) -> bool:
        """Check if provider is in healthy state."""
        return self._status == ProviderStatus.HEALTHY

    @property
    def is_available(self) -> bool:
        """Check if provider is available for use."""
        return self._status != ProviderStatus.UNAVAILABLE

    @property
    def last_error(self) -> Exception | None:
        """Return the last error encountered."""
        return self._last_error

    @abstractmethod
    async def search_listings(self, context: SearchContext) -> ProviderResult:
        """Search for listings using this provider.

        Args:
            context: Search parameters and context information

        Returns:
            ProviderResult containing listings and metadata

        Raises:
            Exception: Provider-specific errors (should be caught and handled)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Perform health check on the provider.

        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    async def get_provider_info(self) -> dict[str, Any]:
        """Get provider information and status.

        Returns:
            Dictionary containing provider metadata
        """
        provider_type_str = (
            self.provider_type.value
            if hasattr(self.provider_type, "value")
            else str(self.provider_type)
        )
        status_str = self.status.value if hasattr(self.status, "value") else str(self.status)
        return {
            "provider_type": provider_type_str,
            "status": status_str,
            "enabled": self.config.enabled,
            "priority": self.config.priority,
            "consecutive_errors": self._consecutive_errors,
            "last_error": str(self._last_error) if self._last_error else None,
            "last_health_check": self._last_health_check.isoformat()
            if self._last_health_check
            else None,
            "rate_limit_config": {
                "requests_per_minute": self.config.rate_limit_requests_per_minute,
                "burst_size": self.config.rate_limit_burst_size,
            },
            "circuit_breaker_config": {
                "threshold": self.config.circuit_breaker_threshold,
                "timeout_seconds": self.config.circuit_breaker_timeout_seconds,
            },
        }

    def _update_status(self, status: ProviderStatus, error: Exception | None = None) -> None:
        """Update provider status and error tracking.

        Args:
            status: New provider status
            error: Optional error that caused the status change
        """
        self._status = status
        if error:
            self._last_error = error
            self._consecutive_errors += 1
            self.logger.warning(
                f"Provider {self.provider_type.value} error #{self._consecutive_errors}: {error}"
            )
        else:
            self._consecutive_errors = 0
            self._last_error = None

        # Implement circuit breaker logic
        if self._consecutive_errors >= self.config.circuit_breaker_threshold:
            self._status = ProviderStatus.UNAVAILABLE
            self.logger.error(
                f"Provider {self.provider_type.value} circuit breaker triggered "
                f"after {self._consecutive_errors} consecutive errors"
            )

    async def _execute_with_circuit_breaker(self, operation_name: str, operation) -> Any:
        """Execute an operation with circuit breaker protection.

        Args:
            operation_name: Name of the operation for logging
            operation: Async callable to execute

        Returns:
            Result of the operation

        Raises:
            Exception: If circuit breaker is open or operation fails
        """
        if self._status == ProviderStatus.UNAVAILABLE:
            # Check if circuit breaker timeout has passed
            if (
                self._last_health_check
                and (datetime.now() - self._last_health_check).seconds
                < self.config.circuit_breaker_timeout_seconds
            ):
                raise Exception(f"Provider {self.provider_type.value} circuit breaker is open")

            # Try to reset circuit breaker
            self.logger.info(
                f"Attempting to reset circuit breaker for provider {self.provider_type.value}"
            )
            if await self.health_check():
                self._update_status(ProviderStatus.HEALTHY)
                self.logger.info(f"Circuit breaker reset for provider {self.provider_type.value}")
            else:
                self._last_health_check = datetime.now()
                raise Exception(f"Provider {self.provider_type.value} health check failed")

        try:
            result = await operation()
            self._update_status(ProviderStatus.HEALTHY)
            return result
        except Exception as e:
            self._update_status(ProviderStatus.DEGRADED, e)
            raise

    def __repr__(self) -> str:
        """Return string representation of the provider."""
        provider_type_str = (
            self.provider_type.value
            if hasattr(self.provider_type, "value")
            else str(self.provider_type)
        )
        status_str = self.status.value if hasattr(self.status, "value") else str(self.status)
        return (
            f"{self.__class__.__name__}("
            f"type={provider_type_str}, "
            f"status={status_str}, "
            f"priority={self.config.priority})"
        )

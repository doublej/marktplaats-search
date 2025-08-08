import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLAlchemyEnum  # Avoid conflict with standard enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # Works with SQLite for UUID type
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_identifier: Mapped[str] = mapped_column(String, unique=True, index=True)
    api_token_hash: Mapped[str] = mapped_column(
        String, unique=True, index=True
    )  # Store hash instead of plaintext
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # Account status
    token_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )  # Track token age
    last_activity: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # Track last API usage
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    searches = relationship("Search", back_populates="owner", cascade="all, delete-orphan")


class SearchStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PriceTypeEnum(str, enum.Enum):
    """Price types from marktplaats library."""

    FREE = "FREE"
    BID = "FAST_BID"
    RESERVED = "RESERVED"
    SEE_DESCRIPTION = "SEE_DESCRIPTION"
    TO_BE_AGREED_UPON = "NOTK"
    ON_REQUEST = "ON_REQUEST"
    EXCHANGE = "EXCHANGE"
    FIXED = "FIXED"
    BID_FROM = "MIN_BID"
    UNKNOWN = "UNKNOWN"


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )

    # Search parameters
    query: Mapped[str] = mapped_column(String)
    zip_code: Mapped[str | None] = mapped_column(String)
    distance: Mapped[int | None] = mapped_column(Integer)
    price_from: Mapped[int | None] = mapped_column(Integer)
    price_to: Mapped[int | None] = mapped_column(Integer)
    limit: Mapped[int] = mapped_column(Integer, default=25)
    sort_by: Mapped[str | None] = mapped_column(String)
    sort_order: Mapped[str | None] = mapped_column(String)

    interval: Mapped[int] = mapped_column(Integer)  # Interval in seconds

    status: Mapped[SearchStatus] = mapped_column(
        SQLAlchemyEnum(SearchStatus), default=SearchStatus.ACTIVE
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    # Provider configuration and tracking
    preferred_provider: Mapped[str | None] = mapped_column(
        String
    )  # Preferred provider name for this search
    provider_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Search-specific provider configuration
    last_successful_provider: Mapped[str | None] = mapped_column(
        String
    )  # Track which provider last succeeded
    provider_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Store provider usage metrics per search

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="searches")

    listings = relationship("Listing", back_populates="search", cascade="all, delete-orphan")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    search_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("searches.id"), index=True
    )

    # Core listing data from marktplaats library
    marktplaats_id: Mapped[str | None] = mapped_column(
        String, index=True
    )  # ID from Marktplaats API
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float | None] = mapped_column(Float)  # Price as float from marktplaats library
    price_type: Mapped[PriceTypeEnum | None] = mapped_column(SQLAlchemyEnum(PriceTypeEnum))
    url: Mapped[str] = mapped_column(String, index=True)  # Link from marktplaats library
    date_posted: Mapped[date | None] = mapped_column(Date)  # Original post date from marktplaats

    # Legacy fields for backward compatibility
    source_listing_id: Mapped[str | None] = mapped_column(
        String, index=True
    )  # Alias for marktplaats_id
    price_numeric: Mapped[int | None] = mapped_column(
        Integer, index=True
    )  # Numeric price in cents for sorting/filtering
    description_snippet: Mapped[str | None] = mapped_column(Text)  # Alias for description
    image_url: Mapped[str | None] = mapped_column(String)  # Primary image URL

    # Location data from marktplaats library
    location_city: Mapped[str | None] = mapped_column(String)
    location_country: Mapped[str | None] = mapped_column(String)
    location_country_short: Mapped[str | None] = mapped_column(String)
    location_latitude: Mapped[float | None] = mapped_column(Float)
    location_longitude: Mapped[float | None] = mapped_column(Float)
    location_distance: Mapped[int | None] = mapped_column(Integer)

    # Seller data from marktplaats library
    seller_id: Mapped[int | None] = mapped_column(Integer, index=True)
    seller_name: Mapped[str | None] = mapped_column(String)
    seller_is_verified: Mapped[bool | None] = mapped_column(Boolean)

    # Category and attributes from marktplaats library
    category_id: Mapped[int | None] = mapped_column(Integer, index=True)
    attributes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)  # List of attribute dicts
    extended_attributes: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON
    )  # List of extended attribute dicts

    # Image data from marktplaats library
    image_extra_small = Column(String, nullable=True)
    image_medium = Column(String, nullable=True)
    image_large = Column(String, nullable=True)
    image_extra_large = Column(String, nullable=True)
    images = Column(JSON, nullable=True)  # All available images

    # Legacy fields maintained for compatibility
    condition: Mapped[str | None] = mapped_column(String)  # Item condition as string
    views: Mapped[int | None] = mapped_column(Integer)  # Number of views (from legacy scraper)
    location: Mapped[str | None] = mapped_column(String)  # Legacy location field
    seller: Mapped[str | None] = mapped_column(String)  # Legacy seller field

    raw_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # Store full raw data from source if needed
    raw_html: Mapped[str | None] = mapped_column(Text)  # Store original HTML from Marktplaats
    is_new: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Provider tracking
    provider_name = Column(String, nullable=True, index=True)  # Which provider found this listing
    provider_type = Column(String, nullable=True, index=True)  # Type of provider used
    provider_response_time = Column(
        Float, nullable=True
    )  # Response time when this listing was found
    provider_metadata = Column(JSON, nullable=True)  # Provider-specific metadata

    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    search = relationship("Search", back_populates="listings")

    # Composite unique constraint: prevent same URL within same search
    # but allow same URL across different searches
    __table_args__ = (
        UniqueConstraint("search_id", "url", name="uq_listing_search_url"),
        # Additional indexes for performance
        {"extend_existing": True},
    )

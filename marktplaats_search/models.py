import enum
import uuid

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
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, nullable=False)
    user_identifier = Column(String, unique=True, index=True, nullable=False)
    api_token_hash = Column(
        String, unique=True, index=True, nullable=False
    )  # Store hash instead of plaintext
    is_active = Column(Boolean, default=True, nullable=False)  # Account status
    token_created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)  # Track token age
    last_activity = Column(DateTime(timezone=True), nullable=True)  # Track last API usage
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

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

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, nullable=False)

    # Search parameters
    query = Column(String, nullable=False)
    zip_code = Column(String, nullable=True)
    distance = Column(Integer, nullable=True)
    price_from = Column(Integer, nullable=True)
    price_to = Column(Integer, nullable=True)
    limit = Column(Integer, default=25, nullable=False)
    sort_by = Column(String, nullable=True)
    sort_order = Column(String, nullable=True)

    interval = Column(Integer, nullable=False)  # Interval in seconds

    status = Column(SQLAlchemyEnum(SearchStatus), default=SearchStatus.ACTIVE, nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Provider configuration and tracking
    preferred_provider = Column(String, nullable=True)  # Preferred provider name for this search
    provider_config = Column(JSON, nullable=True)  # Search-specific provider configuration
    last_successful_provider = Column(String, nullable=True)  # Track which provider last succeeded
    provider_metrics = Column(JSON, nullable=True)  # Store provider usage metrics per search

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="searches")

    listings = relationship("Listing", back_populates="search", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Listing(Base):
    __tablename__ = "listings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True, nullable=False)
    search_id = Column(PG_UUID(as_uuid=True), ForeignKey("searches.id"), nullable=False, index=True)

    # Core listing data from marktplaats library
    marktplaats_id = Column(String, index=True, nullable=True)  # ID from Marktplaats API
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)  # Price as float from marktplaats library
    price_type = Column(SQLAlchemyEnum(PriceTypeEnum), nullable=True)
    url = Column(String, nullable=False, index=True)  # Link from marktplaats library
    date_posted = Column(Date, nullable=True)  # Original post date from marktplaats

    # Legacy fields for backward compatibility
    source_listing_id = Column(String, index=True, nullable=True)  # Alias for marktplaats_id
    price_numeric = Column(
        Integer, nullable=True, index=True
    )  # Numeric price in cents for sorting/filtering
    description_snippet = Column(Text, nullable=True)  # Alias for description
    image_url = Column(String, nullable=True)  # Primary image URL

    # Location data from marktplaats library
    location_city = Column(String, nullable=True)
    location_country = Column(String, nullable=True)
    location_country_short = Column(String, nullable=True)
    location_latitude = Column(Float, nullable=True)
    location_longitude = Column(Float, nullable=True)
    location_distance = Column(Integer, nullable=True)

    # Seller data from marktplaats library
    seller_id = Column(Integer, nullable=True, index=True)
    seller_name = Column(String, nullable=True)
    seller_is_verified = Column(Boolean, nullable=True)

    # Category and attributes from marktplaats library
    category_id = Column(Integer, nullable=True, index=True)
    attributes = Column(JSON, nullable=True)  # List of attribute dicts
    extended_attributes = Column(JSON, nullable=True)  # List of extended attribute dicts

    # Image data from marktplaats library
    image_extra_small = Column(String, nullable=True)
    image_medium = Column(String, nullable=True)
    image_large = Column(String, nullable=True)
    image_extra_large = Column(String, nullable=True)
    images = Column(JSON, nullable=True)  # All available images

    # Legacy fields maintained for compatibility
    condition = Column(String, nullable=True)  # Item condition as string
    views = Column(Integer, nullable=True)  # Number of views (from legacy scraper)
    location = Column(String, nullable=True)  # Legacy location field
    seller = Column(String, nullable=True)  # Legacy seller field

    raw_data = Column(JSON, nullable=True)  # Store full raw data from source if needed
    raw_html = Column(Text, nullable=True)  # Store original HTML from Marktplaats
    is_new = Column(Boolean, default=True, nullable=False, index=True)

    # Provider tracking
    provider_name = Column(String, nullable=True, index=True)  # Which provider found this listing
    provider_type = Column(String, nullable=True, index=True)  # Type of provider used
    provider_response_time = Column(
        Float, nullable=True
    )  # Response time when this listing was found
    provider_metadata = Column(JSON, nullable=True)  # Provider-specific metadata

    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    search = relationship("Search", back_populates="listings")

    # Composite unique constraint: prevent same URL within same search
    # but allow same URL across different searches
    __table_args__ = (
        UniqueConstraint("search_id", "url", name="uq_listing_search_url"),
        # Additional indexes for performance
        {"extend_existing": True},
    )

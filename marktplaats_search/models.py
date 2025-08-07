import enum
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
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

    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String, unique=True, index=True, nullable=False)
    api_token_hash = Column(
        String, unique=True, index=True, nullable=False
    )  # Store hash instead of plaintext
    is_active = Column(Boolean, default=True, nullable=False)  # Account status
    token_created_at = Column(DateTime(timezone=True), server_default=func.now())  # Track token age
    last_activity = Column(DateTime(timezone=True), nullable=True)  # Track last API usage
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    searches = relationship("Search", back_populates="owner", cascade="all, delete-orphan")


class SearchStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Search(Base):
    __tablename__ = "searches"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

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

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="searches")

    listings = relationship("Listing", back_populates="search", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Listing(Base):
    __tablename__ = "listings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    search_id = Column(PG_UUID(as_uuid=True), ForeignKey("searches.id"), nullable=False, index=True)

    source_listing_id = Column(String, index=True, nullable=True)  # ID from Marktplaats
    title = Column(String, nullable=True)
    price = Column(String, nullable=True)  # Storing as string for flexibility
    price_numeric = Column(
        Integer, nullable=True, index=True
    )  # Numeric price in cents for sorting/filtering
    url = Column(String, nullable=False, index=True)  # URL to the listing (removed unique=True)
    description_snippet = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)

    # Additional listing metadata
    location = Column(String, nullable=True)  # Location/city
    seller = Column(String, nullable=True)  # Seller name/username
    views = Column(Integer, nullable=True)  # Number of views
    condition = Column(String, nullable=True)  # Item condition
    date_posted = Column(DateTime(timezone=True), nullable=True)  # Original post date

    raw_data = Column(JSON, nullable=True)  # Store full raw data from source if needed
    raw_html = Column(Text, nullable=True)  # Store original HTML from Marktplaats
    is_new = Column(Boolean, default=True, nullable=False, index=True)

    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    search = relationship("Search", back_populates="listings")

    # Composite unique constraint: prevent same URL within same search
    # but allow same URL across different searches
    __table_args__ = (UniqueConstraint("search_id", "url", name="uq_listing_search_url"),)

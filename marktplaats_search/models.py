import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON, Text, Boolean
from sqlalchemy import Enum as SQLAlchemyEnum # Avoid conflict with standard enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Works with SQLite for UUID type
from sqlalchemy.sql import func

from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_identifier = Column(String, unique=True, index=True, nullable=False)
    api_token_hash = Column(String, unique=True, index=True, nullable=False)  # Store hash instead of plaintext
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
    
    interval = Column(Integer, nullable=False) # Interval in seconds

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
    search_id = Column(PG_UUID(as_uuid=True), ForeignKey("searches.id"), nullable=False)
    
    source_listing_id = Column(String, index=True, nullable=True) # ID from Marktplaats
    title = Column(String, nullable=True)
    price = Column(String, nullable=True) # Storing as string for flexibility
    url = Column(String, unique=True, nullable=False) # URL to the listing
    description_snippet = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    raw_data = Column(JSON, nullable=True) # Store full raw data from source if needed
    is_new = Column(Boolean, default=True, nullable=False)

    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

    search = relationship("Search", back_populates="listings")

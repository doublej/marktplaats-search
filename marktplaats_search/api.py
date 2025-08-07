import uuid
import logging
import sys
import os
from typing import List, Optional, Any
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status, Depends, Query as FastAPIQuery
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete
from sqlalchemy.orm import selectinload

from .database import get_db
from .models import User, Search, Listing, SearchStatus # Import your SQLAlchemy models
from . import scheduler # Import the scheduler module
from .auth import hash_token, verify_token, validate_token_format
from .config import settings
from datetime import datetime

# --- Pydantic Models ---

class SearchQueryBase(BaseModel):
    query: str = Field(..., min_length=1, description="The search term (e.g., 'Samsung SSD').")
    zip_code: Optional[str] = Field(None, pattern=r"^\d{4}[A-Z]{2}$", description="The postal code (e.g., 1234AB).")
    distance: Optional[int] = Field(None, gt=0, description="Search radius in meters.")
    price_from: Optional[int] = Field(None, ge=0, description="Minimum price.")
    price_to: Optional[int] = Field(None, ge=0, description="Maximum price.")
    limit: Optional[int] = Field(25, ge=1, le=100, description="Number of results per page/fetch for the source.")
    sort_by: Optional[str] = Field(None, description="Sorting criteria (e.g., 'date', 'price', 'distance').")
    sort_order: Optional[str] = Field(None, description="Sorting order ('asc', 'desc').")

    @validator('price_to')
    def price_to_must_be_greater_than_price_from(cls, v, values, **kwargs):
        if v is not None and 'price_from' in values and values['price_from'] is not None:
            if v < values['price_from']:
                raise ValueError('price_to must be greater than or equal to price_from')
        return v

class SearchCreateRequest(SearchQueryBase):
    interval: int = Field(..., ge=60, le=86400, description="The interval in seconds for re-execution (min 60s, max 24h).")

class SearchUpdateRequest(BaseModel):
    query: Optional[str] = Field(None, min_length=1)
    zip_code: Optional[str] = Field(None, pattern=r"^\d{4}[A-Z]{2}$")
    distance: Optional[int] = Field(None, gt=0)
    price_from: Optional[int] = Field(None, ge=0)
    price_to: Optional[int] = Field(None, ge=0)
    limit: Optional[int] = Field(None, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: Optional[str] = None
    interval: Optional[int] = Field(None, ge=60, le=86400)
    status: Optional[SearchStatus] = None # Allow changing status, e.g., to reactivate

    @validator('price_to')
    def _price_to_must_be_greater_than_price_from(cls, v, values, **kwargs):
        # This validator needs to handle cases where price_from might not be in `values`
        # if it's not being updated. For simplicity, this check is often better done
        # with the full model state (i.e., after merging with existing data).
        # However, Pydantic runs validators on the input data.
        # If price_from is not in values, we can't validate against it here.
        # This is more robustly handled at the service/DB layer or by ensuring
        # price_from is always provided if price_to is.
        # For now, we'll keep it simple.
        if v is not None and values.get('price_from') is not None:
            if v < values['price_from']:
                raise ValueError('price_to must be greater than or equal to price_from')
        return v


class SearchResponse(SearchQueryBase):
    id: uuid.UUID = Field(..., alias="search_id")
    interval: int
    status: SearchStatus
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        populate_by_name = True # Allows using 'search_id' in response


class ListingResponse(BaseModel):
    id: uuid.UUID = Field(..., alias="listing_id")
    search_id: uuid.UUID
    source_listing_id: Optional[str] = None
    title: Optional[str] = None
    price: Optional[str] = None
    url: Optional[HttpUrl] = None
    description_snippet: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    is_new: bool
    discovered_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

# --- Authentication ---
http_bearer_scheme = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer_scheme)
) -> User:
    if credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    
    # Validate token format
    if not validate_token_format(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Hash the token to compare with database
    token_hash = hash_token(token)
    
    result = await db.execute(
        select(User).where(User.api_token_hash == token_hash)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    
    # Check token expiry if configured
    if settings.token_expiry_days:
        from auth import is_token_expired
        if is_token_expired(user.token_created_at, settings.token_expiry_days):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Update last activity (but don't commit here - let the endpoint handle it)
    user.last_activity = datetime.now(timezone.utc)
    
    return user

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import lifespan # Import the lifespan manager

# Set up logging
logger = logging.getLogger(__name__)

# --- FastAPI Application ---
app = FastAPI(
    title="MarktplaatsSearch API",
    description="API for managing Marktplaats searches and viewing results.",
    version="0.3.0", # Incremented version
    lifespan=lifespan # Assign the lifespan manager
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper to get a search instance for the current user ---
async def get_search_or_404(search_id: uuid.UUID, user_id: int, db: AsyncSession) -> Search:
    result = await db.execute(
        select(Search).where(Search.id == search_id, Search.user_id == user_id)
    )
    search_instance = result.scalars().first()
    if not search_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search not found or access denied")
    return search_instance

# --- API Endpoints ---

@app.post("/api/searches", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def start_new_search_endpoint( # Renamed to avoid conflict with any other start_new_search
    search_request: SearchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiates a new search process. The search will be activated and scheduled for periodic execution.
    """
    new_search = Search(
        **search_request.model_dump(),
        user_id=current_user.id,
        status=SearchStatus.ACTIVE # New searches are active by default
    )
    db.add(new_search)
    await db.commit()
    await db.refresh(new_search)
    
    scheduler.schedule_search_job(new_search)
    return new_search

@app.get("/api/searches", response_model=List[SearchResponse])
async def get_all_searches_endpoint( # Renamed
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = FastAPIQuery(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = FastAPIQuery(100, ge=1, le=200, description="Maximum number of records to return")
):
    """
    Retrieves a list of all searches initiated by the authenticated user.
    """
    result = await db.execute(
        select(Search)
        .where(Search.user_id == current_user.id)
        .order_by(Search.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    searches = result.scalars().all()
    return searches

@app.get("/api/searches/{search_id}", response_model=SearchResponse)
async def get_search_details_endpoint( # Renamed
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves detailed information about a specific search.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)
    return search_instance

@app.put("/api/searches/{search_id}", response_model=SearchResponse)
async def update_search_endpoint( # Renamed
    search_id: uuid.UUID,
    search_update: SearchUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates the parameters or status of an existing search.
    If parameters affecting execution (like interval or query) are changed, the search job will be rescheduled.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)
    
    update_data = search_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    for key, value in update_data.items():
        setattr(search_instance, key, value)
    
    # If price_to is updated, ensure it's valid with current price_from
    if 'price_to' in update_data and search_instance.price_from is not None:
        if search_instance.price_to < search_instance.price_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="price_to cannot be less than price_from")
    elif 'price_from' in update_data and search_instance.price_to is not None:
         if search_instance.price_to < search_instance.price_from:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="price_to cannot be less than price_from")


    await db.commit()
    await db.refresh(search_instance)
    
    try:
        scheduler.schedule_search_job(search_instance) # Reschedule with new params/status
    except Exception as scheduler_error:
        # Log the error but don't fail the API call since the database update succeeded
        logger.error(f"Failed to reschedule search job for {search_id}: {scheduler_error}")
        # Optionally set an error message on the search instance
        search_instance.last_error = f"Scheduler error: {str(scheduler_error)}"
        await db.commit()
    
    return search_instance

@app.post("/api/searches/{search_id}/end", response_model=SearchResponse)
async def end_search_endpoint( # Renamed
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marks a search as inactive. This will stop its periodic execution.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)
    if search_instance.status == SearchStatus.INACTIVE:
        # Optionally, could just return the current state without error
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Search is already inactive")
        
    search_instance.status = SearchStatus.INACTIVE
    await db.commit()
    await db.refresh(search_instance)
    
    scheduler.schedule_search_job(search_instance) # This will remove it from scheduler
    return search_instance

@app.delete("/api/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently deletes a search and all its associated listings.
    This action cannot be undone.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)
    
    # Remove from scheduler first
    scheduler.remove_search_job(search_instance)
    
    # Delete associated listings first (due to foreign key constraint)
    await db.execute(
        delete(Listing).where(Listing.search_id == search_id)
    )
    
    # Delete the search
    await db.delete(search_instance)
    await db.commit()
    
    return

@app.get("/api/searches/{search_id}/results", response_model=List[ListingResponse])
async def get_search_results_endpoint( # Renamed
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = FastAPIQuery(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = FastAPIQuery(20, ge=1, le=100, description="Maximum number of records to return"),
    show_new_only: bool = FastAPIQuery(False, description="Filter to show only new listings")
):
    """
    Retrieves listings found for a specific search, with pagination.
    Can optionally filter for new listings only.
    """
    await get_search_or_404(search_id, current_user.id, db) # Authorize access to search first
    
    query_obj = (
        select(Listing)
        .where(Listing.search_id == search_id)
        .order_by(Listing.discovered_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if show_new_only:
        query_obj = query_obj.where(Listing.is_new == True)
        
    result = await db.execute(query_obj)
    listings = result.scalars().all()
    return listings

@app.get("/api/results/{listing_id}", response_model=ListingResponse)
async def get_listing_details_endpoint( # Renamed
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    mark_as_read: bool = FastAPIQuery(True, description="Mark the listing as read (is_new=False) if it was new.")
):
    """
    Retrieves details for a specific listing.
    Ensures the listing belongs to a search owned by the authenticated user.
    Optionally marks the listing as read.
    """
    result = await db.execute(
        select(Listing)
        .join(Search, Listing.search_id == Search.id) # Join to verify ownership via Search
        .where(Listing.id == listing_id, Search.user_id == current_user.id)
    )
    listing_instance = result.scalars().first()
    
    if not listing_instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found or access denied")
    
    if mark_as_read and listing_instance.is_new:
        listing_instance.is_new = False
        await db.commit()
        await db.refresh(listing_instance)
        
    return listing_instance

# --- Static File Serving ---

# Mount static files for additional assets if needed
# This allows serving CSS, JS, images, etc. from a static directory
import os
project_root = os.path.dirname(os.path.dirname(__file__))

@app.get("/")
async def serve_index():
    """
    Serves the main web UI at the root path.
    """
    index_path = os.path.join(project_root, "static", "index.html")
    return FileResponse(index_path)


# --- User Management Endpoints ---

class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""
    user_identifier: Optional[str] = Field(
        None, 
        min_length=3, 
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Unique username (alphanumeric, _, -). If not provided, will be auto-generated."
    )


class UserCreateResponse(BaseModel):
    """Response model for user creation."""
    user_identifier: str
    api_token: str  # Only returned once during creation
    message: str = "User created successfully. Save your API token securely - it cannot be retrieved again."


class UserInfoResponse(BaseModel):
    """Response model for user information."""
    id: int
    user_identifier: str
    is_active: bool
    created_at: datetime
    last_activity: Optional[datetime]
    token_created_at: datetime
    token_expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


@app.post("/api/auth/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_request: UserCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user and generate a secure API token.
    The API token is only shown once and must be saved securely.
    
    Security notes:
    - Tokens are hashed before storage
    - Original token cannot be retrieved after creation
    - Each user gets a unique, cryptographically secure token
    """
    from auth import generate_secure_token, generate_user_identifier, hash_token
    
    # Generate or use provided username
    if user_request.user_identifier:
        # Check if username already exists
        result = await db.execute(
            select(User).where(User.user_identifier == user_request.user_identifier)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        user_identifier = user_request.user_identifier
    else:
        # Auto-generate unique username
        user_identifier = generate_user_identifier()
        # Ensure uniqueness
        while True:
            result = await db.execute(
                select(User).where(User.user_identifier == user_identifier)
            )
            if not result.scalars().first():
                break
            user_identifier = generate_user_identifier()
    
    # Generate secure token
    api_token = generate_secure_token()
    token_hash = hash_token(api_token)
    
    # Create user
    new_user = User(
        user_identifier=user_identifier,
        api_token_hash=token_hash,
        is_active=True,
        token_created_at=datetime.now(timezone.utc)
    )
    
    db.add(new_user)
    await db.commit()
    
    return UserCreateResponse(
        user_identifier=user_identifier,
        api_token=api_token
    )


@app.get("/api/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about the currently authenticated user.
    """
    # Refresh the user object to ensure we have all attributes loaded
    await db.refresh(current_user)
    
    response = UserInfoResponse(
        id=current_user.id,
        user_identifier=current_user.user_identifier,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_activity=current_user.last_activity,
        token_created_at=current_user.token_created_at
    )
    
    # Calculate token expiry if configured
    if settings.token_expiry_days:
        from datetime import timedelta
        response.token_expires_at = (
            current_user.token_created_at + timedelta(days=settings.token_expiry_days)
        )
    
    return response


@app.post("/api/auth/rotate-token", response_model=UserCreateResponse)
async def rotate_api_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a new API token for the current user.
    The old token will be immediately invalidated.
    
    Security notes:
    - Use this endpoint to rotate tokens periodically
    - The new token is only shown once
    - Old token becomes invalid immediately
    """
    from auth import generate_secure_token, hash_token
    
    # Refresh user to ensure we have the current state
    await db.refresh(current_user)
    
    # Generate new token
    new_token = generate_secure_token()
    new_token_hash = hash_token(new_token)
    
    # Update user with new token
    current_user.api_token_hash = new_token_hash
    current_user.token_created_at = datetime.now(timezone.utc)
    
    # Store username before committing
    username = current_user.user_identifier
    
    await db.commit()
    
    return UserCreateResponse(
        user_identifier=username,
        api_token=new_token,
        message="Token rotated successfully. Save your new API token securely."
    )


@app.delete("/api/auth/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate the current user's account.
    This will prevent the user from accessing the API but won't delete their data.
    """
    current_user.is_active = False
    await db.commit()
    return None

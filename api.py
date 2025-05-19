import uuid
from typing import List, Optional, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, status, Depends, Query as FastAPIQuery
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, Search, Listing, SearchStatus # Import your SQLAlchemy models
import scheduler # Import the scheduler module

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
    
    result = await db.execute(select(User).where(User.api_token == token))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

from main import lifespan # Import the lifespan manager

# --- FastAPI Application ---
app = FastAPI(
    title="MarktplaatsSearch API",
    description="API for managing Marktplaats searches and viewing results.",
    version="0.3.0", # Incremented version
    lifespan=lifespan # Assign the lifespan manager
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
    
    scheduler.schedule_search_job(search_instance) # Reschedule with new params/status
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

import logging
import os
import sys
import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi import Query as FastAPIQuery
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, HttpUrl, validator
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from . import scheduler
from .auth import hash_token, validate_token_format
from .config import settings
from .database import get_db
from .listing_management import (
    cleanup_old_listings,
    get_listing_stats_for_user,
    get_new_listings_summary,
    mark_all_user_listings_as_read,
    mark_search_listings_as_read,
    optimize_listing_queries,
)
from .models import Listing, Search, SearchStatus, User

# --- Enhanced Pydantic Models ---


class SearchQueryBase(BaseModel):
    query: str = Field(..., min_length=1, description="The search term (e.g., 'Samsung SSD').")
    zip_code: str | None = Field(
        None, pattern=r"^\d{4}[A-Z]{2}$", description="The postal code (e.g., 1234AB)."
    )
    distance: int | None = Field(None, gt=0, description="Search radius in kilometers.")
    price_from: int | None = Field(None, ge=0, description="Minimum price in euros.")
    price_to: int | None = Field(None, ge=0, description="Maximum price in euros.")
    limit: int | None = Field(
        25, ge=1, le=100, description="Number of results per page/fetch for the source."
    )
    sort_by: str | None = Field(
        None, description="Sorting criteria ('date', 'price', 'optimized', 'location')."
    )
    sort_order: str | None = Field(None, description="Sorting order ('asc', 'desc').")

    @validator("price_to")
    def price_to_must_be_greater_than_price_from(
        cls, v: int | None, values: dict[str, Any], **kwargs: Any
    ) -> int | None:
        if (
            v is not None
            and "price_from" in values
            and values["price_from"] is not None
            and v < values["price_from"]
        ):
            raise ValueError("price_to must be greater than or equal to price_from")
        return v


class SearchCreateRequest(SearchQueryBase):
    interval: int = Field(
        ...,
        ge=60,
        le=86400,
        description="The interval in seconds for re-execution (min 60s, max 24h).",
    )


class SearchUpdateRequest(BaseModel):
    query: str | None = Field(None, min_length=1)
    zip_code: str | None = Field(None, pattern=r"^\d{4}[A-Z]{2}$")
    distance: int | None = Field(None, gt=0)
    price_from: int | None = Field(None, ge=0)
    price_to: int | None = Field(None, ge=0)
    limit: int | None = Field(None, ge=1, le=100)
    sort_by: str | None = None
    sort_order: str | None = None
    interval: int | None = Field(None, ge=60, le=86400)
    status: SearchStatus | None = None

    @validator("price_to")
    def _price_to_must_be_greater_than_price_from(
        cls, v: int | None, values: dict[str, Any], **kwargs: Any
    ) -> int | None:
        if v is not None and values.get("price_from") is not None and v < values["price_from"]:
            raise ValueError("price_to must be greater than or equal to price_from")
        return v


class SearchResponse(SearchQueryBase):
    id: uuid.UUID
    interval: int
    status: SearchStatus
    last_run_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EnhancedListingResponse(BaseModel):
    """Enhanced listing response with marktplaats library fields."""

    id: uuid.UUID
    search_id: uuid.UUID

    # Core fields from marktplaats library
    marktplaats_id: str | None = None
    title: str
    description: str | None = None
    price: float | None = None
    price_type: str | None = None
    url: HttpUrl
    date_posted: date | None = None

    # Legacy compatibility fields
    source_listing_id: str | None = None
    price_numeric: int | None = None
    description_snippet: str | None = None
    image_url: HttpUrl | None = None

    # Location fields
    location_city: str | None = None
    location_country: str | None = None
    location_country_short: str | None = None
    location_latitude: float | None = None
    location_longitude: float | None = None
    location_distance: int | None = None

    # Seller fields
    seller_id: int | None = None
    seller_name: str | None = None
    seller_is_verified: bool | None = None

    # Category and attributes
    category_id: int | None = None
    attributes: list[dict[str, Any]] | None = None
    extended_attributes: list[dict[str, Any]] | None = None

    # Image fields
    image_extra_small: HttpUrl | None = None
    image_medium: HttpUrl | None = None
    image_large: HttpUrl | None = None
    image_extra_large: HttpUrl | None = None
    images: list[dict[str, Any]] | None = None

    # Legacy compatibility fields
    condition: str | None = None
    views: int | None = None
    location: str | None = None
    seller: str | None = None

    # System fields
    is_new: bool
    discovered_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class ListingResponse(BaseModel):
    """Backward compatible listing response."""

    id: uuid.UUID
    search_id: uuid.UUID
    source_listing_id: str | None = None
    title: str | None = None
    price: str | None = None  # Legacy string format
    price_numeric: int | None = None
    url: HttpUrl | None = None
    description_snippet: str | None = None
    image_url: HttpUrl | None = None
    raw_html: str | None = None
    is_new: bool
    discovered_at: datetime

    # Additional listing metadata
    location: str | None = None
    seller: str | None = None
    views: int | None = None
    condition: str | None = None
    date_posted: datetime | None = None

    class Config:
        from_attributes = True
        populate_by_name = True


class CrossSearchDuplicateResponse(BaseModel):
    """Response model for cross-search duplicate listings."""

    url: HttpUrl
    title: str | None = None
    price: str | None = None
    search_count: int
    total_occurrences: int
    search_queries: list[str]
    first_seen: datetime
    last_seen: datetime


class CrossSearchAnalysisResponse(BaseModel):
    """Enhanced cross-search analysis with marktplaats library data."""

    url: HttpUrl
    title: str | None = None
    marktplaats_id: str | None = None
    price: float | None = None
    price_type: str | None = None
    category_id: int | None = None
    seller_name: str | None = None
    seller_is_verified: bool | None = None
    location_city: str | None = None
    search_count: int
    total_occurrences: int
    search_queries: list[str]
    first_seen: datetime
    last_seen: datetime


class ListingStatsResponse(BaseModel):
    """Response model for listing statistics."""

    total_listings: int
    new_listings: int
    cross_search_duplicates: int
    searches_affected: int


class NewListingsSummaryResponse(BaseModel):
    """Response model for new listings summary per search."""

    search_summaries: dict[str, dict[str, str | int]]
    total_new: int


class MarkAsReadResponse(BaseModel):
    """Response model for mark as read operations."""

    marked_count: int
    message: str


class CleanupResponse(BaseModel):
    """Response model for cleanup operations."""

    deleted_count: int
    searches_affected: list[str]
    dry_run: bool
    message: str


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    version: str
    database_status: str
    scheduler_status: str
    marktplaats_client_status: str
    total_searches: int
    total_listings: int
    timestamp: datetime


# --- Authentication ---
AUTH_COOKIE_NAME = "mp_auth_token"
http_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer_scheme),
) -> User:
    token = None

    # Try Bearer token first
    if credentials and credentials.scheme == "Bearer":
        token = credentials.credentials
    # Fallback to cookie if no Bearer token
    elif AUTH_COOKIE_NAME in request.cookies:
        token = request.cookies[AUTH_COOKIE_NAME]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid authentication token provided",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not validate_token_format(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    hashed_token = hash_token(token)
    result = await db.execute(
        select(User).where(User.api_token_hash == hashed_token, User.is_active.is_(True))
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update last activity
    user.last_activity = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)  # Refresh to keep user attached to session

    return user


async def get_search_or_404(search_id: uuid.UUID, user_id: int, db: AsyncSession) -> Search:
    """Helper function to get a search or raise 404 if not found/not accessible."""
    result = await db.execute(
        select(Search).where(Search.id == search_id, Search.user_id == user_id)
    )
    search_instance = result.scalars().first()
    if not search_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Search not found or access denied"
        )
    return search_instance


# Import lifespan from main module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import lifespan

# --- FastAPI App ---
app = FastAPI(
    title="Marktplaats Search API",
    description="API for monitoring Marktplaats.nl listings with automated search scheduling and per-search listing management",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup and shutdown events are now handled by the lifespan manager


@app.get("/", response_model=None)
async def read_root():
    """Root endpoint that serves the main HTML interface."""
    frontend_file = os.path.join(
        os.path.dirname(__file__), "..", "frontend", "public", "index.html"
    )
    if os.path.exists(frontend_file):
        return FileResponse(frontend_file, media_type="text/html")
    else:
        # Fallback to legacy static file
        static_file = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
        if os.path.exists(static_file):
            return FileResponse(static_file, media_type="text/html")
        else:
            return {"message": "Marktplaats Search API is running", "version": "2.0.0"}


@app.get("/app.js")
async def serve_app_js() -> FileResponse:
    """Serve the main application JavaScript file."""
    js_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "app.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    else:
        raise HTTPException(status_code=404, detail="Application JavaScript file not found")


@app.get("/styles.css")
async def serve_styles() -> FileResponse:
    """Serve the main application CSS file."""
    css_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "styles.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    else:
        raise HTTPException(status_code=404, detail="Application CSS file not found")


@app.get("/enhanced_features.js")
async def serve_enhanced_features() -> FileResponse:
    """Legacy endpoint - redirect to new app.js."""
    js_file = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "app.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    else:
        # Fallback to legacy file
        legacy_js = os.path.join(os.path.dirname(__file__), "..", "static", "enhanced_features.js")
        if os.path.exists(legacy_js):
            return FileResponse(legacy_js, media_type="application/javascript")
        else:
            raise HTTPException(status_code=404, detail="JavaScript file not found")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthCheckResponse:
    """
    Health check endpoint with comprehensive system status.
    """
    try:
        # Check database
        result = await db.execute(select(func.count(Search.id)))
        total_searches = result.scalar() or 0

        result = await db.execute(select(func.count(Listing.id)))
        total_listings = result.scalar() or 0

        database_status = "healthy"
    except Exception as e:
        database_status = f"error: {str(e)}"
        total_searches = 0
        total_listings = 0

    # Check scheduler
    from .scheduler import scheduler as scheduler_instance

    scheduler_status = "running" if scheduler_instance.running else "stopped"

    # Check marktplaats client (basic import test)
    try:
        marktplaats_client_status = "healthy"
    except Exception as e:
        marktplaats_client_status = f"error: {str(e)}"

    return HealthCheckResponse(
        status="healthy"
        if database_status == "healthy" and scheduler_status == "running"
        else "degraded",
        version="2.0.0",
        database_status=database_status,
        scheduler_status=scheduler_status,
        marktplaats_client_status=marktplaats_client_status,
        total_searches=total_searches,
        total_listings=total_listings,
        timestamp=datetime.now(UTC),
    )


# --- User Management Endpoints ---


class UserCreateRequest(BaseModel):
    """Request model for creating a new user."""

    user_identifier: str | None = Field(
        None,
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        description="Unique username (alphanumeric, _, -). If not provided, will be auto-generated.",
    )


class UserCreateResponse(BaseModel):
    """Response model for user creation."""

    user_identifier: str
    api_token: str
    message: str = (
        "User created successfully. Save your API token securely - it cannot be retrieved again."
    )


class UserInfoResponse(BaseModel):
    """Response model for user information."""

    id: int
    user_identifier: str
    is_active: bool
    created_at: datetime
    last_activity: datetime | None
    token_created_at: datetime
    token_expires_at: datetime | None = None

    class Config:
        from_attributes = True


@app.post(
    "/api/auth/register", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_request: UserCreateRequest, db: AsyncSession = Depends(get_db)
) -> UserCreateResponse:
    """Register a new user and generate a secure API token."""
    from .auth import generate_secure_token, generate_user_identifier, hash_token

    # Generate or use provided username
    if user_request.user_identifier:
        result = await db.execute(
            select(User).where(User.user_identifier == user_request.user_identifier)
        )
        if result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )
        user_identifier = user_request.user_identifier
    else:
        user_identifier = generate_user_identifier()
        while True:
            result = await db.execute(select(User).where(User.user_identifier == user_identifier))
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
        token_created_at=datetime.now(UTC),
    )

    db.add(new_user)
    await db.commit()

    return UserCreateResponse(user_identifier=user_identifier, api_token=api_token)


@app.get("/api/auth/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserInfoResponse:
    """Get information about the currently authenticated user."""
    await db.refresh(current_user)

    response = UserInfoResponse(
        id=current_user.id,
        user_identifier=current_user.user_identifier,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_activity=current_user.last_activity,
        token_created_at=current_user.token_created_at,
    )

    if settings.token_expiry_days:
        from datetime import timedelta

        response.token_expires_at = current_user.token_created_at + timedelta(
            days=settings.token_expiry_days
        )

    return response


@app.post("/api/auth/set-cookie", status_code=status.HTTP_200_OK)
async def set_auth_cookie(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Set authentication cookie for the current session."""
    # Extract token from the request (Bearer or cookie)
    token = None

    # Get Authorization header directly
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
    elif AUTH_COOKIE_NAME in request.cookies:
        token = request.cookies[AUTH_COOKIE_NAME]

    if token:
        # Set cookie with appropriate security settings
        max_age = None
        if settings.token_expiry_days:
            max_age = settings.token_expiry_days * 24 * 60 * 60

        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            max_age=max_age,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="strict",
            path="/",
        )
        return {"message": "Authentication cookie set successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid token found to set cookie"
        )


@app.post("/api/auth/rotate-token", response_model=UserCreateResponse)
async def rotate_api_token(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserCreateResponse:
    """Generate a new API token for the current user."""
    from .auth import generate_secure_token, hash_token

    await db.refresh(current_user)
    new_token = generate_secure_token()
    new_token_hash = hash_token(new_token)

    current_user.api_token_hash = new_token_hash
    current_user.token_created_at = datetime.now(UTC)
    username = current_user.user_identifier

    await db.commit()

    # Clear old cookie and potentially set new one
    response.delete_cookie(
        key=AUTH_COOKIE_NAME, path="/", httponly=True, secure=True, samesite="strict"
    )

    return UserCreateResponse(
        user_identifier=username,
        api_token=new_token,
        message="Token rotated successfully. Save your new API token securely.",
    )


@app.post("/api/auth/logout", status_code=status.HTTP_200_OK)
async def logout_user(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Logout user and clear authentication cookies."""
    response.delete_cookie(
        key=AUTH_COOKIE_NAME, path="/", httponly=True, secure=True, samesite="strict"
    )
    return {"message": "Successfully logged out"}


@app.delete("/api/auth/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Deactivate the current user's account."""
    current_user.is_active = False
    await db.commit()

    # Clear cookie on account deactivation
    response.delete_cookie(
        key=AUTH_COOKIE_NAME, path="/", httponly=True, secure=True, samesite="strict"
    )
    return None


# --- Search Management Endpoints ---


@app.post("/api/searches", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def create_search_endpoint(
    search_data: SearchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Search:
    """
    Creates a new search and schedules it for periodic execution.
    """
    new_search = Search(
        query=search_data.query,
        zip_code=search_data.zip_code,
        distance=search_data.distance,
        price_from=search_data.price_from,
        price_to=search_data.price_to,
        limit=search_data.limit or 25,
        sort_by=search_data.sort_by,
        sort_order=search_data.sort_order,
        interval=search_data.interval,
        user_id=current_user.id,
        status=SearchStatus.ACTIVE,
    )

    db.add(new_search)
    await db.commit()
    await db.refresh(new_search)

    # Schedule the search
    scheduler.schedule_search_job(new_search)

    return new_search


@app.get("/api/searches", response_model=list[SearchResponse])
async def get_user_searches_endpoint(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Search]:
    """
    Retrieves all searches for the authenticated user.
    """
    user_id = current_user.id  # Get user_id before using in query
    result = await db.execute(
        select(Search).where(Search.user_id == user_id).order_by(Search.created_at.desc())
    )
    searches = result.scalars().all()
    return list(searches)


@app.get("/api/searches/{search_id}", response_model=SearchResponse)
async def get_search_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Search:
    """
    Retrieves details for a specific search.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)
    return search_instance


@app.put("/api/searches/{search_id}", response_model=SearchResponse)
async def update_search_endpoint(
    search_id: uuid.UUID,
    search_updates: SearchUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Search:
    """
    Updates an existing search. Changes to interval or status affect scheduling.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)

    update_data = search_updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(search_instance, field, value)

    search_instance.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(search_instance)

    # Update scheduler
    scheduler.schedule_search_job(search_instance)

    return search_instance


@app.post("/api/searches/{search_id}/pause", response_model=SearchResponse)
async def pause_search_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Search:
    """
    Pauses a search by setting its status to INACTIVE.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)

    if search_instance.status == SearchStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Search is already inactive"
        )

    search_instance.status = SearchStatus.INACTIVE
    await db.commit()
    await db.refresh(search_instance)

    scheduler.schedule_search_job(search_instance)  # This will remove it from scheduler
    return search_instance


@app.delete("/api/searches/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_search_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Permanently deletes a search and all its associated listings.
    """
    search_instance = await get_search_or_404(search_id, current_user.id, db)

    # Remove from scheduler first
    scheduler.remove_search_job(search_instance)

    # Delete associated listings first (due to foreign key constraint)
    await db.execute(delete(Listing).where(Listing.search_id == search_id))

    # Delete the search
    await db.delete(search_instance)
    await db.commit()

    return


# --- Listing Endpoints ---


@app.get("/api/searches/{search_id}/results", response_model=list[EnhancedListingResponse])
async def get_search_results_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = FastAPIQuery(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = FastAPIQuery(
        settings.default_frontend_limit,
        ge=1,
        le=100,
        description="Maximum number of records to return",
    ),
    show_new_only: bool = FastAPIQuery(False, description="Filter to show only new listings"),
    category_id: int | None = FastAPIQuery(None, description="Filter by category ID"),
    seller_type: str | None = FastAPIQuery(
        None, description="Filter by seller type (verified/unverified)"
    ),
    min_price: float | None = FastAPIQuery(None, ge=0, description="Minimum price filter"),
    max_price: float | None = FastAPIQuery(None, ge=0, description="Maximum price filter"),
) -> list[Listing]:
    """
    Retrieves listings found for a specific search, with enhanced filtering and pagination.
    """
    await get_search_or_404(search_id, current_user.id, db)

    query_obj = (
        select(Listing)
        .where(Listing.search_id == search_id)
        .order_by(Listing.discovered_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if show_new_only:
        query_obj = query_obj.where(Listing.is_new.is_(True))

    if category_id is not None:
        query_obj = query_obj.where(Listing.category_id == category_id)

    if seller_type == "verified":
        query_obj = query_obj.where(Listing.seller_is_verified.is_(True))
    elif seller_type == "unverified":
        query_obj = query_obj.where(Listing.seller_is_verified.is_(False))

    if min_price is not None:
        query_obj = query_obj.where(Listing.price >= min_price)

    if max_price is not None:
        query_obj = query_obj.where(Listing.price <= max_price)

    result = await db.execute(query_obj)
    listings = result.scalars().all()
    return listings


@app.get("/api/results/{listing_id}", response_model=EnhancedListingResponse)
async def get_listing_details_endpoint(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    mark_as_read: bool = FastAPIQuery(
        True, description="Mark the listing as read (is_new=False) if it was new."
    ),
) -> Listing:
    """
    Retrieves enhanced details for a specific listing.
    """
    result = await db.execute(
        select(Listing)
        .join(Search, Listing.search_id == Search.id)
        .where(Listing.id == listing_id, Search.user_id == current_user.id)
    )
    listing_instance = result.scalars().first()

    if not listing_instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found or access denied"
        )

    if mark_as_read and listing_instance.is_new:
        listing_instance.is_new = False
        await db.commit()
        await db.refresh(listing_instance)

    return listing_instance


@app.get("/api/cross-search-analysis", response_model=list[CrossSearchAnalysisResponse])
async def get_cross_search_analysis_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = FastAPIQuery(50, ge=1, le=200, description="Maximum number of duplicate groups"),
    min_searches: int = FastAPIQuery(
        2, ge=2, description="Minimum number of searches a listing must appear in"
    ),
) -> list[CrossSearchAnalysisResponse]:
    """
    Enhanced cross-search analysis with marktplaats library data.
    """
    from sqlalchemy import text

    query = text("""
        SELECT
            l.url,
            l.title,
            l.marktplaats_id,
            l.price,
            l.price_type,
            l.category_id,
            l.seller_name,
            l.seller_is_verified,
            l.location_city,
            COUNT(DISTINCT l.search_id) as search_count,
            COUNT(l.id) as total_occurrences,
            GROUP_CONCAT(DISTINCT s.query) as search_queries,
            MIN(l.discovered_at) as first_seen,
            MAX(l.discovered_at) as last_seen
        FROM listings l
        JOIN searches s ON l.search_id = s.id
        WHERE s.user_id = :user_id
        GROUP BY l.url
        HAVING COUNT(DISTINCT l.search_id) >= :min_searches
        ORDER BY search_count DESC, total_occurrences DESC
        LIMIT :limit
    """)

    result = await db.execute(
        query, {"user_id": current_user.id, "min_searches": min_searches, "limit": limit}
    )

    analysis = []
    for row in result.fetchall():
        analysis.append(
            CrossSearchAnalysisResponse(
                url=row[0],
                title=row[1],
                marktplaats_id=row[2],
                price=row[3],
                price_type=row[4],
                category_id=row[5],
                seller_name=row[6],
                seller_is_verified=row[7],
                location_city=row[8],
                search_count=row[9],
                total_occurrences=row[10],
                search_queries=row[11].split(",") if row[11] else [],
                first_seen=row[12],
                last_seen=row[13],
            )
        )

    return analysis


# --- Listing Management Endpoints ---


@app.get("/api/listings/stats", response_model=ListingStatsResponse)
async def get_listing_stats_endpoint(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ListingStatsResponse:
    """
    Get comprehensive listing statistics for the user.
    """
    stats = await get_listing_stats_for_user(db, current_user.id)
    return ListingStatsResponse(
        total_listings=stats.total_listings,
        new_listings=stats.new_listings,
        cross_search_duplicates=stats.cross_search_duplicates,
        searches_affected=stats.searches_affected,
    )


@app.get("/api/listings/new-summary", response_model=NewListingsSummaryResponse)
async def get_new_listings_summary_endpoint(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> NewListingsSummaryResponse:
    """
    Get summary of new listings per search.
    """
    summary = await get_new_listings_summary(db, current_user.id)
    total_new = sum(data["new_count"] for data in summary.values())

    return NewListingsSummaryResponse(
        search_summaries=summary,
        total_new=total_new,
    )


@app.post("/api/searches/{search_id}/mark-read", response_model=MarkAsReadResponse)
async def mark_search_listings_read_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkAsReadResponse:
    """
    Mark all new listings for a specific search as read.
    """
    marked_count = await mark_search_listings_as_read(db, search_id, current_user.id)
    return MarkAsReadResponse(
        marked_count=marked_count,
        message=f"Marked {marked_count} listings as read for search {search_id}",
    )


@app.post("/api/listings/mark-all-read", response_model=MarkAsReadResponse)
async def mark_all_listings_read_endpoint(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MarkAsReadResponse:
    """
    Mark all new listings for all user's searches as read.
    """
    marked_count = await mark_all_user_listings_as_read(db, current_user.id)
    return MarkAsReadResponse(
        marked_count=marked_count,
        message=f"Marked {marked_count} listings as read across all searches",
    )


# Keep backward compatibility endpoints
@app.get("/api/searches/{search_id}/listings", response_model=list[ListingResponse])
async def get_search_listings_legacy_endpoint(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = FastAPIQuery(0, ge=0),
    limit: int = FastAPIQuery(20, ge=1, le=100),
    show_new_only: bool = FastAPIQuery(False),
) -> list[ListingResponse]:
    """
    Legacy endpoint for backward compatibility.
    """
    await get_search_or_404(search_id, current_user.id, db)

    query_obj = (
        select(Listing)
        .where(Listing.search_id == search_id)
        .order_by(Listing.discovered_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if show_new_only:
        query_obj = query_obj.where(Listing.is_new.is_(True))

    result = await db.execute(query_obj)
    listings = result.scalars().all()

    # Convert to legacy format
    legacy_listings = []
    for listing in listings:
        legacy_listing = {
            "id": listing.id,
            "search_id": listing.search_id,
            "source_listing_id": listing.source_listing_id or listing.marktplaats_id,
            "title": listing.title,
            "price": f"€ {listing.price:.2f}" if listing.price else None,
            "price_numeric": listing.price_numeric,
            "url": listing.url,
            "description_snippet": listing.description_snippet or listing.description,
            "image_url": listing.image_url,
            "raw_html": listing.raw_html,
            "is_new": listing.is_new,
            "discovered_at": listing.discovered_at,
            "location": listing.location or listing.location_city,
            "seller": listing.seller or listing.seller_name,
            "views": listing.views,
            "condition": listing.condition,
            "date_posted": listing.date_posted,
        }
        legacy_listings.append(ListingResponse(**legacy_listing))

    return legacy_listings


# --- Admin Endpoints ---


@app.post("/api/admin/refresh-searches", status_code=status.HTTP_200_OK)
async def refresh_all_searches_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | int]:
    """
    Refresh all searches by deleting their results and restarting them.
    This preserves the search configurations but clears accumulated results.
    """
    try:
        # Get all user's searches
        result = await db.execute(select(Search).where(Search.user_id == current_user.id))
        user_searches = result.scalars().all()

        if not user_searches:
            return {"message": "No searches found to refresh.", "refreshed_count": 0}

        # Delete all listings for user's searches
        search_ids = [search.id for search in user_searches]
        await db.execute(delete(Listing).where(Listing.search_id.in_(search_ids)))

        # Reset search states
        refreshed_count = 0
        for search in user_searches:
            search.last_run_at = None
            search.last_error = None
            # Reschedule active searches
            if search.status == SearchStatus.ACTIVE:
                try:
                    scheduler.schedule_search_job(search)
                except Exception as scheduler_error:
                    logging.warning(f"Failed to reschedule search {search.id}: {scheduler_error}")
                    search.last_error = f"Scheduler error: {str(scheduler_error)}"
            refreshed_count += 1

        await db.commit()

        return {
            "message": f"Successfully refreshed {refreshed_count} searches.",
            "refreshed_count": refreshed_count,
        }

    except Exception as e:
        logging.error(f"Error refreshing searches for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh searches: {str(e)}",
        ) from e


@app.post("/api/admin/cleanup-listings", response_model=CleanupResponse)
async def cleanup_old_listings_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days_old: int = FastAPIQuery(
        30, ge=1, le=365, description="Delete listings older than this many days"
    ),
    keep_new_listings: bool = FastAPIQuery(
        True, description="If true, never delete listings marked as new"
    ),
    dry_run: bool = FastAPIQuery(
        True, description="If true, only count what would be deleted without deleting"
    ),
) -> CleanupResponse:
    """
    Clean up old listings to manage database size.
    By default runs in dry-run mode to show what would be deleted.
    """
    try:
        deleted_count, searches_affected = await cleanup_old_listings(
            db, days_old, keep_new_listings, dry_run
        )

        action = "Would delete" if dry_run else "Deleted"
        return CleanupResponse(
            deleted_count=deleted_count,
            searches_affected=searches_affected,
            dry_run=dry_run,
            message=f"{action} {deleted_count} listings older than {days_old} days from {len(searches_affected)} searches",
        )
    except Exception as e:
        logging.error(f"Error cleaning up listings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup listings: {str(e)}",
        ) from e


@app.post("/api/admin/optimize-queries", status_code=status.HTTP_200_OK)
async def optimize_listing_queries_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | dict[str, Any]]:
    """
    Optimize database queries by creating missing indexes.
    This improves performance for listing operations.
    """
    try:
        optimizations = await optimize_listing_queries(db)

        success_count = sum(1 for result in optimizations.values() if result)
        total_count = len(optimizations)

        return {
            "message": f"Optimization completed: {success_count}/{total_count} indexes created/verified",
            "optimizations": optimizations,
            "success_rate": f"{success_count}/{total_count}",
        }
    except Exception as e:
        logging.error(f"Error optimizing queries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize queries: {str(e)}",
        ) from e

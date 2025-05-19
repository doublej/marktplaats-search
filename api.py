import uuid
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# --- Pydantic Models ---

class SearchQueryBase(BaseModel):
    query: str = Field(..., description="The search term (e.g., 'Samsung SSD').")
    zip_code: Optional[str] = Field(None, description="The postal code for location-based searches.")
    distance: Optional[int] = Field(None, description="Search radius in meters.")
    price_from: Optional[int] = Field(None, description="Minimum price.")
    price_to: Optional[int] = Field(None, description="Maximum price.")
    limit: Optional[int] = Field(25, description="Number of results per page/fetch.")
    sort_by: Optional[str] = Field(None, description="Sorting criteria (e.g., 'LOCATION', 'PRICE').")
    sort_order: Optional[str] = Field(None, description="Sorting order ('ASC', 'DESC').")

class SearchCreateRequest(SearchQueryBase):
    interval: int = Field(..., description="The interval in seconds for re-execution or checking new results.")

class SearchResponse(SearchQueryBase):
    search_id: str
    interval: int
    status: str = "active" # Default status for a new search
    # user_id: str # To be added when user context is fully implemented

# --- In-memory Data Store ---
# For simplicity, we'll use a dictionary to store searches.
# Key: user_id (placeholder for now), Value: List of SearchResponse objects
# For now, we'll use a default "global_user" until auth is in place.
db_searches: Dict[str, List[SearchResponse]] = {} # Initialize as empty

# --- API Token Management (Placeholder) ---
# In a real app, this would be more secure and likely involve a database.
VALID_API_TOKENS = {"test_token_123": "user_alpha"} # token: user_id

http_bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(http_bearer_scheme)) -> str:
    if credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Use 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    user_id = VALID_API_TOKENS.get(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id

# --- FastAPI Application ---
app = FastAPI(
    title="MarktplaatsSearch API",
    description="API for managing Marktplaats searches.",
    version="0.1.0",
)

@app.post("/api/searches", response_model=SearchResponse, status_code=status.HTTP_201_CREATED)
async def start_new_search(search_request: SearchCreateRequest, current_user_id: str = Depends(get_current_user)):
    """
    Initiates a new search process based on the provided query parameters and search interval.
    """
    user_id = current_user_id

    search_id = str(uuid.uuid4())
    new_search_data = search_request.model_dump()
    new_search = SearchResponse(
        search_id=search_id,
        status="active",
        **new_search_data
    )

    if user_id not in db_searches:
        db_searches[user_id] = []
    db_searches[user_id].append(new_search)
    
    print(f"Search {search_id} for user {user_id} started with params: {search_request.model_dump_json(indent=2)}")
    
    return new_search

@app.get("/api/searches", response_model=List[SearchResponse])
async def get_all_searches(current_user_id: str = Depends(get_current_user)):
    """
    Retrieves a list of all searches initiated by the authenticated user.
    """
    user_id = current_user_id
    
    user_specific_searches = db_searches.get(user_id, [])
    return user_specific_searches

# To run this API (save as api.py and run in terminal):
# uvicorn api:app --reload --host 0.0.0.0 --port 8000
#
# Example curl for POST:
# curl -X POST "http://127.0.0.1:8000/api/searches" \
# -H "Authorization: Bearer test_token_123" \
# -H "Content-Type: application/json" \
# -d '{
#   "query": "Samsung SSD 1TB",
#   "zip_code": "3522RA",
#   "price_to": 100,
#   "interval": 3600
# }'
#
# Example curl for GET:
# curl -X GET "http://127.0.0.1:8000/api/searches" \
# -H "Authorization: Bearer test_token_123"

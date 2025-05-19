import asyncio
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, HttpUrl

class MockListingItem(BaseModel):
    source_listing_id: str
    title: str
    price: str
    url: HttpUrl # Use HttpUrl for validation
    description_snippet: Optional[str] = None
    image_url: Optional[HttpUrl] = None

async def fetch_listings(
    query: str,
    zip_code: Optional[str] = None,
    distance: Optional[int] = None,
    price_from: Optional[int] = None,
    price_to: Optional[int] = None,
    limit: int = 10,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    # Add other relevant parameters from models.Search as needed
) -> List[MockListingItem]:
    """
    Mock function to simulate fetching listings from Marktplaats.
    """
    print(
        f"MOCK CLIENT: Fetching listings for query='{query}', zip='{zip_code}', "
        f"price_to='{price_to}', limit='{limit}'"
    )
    await asyncio.sleep(random.uniform(0.2, 1.0)) # Simulate network latency

    mock_results = []
    num_results = random.randint(0, limit if limit <=10 else 10) # Generate fewer for mock
    for i in range(num_results):
        item_id_num = random.randint(1000000, 9999999)
        item_id = f"m{item_id_num}" # Marktplaats-like ID
        mock_price = random.randint(price_from or 5, price_to or 500)
        mock_results.append(
            MockListingItem(
                source_listing_id=item_id,
                title=f"{query} - Mock Item {i+1} - ID {item_id_num}",
                price=f"€ {mock_price:.2f}",
                url=f"https://www.marktplaats.nl/v/{item_id}/",
                description_snippet=f"This is a mock description for '{query}'. Condition: {random.choice(['New', 'Used', 'As good as new'])}.",
                image_url=f"https://picsum.photos/seed/{item_id}/200/150"
            )
        )
    
    print(f"MOCK CLIENT: Found {len(mock_results)} listings for query '{query}'.")
    return mock_results

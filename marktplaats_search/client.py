import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus, urlencode

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from pydantic import BaseModel, HttpUrl, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ListingItem(BaseModel):
    source_listing_id: str
    title: str
    price: str
    url: HttpUrl
    description_snippet: Optional[str] = None
    image_url: Optional[HttpUrl] = None

class MarktplaatsScrapingError(Exception):
    """Custom exception for scraping-related errors."""
    pass

class MarktplaatsScraper:
    """Real Marktplaats.nl web scraper."""
    
    BASE_URL = "https://www.marktplaats.nl"
    SEARCH_URL = "https://www.marktplaats.nl/q/{query}/"
    
    def __init__(self):
        self.ua = UserAgent()
        self.session: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": self.ua.random,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    def _build_search_url(
        self,
        query: str,
        zip_code: Optional[str] = None,
        distance: Optional[int] = None,
        price_from: Optional[int] = None,
        price_to: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None,
    ) -> str:
        """Build the search URL with parameters."""
        # Ensure query is lowercase to avoid Marktplaats redirects
        query = query.lower()
        encoded_query = quote_plus(query)
        url = self.SEARCH_URL.format(query=encoded_query)
        
        params = {}
        
        if zip_code:
            params["postcode"] = zip_code
        if distance:
            params["distanceMeters"] = str(distance * 1000)  # Convert km to meters
        if price_from:
            params["PriceCentsFrom"] = str(price_from * 100)  # Convert euros to cents
        if price_to:
            params["PriceCentsTo"] = str(price_to * 100)  # Convert euros to cents
        if sort_by == "price" and sort_order == "asc":
            params["sortBy"] = "PRICE"
            params["sortOrder"] = "INCREASING"
        elif sort_by == "price" and sort_order == "desc":
            params["sortBy"] = "PRICE" 
            params["sortOrder"] = "DECREASING"
        elif sort_by == "date":
            params["sortBy"] = "DATE"
        
        if params:
            url += "?" + urlencode(params)
        
        return url
    
    def _extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from Marktplaats URL."""
        # Pattern: /m1234567890-title-here/
        match = re.search(r'/m(\d+)-', url)
        if match:
            return f"m{match.group(1)}"
        return None
    
    def _clean_price(self, price_text: str) -> str:
        """Clean and normalize price text."""
        if not price_text:
            return "Price on request"
        
        # Remove extra whitespace and normalize
        price = re.sub(r'\s+', ' ', price_text.strip())
        
        # Handle various price formats
        if "vraagprijs" in price.lower() or "v.o.n" in price.lower():
            return "Price on request"
        elif "gratis" in price.lower():
            return "€ 0"
        elif "€" not in price and price.replace(".", "").replace(",", "").isdigit():
            # Add euro sign if missing
            return f"€ {price}"
        
        return price
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text content."""
        if not text:
            return None
        return re.sub(r'\s+', ' ', text.strip())
    
    def _parse_listings(self, html: str) -> List[ListingItem]:
        """Parse listings from HTML content."""
        soup = BeautifulSoup(html, 'lxml')
        listings = []
        
        # Try to find listings in different ways
        
        # Method 1: Look for specific listing containers
        listing_containers = soup.find_all('div', class_=re.compile(r'hz-Listing-item-wrapper', re.I))
        
        if not listing_containers:
            # Method 2: Look for elements with listing content
            listing_containers = soup.find_all('div', class_=re.compile(r'hz-Listing-listview-content', re.I))
        
        if not listing_containers:
            # Method 3: Find parent containers of listing links  
            listing_links = soup.find_all('a', href=re.compile(r'/m\d+'))
            listing_containers = []
            for link in listing_links:
                # Find parent container that likely contains all listing info
                parent = link.find_parent('div', class_=re.compile(r'hz-Listing', re.I))
                if parent and parent not in listing_containers:
                    listing_containers.append(parent)
                elif not parent:
                    # Use the link itself as container
                    listing_containers.append(link)
        
        logger.info(f"Found {len(listing_containers)} potential listing containers")
        
        for container in listing_containers[:50]:  # Limit to prevent excessive parsing
            try:
                listing = self._parse_single_listing(container)
                if listing:
                    listings.append(listing)
            except Exception as e:
                logger.debug(f"Failed to parse listing container: {e}")
                continue
        
        return listings
    
    def _parse_single_listing(self, container) -> Optional[ListingItem]:
        """Parse a single listing from its container element."""
        # Find URL first (most reliable identifier)
        link_elem = None
        if container.name == 'a' and re.search(r'/m\d+', container.get('href', '')):
            link_elem = container
        else:
            link_elem = container.find('a', href=re.compile(r'/m\d+'))
        
        if not link_elem:
            return None
        
        href = link_elem.get('href', '')
        if href.startswith('/'):
            url = self.BASE_URL + href
        else:
            url = href
        
        # Extract listing ID
        listing_id = self._extract_listing_id(url)
        if not listing_id:
            return None
        
        # Find title - could be in the link text or separate element
        title = None
        
        # Try link text first
        link_text = self._clean_text(link_elem.get_text())
        if link_text and len(link_text) > 5:
            title = link_text
        
        # If no good title from link, look for title elements
        if not title:
            title_elem = (
                container.find(['h1', 'h2', 'h3'], class_=re.compile(r'title', re.I)) or
                container.find(['h1', 'h2', 'h3']) or
                container.find(class_=re.compile(r'hz-Listing-title', re.I))
            )
            if title_elem:
                title = self._clean_text(title_elem.get_text())
        
        if not title:
            return None
        
        # Clean title - remove price and details text
        title = re.sub(r'€\s*[\d.,]+[^a-zA-Z]*$', '', title).strip()
        title = re.sub(r'\s*details\s*.*$', '', title, flags=re.I).strip()
        title = re.sub(r'\s*\d+\s*$', '', title).strip()  # Remove trailing numbers
        
        # Find price
        price = "Price on request"
        
        # Look for price in various ways
        price_patterns = [
            r'€\s*[\d.,]+(?:\s*,-)?',
            r'euro\s*[\d.,]+',
            r'[\d.,]+\s*euro'
        ]
        
        # Try to find price in the text content
        all_text = container.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, all_text, re.I)
            if match:
                price = self._clean_price(match.group())
                break
        
        # Also look for price elements
        if price == "Price on request":
            price_elem = (
                container.find(class_=re.compile(r'price', re.I)) or
                container.find('span', string=re.compile(r'€', re.I)) or
                container.find('div', string=re.compile(r'€', re.I))
            )
            if price_elem:
                price = self._clean_price(price_elem.get_text())
        
        # Find description - look for text that's not title or price
        description = None
        desc_candidates = [
            container.find(class_=re.compile(r'description|snippet', re.I)),
            container.find('p'),
        ]
        
        for candidate in desc_candidates:
            if candidate:
                desc_text = self._clean_text(candidate.get_text())
                if desc_text and desc_text != title and len(desc_text) > 10:
                    description = desc_text[:200]  # Limit length
                    break
        
        # Find image
        image_url = None
        img_elem = container.find('img')
        if img_elem:
            img_src = (
                img_elem.get('src') or 
                img_elem.get('data-src') or 
                img_elem.get('data-lazy-src')
            )
            if img_src:
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    img_src = self.BASE_URL + img_src
                elif img_src.startswith('data:') or not img_src.startswith('http'):
                    img_src = None
                    
                if img_src:
                    try:
                        image_url = HttpUrl(img_src)
                    except ValidationError:
                        pass
        
        try:
            return ListingItem(
                source_listing_id=listing_id,
                title=title,
                price=price,
                url=HttpUrl(url),
                description_snippet=description,
                image_url=image_url
            )
        except ValidationError as e:
            logger.debug(f"Validation error for listing {listing_id}: {e}")
            return None

async def fetch_listings(
    query: str,
    zip_code: Optional[str] = None,
    distance: Optional[int] = None,
    price_from: Optional[int] = None,
    price_to: Optional[int] = None,
    limit: int = 10,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
) -> List[ListingItem]:
    """
    Fetch real listings from Marktplaats.nl.
    
    Args:
        query: Search query string
        zip_code: Dutch postal code (e.g., "1012AB")  
        distance: Search radius in kilometers
        price_from: Minimum price in euros
        price_to: Maximum price in euros
        limit: Maximum number of listings to return
        sort_by: Sort criteria ("price", "date", "relevance")
        sort_order: Sort order ("asc", "desc")
        
    Returns:
        List of ListingItem objects
        
    Raises:
        MarktplaatsScrapingError: If scraping fails
    """
    logger.info(
        f"Fetching listings: query='{query}', zip='{zip_code}', "
        f"distance={distance}km, price={price_from}-{price_to}, limit={limit}"
    )
    
    try:
        async with MarktplaatsScraper() as scraper:
            # Build search URL
            search_url = scraper._build_search_url(
                query=query,
                zip_code=zip_code,
                distance=distance,
                price_from=price_from,
                price_to=price_to,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Requesting URL: {search_url}")
            
            # Add rate limiting delay
            await asyncio.sleep(1.0)
            
            # Fetch the search results page with redirect handling
            response = await scraper.session.get(search_url, follow_redirects=True)
            response.raise_for_status()
            
            # Check for blocking or rate limiting
            if response.status_code == 429:
                raise MarktplaatsScrapingError("Rate limited by Marktplaats")
            
            if "blocked" in response.text.lower() or "captcha" in response.text.lower():
                raise MarktplaatsScrapingError("Blocked by anti-scraping measures")
            
            # Parse listings from HTML
            listings = scraper._parse_listings(response.text)
            
            # Apply limit
            if limit:
                listings = listings[:limit]
            
            logger.info(f"Successfully scraped {len(listings)} listings for query '{query}'")
            return listings
            
    except httpx.HTTPError as e:
        logger.error(f"HTTP error while fetching listings: {e}")
        raise MarktplaatsScrapingError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching listings: {e}")
        raise MarktplaatsScrapingError(f"Scraping failed: {e}")

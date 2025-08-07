import asyncio
import contextlib
import logging
import re
from datetime import datetime, timedelta
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
    price_numeric: int | None = None  # Price in cents for sorting/filtering
    url: HttpUrl
    description_snippet: str | None = None
    image_url: HttpUrl | None = None
    raw_html: str | None = None

    # Additional listing metadata
    location: str | None = None
    seller: str | None = None
    views: int | None = None
    condition: str | None = None
    date_posted: datetime | None = None


class MarktplaatsScrapingError(Exception):
    """Custom exception for scraping-related errors."""

    pass


class MarktplaatsScraper:
    """Real Marktplaats.nl web scraper."""

    BASE_URL = "https://www.marktplaats.nl"
    SEARCH_URL = "https://www.marktplaats.nl/q/{query}/"

    def __init__(self):
        self.ua = UserAgent()
        self.session: httpx.AsyncClient | None = None

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
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()

    def _build_search_url(
        self,
        query: str,
        zip_code: str | None = None,
        distance: int | None = None,
        price_from: int | None = None,
        price_to: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
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

    def _extract_listing_id(self, url: str) -> str | None:
        """Extract listing ID from Marktplaats URL."""
        # Pattern: /m1234567890-title-here/
        match = re.search(r"/m(\d+)-", url)
        if match:
            return f"m{match.group(1)}"
        return None

    def _clean_price(self, price_text: str) -> tuple[str, int | None]:
        """Clean and normalize price text, returning both display text and numeric value."""
        if not price_text:
            return "Price on request", None

        # Remove extra whitespace and normalize
        price = re.sub(r"\s+", " ", price_text.strip())

        # Handle various price formats
        if "vraagprijs" in price.lower() or "v.o.n" in price.lower():
            return "Price on request", None
        elif "gratis" in price.lower():
            return "€ 0", 0

        # Extract numeric value for sorting/filtering
        numeric_match = re.search(r"[\d.,]+", price.replace(",", "."))
        numeric_value = None
        if numeric_match:
            try:
                # Convert to cents for precise integer storage
                numeric_value = int(float(numeric_match.group().replace(",", ".")) * 100)
            except ValueError:
                numeric_value = None

        # Format display text
        if "€" not in price and price.replace(".", "").replace(",", "").isdigit():
            # Add euro sign if missing
            return f"€ {price}", numeric_value

        return price, numeric_value

    def _clean_text(self, text: str | None) -> str | None:
        """Clean and normalize text content."""
        if not text:
            return None
        return re.sub(r"\s+", " ", text.strip())

    def _clean_description(self, text: str | None) -> str | None:
        """Clean and normalize description text, removing price and metadata pollution."""
        if not text:
            return None

        # Start with basic text cleaning
        cleaned = self._clean_text(text)
        if not cleaned:
            return None

        # Remove price patterns that commonly appear in descriptions
        cleaned = re.sub(r"€\s*[\d.,]+(?:\s*,\d+)?\s*", "", cleaned)  # Remove Euro prices
        cleaned = re.sub(r"\$\s*[\d.,]+\s*", "", cleaned)  # Remove Dollar prices
        cleaned = re.sub(r"[\d,]+\s*€\s*", "", cleaned)  # Remove reversed Euro format

        # Remove metadata patterns more aggressively
        cleaned = re.sub(r"\s*details\s*", "", cleaned, flags=re.I)  # Remove "details" text
        cleaned = re.sub(r"🇳🇱\s*", "", cleaned)  # Remove Netherlands flag emoji

        # Remove condition and shipping info - more comprehensive patterns
        cleaned = re.sub(
            r"\s*(Gebruikt|Nieuw|Zo goed als nieuw|Used|New|Like new)\s*", "", cleaned, flags=re.I
        )
        cleaned = re.sub(
            r"\s*(Ophalen|Verzenden|Ophalen of Verzenden|Pickup|Shipping)\s*",
            "",
            cleaned,
            flags=re.I,
        )

        # Remove title repetition - often the description starts with title + price
        # Split on common patterns and take meaningful content
        parts = re.split(r"€[\d.,]+(?:,\d+)?details", cleaned, maxsplit=1, flags=re.I)
        if len(parts) > 1:
            cleaned = parts[1].strip()

        # Remove standalone price mentions that remain
        cleaned = re.sub(r"€[\d.,]+(?:,\d+)?", "", cleaned)

        # Remove common trailing elements
        cleaned = re.sub(r"\s*(Alle|All)\s*$", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*\|\s*$", "", cleaned)  # Remove trailing pipe

        # Clean up punctuation
        cleaned = re.sub(r"!+", "!", cleaned)  # Multiple ! to single !
        cleaned = re.sub(r"\s*!\s*$", "", cleaned)  # Remove trailing !
        cleaned = re.sub(r",\s*$", "", cleaned)  # Remove trailing comma

        # Clean up whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Return None if cleaned text is too short or mostly punctuation
        if len(cleaned) < 10 or len(re.sub(r"[^a-zA-Z0-9\s]", "", cleaned)) < 5:
            return None

        return cleaned

    def _parse_listings(self, html: str) -> list[ListingItem]:
        """Parse listings from HTML content."""
        soup = BeautifulSoup(html, "lxml")
        listings = []

        # Try to find listings in different ways

        # Method 1: Look for specific listing containers
        listing_containers = soup.find_all(
            "div", class_=re.compile(r"hz-Listing-item-wrapper", re.I)
        )

        if not listing_containers:
            # Method 2: Look for elements with listing content
            listing_containers = soup.find_all(
                "div", class_=re.compile(r"hz-Listing-listview-content", re.I)
            )

        if not listing_containers:
            # Method 3: Find parent containers of listing links
            listing_links = soup.find_all("a", href=re.compile(r"/m\d+"))
            listing_containers = []
            for link in listing_links:
                # Find parent container that likely contains all listing info
                parent = link.find_parent("div", class_=re.compile(r"hz-Listing", re.I))
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

    def _parse_single_listing(self, container) -> ListingItem | None:
        """Parse a single listing from its container element."""
        # Find URL first (most reliable identifier)
        link_elem = None
        if container.name == "a" and re.search(r"/m\d+", container.get("href", "")):
            link_elem = container
        else:
            link_elem = container.find("a", href=re.compile(r"/m\d+"))

        if not link_elem:
            return None

        href = link_elem.get("href", "")
        url = self.BASE_URL + href if href.startswith("/") else href

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
                container.find(["h1", "h2", "h3"], class_=re.compile(r"title", re.I))
                or container.find(["h1", "h2", "h3"])
                or container.find(class_=re.compile(r"hz-Listing-title", re.I))
            )
            if title_elem:
                title = self._clean_text(title_elem.get_text())

        if not title:
            return None

        # Clean title - remove price and details text
        # Remove various price patterns that can appear anywhere in title
        title = re.sub(r"€\s*[\d.,]+\s*,?\s*", "", title)  # Remove Euro prices with optional comma
        title = re.sub(r"\$\s*[\d.,]+\s*,?\s*", "", title)  # Remove Dollar prices
        title = re.sub(r"[\d,]+\s*€\s*,?\s*", "", title)  # Remove reversed Euro format
        title = re.sub(r"€\s*[\d.,]+[^a-zA-Z]*$", "", title)  # Remove trailing Euro prices
        title = re.sub(r"\s*details\s*.*$", "", title, flags=re.I)  # Remove details text
        title = re.sub(
            r"^\s*[Nn]u ook ideal in \d*", "", title
        )  # Remove "Nu ook ideal in X" prefix
        title = re.sub(r"\s*\d+\s*$", "", title)  # Remove trailing numbers
        title = re.sub(r"\|\s*$", "", title)  # Remove trailing pipe
        title = re.sub(r",\s*$", "", title)  # Remove trailing comma
        title = re.sub(r"\s+", " ", title).strip()  # Normalize whitespace

        # Find price
        price = "Price on request"
        price_numeric = None

        # Look for price in various ways
        price_patterns = [r"€\s*[\d.,]+(?:\s*,-)?", r"euro\s*[\d.,]+", r"[\d.,]+\s*euro"]

        # Try to find price in the text content
        all_text = container.get_text()
        for pattern in price_patterns:
            match = re.search(pattern, all_text, re.I)
            if match:
                price, price_numeric = self._clean_price(match.group())
                break

        # Also look for price elements
        if price == "Price on request":
            price_elem = (
                container.find(class_=re.compile(r"price", re.I))
                or container.find("span", string=re.compile(r"€", re.I))
                or container.find("div", string=re.compile(r"€", re.I))
            )
            if price_elem:
                price, price_numeric = self._clean_price(price_elem.get_text())

        # Find description - look for text that's not title or price
        description = None
        desc_candidates = [
            container.find(class_=re.compile(r"description|snippet", re.I)),
            container.find("p"),
        ]

        for candidate in desc_candidates:
            if candidate:
                desc_text = self._clean_description(candidate.get_text())
                if desc_text and desc_text != title and len(desc_text) > 10:
                    description = desc_text[:200]  # Limit length
                    break

        # Find image
        image_url = None
        img_elem = container.find("img")
        if img_elem:
            img_src = (
                img_elem.get("src") or img_elem.get("data-src") or img_elem.get("data-lazy-src")
            )
            if img_src:
                if img_src.startswith("//"):
                    img_src = "https:" + img_src
                elif img_src.startswith("/"):
                    img_src = self.BASE_URL + img_src
                elif img_src.startswith("data:") or not img_src.startswith("http"):
                    img_src = None

                if img_src:
                    with contextlib.suppress(ValidationError):
                        image_url = HttpUrl(img_src)

        # Extract additional metadata
        # Extract location
        location = None
        all_text = container.get_text()
        for location_elem in container.find_all(text=True):
            if location_elem and any(
                word in location_elem.lower() for word in ["op ", "km", "plaats"]
            ):
                location_text = self._clean_text(location_elem.strip())
                if location_text and len(location_text) < 50:
                    location = location_text
                    break

        # Extract seller info
        seller = None
        seller_patterns = [r"verkoper", r"aanbieder", r"particulier", r"handel"]
        for pattern in seller_patterns:
            seller_match = re.search(f"{pattern}[:\\s]*([^\\n\\r,]+)", all_text, re.I)
            if seller_match:
                seller = self._clean_text(seller_match.group(1))[:50]
                break

        # Extract views
        views = None
        views_match = re.search(r"(\d+)\s*(?:keer\s*)?bekeken", all_text, re.I)
        if views_match:
            try:
                views = int(views_match.group(1))
            except ValueError:
                views = None

        # Extract condition
        condition = None
        condition_patterns = [
            r"nieuw",
            r"gebruikt",
            r"zo goed als nieuw",
            r"redelijke staat",
            r"matige staat",
        ]
        for pattern in condition_patterns:
            if re.search(pattern, all_text, re.I):
                condition = pattern.title()
                break

        # Extract post date - look for date patterns
        date_posted = None
        date_patterns = [
            r"(\d{1,2})\s*(jan|feb|mrt|apr|mei|jun|jul|aug|sep|okt|nov|dec)\s*(\d{4})",
            r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
            r"gisteren|vandaag|(?:\d+\s*(?:uur|dag|week)(?:en)?\s*geleden)",
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, all_text, re.I)
            if date_match:
                # For now, just store the matched text - proper parsing can be added later
                date_text = date_match.group(0)
                # Convert basic patterns to datetime if possible
                if "vandaag" in date_text.lower():
                    date_posted = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
                elif "gisteren" in date_text.lower():
                    date_posted = (datetime.now() - timedelta(days=1)).replace(
                        hour=12, minute=0, second=0, microsecond=0
                    )
                break

        try:
            return ListingItem(
                source_listing_id=listing_id,
                title=title,
                price=price,
                price_numeric=price_numeric,
                url=HttpUrl(url),
                description_snippet=description,
                image_url=image_url,
                raw_html=str(container),
                # Additional metadata
                location=location,
                seller=seller,
                views=views,
                condition=condition,
                date_posted=date_posted,
            )
        except ValidationError as e:
            logger.debug(f"Validation error for listing {listing_id}: {e}")
            return None


async def fetch_listings(
    query: str,
    zip_code: str | None = None,
    distance: int | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    limit: int = 10,
    sort_by: str | None = None,
    sort_order: str | None = None,
) -> list[ListingItem]:
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
                sort_order=sort_order,
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
        raise MarktplaatsScrapingError(f"Network error: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error while fetching listings: {e}")
        raise MarktplaatsScrapingError(f"Scraping failed: {e}") from e

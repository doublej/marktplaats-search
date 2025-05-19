import requests
import json

from marktplaats import SearchQuery, SortBy, SortOrder

search = SearchQuery()

search.query = "Samsung SSD",
search.zip_code = "3522RA",  # Zip code to base distance from
search.distance = 100,  # Max distance from the zip code for listings
search.price_from = 50,  # Lowest price to search for
search.price_to = 250,  # Highest price to search for
search.limit = 25,  # Max listings (page size, max 25)
search.offset = 0,  # Offset for listings (page * limit)
search.sort_by = SortBy.LOCATION,  # DATE, PRICE, LOCATATION, OPTIMIZED
search.sort_order = SortOrder.ASC # ASCending or DESCending

listings = search.get_listings()

# listing to json
json_listings = []
for listing in listings:
    json_listings.append({
        "title": listing.title,
        "description": listing.description,
        "location": {
            "latitude": listing.location.latitude,
            "longitude": listing.location.longitude
        }
    })

print(json.dumps(json_listings, indent=4))

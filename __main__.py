import os

import folium
from marktplaats import SearchQuery, SortBy, SortOrder


search = SearchQuery()

search.query = "Samsung SSD"
search.zip_code = "3522RA"
search.distance = 5000
search.price_from = 50
search.price_to = 350
search.limit = 1
search.offset = 0
search.sort_by = SortBy.LOCATION
search.sort_order = SortOrder.ASC

listings = search.get_listings()
max_pages = search.page_count()

map = folium.Map(location=[52.090737, 5.121420], zoom_start=13)
page = 0

for page in range(1, max_pages):


    listings = SearchQuery("fiets",  # Search query
                     zip_code=zip_code,
                    distance=distance,
                    price_from=price_from,
                    price_to=price_to,
                    limit=limit,
                    offset=limit*page,
                    sort_by=sort_by,
                    sort_order=sort_order).get_listings()


    for listing in listings:
        print(listing.title)
        print(listing.description)
        # print(listing.price)
        # print(listing.link)
        #
        # # the location object
        print(listing.location)

        folium.Marker([listing.location.latitude, listing.location.longitude], popup=listing.title).add_to(map)
    page += 1

# create folium map

# open map in browser
map.save("map.html")

#open with default os settings
import webbrowser
webbrowser.open('file://' + os.path.realpath("map.html"))


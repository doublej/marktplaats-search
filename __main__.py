import os
import folium
from marktplaats import SearchQuery, SortBy, SortOrder

args = {
    "query": "Samsung SSD",
    "zip_code": "3522RA",
    "distance": 5000,
    "price_from": 50,
    "price_to": 350,
    "limit": 25,
    "offset": 0,
    "sort_by": SortBy.LOCATION,
    "sort_order": SortOrder.ASC,
}

search = SearchQuery(**args)
listings = search.get_listings()
map = folium.Map(location=[52.090737, 5.121420], zoom_start=13)
page = 0

for page in x:


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


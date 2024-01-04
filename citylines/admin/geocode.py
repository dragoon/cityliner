import logging

import requests


def get_place_relation_id(lat, lon) -> str | None:
    # Base URL for Nominatim API
    url = "https://nominatim.openstreetmap.org/reverse"

    # Parameters for the API request
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 10,
        "addressdetails": 1
    }

    # Sending the GET request
    response = requests.get(url, params=params)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        # Extracting the place name
        if data['osm_type'] == 'relation':
            logging.debug(f"OSM Relation found for {data['display_name']}, id: {data['osm_id']}")
            return data['osm_id']
    else:
        print("Error:", response.status_code, response.reason)
    return None

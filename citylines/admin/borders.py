import logging

import requests

from citylines.gtfs.gtfs import BoundingBox, coord2px


def _parse_osm_borders(osm_data: dict, bbox: BoundingBox) -> list:
    nodes = {node['id']: coord2px(node['lat'], node['lon'], bbox) for node in osm_data['elements'] if node['type'] == 'node'}
    ways = [way for way in osm_data['elements'] if way['type'] == 'way']

    # Create a list of way paths, which are lists of node coordinates
    way_paths = []
    for way in ways:
        way_path = [nodes[node_id] for node_id in way['nodes']]
        way_paths.append(way_path)

    return way_paths


def get_osm_admin_borders(place_id: str, bbox: BoundingBox) -> list:
    # Overpass API URL
    url = "https://overpass-api.de/api/interpreter"

    # Overpass QL query to fetch administrative borders
    query = f"""
    [out:json][timeout:25];
    relation({place_id});
    out body;
    >;
    out skel qt;
    """

    # Sending the request to the Overpass API
    response = requests.get(url, params={'data': query})

    # Check if the request was successful
    if response.status_code == 200:
        return _parse_osm_borders(response.json(), bbox)
    else:
        raise Exception(f"Overpass response error {response.status_code}: {response.text}")

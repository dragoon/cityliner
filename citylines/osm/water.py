import requests

from citylines.gtfs.gtfs import BoundingBox, coord2px


def get_osm_water_bodies(bbox: BoundingBox):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][bbox:{bbox.bottom},{bbox.left},{bbox.top},{bbox.right}];
    (
      relation["natural"="water"]["water"~"lake|river|pond|reservoir|stream|canal"];
      way(r:"outer");
    );
    out body;
    >;
    out skel qt;
    """
    response = requests.get(overpass_url, params={'data': query})
    data = response.json()
    flat_ways = []
    node_dict = {}
    for n in data["elements"]:
        if n["type"] == "node":
            px = coord2px(n["lat"], n["lon"], bbox)
            node_dict[n["id"]] = px
    for way in data["elements"]:
        if way["type"] == "way":
            way_nodes = [node_dict[n_id] for n_id in way["nodes"]]
            flat_ways.append(way_nodes)

    # convert ways to
    return flat_ways

import requests


def get_osm_water_bodies(bbox):
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][bbox:{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}];
    way["natural"="water"];
    (._;>;);
    out;
    """
    response = requests.get(overpass_url, params={'data': query})
    data = response.json()
    flat_ways = []
    node_dict = {n["id"]: {"lat": n["lat"], "lon": n["lon"]} for n in data["elements"] if n["type"] == "node"}
    for way in data["elements"]:
        if way["type"] == "way":
            way_nodes = [node_dict[n_id] for n_id in way["nodes"]]
            flat_ways.append(way_nodes)

    # convert ways to
    return flat_ways

from itertools import chain

import requests

from citylines.gtfs.gtfs import BoundingBox, coord2px


def get_osm_water_bodies(bbox: BoundingBox) -> list[dict]:
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][bbox:{bbox.bottom},{bbox.left},{bbox.top},{bbox.right}];
    (
      relation["natural"="water"]["water"~"lake|river|pond|reservoir|stream|canal"];
      way(r);
      way["natural"="water"]["water"~"lake|river|pond|reservoir|stream|canal"];
    );
    out tags body;
    >;
    out tags skel qt;
    """
    response = requests.get(overpass_url, params={'data': query})
    data = response.json()
    relations = []
    way_dict = {}
    node_dict = {}
    # first nodes
    for n in data["elements"]:
        if n["type"] == "node":
            px = coord2px(n["lat"], n["lon"], bbox)
            node_dict[n["id"]] = px
    # then ways
    for w in data["elements"]:
        if w["type"] == "way":
            way_nodes = [node_dict[n_id] for n_id in w["nodes"]]
            way_dict[w["id"]] = way_nodes
    # finally reconstruct relations
    for r in data["elements"]:
        if r["type"] == "relation":
            r_ways = []
            for w in r["members"]:
                if w["type"] == "way" and w["role"] == "outer":
                    if w["ref"] in way_dict:
                        # pop from dict
                        r_ways.append(way_dict.pop(w["ref"]))
            # flatten
            r_ways = list(chain.from_iterable(r_ways))
            relations.append({"name": r["tags"].get("name"), "nodes": r_ways})
    # also add other ways that were not part of relations
    for w in way_dict.values():
        relations.append({"name": "water-unnamed", "nodes": w})

    return relations

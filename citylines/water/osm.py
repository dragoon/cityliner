from itertools import chain

import requests

from citylines.gtfs.gtfs import BoundingBox, coord2px


def order_ways(ways):
    if not ways:
        return []

    # Use the first way as the starting point
    ordered_ways = [ways.pop(0)]

    while ways:
        # Get the last node of the current ordered way
        last_node = ordered_ways[-1][-1]

        # Find the next way that connects to this node
        next_way_index = next((i for i, way in enumerate(ways) if way[0] == last_node or way[-1] == last_node), None)

        if next_way_index is not None:
            next_way = ways.pop(next_way_index)
            # If the way is in the reverse direction, reverse it
            if next_way[0] == last_node:
                ordered_ways.append(next_way)
            else:
                ordered_ways.append(next_way[::-1])
        else:
            # If no more connecting ways, break the loop
            break

    return list(chain.from_iterable(ordered_ways))


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
            r_ways_unordered = []
            for w in r["members"]:
                if w["type"] == "way" and w["role"] == "outer":
                    if w["ref"] in way_dict:
                        r_ways_unordered.append(way_dict.pop(w["ref"]))
            r_ways = order_ways(r_ways_unordered)
            relations.append({"name": r["tags"].get("name"), "nodes": r_ways})
    # also add other ways that were not part of relations
    for w in way_dict.values():
        relations.append({"name": "water-unnamed", "nodes": w})

    return relations

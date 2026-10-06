"""Build a clipped, projected water layer from a fresh Overpass response."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize_full, unary_union

from .export import write_json
from .geometry import R, bounds_for, project


def query_for(center, radius):
    delta = radius * 1000 / R * 180 / math.pi
    longitude = delta / math.cos(math.radians(center[0]))
    bbox = f"{center[0]-delta},{center[1]-longitude},{center[0]+delta},{center[1]+longitude}"
    selectors = [f'{kind}[{tag}]({bbox});' for kind in ("way", "relation")
                 for tag in ('"natural"="water"', '"waterway"="riverbank"')]
    return '[out:json][timeout:180];(' + ''.join(selectors) + ');out geom;'


def build_shapefile_water(path, center, radius, retrieved_at, url, data_timestamp):
    """Use a fresh regional extract when public Overpass services time out."""
    import geopandas as gpd
    from shapely.ops import transform

    delta = radius * 1000 / R * 180 / math.pi
    longitude = delta / math.cos(math.radians(center[0]))
    geographic = (center[1]-longitude, center[0]-delta, center[1]+longitude, center[0]+delta)
    frame = gpd.read_file(path, bbox=geographic)
    if frame.crs is None or frame.crs.to_epsg() != 4326:
        raise ValueError("Water shapefile must declare WGS84 / EPSG:4326")
    polygons, diagnostics = [], Counter()
    for polygon in frame.geometry:
        if polygon is None or polygon.is_empty or not polygon.is_valid:
            diagnostics["Invalid water polygon"] += 1
            continue
        projected = transform(lambda x, y, z=None: project(y, x, center), polygon)
        clipped = projected.intersection(box(*bounds_for(radius))).simplify(12, preserve_topology=True)
        pieces = [clipped] if clipped.geom_type == "Polygon" else getattr(clipped, "geoms", [])
        for piece in pieces:
            if piece.geom_type == "Polygon" and not piece.is_empty:
                polygons.append([[[round(x, 1), round(y, 1)] for x, y in ring.coords]
                                 for ring in [piece.exterior, *piece.interiors]])
        diagnostics["processed_elements"] += 1
    if not polygons:
        raise ValueError(f"No usable regional water polygons: {dict(diagnostics)}")
    return {"center": list(center), "bounds": bounds_for(radius), "polygons": polygons,
            "source": {"name": "© OpenStreetMap contributors, extract by Geofabrik", "url": "https://www.openstreetmap.org/copyright",
                       "license": "ODbL-1.0", "retrievedAt": retrieved_at,
                       "dataTimestamp": data_timestamp, "endpoint": url}, "diagnostics": dict(diagnostics)}


def build_water(data, center, radius, retrieved_at, endpoint):
    if data.get("remark"):
        raise ValueError("Overpass returned an incomplete result: " + data["remark"])
    diagnostics = Counter()
    polygons = []
    elements = data["elements"]
    # Members are rendered through their relations, preserving islands and holes.
    members = {m["ref"] for e in elements if e["type"] == "relation"
               for m in e.get("members", []) if m["type"] == "way"}

    def line(geometry):
        if not geometry or any(p is None or "lat" not in p or "lon" not in p for p in geometry):
            raise ValueError("Missing member geometry")
        return LineString([project(p["lat"], p["lon"], center) for p in geometry])

    def rings(lines):
        if not lines:
            raise ValueError("Missing outer ring")
        result, cuts, dangles, invalid = polygonize_full(unary_union(lines))
        if cuts.length or dangles.length or invalid.length or result.is_empty:
            raise ValueError("Unclosed relation rings")
        return unary_union(list(result.geoms))

    for element in elements:
        try:
            if element["type"] == "way":
                if element["id"] in members:
                    continue
                boundary = line(element.get("geometry"))
                if not boundary.is_ring:
                    raise ValueError("Unclosed water way")
                polygon = Polygon(boundary)
            elif element["type"] == "relation":
                outer, inner = [], []
                for member in element.get("members", []):
                    if member["type"] != "way":
                        if member["type"] == "relation":
                            raise ValueError("Nested water relation")
                        continue
                    role = member.get("role", "")
                    if role not in ("outer", "inner", ""):
                        raise ValueError("Unsupported member role")
                    (inner if role == "inner" else outer).append(line(member.get("geometry")))
                polygon = rings(outer)
                if inner:
                    polygon = polygon.difference(rings(inner))
            else:
                continue
            if not polygon.is_valid:
                raise ValueError("Invalid water polygon")
            polygon = polygon.intersection(box(*bounds_for(radius))).simplify(12, preserve_topology=True)
            pieces = [polygon] if polygon.geom_type == "Polygon" else getattr(polygon, "geoms", [])
            for piece in pieces:
                if piece.geom_type == "Polygon" and not piece.is_empty:
                    polygons.append([[[round(x, 1), round(y, 1)] for x, y in ring.coords]
                                     for ring in [piece.exterior, *piece.interiors]])
            diagnostics["processed_elements"] += 1
        except ValueError as exc:
            diagnostics[str(exc)] += 1
    if not polygons:
        raise ValueError(f"No usable water polygons: {dict(diagnostics)}")
    return {"center": list(center), "bounds": bounds_for(radius), "polygons": polygons,
            "source": {"name": "© OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright",
                       "license": "ODbL-1.0", "retrievedAt": retrieved_at,
                       "dataTimestamp": data.get("osm3s", {}).get("timestamp_osm_base"), "endpoint": endpoint},
            "diagnostics": dict(diagnostics)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--center", required=True)
    parser.add_argument("--max-dist", type=float, default=30)
    parser.add_argument("--query-output", type=Path)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--shapefile", type=Path, help="Regional WGS84 water polygon shapefile instead of Overpass JSON")
    parser.add_argument("--data-timestamp", help="Regional extract's published OSM timestamp")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--retrieved-at")
    parser.add_argument("--endpoint")
    args = parser.parse_args()
    center = tuple(map(float, args.center.split(",")))
    if len(center) != 2 or not -80 < center[0] < 80 or not 0 < args.max_dist <= 250:
        parser.error("Use latitude,longitude and a radius of 0–250 km below 80° latitude")
    if args.query_output:
        args.query_output.write_text(query_for(center, args.max_dist))
    if args.input or args.shapefile:
        if not args.output or not args.retrieved_at or not args.endpoint:
            parser.error("Water conversion requires --output, --retrieved-at and --endpoint")
        if args.input and args.shapefile:
            parser.error("Use --input or --shapefile, not both")
        if args.shapefile:
            if not args.data_timestamp:
                parser.error("Regional water requires --data-timestamp")
            layer = build_shapefile_water(args.shapefile, center, args.max_dist, args.retrieved_at, args.endpoint, args.data_timestamp)
        else:
            layer = build_water(json.loads(args.input.read_text()), center, args.max_dist, args.retrieved_at, args.endpoint)
        write_json(args.output, layer)
        print(json.dumps({"polygons": len(layer["polygons"]), "diagnostics": layer["diagnostics"], "source": layer["source"]}))


if __name__ == "__main__":
    main()

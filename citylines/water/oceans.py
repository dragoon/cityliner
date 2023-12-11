import geopandas as gpd
from shapely.geometry import box

from citylines.gtfs.gtfs import BoundingBox, coord2px


def process_polygon(polygon, bbox_orig: BoundingBox):
    exterior_nodes = [coord2px(lat, lon, bbox_orig) for lon, lat in polygon.exterior.coords]
    interiors = [[coord2px(lat, lon, bbox_orig) for lon, lat in interior.coords] for interior in polygon.interiors]
    return {"nodes": exterior_nodes, "name": "ocean", "interiors": interiors}


def get_ocean_water_bodies(bbox_orig: BoundingBox):
    # Load the Natural Earth Data
    water_gdf = gpd.read_file('oceans/water_polygons.shp')
    bbox = box(bbox_orig.left, bbox_orig.bottom, bbox_orig.right, bbox_orig.top)
    # Filter the data
    filtered_water_gdf = water_gdf[water_gdf.geometry.intersects(bbox)]

    # Initialize the result dictionary with an empty list for nodes
    result = []
    for geometry in filtered_water_gdf.geometry:
        if geometry.geom_type == 'Polygon':
            result.append(process_polygon(geometry, bbox_orig))
        elif geometry.geom_type == 'MultiPolygon':
            for polygon in geometry:
                result.append(process_polygon(polygon, bbox_orig))
    return result

import geopandas as gpd
from shapely.geometry import box

from citylines.gtfs.gtfs import BoundingBox, coord2px


def get_ocean_water_bodies(bbox_orig: BoundingBox):
    # Load the Natural Earth Data
    water_gdf = gpd.read_file('oceans/oceans-osm/water_polygons.shp')

    # Define your bounding box
    bbox = box(bbox_orig.left, bbox_orig.bottom, bbox_orig.right, bbox_orig.top)

    # Filter the data
    filtered_water_gdf = water_gdf[water_gdf.geometry.intersects(bbox)]

    # Initialize the result dictionary with an empty list for nodes
    result = []

    # Loop through each geometry in the filtered GeoDataFrame
    for geometry in filtered_water_gdf.geometry:
        if geometry.geom_type == 'Polygon':
            polygon_nodes = []
            for lon, lat in geometry.exterior.coords:
                polygon_nodes.append(coord2px(lat, lon, bbox_orig))
            result.append({"nodes": polygon_nodes, "name": "ocean"})
        elif geometry.geom_type == 'MultiPolygon':
            for polygon in geometry:
                exterior_nodes = []
                interior_nodes = []
                for lon, lat in polygon.exterior.coords:
                    exterior_nodes.append(coord2px(lat, lon, bbox_orig))

                for lon, lat in polygon.exterior.coords:
                    interior_nodes.append(coord2px(lat, lon, bbox_orig))
                result.append({"nodes": exterior_nodes, "name": "ocean", "interior": interior_nodes})
    return result

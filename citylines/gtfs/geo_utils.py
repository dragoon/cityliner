import math

from citylines.gtfs.domain import Point, MaxDistance


def _get_distance_from_lat_lon_in_km(point1: Point, point2: Point):
    earth_r = 6371
    d_lat = deg2rad(point2.lat - point1.lat)
    d_lon = deg2rad(point2.lon - point1.lon)
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.cos(deg2rad(point1.lat)) * math.cos(deg2rad(point2.lat)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_r * c


def deg2rad(deg):
    return deg * (math.pi / 180)


def _get_bearing(point1: Point, point2: Point):
    d_lon = deg2rad(point2.lon - point1.lon)
    y = math.sin(d_lon) * math.cos(deg2rad(point2.lat))
    x = math.cos(deg2rad(point1.lat)) * math.sin(deg2rad(point2.lat)) - \
        math.sin(deg2rad(point1.lat)) * math.cos(deg2rad(point2.lat)) * math.cos(d_lon)
    return abs(math.atan2(y, x))


def is_allowed_point(point1: Point, point2: Point, max_dist: MaxDistance):
    brng = _get_bearing(point1, point2)
    dist = _get_distance_from_lat_lon_in_km(point1, point2)

    if max_dist.max_angle < brng < math.pi - max_dist.max_angle:
        max_allowed_dist = max_dist.x / abs(math.sin(brng))
    else:
        max_allowed_dist = max_dist.y / abs(math.sin(math.pi / 2 - brng))
    return dist <= max_allowed_dist

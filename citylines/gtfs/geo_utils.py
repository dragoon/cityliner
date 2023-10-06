import math
from dataclasses import dataclass

from citylines.gtfs.domain import Point, RenderArea


@dataclass(frozen=True)
class Distance:
    dist_meters: float

    @staticmethod
    def from_km(dist_km: float) -> 'Distance':
        return Distance(dist_km * 1000)

    def m(self) -> int:
        return int(self.dist_meters)

    def km(self) -> int:
        return int(self.dist_meters / 1000)


@dataclass(frozen=True)
class MaxDistance:
    x: float
    y: float
    max_angle: float

    @staticmethod
    def from_distance(dist: Distance, render_area: RenderArea):
        x = dist.km() * render_area.width_px / render_area.height_px
        y = dist.km()
        max_angle = math.asin(x / math.sqrt(x ** 2 + y ** 2))
        return MaxDistance(x, y, max_angle)


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

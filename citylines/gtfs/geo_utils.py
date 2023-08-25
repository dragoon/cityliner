import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class MaxDistance:
    x: float
    y: float
    max_angle: float = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, "max_angle", math.asin(self.x / math.sqrt(self.x ** 2 + self.y ** 2)))


def _get_distance_from_lat_lon_in_km(lat1, lon1, lat2, lon2):
    earth_r = 6371
    d_lat = deg2rad(lat2 - lat1)
    d_lon = deg2rad(lon2 - lon1)
    a = math.sin(d_lat / 2) * math.sin(d_lat / 2) + \
        math.cos(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * \
        math.sin(d_lon / 2) * math.sin(d_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_r * c


def deg2rad(deg):
    return deg * (math.pi / 180)


def _get_bearing(lat1, lon1, lat2, lon2):
    d_lon = deg2rad(lon2 - lon1)
    y = math.sin(d_lon) * math.cos(deg2rad(lat2))
    x = math.cos(deg2rad(lat1)) * math.sin(deg2rad(lat2)) - \
        math.sin(deg2rad(lat1)) * math.cos(deg2rad(lat2)) * math.cos(d_lon)
    return abs(math.atan2(y, x))


def is_allowed_point(lat1, lon1, lat2, lon2, max_dist: MaxDistance):
    brng = _get_bearing(lat1, lon1, lat2, lon2)
    dist = _get_distance_from_lat_lon_in_km(lat1, lon1, lat2, lon2)

    if max_dist.max_angle < brng < math.pi - max_dist.max_angle:
        max_allowed_dist = max_dist.x / abs(math.sin(brng))
    else:
        max_allowed_dist = max_dist.y / abs(math.sin(math.pi / 2 - brng))
    return dist <= max_allowed_dist

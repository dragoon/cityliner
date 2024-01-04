import math
from dataclasses import dataclass

from geopy.distance import distance


@dataclass(frozen=True)
class RenderArea:
    width_px: int
    height_px: int

    @staticmethod
    def poster() -> 'RenderArea':
        return RenderArea(width_px=9933, height_px=14043)


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


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


@dataclass(frozen=True)
class BoundingBox:
    left: float
    right: float
    top: float
    bottom: float
    center: Point
    render_area: RenderArea

    @staticmethod
    def from_center(center_p: Point, max_dist: MaxDistance, render_area: RenderArea) -> 'BoundingBox':
        center = (center_p.lat, center_p.lon)

        # Calculate the points north, south, east, and west of the center
        north = distance(kilometers=max_dist.y).destination(center, bearing=0)
        south = distance(kilometers=max_dist.y).destination(center, bearing=180)
        east = distance(kilometers=max_dist.x).destination(center, bearing=90)
        west = distance(kilometers=max_dist.x).destination(center, bearing=270)

        # Extract latitudes and longitudes to form the bounding box
        return BoundingBox(west.longitude, east.longitude, north.latitude, south.latitude, center_p, render_area)

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def scale_factor_lat(self):
        return self.render_area.height_px / max(abs(self.center.lat - self.top), abs(self.center.lat - self.bottom))

    @property
    def scale_factor_lon(self):
        return self.render_area.width_px / max(abs(self.center.lon - self.left), abs(self.center.lon - self.right))


@dataclass(frozen=True)
class SegmentsDataset:
    segments: list[dict]
    max_trips_per_seg: int
    min_trips_per_seg: int

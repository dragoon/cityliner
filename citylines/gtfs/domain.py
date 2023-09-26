from dataclasses import dataclass


@dataclass(frozen=True)
class RenderArea:
    width_px: int
    height_px: int


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


@dataclass(frozen=True)
class BoundingBox:
    left: float
    right: float
    top: float
    bottom: float
    center: Point
    render_area: RenderArea

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def aspect_ratio(self):
        return self.width / self.height

    @property
    def canvas_aspect_ratio(self):
        return self.render_area.width_px / self.render_area.height_px

    @property
    def scale_factor_lat(self):
        return self.render_area.height_px / max(abs(self.center.lat - self.top), abs(self.center.lat - self.bottom))

    @property
    def scale_factor_lon(self):
        return self.render_area.width_px / max(abs(self.center.lon - self.left), abs(self.center.lon - self.right))


@dataclass(frozen=True)
class SegmentsDataset:
    segments: list[dict]
    bbox: BoundingBox
    max_trips_per_seg: int
    min_trips_per_seg: int

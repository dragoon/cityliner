import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import csv

from gtfs.geo_utils import is_allowed_point, MaxDistance


@dataclass(frozen=True)
class BoundingBox:
    left: int
    right: int
    top: int
    bottom: int
    render_area: dict

    @property
    def width(self):
        return self.right - self.left

    @property
    def height(self):
        return self.top - self.bottom

    @property
    def width_f(self):
        return self.render_area["width"] / self.width

    @property
    def height_f(self):
        return self.render_area["height"] / self.height

    @staticmethod
    def from_shapes() -> 'BoundingBox':
        pass


@dataclass(frozen=True)
class SegmentsDataset:
    segments: list[dict]
    bbox: BoundingBox
    max_trips_per_seg: int
    min_trips_per_seg: int


@dataclass(frozen=True)
class GTFSDataset:
    gtfs_folder_path: Path

    def _parse_routes(self) -> Iterable:
        with open(self.gtfs_folder_path / "routes.txt", 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                route_id = row["route_id"]
                route_type = row["route_type"]
                yield route_id, route_type

    def _parse_trips(self) -> Iterable:
        with open(self.gtfs_folder_path / "trips.txt", 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                shape_id = row["shape_id"]
                route_id = row["route_id"]
                yield shape_id, route_id

    def _parse_shapes(self) -> Iterable:
        with open(self.gtfs_folder_path / "shapes.txt", 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                shape_id = row["shape_id"]
                shape_pt_lat = row["shape_pt_lat"]
                shape_pt_lon = row["shape_pt_lon"]
                shape_pt_sequence = row["shape_pt_sequence"]
                yield shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence, row

    def _get_route_id_types(self) -> dict:
        logging.debug("Starting route types iteration...")
        route_id_types = {}
        for route_id, route_type in self._parse_routes():
            route_id_types[route_id] = int(route_type)
        logging.debug("Finished route type iteration")
        logging.debug(f"Total routes: {len(route_id_types)}")
        return route_id_types

    def _get_trips_and_routes(self) -> Tuple[dict, dict]:
        route_id_types = self._get_route_id_types()
        route_types = {}
        # count the trips on a certain id
        trips_on_a_shape = defaultdict(lambda: 0)

        logging.debug("Starting trip iteration...")

        for shape_id, route_id in self._parse_trips():
            trips_on_a_shape[shape_id] += 1
            route_type = route_id_types[route_id]
            if shape_id not in route_types:
                route_types[shape_id] = route_type

        logging.debug("Finished trip iteration")
        return route_types, trips_on_a_shape

    def _get_sequences(self, center_lat: float | None, center_lon: float | None, max_dist: MaxDistance) -> dict:
        logging.debug("Starting shape iteration...")
        sequences = defaultdict(dict)
        for shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence, shape_row in self._parse_shapes():
            # check out of boundaries
            if center_lat and center_lon:
                if is_allowed_point(float(shape_pt_lat), float(shape_pt_lon), center_lat, center_lon, max_dist):
                    sequences[shape_id][shape_pt_sequence] = shape_row
            else:
                sequences[shape_id][shape_pt_sequence] = shape_row

        logging.debug("Finished shape iteration")
        return sequences

    def compute_segments(self, center_lat: float | None, center_lon: float | None, render_area: dict,
                         max_dist: MaxDistance) -> SegmentsDataset:
        route_types, trips_on_a_shape = self._get_trips_and_routes()
        sequences = self._get_sequences(center_lat, center_lon, max_dist)
        segments = []
        max_trips, min_trips = 0, math.inf
        min_left, max_right, max_top, min_bottom = math.inf, 0, 0, math.inf

        for shape_id, shape_sequences in sequences.items():
            route_type = get_route_type_for_shape_id(shape_id, route_types)

            if route_type is None:
                continue
            if shape_id not in trips_on_a_shape:
                continue

            trips_n = trips_on_a_shape[shape_id]

            if trips_n > max_trips:
                max_trips = trips_n

            if trips_n < min_trips:
                min_trips = trips_n

            pts = []
            for seq, shape in shape_sequences.items():
                y = float(shape['shape_pt_lat'])
                x = float(shape['shape_pt_lon'])
                min_left = min(x, min_left)
                min_bottom = min(y, min_bottom)
                max_top = max(y, max_top)
                max_right = max(x, max_right)

                pts.append({'lat': shape['shape_pt_lat'], 'lon': shape['shape_pt_lon']})

            if len(pts) == 0:
                continue

            segments.append({
                "trips": trips_n,
                "coordinates": pts,
                "route_type": route_type
            })

        logging.debug("Segments created.")

        if max_trips == min_trips and max_trips > 0:
            min_trips -= 1
        if max_trips == min_trips and max_trips <= 0:
            max_trips += 1

        logging.debug(f"max trips per segment: {max_trips}")
        logging.debug(f"min trips per segment: {min_trips}")

        return SegmentsDataset(segments, BoundingBox(min_left, max_right, max_top, min_bottom, render_area), max_trips,
                               min_trips)

    @staticmethod
    def from_path(gtfs_folder: str) -> 'GTFSDataset':
        return GTFSDataset(Path(gtfs_folder))


def get_route_type_for_shape_id(shape_id, route_types):
    route_type = route_types.get(shape_id)
    short_type = route_type // 100  # Integer division to get the equivalent of '>>0'

    if short_type == 7:
        route_type = 3
    elif short_type == 1:
        route_type = 2
    elif short_type == 5:
        route_type = 1
    elif short_type in [9, 8]:
        route_type = 0

    return route_type

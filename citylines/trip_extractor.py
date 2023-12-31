import json
import logging
from pathlib import Path

from citylines.admin.borders import get_osm_admin_borders
from citylines.admin.geocode import get_place_relation_id
from citylines.gtfs.domain import RenderArea, MaxDistance, Distance, BoundingBox
from citylines.water.oceans import get_ocean_water_bodies
from citylines.water.other_water import get_osm_water_bodies
from citylines.gtfs.gtfs import GTFSDataset, SegmentsDataset, coord2px, Point


def create_file(out_dir: Path, seg: SegmentsDataset, bbox: BoundingBox):
    segm_length = len(seg.segments)
    logging.info("Starting to write file: data.lines")

    # Open the file once for writing
    with open(out_dir / "data.lines", "w", encoding="utf-8") as file:
        for idx, segment in enumerate(seg.segments):
            coords = ",".join(
                f'{px["x"]} {px["y"]}'
                for un in segment["coordinates"]
                for px in [coord2px(float(un["lat"]), float(un["lon"]), bbox)]
            )
            route_type = segment["route_type"]
            line = f"{segment['trips']}\t{route_type}\t{coords}\n"
            file.write(line)

            if (segm_length - idx) % 10 == 0:
                logging.debug(f"{(segm_length - idx)} segments left")

    # Write max and min values
    logging.info("Starting to write file: maxmin.lines")
    with open(out_dir / "maxmin.lines", "w", encoding="utf-8") as file:
        file.write(f"{seg.max_trips_per_seg}\n{seg.min_trips_per_seg}")

    logging.info("Write complete")


def process_gtfs_trips(center_point: Point, out_dir: Path, gtfs_dir: str, max_dist_y: Distance,
                       render_area: RenderArea, add_water: bool, add_borders: bool):
    max_dist = MaxDistance.from_distance(max_dist_y, render_area)
    bbox = BoundingBox.from_center(center_point, max_dist, render_area=render_area)
    out_dir.mkdir(parents=True, exist_ok=True)

    if add_borders and not (out_dir / "borders_osm.json").exists():
        logging.debug("Extracting borders...")
        place_id = get_place_relation_id(center_point.lat, center_point.lon)
        borders = get_osm_admin_borders(place_id=place_id, bbox=bbox)
        with open(out_dir / "borders_osm.json", 'w') as f:
            json.dump(borders, f)

    if add_water and not (out_dir / "water_bodies_osm.json").exists():
        logging.debug("Extracting water bodies...")
        water_bodies = get_osm_water_bodies(bbox=bbox)
        water_bodies.extend(get_ocean_water_bodies(bbox_orig=bbox))
        with open(out_dir / "water_bodies_osm.json", 'w') as f:
            json.dump(water_bodies, f)

    if not (out_dir / "data.lines").exists():
        logging.debug(f"GTFS provider: {gtfs_dir}")
        logging.debug(f"Render area: {render_area.width_px} x {render_area.height_px} px")
        logging.debug(f"Center coordinates: {center_point}")
        logging.debug(f"Max distance from center: {max_dist.x}x{max_dist.y}km")

        logging.debug("Computing GTFS segments data...")
        dataset = GTFSDataset.from_path(gtfs_dir)
        segments = dataset.compute_segments(center_point, max_dist)
        create_file(out_dir, segments, bbox)
        logging.debug(f"Route frequency files written to {out_dir}")
    else:
        logging.debug(f"data.lines file in {out_dir} already exists, skipping re-generation")

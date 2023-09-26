import json
import os
import argparse
import logging

from citylines.gtfs.domain import RenderArea
from citylines.water.oceans import get_ocean_water_bodies
from citylines.water.osm import get_osm_water_bodies
from gtfs.geo_utils import MaxDistance, Distance
from gtfs.gtfs import GTFSDataset, SegmentsDataset, coord2px, Point

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def create_file(out_dir: str, seg: SegmentsDataset):
    # Create directory if it doesn't exist
    os.makedirs(out_dir, exist_ok=True)

    segm_length = len(seg.segments)
    logger.info("Starting to write file: data.lines")

    # Open the file once for writing
    with open(os.path.join(out_dir, "data.lines"), "w", encoding="utf-8") as file:
        for idx, segment in enumerate(seg.segments):
            coords = ",".join(
                f'{px["x"]} {px["y"]}'
                for un in segment["coordinates"]
                for px in [coord2px(float(un["lat"]), float(un["lon"]), seg.bbox)]
            )
            route_type = segment["route_type"]
            line = f"{segment['trips']}\t{route_type}\t{coords}\n"
            file.write(line)

            if (segm_length - idx) % 10 == 0:
                logger.debug(f"{(segm_length - idx)} segments left")

    # Write max and min values
    logger.info("Starting to write file: maxmin.lines")
    with open(os.path.join(out_dir, "maxmin.lines"), "w", encoding="utf-8") as file:
        file.write(f"{seg.max_trips_per_seg}\n{seg.min_trips_per_seg}")

    logger.info("Write complete")


def process_gtfs_trips(center_point: Point, out_dir: str, gtfs_dir: str, max_dist_y: Distance, render_area: RenderArea):
    max_dist = MaxDistance.from_distance(max_dist_y, render_area)

    logger.debug(f"GTFS provider: {gtfs_dir}")
    logger.debug(f"Render area: {render_area.width_px} x {render_area.height_px} px")
    logger.debug(f"Center coordinates: {center_point}")
    logger.debug(f"Max distance from center: {max_dist.x}x{max_dist.y}km")

    logger.debug("Starting to prepare data...")
    dataset = GTFSDataset.from_path(gtfs_dir)
    segments = dataset.compute_segments(center_point, render_area, max_dist)
    water_bodies = get_osm_water_bodies(bbox=segments.bbox)
    water_bodies.extend(get_ocean_water_bodies(bbox_orig=segments.bbox))
    with open(f'{out_dir}/water_bodies_osm.json', 'w') as f:
        json.dump(water_bodies, f)
    create_file(out_dir, segments)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process GTFS data to output lines.')
    parser.add_argument('--gtfs', required=True, help='Path to the gtfs directory')
    parser.add_argument('--out', required=True, help="Path to the output directory (will be created if doesn't exist)")
    parser.add_argument('--max-dist', type=float, default=20.0, help='Maximum distance from the center on y axis')
    parser.add_argument('--size', type=int, default=5000, help='Size of the output drawing in px')
    parser.add_argument('--center', help='Coordinates of the center')
    parser.add_argument('--poster', action='store_true', help='Make drawing for A0 poster size')

    args = parser.parse_args()
    logger.setLevel(logging.DEBUG)
    center_lat, center_lon = map(float, args.center.split(","))
    if args.poster:
        render_area = RenderArea(width_px=9933, height_px=14043)
    else:
        render_area = RenderArea(args.size, args.size)
    process_gtfs_trips(center_point=Point(center_lat, center_lon), out_dir=args.out, gtfs_dir=args.gtfs,
                       max_dist_y=Distance.from_km(args.max_dist), render_area=render_area)

import os
import argparse
from pathlib import Path
import logging

from gtfs.geo_utils import MaxDistance
from gtfs.gtfs import GTFSDataset, BoundingBox, SegmentsDataset

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def coord2px(lat: float, lng: float, bbox: BoundingBox):
    coord_x = bbox.width_f * (lng - bbox.left)
    coord_y = bbox.height_f * (bbox.top - lat)
    return {'x': coord_x, 'y': coord_y}


def create_file(out_dir: str, seg: SegmentsDataset):
    # Create directory if it doesn't exist
    os.makedirs(out_dir, exist_ok=True)

    segm_length = len(seg.segments)
    logger.debug("Starting to create file...")

    # Open the file once for writing
    with open(os.path.join(out_dir, "data.lines"), "w", encoding="utf-8") as file:
        for idx, segment in enumerate(seg.segments):
            coords = ",".join(
                f'{coord2px(float(un["lat"]), float(un["lon"]), seg.bbox)["x"]} {coord2px(float(un["lat"]), float(un["lon"]), seg.bbox)["y"]}'
                for un in segment["coordinates"])
            route_type = segment["route_type"]
            line = f"{segment['trips']}\t{route_type}\t{coords}\n"
            file.write(line)

            if (segm_length - idx) % 10 == 0:
                logger.debug(f"{(segm_length - idx)} segments left")

    # Write max and min values
    with open(os.path.join(out_dir, "maxmin.lines"), "w", encoding="utf-8") as file:
        file.write(f"{seg.max_trips_per_seg}\n{seg.min_trips_per_seg}")

    logger.debug("Write complete")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process GTFS data to output lines.')
    parser.add_argument('--verbose', '-v', action='store_true', help='Make verbose')
    parser.add_argument('--gtfs', required=True, help='Path to the gtfs directory')
    parser.add_argument('--out', help="Path to the output directory (will be created if doesn't exist)")
    parser.add_argument('--max-dist', type=float, default=20.0, help='Maximum distance from the center on y axis')
    parser.add_argument('--size', type=int, default=5000, help='Size of the output drawing in px')
    parser.add_argument('--center', help='Coordinates of the center')
    parser.add_argument('--poster', action='store_true', help='Make drawing for A0 poster size')

    args = parser.parse_args()
    render_area_a0 = {'width': 9933, 'height': 14043}
    center_lat = None
    center_lon = None
    out_dir = args.out or args.gtfs

    if args.center:
        center_lat, center_lon = map(float, args.center.split(","))

    if args.poster:
        render_area = render_area_a0
    else:
        render_area = {'width': args.size, 'height': args.size}

    max_dist = MaxDistance(args.max_dist * render_area['width'] / render_area['height'], args.max_dist)

    logger.debug(f"GTFS provider: {args.gtfs}", args.verbose)
    logger.debug(f"Render area: {render_area['width']} x {render_area['height']} px", args.verbose)
    if args.center:
        logger.debug(f"Center coordinates: {center_lat}, {center_lon}", args.verbose)
    logger.debug(f"Max distance from center: {max_dist.x}x{max_dist.y}km", args.verbose)

    required_file = Path("./gtfs/") / args.gtfs / "shapes.txt"
    if not required_file.exists():
        print(f"\nERROR: {required_file} does not exist.\nExiting.\n")
        exit(1)

    logger.debug("Starting to prepare data...")
    dataset = GTFSDataset.from_path(Path("./gtfs/") / args.gtfs)
    segments = dataset.compute_segments(center_lat, center_lon, render_area, max_dist)
    create_file(out_dir, segments)

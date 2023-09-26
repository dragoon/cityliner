import argparse
import logging
from pathlib import Path

from citylines.generate_poster import Poster
from citylines.gtfs.domain import RenderArea, Point
from citylines.gtfs.geo_utils import Distance
from citylines.trip_extractor import process_gtfs_trips

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Process GTFS data to output lines.')
    parser.add_argument('--gtfs', required=True, help='Path to the gtfs directory')
    parser.add_argument('--out', required=True, help="Path to the output directory (will be created if doesn't exist)")
    parser.add_argument('--max-dist', type=float, default=20.0, help='Maximum distance from the center on y axis')
    parser.add_argument('--size', type=int, default=5000, help='Size of the output drawing in px')
    parser.add_argument('--water', action='store_true', help='Add water bodies on poster')
    parser.add_argument('--center', help='Coordinates of the center')
    parser.add_argument('--poster', action='store_true', help='Make drawing for A0 poster size')

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    args = parser.parse_args()
    center_lat, center_lon = map(float, args.center.split(","))
    if args.poster:
        render_area = RenderArea.poster()
    else:
        render_area = RenderArea(args.size, args.size)

    process_gtfs_trips(center_point=Point(center_lat, center_lon), out_dir=args.out, gtfs_dir=args.gtfs,
                       max_dist_y=Distance.from_km(args.max_dist), render_area=render_area)

    p = Poster(render_area, name="helsinki", out_dir=Path("./posters"),
               input_dir=Path("./processed"), city="helsinki",
               logos=["helsinki.svg", "hsl.svg"])
    p.generate_single(add_water=args.water)
    # p.apply_fade_effect()

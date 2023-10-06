import argparse
import logging
from pathlib import Path

from citylines.generate_poster import Poster
from citylines.gtfs.domain import RenderArea, Point
from citylines.gtfs.geo_utils import Distance
from citylines.trip_extractor import process_gtfs_trips
from citylines.util.colors import color_schemes

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(description='Process GTFS data to output lines.')
    parser.add_argument('--gtfs', required=True, help='Path to the input gtfs directory')
    parser.add_argument('--processed-dir', default="processed",
                        help="Base path to the processed gtfs directory (will be created if doesn't exist)")
    parser.add_argument('--max-dist', type=int, default=20,
                        help='Maximum distance from the center on y axis (in km)')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--poster', action='store_true', help='Make A0 poster (9933x14043 px)')
    group.add_argument('--size', type=int, help='Size of the output drawing (in px)')

    parser.add_argument('--water', action='store_true', help='Add water bodies to the poster')
    parser.add_argument('--center', required=True, help='Coordinates of the center')
    parser.add_argument('--place_name', required=True, help='Name for the place')
    parser.add_argument('--logos', nargs='*', default=[],
                        help='List of logos for the poster (inside ./assets/logos/{place_name}/)')
    parser.add_argument('--color-scheme', choices=color_schemes.keys(), default='default',
                        help='Choose a color scheme for the poster. Allowed values are: %(choices)s')

    args = parser.parse_args()
    center_lat, center_lon = map(float, args.center.split(","))
    if args.poster:
        render_area = RenderArea.poster()
    else:
        render_area = RenderArea(args.size, args.size)

    dist = Distance.from_km(args.max_dist)
    out_dir = Path(f"{args.processed_dir}/{args.place_name}/{dist.km()}")

    process_gtfs_trips(center_point=Point(center_lat, center_lon), out_dir=out_dir, gtfs_dir=args.gtfs,
                       max_dist_y=dist, render_area=render_area)

    p = Poster(render_area, out_path=Path(f"./posters/{args.place_name}-{dist.km()}"),
               input_dir=out_dir, city=args.place_name,
               logos=[logo for logo in args.logos], text="")
    p.generate_single(add_water=args.water, color_scheme=color_schemes[args.color_scheme])

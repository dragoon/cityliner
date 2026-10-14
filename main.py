import argparse
import logging
from pathlib import Path

from citylines.generate_poster import Poster, heading_font_path
from citylines.gtfs.domain import RenderArea, Point, Distance
from citylines.trip_extractor import process_gtfs_trips
from citylines.util.colors import color_schemes

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger('fiona.ogrext').setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description='Process GTFS data to output lines.')
    parser.add_argument('--gtfs', required=True, help='Path to the input gtfs directory')
    parser.add_argument('--processed-dir', default="processed",
                        help="Base path to the processed gtfs directory (will be created if doesn't exist)")
    parser.add_argument('--max-dist', type=int, default=20,
                        help='Maximum distance from the center on y axis (in km)')

    parser.add_argument('--poster', action='store_true', help='Make A0 poster (9933x14043 px)')
    parser.add_argument('--width', type=int, help='Width of the output drawing (in px)')
    parser.add_argument('--height', type=int, help='Height of the output drawing (in px)')

    parser.add_argument('--water', action='store_true', help='Add water bodies to the poster')
    parser.add_argument('--admin-borders', action='store_true', help='Add water bodies to the poster')
    parser.add_argument('--center', required=True, help='Coordinates of the center')
    parser.add_argument('--place-name', required=True, help='Name for the place')
    parser.add_argument('--logos', nargs='*', default=[],
                        help='Optional marks you are entitled to use (inside ./assets/logos/{place_name}/)')
    parser.add_argument('--color-scheme', choices=color_schemes.keys(), default='pastel',
                        help='Choose a color scheme for the poster. Allowed values are: %(choices)s')
    parser.add_argument('--credit', action='append', default=[], help='Source/license credit line (repeatable)')
    parser.add_argument('--heading-font', type=Path, help='Optional heading .ttf override; defaults to bundled Gelasio')

    args = parser.parse_args()

    try:
        args.heading_font = heading_font_path(args.heading_font)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    center_lat, center_lon = map(float, args.center.split(","))
    if args.poster:
        render_area = RenderArea.poster()
    elif args.width and args.height:
        render_area = RenderArea(args.width, args.height)
    else:
        parser.error("Either both width and height must be provided, or --poster must be set.")

    dist = Distance.from_km(args.max_dist)
    out_dir = Path(f"{args.processed_dir}/{args.place_name}/{dist.km()}")

    process_gtfs_trips(center_point=Point(center_lat, center_lon), out_dir=out_dir, gtfs_dir=args.gtfs,
                       max_dist_y=dist, render_area=render_area, add_water=args.water, add_borders=args.admin_borders)
    logging.info("Generating pdf image...")

    image_filepath = Path(f"./posters/{args.place_name}-{dist.km()}.pdf")
    p = Poster(render_area, out_path=image_filepath,
               input_dir=out_dir, city=args.place_name,
               logos=[logo for logo in args.logos],
               text='\n'.join(args.credit + ['Cityliner by Roman Prokofyev | cityliner.app']),
               heading_font=args.heading_font)
    p.generate_single(add_water=args.water, add_admin_borders=args.admin_borders,
                      color_scheme=color_schemes[args.color_scheme])
    logging.info(f"PDF generated at {image_filepath}")

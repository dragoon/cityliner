import argparse
import logging
from pathlib import Path

from citylines.generate_poster import Poster
from citylines.gtfs.domain import RenderArea, Point
from citylines.gtfs.geo_utils import Distance
from citylines.trip_extractor import process_gtfs_trips
from citylines.util.colors import inferno_scheme

PLACE_CONFIGS = {
    "zurich": {
        "center": Point(47.3773887, 8.5386569),
        "distances": [10, 20, 30],
        "logos": ["kanton_zurich.svg", "zurich_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "bern": {
        "center": Point(46.948020, 7.447440),
        "distances": [5, 10, 20],
        "logos": ["kanton_bern.svg", "bern_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "fribourg": {
        "center": Point(46.806477, 7.161972),
        "distances": [5, 10, 20],
        "logos": ["kanton_fribourg.svg", "fribourg_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "basel": {
        "center": Point(47.559601, 7.588576),
        "distances": [10, 20, 30],
        "logos": ["kanton_basel.svg", "basel_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "st. gallen": {
        "center": Point(47.422258, 9.376610),
        "distances": [5, 10, 20],
        "logos": ["kanton_st_gallen.svg", "st_gallen_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "geneva": {
        "center": Point(46.204391, 6.143158),
        "distances": [10, 20, 30],
        "logos": ["kanton_geneva.svg", "geneva_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "lausanne": {
        "center": Point(46.519654, 6.632273),
        "distances": [10, 20, 30],
        "logos": ["kanton_vaud.svg", "lausanne_coat_of_arms.svg"],
        "gtfs": "switzerland"
    },
    "helsinki": {
        "center": Point(60.1706017, 24.9414482),
        "distances": [10, 20, 30],
        "logos": ["helsinki.svg", "hsl.svg"],
        "gtfs": "helsinki"
    },
    "tallinn": {
        "center": Point(59.4370, 24.7365),
        "distances": [5, 10, 20],
        "logos": ["tallinn.svg", "tlt.svg"],
        "gtfs": "tallinn"
    },
    "berlin": {
        "center": Point(52.52493, 13.36963),
        "distances": [10, 20, 30, 50],
        "logos": ["berlin_city.svg", "bvb.svg"],
        "gtfs": "berlin"
    },
    "hamburg": {
        "center": Point(53.552968, 10.006038),
        "distances": [10, 20, 30, 50],
        "logos": ["hamburg.svg", "hvv.svg"],
        "gtfs": "hamburg"
    },
    "amsterdam": {
        "center": Point(52.379189, 4.899431),
        "distances": [10, 20, 30, 50],
        "logos": ["gemeente_amsterdam.svg", "gvb.svg"],
        "gtfs": "netherlands"
    },
    "urtrecht": {
        "center": Point(52.0894444, 5.1077981),
        "distances": [5, 10, 20],
        "logos": ["city_of_utrecht.svg", "u-ov.svg"],
        "gtfs": "netherlands"
    }
}

if __name__ == "__main__":

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    for name, place_config in PLACE_CONFIGS.items():
        render_area = RenderArea.poster()
        for max_dist in place_config["distances"]:
            out_dir = f"./processed/{name}/{max_dist.replace('.', '_')}"

            process_gtfs_trips(center_point=place_config["center"],
                               out_dir=out_dir,
                               gtfs_dir=place_config["gtfs"],
                               max_dist_y=Distance.from_km(max_dist),
                               render_area=render_area)

            p = Poster(render_area, out_path=Path(f"./posters/{name}-{max_dist.replace('.', '_')}.pdf"),
                       input_dir=Path(out_dir), city=name,
                       logos=place_config["logos"])
            p.generate_single(add_water=True, color_scheme=inferno_scheme)
            # p.apply_fade_effect()

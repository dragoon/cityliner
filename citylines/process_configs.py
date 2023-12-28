import argparse
import logging
from pathlib import Path

from citylines.generate_poster import Poster
from citylines.gtfs.domain import RenderArea, Point
from citylines.gtfs.geo_utils import Distance
from citylines.trip_extractor import process_gtfs_trips
from citylines.util.colors import color_schemes

PLACE_CONFIGS = {
    "warsaw": {
        "center": Point(52.228865, 21.0006369),
        "distances": [30, 50],
        "logos": [],
        "gtfs": "warsaw",
        "color_scheme": "pastel",
        "text": """Warsaw public transport routes"""
    },
    "wroclaw": {
        "center": Point(51.1094782, 17.0108073),
        "distances": [30, 50],
        "logos": [],
        "gtfs": "wroclaw",
        "color_scheme": "pastel",
        "text": """Wrocław public transport routes"""
    },
    "zurich": {
        "center": Point(47.3773887, 8.5386569),
        "distances": [20, 30, 50],
        "logos": ["kanton_zurich.svg", "zurich_coat_of_arms.svg"],
        "gtfs": "switzerland",
        "color_scheme": "inferno",
        "text": """Based on GTFS feed by Swiss Federal Railways\nZurich public transport routes"""
    },
    "bern": {
        "center": Point(46.948020, 7.447440),
        "distances": [10, 20, 30],
        "logos": ["kanton_bern.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nBern public transport routes"""
    },
    "fribourg": {
        "center": Point(46.806477, 7.161972),
        "distances": [10, 20, 30],
        "logos": ["kanton_fribourg.svg", "logo-fribourg-en.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nFribourg public transport routes"""
    },
    "basel": {
        "center": Point(47.559601, 7.588576),
        "distances": [20, 30],
        "logos": ["kanton_basel.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nBasel public transport routes"""
    },
    "st-gallen": {
        "center": Point(47.422258, 9.376610),
        "distances": [20, 30],
        "logos": ["kanton_st_gallen.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nSt. Gallen public transport routes"""
    },
    "geneva": {
        "center": Point(46.204391, 6.143158),
        "distances": [20, 30, 50],
        "logos": ["kanton_geneva.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nGeneva public transport routes"""
    },
    "lausanne": {
        "center": Point(46.519654, 6.632273),
        "distances": [20, 30],
        "logos": ["kanton_vaud.svg"],
        "gtfs": "switzerland",
        "text": """Based on GTFS feed by Swiss Federal Railways\nLausanne public transport routes"""
    },
    "helsinki": {
        "center": Point(60.1706017, 24.9414482),
        "distances": [20, 30],
        "logos": ["helsinki.svg", "hsl.svg"],
        "gtfs": "helsinki",
        "color_scheme": "default",
        "text": """Based on GTFS feed by HSL\nHelsinki public transport routes"""
    },
    "tallinn": {
        "center": Point(59.4370, 24.7365),
        "distances": [20, 30, 50],
        "logos": ["tallinn.svg", "tlt.svg"],
        "gtfs": "tallinn",
        "color_scheme": "pastel",
        "text": """Based on GTFS feed by TLT\nTallinn public transport routes"""
    },
    "berlin": {
        "center": Point(52.52493, 13.36963),
        "distances": [30, 50],
        "logos": ["berlin_city.svg", "bvg.svg"],
        "gtfs": "berlin",
        "color_scheme": "cool",
        "text": """Based on GTFS feed by BVG\nBerlin public transport routes"""
    },
    "hamburg": {
        "center": Point(53.552968, 10.006038),
        "distances": [20, 30, 50],
        "logos": ["hamburg.svg", "hvv.svg"],
        "gtfs": "hamburg",
        "text": """Based on GTFS feed by HVV\nHamburg public transport routes"""
    },
    "amsterdam": {
        "center": Point(52.379189, 4.899431),
        "distances": [20, 30, 50],
        "logos": ["gemeente_amsterdam.svg", "gvb.svg"],
        "gtfs": "netherlands",
        "text": """Based on GTFS feed by NS\nAmsterdam public transport routes"""
    },
    "utrecht": {
        "center": Point(52.0894444, 5.1077981),
        "distances": [20, 30],
        "logos": ["city_of_utrecht.svg", "u-ov.svg"],
        "gtfs": "netherlands",
        "text": """Based on GTFS feed by NS\nUtrecht public transport routes"""
    },
    "prague": {
        "center": Point(50.0837751, 14.4249287),
        "distances": [30, 50],
        "logos": ["prague.svg", "pid.svg"],
        "gtfs": "prague",
        "text": """Based on GTFS feed by NS\nUtrecht public transport routes"""
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
        logger.info(f"Processing {name}")
        for max_dist in place_config["distances"]:
            logger.info(f"Distance: {max_dist}")
            out_dir = Path(f"./processed/{name}/{max_dist}")

            process_gtfs_trips(center_point=place_config["center"],
                               out_dir=out_dir,
                               gtfs_dir=f"./gtfs/{place_config['gtfs']}",
                               max_dist_y=Distance.from_km(max_dist),
                               render_area=render_area,
                               add_water=True)

            p = Poster(render_area, out_path=Path(f"./posters/{name}-{max_dist}.pdf"),
                       input_dir=out_dir, city=name,
                       logos=place_config["logos"],
                       text="")
            color_scheme = color_schemes[place_config.get("color_scheme", "default")]
            p.generate_single(add_water=True, color_scheme=color_scheme)

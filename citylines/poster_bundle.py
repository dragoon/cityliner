"""Build static, date-aware posters from the validated explorer geometry."""
import argparse
import gzip
import json
from pathlib import Path

from citylines.generate_poster import Poster, heading_font_path
from citylines.gtfs.domain import RenderArea
from citylines.util.colors import color_schemes

MODE_TYPES = {'tram': 0, 'subway': 1, 'rail': 2, 'bus': 3,
              'ferry_water': 4, 'funicular_cable_gondola': 6}


def prepare_bundle(bundle: Path, output: Path, area: RenderArea):
    """Preserve disconnected paths; use the actual weekly one-hour maxima."""
    manifest = json.loads((bundle / 'manifest.json').read_text())
    geometry = json.loads(gzip.decompress((bundle / manifest['geometry']).read_bytes()))
    output.mkdir(parents=True, exist_ok=True)
    radius = manifest['bounds'][3]
    scale = area.height_px / (2 * radius)
    values = []
    with (output / 'data.lines').open('w') as handle:
        for section in geometry['sections']:
            peak = section['peakDepartures']
            if peak <= 0 or section['mode'] not in MODE_TYPES:
                continue
            for points in section['paths']:
                if len(points) < 2:
                    continue
                # Explorer y increases downward; PDF y increases upward.
                coords = ','.join(f'{x*scale:.3f} {-y*scale:.3f}' for x,y in points)
                handle.write(f'{peak}\t{MODE_TYPES[section["mode"]]}\t{coords}\n')
                values.append(peak)
    if not values:
        raise ValueError('Bundle has no drawable scheduled sections')
    (output / 'maxmin.lines').write_text(f'{max(values)}\n{min(values)}\n')
    water = [{'nodes': [{'x': x*scale, 'y': -y*scale} for x,y in rings[0]],
              'interiors': [[{'x': x*scale, 'y': -y*scale} for x,y in ring] for ring in rings[1:]]}
             for rings in geometry.get('water', [])]
    (output / 'water_bodies_osm.json').write_text(json.dumps(water))
    return manifest


def render_bundle(bundle, output, palette='pastel', credits=(), heading_font=None):
    heading_font = heading_font_path(heading_font)
    bundle, output = Path(bundle), Path(output)
    area = RenderArea.poster()
    # Cache belongs to this immutable bundle, not merely a city/radius name.
    inputs = Path('processed/poster-inputs') / f'{bundle.name}-{area.width_px}x{area.height_px}'
    manifest = prepare_bundle(bundle, inputs, area)
    first, last = manifest['dates'][0]['date'], manifest['dates'][-1]['date']
    lines = [f'Peak hourly service | {first} - {last}', *credits,
             'Cityliner by Roman Prokofyev | cityliner.app']
    poster = Poster(area, output, inputs, manifest['city'], '\n'.join(reversed(lines)),
                    title=manifest['title'], heading_font=heading_font, intensity_metric='peak-hour')
    poster.generate_single(color_schemes[palette], add_water=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--color-scheme', choices=color_schemes, default='pastel')
    parser.add_argument('--credit', action='append', default=[])
    parser.add_argument('--heading-font', type=Path, help='Optional heading .ttf override; defaults to bundled Gelasio')
    args = parser.parse_args()
    try:
        args.heading_font = heading_font_path(args.heading_font)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    render_bundle(args.bundle, args.output, args.color_scheme, args.credit, args.heading_font)


if __name__ == '__main__':
    main()

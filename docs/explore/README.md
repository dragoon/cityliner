# GTFS Time Explorer

Export a week of schedules into static geometry and five-minute frames. The Canvas viewer provides playback, mode filters, share links and credited PNG downloads.

## Local demo

After the [Python setup](../../readme.md#setup), run:

```sh
.venv/bin/python -m scripts.build_explorer_demo
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory processed/explorer-demo
```

Open <http://127.0.0.1:8765/>. The synthetic network covers 1–7 January 2024 in UTC.
`--output-dir PATH` selects another demo directory. Use HTTP, not `file://`; the browser needs Canvas, Path2D and gzip `DecompressionStream`.

## Export your data

Use a GTFS directory or ZIP with shapes, stop times and service calendars. Choose a week covered by the feed:

```sh
.venv/bin/python -m citylines.explorer.export --gtfs gtfs/berlin \
  --place-name berlin --title Berlin --center 52.52493,13.36963 \
  --max-dist 30 --week-start 2026-10-14 --color-scheme pastel \
  --attribution "VBB · CC BY 4.0" --output-dir processed/explorer/berlin
```

Optional flags: `--provenance source.json`, `--water water.json`, `--cache-dir PATH`.
Provenance contains `url`, `retrievedAt`, `license` and `licenseUrl`; retain provider and map credits.
`--max-dist` is the square map's half-width in km (maximum 250). Absolute latitude must be below 80°; maps crossing the antimeridian are unsupported.

Stage the resulting bundle into the generated local demo or another website directory:

```sh
.venv/bin/python -m citylines.explorer.publish --bundle processed/explorer/berlin/BUNDLE_ID
# For a separate website, add --gallery-root PATH.
```

Staging copies only derived assets and updates the destination catalog; it does not deploy.
A separate host needs the viewer HTML, JavaScript, compiled CSS and `fonts/` from this directory.
Production catalogs and bundles belong to the website repository.

## Bundle and counting rules

- `manifest.json`: dates, bounds, modes, palettes, source credits and asset names.
- `geometry.json.gz`: clipped sections, paths, water and weekly peak departures.
- Daily `.json.gz`: sparse changes for each five-minute sample's next-hour window.
- `report.json`: processed/excluded trips, estimates and diagnostics. Review it before publishing.

Calendars, exceptions, overnight trips, agency timezones and daylight saving affect counts.
Stop times locate service along each route; missing times may be interpolated. Unusable geometry is excluded.
Frequency-based trips produce fractional expected counts. Disconnected paths remain separate.
Bundle identity includes feed contents, bounds, week, metadata, water and palette colours.
Retain old published bundles only when exact share-link reproduction is needed; missing versions fall back to the current bundle with a notice.

## Views and water

**Rhythm** compares each section with its weekly peak; **Departures** shows absolute intensity; **Change** compares with 08:00. Paused counts are exact; playback blends samples. These are schedules, not live positions.
Water is optional. Legacy poster caches must match the same centre and radius. Alternatively use the [water converter](../../citylines/explorer/water.py) with a georeferenced Overpass response or shapefile and source timestamp; see its `--help`.

## Development

```sh
npm ci
npm run build:css
```

Rebuild CSS after editing styles or viewer markup. [Testing](TESTING.md), [source credits](SOURCES.md) and [host callbacks](INTEGRATION.md) cover validation and integration.

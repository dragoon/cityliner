# Generic GTFS Time Explorer

One exporter and one static Canvas viewer serve every city. The existing
`main.py` poster command and its cache formats remain independent.

The published schedules cover October 7–13, 2026, using feeds downloaded on
October 6, 2026. The viewer displays their actual dates, feed coverage,
download information, and exclusions. These are scheduled departures, not live
transit information. See [SOURCES.md](SOURCES.md) for attribution, licenses,
and coverage.

## Run locally

Use Python 3.11 and create a local environment:

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt pytest
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8765/explore/`. The compiled stylesheet is included, so
previewing the site requires no CSS build. Serve over HTTP rather than opening
`index.html` as a local file.
The browser must support Canvas, Path2D, and gzip `DecompressionStream`.

## Edit the viewer styles

The explorer uses Tailwind CSS 4 for layout and daisyUI 5 for buttons, selects,
and the time slider. Its `cityliner` theme preserves the dark palette and uses
pill-shaped controls. All viewer CSS is compiled locally; the demo loads no
styling library from a CDN.

Install the pinned dependencies from the repository root and rebuild after
editing `index.html`, `explorer.js`, or `styles.css`:

```sh
npm ci
npm run build:css
```

Use `npm run watch:css` while editing. Commit the source, `package.json`,
`package-lock.json`, and generated `explorer.css` together. Pages serves that
stylesheet directly and needs no Node.js runtime. The CSS source only scans
the explorer HTML and JavaScript, keeping raw data outside the style build.

## Add a city

Use an extracted GTFS directory or a ZIP with GTFS files at its root. Supply a
week entirely inside the feed's calendar coverage and an attribution suitable
for publishing the derived output. A city identifier must be a lowercase slug.
Prepare the provenance and water files using the refresh instructions below;
both options can be omitted when generating a basic preview.

```sh
.venv/bin/python -m citylines.explorer.export \
  --gtfs ./gtfs/berlin \
  --place-name berlin --title Berlin \
  --center 52.52493,13.36963 --max-dist 30 \
  --week-start 2026-10-07 --color-scheme cool \
  --attribution 'Verkehrsverbund Berlin-Brandenburg (VBB), CC BY 4.0 · © OpenStreetMap contributors' \
  --provenance ./gtfs/berlin-provenance.json \
  --water ./processed/explorer/berlin-water.json \
  --output-dir ./processed/explorer/berlin

.venv/bin/python -m citylines.explorer.export \
  --gtfs ./gtfs/warsaw \
  --place-name warsaw --title Warsaw \
  --center 52.228865,21.0006369 --max-dist 30 \
  --week-start 2026-10-07 --color-scheme pastel \
  --attribution 'Zarząd Transportu Miejskiego w Warszawie (ZTM / WTP) · © OpenStreetMap contributors' \
  --provenance ./gtfs/warsaw-provenance.json \
  --water ./processed/explorer/warsaw-water.json \
  --output-dir ./processed/explorer/warsaw
```

The example dates match the included demo bundles. For another feed version,
choose a week covered by its calendar. `--max-dist` is the half-width of a square map
in kilometres, using a local metric projection. The camera stays fixed at
those bounds. V1 limits radius to 250 km, latitude to below 80° absolute,
and excludes maps crossing the antimeridian.

`--water` is optional. A legacy Cityliner water cache must have been generated
with the **same center and radius**, because it does not contain its own
projection metadata. The exporter converts its poster coordinates back to
geography and clips them. Alternatively supply an object with `center`,
`bounds`, and `polygons` already in the export's metric projection; polygon
rings contain `[x,y]` pairs. Missing or incompatible water is a diagnostic,
not a failed export. No water download is performed by the exporter. The
separate water converter accepts a freshly downloaded Overpass response and
preserves relation holes and disconnected outer rings.

Stage only a reviewed derived bundle into the local viewer:

```sh
.venv/bin/python -m citylines.explorer.publish \
  --bundle ./processed/explorer/YOUR_CITY/BUNDLE_ID
```

Use the bundle path printed by your export. This command copies a whitelist of
derived assets into `docs/explore/data` and updates `catalog.json`; it does
**not** deploy the site. The public demo contains a fictional network.
Production galleries choose their own cities and bundle retention policy.
Superseded bundles can be archived under ignored `processed/` directories. Links
to unavailable versions open the current bundle with a visible notice; retain a
published version if exact reproduction of its original view is required.
Raw feeds, SQLite caches, audit working files, and poster outputs stay
under ignored directories. Source feed licenses still govern their derived use.

## Schedule and geometry rules

Calendar exceptions override weekly calendars; exception-only feeds work.
Times use the agency timezone and the GTFS service-day origin. Departures
beyond `24:00` are included from preceding service dates, and windows near
midnight include the needed following dates. The
[GTFS schedule reference](https://gtfs.org/documentation/schedule/reference/)
defines these service times and frequency rules.

Each window covers 60 elapsed minutes, sampled every 5 elapsed minutes. A
normal date has 288 frames; a typical spring/fall DST date has 276/300. Timestamps
are absolute Unix seconds; repeated clock times carry timezone abbreviations.
The viewer describes the loaded bundle's sampling interval, including any
older bundles explicitly retained in the gallery.
Exact frequency rules expand to departures. Other frequency rules contribute
the overlap duration divided by headway, shifted by each stop's timetable
offset. The template trip is never counted separately.

Stops match consistent shape distances when available; otherwise they project
in order along the remaining directed shape. Matches further than 300 metres
from the shape are excluded. Missing intermediate times interpolate by matched
distance between the preceding departure and following arrival. First and last
times must exist. Sections count departures at their upstream stop, so long
trips brighten different sections at different times. Actual shape sections
are clipped at the square boundary, retaining separate pieces, then simplified
with a 12-metre tolerance.

V1 requires fixed-route, shape-backed schedules and one shared agency timezone.
Flexible-service rows, invalid time order, unreliable mapping, and missing
shapes receive diagnostics. Unsupported trips do not silently contribute.
Exclusion totals describe source trip/section instances, rather than deduplicated
public sections. The exporter stops if the selected week/area has no usable
departures. Read `report.json` before publishing.

CSV rows stage in SQLite in 20,000-row batches. Large stop-time and shape tables
stay on disk with numeric sequence indexes and a bounded SQLite page cache.
Staging identity is feed contents plus staging-format version; the derived bundle
identity additionally includes bounds, week, city metadata, palette, and water.
Source trip, route, stop, shape, and direction references remain in the private
staging model for a future Transit Portrait feature.

## Bundle format and viewer

`schemaVersion: 1`, processor `1.2.0`, frame encoding `sparse-deltas-v1`:

- `manifest.json`: identity, fingerprint, timezone, dates, source, bounds,
  modes, palettes, warnings, and one intensity maximum for the entire week.
  Feed credits are in `attributions`; `provenance` records the download URL,
  retrieval time and license; `waterSource` records the OSM data timestamp.
- `geometry.json.gz`: reusable section paths in metres, transport categories,
  route names, stop references, estimation flags, a fixed `peakDepartures` per
  section computed across every exported window, and optional water polygons.
- `YYYY-MM-DD.json.gz`: explicit window start/end timestamps and labels;
  `changes` contains `[sectionId,newCount]` pairs against the previous frame.
  Each day starts from all-zero counts. Zero changes remove prior service.
- `report.json`: processed/excluded counts, timing estimates, diagnostic
  examples, processing duration, process peak memory, and asset sizes.
- `latest.json` in the private output directory points to the generated version.

The viewer loads geometry once per city and caches three expanded daily frame
arrays. Slider movement and playback do not fetch or calculate schedules.
The camera and weekly references survive mode/date changes. **Daily rhythm**
(the default) scales each section against its own busiest hour in the week.
A gentle power curve uses the larger of the weekly peak or four departures
per hour as its fixed reference. Rare services stay subdued instead of
flashing at full brightness when their only departure enters a window. **Departures** retains a city-wide logarithmic scale. **Change from 08:00**
compares against the 08:00 window on the selected date, showing increases in
mint and decreases in coral, including sections that have stopped running.
Unchanged sections remain faint; an identical baseline has an explicit message.
Palette controls apply to rhythm/departures; difference colors have a fixed legend.
Opaque intensity-colored strokes use maximum-brightness compositing, so overlapping
shape variants cannot accumulate a misleading glow. All five palettes remain
available. A blank service view explicitly reports zero service.

Opening without a saved view starts paused at 08:00 on the first date. Playback
loops the selected date in about 30 seconds, blending adjacent 5-minute
counts continuously on animation frames, including the visual loop seam.
Blended display values are marked as approximate; they are not new timetable
measurements. Dragging or using the keyboard on the slider pauses playback
and eases brightness to the selected exact source sample over 220 ms.
Pausing also settles onto the source sample. Cached daily counts are never
mutated by animation. PNG export stops playback and uses the source sample. Tap or hover shows route/type/count details. The URL hash
restores city, immutable bundle, date, absolute window time, modes, palette, and view.
An unavailable archive version falls back visibly to the catalog version.
PNG export includes the selected date/window, source, frequency explanation,
the view and its scale/legend, and **Cityliner by Roman Prokofyev**. A visible download link remains available
when a browser does not automatically start the download.

See [TESTING.md](TESTING.md) for automated checks and independent timetable
audits. Visitor uploads, vehicle animation, payments, comparisons, and Transit
Portrait are outside V1.

## Refresh inputs

Download feeds from the publishers listed in [SOURCES.md](SOURCES.md), or use
another source whose license permits the intended publication. Inspect its
calendar coverage and attribution records before selecting a new export week.

Create a provenance JSON file in the location passed to `--provenance`, with
these public metadata fields:

```json
{
  "url": "https://unternehmen.vbb.de/gtfs",
  "retrievedAt": "ACTUAL_DOWNLOAD_TIME_IN_ISO_8601",
  "license": "CC-BY-4.0",
  "licenseUrl": "https://unternehmen.vbb.de/digitale-services/datensaetze/"
}
```

Use the actual UTC download time and source-specific license terms. The
exporter includes this metadata in the manifest; source credits from
`attributions.txt` are retained automatically.

To refresh water, generate a query for the same center and radius:

```sh
.venv/bin/python -m citylines.explorer.water \
  --center 52.52493,13.36963 --max-dist 30 \
  --query-output gtfs/berlin-water.query

curl -sS --fail --get \
  -A 'Cityliner (https://github.com/dragoon/cityliner)' \
  --data-urlencode data@gtfs/berlin-water.query \
  -o gtfs/berlin-water.json https://overpass-api.de/api/interpreter

.venv/bin/python -m citylines.explorer.water \
  --input gtfs/berlin-water.json \
  --center 52.52493,13.36963 --max-dist 30 \
  --retrieved-at ACTUAL_DOWNLOAD_TIME_IN_ISO_8601 \
  --endpoint https://overpass-api.de/api/interpreter \
  --output processed/explorer/berlin-water.json
```

Replace the retrieval-time placeholder before conversion. Regional OSM water
extracts are also supported: use `--shapefile PATH --data-timestamp
PUBLISHED_OSM_TIME` instead of `--input`, and set `--endpoint` to the extract's
source URL. The water polygon file must declare EPSG:4326. Source timestamps
should come from the downloaded response or extract metadata.

Validate the replacement bundle before updating the catalog. Keep raw feeds,
water responses, and processing caches outside the published site. Archive
superseded bundles privately unless their original views need to stay available.

## Website integration

This repository contains a reusable viewer and a small synthetic demo.
Production branding, city catalogs, analytics, and deployment are maintained
separately. See [INTEGRATION.md](INTEGRATION.md) for optional host callbacks.
No analytics script loads in the standalone viewer.

Regenerate the demo without downloading a feed:

```sh
.venv/bin/python -m scripts.build_explorer_demo
```

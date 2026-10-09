# Testing the Time Explorer

Run these checks from the repository root after installing the dependencies
in [README.md](README.md):

```sh
.venv/bin/python -m pytest -q tests
npm ci
npm run build:css
node --check docs/explore/explorer.js
node --check docs/explore/integration.js
npm test
git diff --check
```

The fixtures cover calendars and exceptions, overnight service, frequency
rules, daylight-saving changes, local timing along routes, missing stop times,
loops, geometry clipping, water polygon holes, source attribution, and poster
compatibility. JavaScript tests cover intensity scaling, animation blending,
optional host callbacks, callback failure isolation, and share-link overrides.

## Compare a bundle with its source

`scripts/audit_explorer.py` independently reads the source CSV files and compares
sample stop-pair window counts with an exported bundle. Replace `BUNDLE_ID`
with the version printed by the exporter:

```sh
.venv/bin/python scripts/audit_explorer.py \
  --gtfs gtfs/berlin \
  --bundle processed/explorer/berlin/BUNDLE_ID \
  --output processed/explorer/berlin-audit.json
```

Use a week without a daylight-saving transition for this audit; transition
semantics are covered by synthetic tests. The audit samples sections rather
than checking every trip. Review `report.json` for exclusions and estimates.

## Check the viewer

Serve the site using the local-preview command in [README.md](README.md).
Check city and date changes, keyboard and touch scrubbing, playback, mode
filters, share-link restoration, and artwork downloads. Confirm source credits
and dates appear in the viewer and exported PNG, including on narrow screens.
Check that unavailable assets produce a visible error and retry control.

## Check host integrations

The standalone viewer must issue no analytics requests. See
[INTEGRATION.md](INTEGRATION.md) for callbacks a host can implement. Check
that the viewer still loads, shares, and exports if host callbacks throw.
Production analytics tests belong in the host website repository.

# Checks

From the repository root, after installing dependencies:

```sh
.venv/bin/python -m pytest -q tests
npm ci
npm run build:css
npm test
node --check docs/explore/explorer.js
git diff --check
```

Tests cover calendars, overnight service, frequencies, timezones, geometry, credits, poster rendering and host callbacks.
For an independent sample audit against the GTFS input:

```sh
.venv/bin/python scripts/audit_explorer.py --gtfs gtfs/CITY \
  --bundle processed/explorer/CITY/BUNDLE_ID --output processed/explorer/audit.json
```

Use a week without a daylight-saving transition for this audit; tests cover transition semantics. Review `report.json` for estimates and exclusions.
In the [local viewer](README.md#local-demo), check city/date changes, playback, scrubbing, mode filters, restored share links and PNG credits on desktop and mobile. Missing assets must show an error with retry. The standalone viewer should send no analytics and remain usable if host callbacks fail.

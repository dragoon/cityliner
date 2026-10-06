# Data sources and attribution

The included Berlin and Warsaw datasets cover **October 7–13, 2026**. Both
GTFS feeds were downloaded on October 6, 2026. The explorer shows scheduled
service, with expected departures for frequency-based services.

## Transit schedules

| City | Transport authority | GTFS publisher | License / usage terms |
| --- | --- | --- | --- |
| Berlin | Verkehrsverbund Berlin-Brandenburg (VBB) | [VBB](https://unternehmen.vbb.de/gtfs) | [CC BY 4.0](https://unternehmen.vbb.de/digitale-services/datensaetze/) |
| Warsaw | Zarząd Transportu Miejskiego w Warszawie (ZTM), Warszawski Transport Publiczny (WTP) | [Mikołaj Kuranowski](https://mkuran.pl/gtfs/) | [ZTM data usage terms](https://www.ztm.waw.pl/pliki-do-pobrania/dane-rozkladowe/); ODbL for OSM bus shapes |

Warsaw schedules originate from ZTM/WTP and are converted into GTFS by
Mikołaj Kuranowski. The viewer and downloaded artwork credit the authority,
GTFS publisher, and OpenStreetMap contributors as required by the feed.

## Water geometry

Water geometry is © OpenStreetMap contributors, available under the
[Open Database License (ODbL)](https://www.openstreetmap.org/copyright).

| City | Distribution source | OSM data timestamp (UTC) |
| --- | --- | --- |
| Berlin | [Overpass API](https://overpass-api.de/) | October 6, 2026, 10:57 |
| Warsaw | [Geofabrik Mazovian extract](https://download.geofabrik.de/europe/poland/mazowieckie.html) | October 5, 2026, 20:21 |

## Coverage and interpretation

The source feeds cover October 1–December 12, 2026 for Berlin and October
6–November 5, 2026 for Warsaw. Each map is clipped to a square extending
30 km from its center in each direction.

Counts represent departures from each section's upstream stop in the next
60 minutes. Trips whose stops cannot be matched reliably to their shapes are
excluded. The Berlin export excludes 617 trips for this reason; the Warsaw
export has no excluded trips. Detailed coverage notes appear in the viewer
and bundle reports.

Source-data licenses apply to the derived datasets separately from the
Cityliner code and gallery artwork licenses. Each bundle's manifest records
its source credits, download time, feed fingerprint, and water data timestamp.

"""Run: python -m citylines.explorer.export --help."""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, timedelta
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import sys
import sqlite3
import time
from zoneinfo import ZoneInfo
from zipfile import BadZipFile

import numpy as np

from citylines.util.colors import color_schemes
from . import VERSION, STAGING_VERSION
from .geometry import bounds_for, clipped_paths, interpolate_times, match_stops, project, shape_model
from .schedule import active_services, add_departure, add_frequency, day_windows, seconds, service_origin
from .source import Feed, coordinate, stage


def mode_for(value):
    value = int(value)
    if value == 0 or 900 <= value <= 999:
        return "tram"
    if value in (1, 12) or 400 <= value <= 499:
        return "subway"
    if value == 2 or 100 <= value <= 199:
        return "rail"
    if value in (3, 11) or 200 <= value <= 299 or 700 <= value <= 899:
        return "bus"
    if value == 4 or 1000 <= value <= 1099:
        return "ferry_water"
    if value in (5, 6, 7) or 1300 <= value <= 1499:
        return "funicular_cable_gondola"
    return "other"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
    if path.suffix == ".gz":
        content = gzip.compress(content, compresslevel=9, mtime=0)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def export_feed(gtfs, place_name, title, center, radius, week_start, palette,
                output_dir, attribution="", cache_dir=Path("processed/explorer-cache"), water=None, provenance=None):
    started = time.perf_counter()
    if not -80 < center[0] < 80 or not -180 <= center[1] <= 180 or not 0 < radius <= 250:
        raise ValueError("Use a center below 80° latitude and a radius of 0–250 km")
    feed = Feed(gtfs)
    db = None
    try:
        fingerprint = feed.fingerprint()
        identity = {"version": VERSION, "feed": fingerprint, "center": center,
                    "radius": radius, "week": week_start.isoformat(), "palette": palette,
                    "place": place_name, "title": title, "attribution": attribution,
                    "water": hashlib.sha256(Path(water).read_bytes()).hexdigest() if water and Path(water).is_file() else None,
                    "provenance": provenance}
        bundle_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
        db = stage(feed, Path(cache_dir) / f"{STAGING_VERSION}-{fingerprint}.sqlite")
        agencies = list(feed.rows("agency.txt", ("agency_timezone",)))
        credits = [{"name": r["organization_name"], "url": r.get("attribution_url", ""),
                    "producer": r.get("is_producer") == "1", "authority": r.get("is_authority") == "1",
                    "operator": r.get("is_operator") == "1", "dataSource": r.get("is_data_source") == "1"}
                   for r in feed.rows("attributions.txt", ("organization_name",))]
        timezones = {a["agency_timezone"] for a in agencies}
        if len(timezones) != 1:
            raise ValueError("The feed must declare one shared agency timezone")
        tz = ZoneInfo(next(iter(timezones)))
        calendars = [(r["service_id"], r["start_date"], r["end_date"],
                      ''.join(r[d] for d in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")))
                     for r in feed.rows("calendar.txt", ("service_id", "start_date", "end_date"))]
        exceptions = defaultdict(list)
        for row in feed.rows("calendar_dates.txt", ("date", "service_id", "exception_type")):
            kind = int(row["exception_type"])
            if kind not in (1, 2):
                raise ValueError("calendar_dates.txt has an invalid exception_type")
            exceptions[row["date"]].append((row["service_id"], kind))
        coverage = [d for _, a, b, _ in calendars for d in (a, b)] + list(exceptions)
        if not coverage:
            raise ValueError("The feed has no service calendar dates")
        start_date, end_date = min(coverage), max(coverage)
        end_day = week_start + timedelta(days=6)
        if week_start.strftime("%Y%m%d") < start_date or end_day.strftime("%Y%m%d") > end_date:
            raise ValueError(f"Requested week is outside feed coverage {start_date}–{end_date}")
        days = [(week_start + timedelta(days=i)) for i in range(7)]
        frames_by_day = [day_windows(d, tz) for d in days]
        windows = [frame for frames in frames_by_day for frame in frames]
        window_starts = [w["start"] for w in windows]
        frequencies = defaultdict(list)
        for row in feed.rows("frequencies.txt", ("trip_id", "start_time", "end_time", "headway_secs")):
            a, b, h = seconds(row["start_time"]), seconds(row["end_time"]), int(row["headway_secs"])
            exact = int(row.get("exact_times") or 0)
            if a is None or b is None or a >= b or h <= 0 or exact not in (0, 1):
                raise ValueError(f"Invalid frequency rule for {row['trip_id']}")
            frequencies[row["trip_id"]].append((a, b, h, exact))
        # Frequency trips can start late and continue for the longest template duration.
        max_departure = db.execute("SELECT MAX(COALESCE(departure,arrival,0)) FROM times").fetchone()[0] or 0
        max_frequency = max((b for rules in frequencies.values() for _, b, _, _ in rules), default=0)
        padding = math.ceil((max_departure + max_frequency) / 86400) + 2
        for tid, rules in frequencies.items():
            rules.sort()
            if any(a[1] > b[0] for a, b in zip(rules, rules[1:])):
                raise ValueError(f"Overlapping frequency rules for {tid}")
        service_days = [week_start + timedelta(days=i) for i in range(-padding, 9)]
        service_dates = defaultdict(list)
        for day in service_days:
            for sid in active_services(day, calendars, exceptions):
                service_dates[sid].append(service_origin(day, tz))
        routes = {}
        for row in feed.rows("routes.txt", ("route_id", "route_type")):
            routes[row["route_id"]] = {"name": row.get("route_short_name") or row.get("route_long_name") or row["route_id"],
                                       "mode": mode_for(row["route_type"])}
        stops = {r["stop_id"]: (coordinate(r["stop_lat"], 90), coordinate(r["stop_lon"], 180))
                 for r in feed.rows("stops.txt", ("stop_id", "stop_lat", "stop_lon")) if r.get("stop_lat") and r.get("stop_lon")}
        bounds = bounds_for(radius)
        lat_delta = radius * 1000 / 6371000 * 180 / math.pi
        lon_delta = lat_delta / math.cos(math.radians(center[0]))
        if abs(center[1]) + lon_delta >= 180:
            raise ValueError("V1 does not support a map crossing the antimeridian")
        selected = [r[0] for r in db.execute("""SELECT id FROM shapes GROUP BY id
            HAVING MIN(lat)<=? AND MAX(lat)>=? AND MIN(lon)<=? AND MAX(lon)>=?""",
            (center[0]+lat_delta, center[0]-lat_delta, center[1]+lon_delta, center[1]-lon_delta))]
        sections, values, section_index = [], [], {}
        diagnostics = Counter()
        examples = defaultdict(list)

        def exclude(reason, tid):
            diagnostics[reason] += 1
            diagnostics["excluded_trips"] += 1
            diagnostics["excluded_section_instances"] += max(0, db.execute("SELECT COUNT(*) FROM times WHERE trip=?", (tid,)).fetchone()[0] - 1)
            if len(examples[reason]) < 3:
                examples[reason].append(tid)

        invalid = {r[0] for r in db.execute("SELECT id FROM invalid_trips")}
        print(f"Computing local timing for {len(selected)} shapes…", flush=True)
        for shape_number, shape_id in enumerate(selected):
            raw_shape = list(db.execute("SELECT seq,lat,lon,distance FROM shapes WHERE id=? ORDER BY seq", (shape_id,)))
            if len(raw_shape) < 2:
                diagnostics["degenerate_shapes"] += 1
                continue
            try:
                line, cumulative, distances = shape_model(raw_shape, center)
            except ValueError:
                diagnostics["degenerate_shapes"] += 1
                continue
            layouts = {}
            for tid, rid, sid, direction in db.execute("SELECT id,route,service,direction FROM trips WHERE shape=?", (shape_id,)):
                if sid not in service_dates:
                    continue
                if tid in invalid or rid not in routes:
                    exclude("invalid_trip_or_route", tid)
                    continue
                rows = list(db.execute("SELECT seq,stop,arrival,departure,distance,flex FROM times WHERE trip=? ORDER BY seq", (tid,)))
                if len(rows) < 2 or any(r[5] or r[1] not in stops for r in rows):
                    exclude("missing_stops_or_flexible_service", tid)
                    continue
                pattern = tuple((r[1], r[4]) for r in rows)
                try:
                    if pattern not in layouts:
                        positions = match_stops(rows, line, cumulative, distances, stops, center)
                        paths = [clipped_paths(line, a, b, bounds) for a, b in zip(positions, positions[1:])]
                        layouts[pattern] = positions, paths
                    positions, paths = layouts[pattern]
                    departures, estimated = interpolate_times(rows, positions)
                except (ValueError, KeyError) as exc:
                    exclude(str(exc), tid)
                    continue
                diagnostics["processed_trips"] += 1
                diagnostics["interpolated_stop_times"] += estimated
                for i, pieces in enumerate(paths):
                    if not pieces:
                        continue
                    key = (routes[rid]["mode"], rows[i][1], rows[i+1][1], json.dumps(pieces, separators=(",", ":")))
                    if key not in section_index:
                        index = len(sections)
                        section_index[key] = index
                        sections.append({"id": index, "mode": key[0], "paths": pieces, "routes": [],
                                         "fromStop": key[1], "toStop": key[2], "estimated": False,
                                         "interpolated": False})
                        values.append(np.zeros(len(windows), dtype=np.float32))
                    index = section_index[key]
                    section = sections[index]
                    if rid not in section["routes"]:
                        section["routes"].append(rid)
                    section["estimated"] |= any(not r[3] for r in frequencies.get(tid, []))
                    section["interpolated"] |= bool(estimated)
                    for origin in service_dates[sid]:
                        if tid in frequencies:
                            offset = departures[i] - departures[0]
                            for a, b, h, exact in frequencies[tid]:
                                add_frequency(values[index], window_starts, origin, offset, a, b, h, exact)
                        else:
                            add_departure(values[index], window_starts, origin + departures[i])
            if shape_number % 500 == 0:
                print(f"  {shape_number}/{len(selected)} shapes; {len(sections)} sections", flush=True)
        if not sections or not diagnostics["processed_trips"]:
            raise ValueError(f"No usable scheduled sections in the selected area/week. Check shape/stop alignment and service dates. Diagnostics: {dict(diagnostics)}; examples: {dict(examples)}")
        diagnostics["trips_without_shapes"] = db.execute("SELECT COUNT(*) FROM trips WHERE shape='' OR shape NOT IN (SELECT id FROM shapes)").fetchone()[0]
        bundle = Path(output_dir) / bundle_id
        for section, counts in zip(sections, values):
            section["peakDepartures"] = round(float(counts.max()), 4)
        maximum = max(s["peakDepartures"] for s in sections)
        if maximum <= 0:
            raise ValueError("No departures in the requested week and area")
        used_routes = {rid for s in sections for rid in s["routes"]}
        geometry = {"sections": sections, "routes": {rid: routes[rid] for rid in sorted(used_routes)}, "water": []}
        water_source = None
        if water:
            try:
                layer = json.loads(Path(water).read_text())
                if isinstance(layer, list):
                    # Explicit legacy poster cache: convert its poster pixels back
                    # to geography using the same caller-supplied center/radius.
                    from citylines.gtfs.domain import BoundingBox, Distance, MaxDistance, Point, RenderArea
                    area = RenderArea.poster()
                    bbox = BoundingBox.from_center(Point(*center), MaxDistance.from_distance(Distance.from_km(radius), area), area)
                    from shapely.geometry import Polygon, box
                    for body in layer:
                        def ring(nodes):
                            return [project(center[0] + p["y"] / bbox.scale_factor_lat,
                                            center[1] + p["x"] / bbox.scale_factor_lon, center) for p in nodes]
                        exterior = ring(body["nodes"])
                        holes = [ring(nodes) for nodes in body.get("interiors", [])]
                        if len(exterior) < 3:
                            continue
                        polygon = Polygon(exterior, holes)
                        if not polygon.is_valid:
                            polygon = polygon.buffer(0)
                        clipped = polygon.intersection(box(*bounds))
                        polygons = [clipped] if clipped.geom_type == "Polygon" else getattr(clipped, "geoms", [])
                        for p in polygons:
                            if p.geom_type == "Polygon" and not p.is_empty:
                                p = p.simplify(12, preserve_topology=True)
                                geometry["water"].append([[[round(x, 1), round(y, 1)] for x, y in r.coords]
                                                          for r in [p.exterior, *p.interiors]])
                else:
                    if layer.get("center") != list(center) or layer.get("bounds") != bounds:
                        raise ValueError("Water cache projection does not match export")
                    geometry["water"] = layer["polygons"]
                    water_source = layer.get("source")
                    for reason, count in layer.get("diagnostics", {}).items():
                        if reason != "processed_elements" and count:
                            diagnostics[f"water_{reason}"] += count
            except (ValueError, KeyError, AttributeError, OSError) as exc:
                diagnostics["water_cache_unavailable"] += 1
                examples["water_cache_unavailable"] = [str(exc)]
        else:
            diagnostics["water_cache_unavailable"] = 1
        write_json(bundle / "geometry.json.gz", geometry)
        date_files = []
        cursor = 0
        for day, frames in zip(days, frames_by_day):
            # Store changes against the previous frame, reducing repeated counts dramatically.
            previous = {}
            for frame in frames:
                current = {i: round(float(v[cursor]), 4) for i, v in enumerate(values) if v[cursor] > 0}
                frame.pop("counts")
                frame["changes"] = [[i, current.get(i, 0)] for i in sorted(current.keys() | previous.keys())
                                    if current.get(i, 0) != previous.get(i, 0)]
                previous = current
                cursor += 1
            filename = day.isoformat() + ".json.gz"
            write_json(bundle / filename, {"date": day.isoformat(), "frames": frames})
            date_files.append({"date": day.isoformat(), "file": filename})
        warnings = [f"{key}: {value}" for key, value in diagnostics.items()
                    if value and key not in ("processed_trips", "interpolated_stop_times")]
        if diagnostics["interpolated_stop_times"]:
            warnings.append(f"{diagnostics['interpolated_stop_times']} intermediate stop times were interpolated")
        if any(s["estimated"] for s in sections):
            warnings.append("Frequency-based service shows expected departures, not exact timetable departures")
        if days[-1] < date.today():
            warnings.insert(0, "Archived schedule; these dates do not describe current service")
        if week_start.strftime("%Y%m%d") == start_date or end_day.strftime("%Y%m%d") == end_date:
            warnings.append("Feed boundary: overnight coverage outside the declared feed range may be incomplete")
        palette_data = {name: {**asdict(scheme), "other": "#aab4c1"} for name, scheme in color_schemes.items()}
        manifest = {"schemaVersion": 1, "processorVersion": VERSION, "bundle": bundle_id,
                    "city": place_name, "title": title, "timezone": str(tz), "center": center,
                    "bounds": bounds, "feedFingerprint": fingerprint,
                    "feedCoverage": [date.fromisoformat(f"{d[:4]}-{d[4:6]}-{d[6:]}").isoformat() for d in (start_date, end_date)],
                    "source": attribution or "; ".join(a.get("agency_name", "") for a in agencies),
                    "attributions": credits, "provenance": provenance, "waterSource": water_source,
                    "dates": date_files, "geometry": "geometry.json.gz", "modes": sorted({s["mode"] for s in sections}),
                    "palette": palette, "palettes": palette_data, "windowSeconds": 3600,
                    "stepSeconds": 900, "intensityMaximum": maximum, "warnings": warnings,
                    "metric": "Departures from each section's upstream stop in the next hour",
                    "frameEncoding": "sparse-deltas-v1"}
        write_json(bundle / "manifest.json", manifest)
        report = {"counts": dict(diagnostics), "examples": dict(examples),
                  "seconds": round(time.perf_counter() - started, 2),
                  "peakMemoryMB": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024*1024 if sys.platform == "darwin" else 1024), 1),
                  "sections": len(sections), "maxDepartures": maximum,
                  "bytes": {p.name: p.stat().st_size for p in bundle.iterdir() if p.is_file()}}
        write_json(bundle / "report.json", report)
        write_json(Path(output_dir) / "latest.json", {"manifest": f"{bundle_id}/manifest.json"})
        print(json.dumps({"manifest": str(bundle / 'manifest.json'), **report}, ensure_ascii=False), flush=True)
        return manifest, report, bundle
    finally:
        feed.close()
        if db:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Export seven days of GTFS local service intensity")
    parser.add_argument("--gtfs", required=True, type=Path)
    parser.add_argument("--place-name", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--center", required=True, help="latitude,longitude")
    parser.add_argument("--max-dist", type=float, default=30)
    parser.add_argument("--week-start", required=True, type=date.fromisoformat)
    parser.add_argument("--color-scheme", choices=color_schemes, default="default")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--attribution", default="")
    parser.add_argument("--provenance", type=Path, help="Public source metadata JSON: url, retrievedAt, license and licenseUrl")
    parser.add_argument("--cache-dir", type=Path, default=Path("processed/explorer-cache"))
    parser.add_argument("--water", type=Path, help="Optional projected water cache; see explorer documentation")
    args = parser.parse_args()
    try:
        center = tuple(map(float, args.center.split(",")))
        if len(center) != 2:
            raise ValueError("Center must be latitude,longitude")
        export_feed(args.gtfs, args.place_name, args.title, center, args.max_dist,
                    args.week_start, args.color_scheme, args.output_dir, args.attribution,
                    args.cache_dir, args.water,
                    json.loads(args.provenance.read_text()) if args.provenance else None)
    except (ValueError, KeyError, OSError, sqlite3.Error, BadZipFile) as exc:
        parser.exit(2, f"Export failed: {exc}\n")


if __name__ == "__main__":
    main()

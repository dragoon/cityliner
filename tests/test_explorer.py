import csv
import gzip
import json
import zipfile
from datetime import date
from zoneinfo import ZoneInfo

import pytest
from shapely.geometry import LineString

from citylines.explorer.export import export_feed, mode_for
from citylines.explorer.geometry import clipped_paths, interpolate_times, match_stops, shape_model
from citylines.explorer.schedule import active_services, add_departure, add_frequency, day_windows, seconds, service_origin
from citylines.explorer.source import Feed


def table(folder, name, header, rows):
    with (folder / name).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(header.split(","))
        writer.writerows(rows)


@pytest.fixture
def feed(tmp_path):
    folder = tmp_path / "feed"
    folder.mkdir()
    table(folder, "agency.txt", "agency_id,agency_name,agency_timezone", [("agency", "Test transit", "Europe/Berlin")])
    table(folder, "routes.txt", "route_id,route_short_name,route_type", [("r", "R1", 3), ("f", "F1", 1)])
    table(folder, "stops.txt", "stop_id,stop_lat,stop_lon", [("a", 0, 0), ("b", 0, .01), ("c", 0, .02)])
    table(folder, "shapes.txt", "shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon,shape_dist_traveled",
          [("s", 20, 0, .02, 2000), ("s", 0, 0, 0, 0), ("s", 10, 0, .01, 1000)])
    table(folder, "trips.txt", "trip_id,route_id,service_id,shape_id,direction_id",
          [("t", "r", "base", "s", 0), ("overnight", "r", "base", "s", 0), ("frequency", "f", "base", "s", 0)])
    times = [("t", "08:00:00", "08:00:00", "a", 0, 0), ("t", "09:20:00", "09:20:00", "b", 10, 1000),
             ("t", "09:30:00", "09:30:00", "c", 20, 2000),
             ("overnight", "25:00:00", "25:00:00", "a", 0, 0),
             ("overnight", "25:20:00", "25:20:00", "b", 10, 1000),
             ("overnight", "25:30:00", "25:30:00", "c", 20, 2000),
             ("frequency", "00:00:00", "00:00:00", "a", 0, 0),
             ("frequency", "01:20:00", "01:20:00", "b", 10, 1000),
             ("frequency", "01:30:00", "01:30:00", "c", 20, 2000)]
    table(folder, "stop_times.txt", "trip_id,arrival_time,departure_time,stop_id,stop_sequence,shape_dist_traveled", list(reversed(times)))
    table(folder, "calendar.txt", "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date",
          [("base", 1, 1, 1, 1, 1, 1, 1, "20231230", "20240115")])
    table(folder, "frequencies.txt", "trip_id,start_time,end_time,headway_secs,exact_times", [("frequency", "07:00:00", "08:00:00", 600, 0)])
    return folder


def inflate(bundle, day):
    data = json.loads(gzip.decompress((bundle / f"{day}.json.gz").read_bytes()))
    current, result = {}, []
    for frame in data["frames"]:
        for sid, value in frame["changes"]:
            current[sid] = value
        result.append((frame, current.copy()))
    return result


def test_calendar_exceptions_and_weekends():
    calendars = [("weekday", "20240101", "20240131", "1111100")]
    exceptions = {"20240103": [("weekday", 2), ("special", 1)]}
    assert active_services(date(2024, 1, 2), calendars, exceptions) == {"weekday"}
    assert active_services(date(2024, 1, 3), calendars, exceptions) == {"special"}
    assert active_services(date(2024, 1, 6), calendars, exceptions) == set()
    assert active_services(date(2024, 1, 3), [], exceptions) == {"special"}


def test_dst_service_origin_and_day_lengths():
    tz = ZoneInfo("Europe/Berlin")
    assert len(day_windows(date(2024, 3, 31), tz)) == 276
    autumn = day_windows(date(2024, 10, 27), tz)
    assert len(autumn) == 300
    assert {f["label"] for f in autumn if f["label"].startswith("02:00")} == {"02:00 CEST", "02:00 CET"}
    assert {f["label"] for f in autumn if f["label"].startswith("02:05")} == {"02:05 CEST", "02:05 CET"}
    assert service_origin(date(2024, 3, 31), tz) == day_windows(date(2024, 3, 31), tz)[0]["start"] - 3600
    assert seconds("25:35:00") == 92100
    with pytest.raises(ValueError):
        seconds("01:75:00")


def test_window_boundaries_and_frequencies():
    values = [0.] * 5
    starts = [0, 300, 600, 900, 3600]
    add_departure(values, starts, 3600)
    assert values == [0, 1, 1, 1, 1]  # End exclusive; start inclusive.
    exact, estimated = [0.] * 5, [0.] * 5
    add_frequency(exact, starts, 0, 0, 0, 3600, 600, 1)
    add_frequency(estimated, starts, 0, 0, 0, 3600, 600, 0)
    assert exact[0] == estimated[0] == 6
    assert exact[1] == 5 and estimated[1] == 5.5
    assert exact[4] == estimated[4] == 0


def test_clipping_does_not_bridge_outside_excursion():
    line = LineString([(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)])
    paths = clipped_paths(line, 0, line.length, [-1, -1, 1, 1])
    assert len(paths) == 2
    assert all(-1 <= x <= 1 and -1 <= y <= 1 for path in paths for x, y in path)


def test_loop_matching_by_shape_distance():
    raw = [(0, 0, 0, 0), (1, 0, .01, 1000), (2, .01, .01, 2000), (3, 0, 0, 3000)]
    line, cumulative, distances = shape_model(raw, (0, 0))
    rows = [(0, "a", 0, 0, 0, 0), (1, "b", 100, 100, 1000, 0), (2, "a", 300, 300, 3000, 0)]
    positions = match_stops(rows, line, cumulative, distances, {"a": (0, 0), "b": (0, .01)}, (0, 0))
    assert positions == pytest.approx([0, cumulative[1], line.length])


def test_intermediate_times():
    rows = [(0, "a", 0, 0, None, 0), (1, "b", None, None, None, 0), (2, "c", 600, 600, None, 0)]
    departures, estimated = interpolate_times(rows, [0, 100, 400])
    assert departures == [0, 150, 600] and estimated == 1


def test_full_export_local_timing_overnight_and_frequency(feed, tmp_path):
    manifest, report, bundle = export_feed(feed, "test", "Test", (0, .01), 2, date(2024, 1, 1), "cool", tmp_path / "out", cache_dir=tmp_path / "cache")
    geometry = json.loads(gzip.decompress((bundle / "geometry.json.gz").read_bytes()))
    first = next(s["id"] for s in geometry["sections"] if s["mode"] == "bus" and s["fromStop"] == "a")
    second = next(s["id"] for s in geometry["sections"] if s["mode"] == "bus" and s["fromStop"] == "b")
    frequency = next(s["id"] for s in geometry["sections"] if s["mode"] == "subway" and s["fromStop"] == "a")
    frames = inflate(bundle, "2024-01-01")
    assert len(frames) == 288
    assert frames[-1][0]["label"].startswith("23:55")
    assert all(b[0]["start"] - a[0]["start"] == 300 for a, b in zip(frames, frames[1:]))
    assert all(f["end"] - f["start"] == 3600 for f, _ in frames)
    assert manifest["stepSeconds"] == 300 and manifest["windowSeconds"] == 3600
    at8 = next(v for f, v in frames if f["label"].startswith("08:00"))
    at9 = next(v for f, v in frames if f["label"].startswith("09:00"))
    at7 = next(v for f, v in frames if f["label"].startswith("07:00"))
    assert at8[first] == 1 and at8.get(second, 0) == 0
    assert at9[second] == 1 and at9.get(first, 0) == 0
    assert at7[frequency] == 6 and at8.get(frequency, 0) == 0
    at705 = next(v for f, v in frames if f["label"].startswith("07:05"))
    at805 = next(v for f, v in frames if f["label"].startswith("08:05"))
    at820 = next(v for f, v in frames if f["label"].startswith("08:20"))
    at825 = next(v for f, v in frames if f["label"].startswith("08:25"))
    assert at705[frequency] == 5.5
    assert at805.get(first, 0) == 0
    assert at820.get(second, 0) == 0 and at825[second] == 1
    at1 = next(v for f, v in inflate(bundle, "2024-01-02") if f["label"].startswith("01:00"))
    assert at1[first] == 1
    assert len(manifest["dates"]) == 7 and manifest["intensityMaximum"] == 6
    assert report["counts"]["processed_trips"] == 3


def test_zip_and_exception_only_export(feed, tmp_path):
    (feed / "calendar.txt").unlink()
    table(feed, "calendar_dates.txt", "service_id,date,exception_type", [("base", f"202401{i:02}", 1) for i in range(1, 9)])
    archive = tmp_path / "feed.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for p in feed.iterdir():
            z.write(p, p.name)
    result, _, bundle = export_feed(archive, "zip", "ZIP", (0, .01), 2, date(2024, 1, 1), "default", tmp_path / "zip-out", cache_dir=tmp_path / "cache")
    assert result["title"] == "ZIP" and (bundle / "geometry.json.gz").exists()


def test_missing_required_input_is_actionable(feed):
    (feed / "stop_times.txt").unlink()
    with pytest.raises(ValueError, match="stop_times.txt"):
        Feed(feed)


def test_route_types():
    assert [mode_for(v) for v in [0, 100, 401, 700, 1000, 1300, 9999]] == ["tram", "rail", "subway", "bus", "ferry_water", "funicular_cable_gondola", "other"]


def test_feed_attributions_and_refresh_provenance_survive_export(feed, tmp_path):
    table(feed, "attributions.txt", "organization_name,attribution_url,is_producer,is_authority",
          [("Transit authority", "https://authority.example", 0, 1), ("GTFS converter", "https://publisher.example", 1, 0)])
    provenance = {"url": "https://publisher.example/feed.zip", "retrievedAt": "2026-10-06T11:00:00Z", "license": "Test license"}
    manifest, _, _ = export_feed(feed, "test", "Test", (0, .01), 2, date(2024, 1, 1), "default",
                                 tmp_path / "out", "Transit authority", tmp_path / "cache", provenance=provenance)
    assert manifest["source"] == "Transit authority"
    assert manifest["attributions"][0]["authority"]
    assert manifest["attributions"][1]["producer"]
    assert manifest["provenance"] == provenance

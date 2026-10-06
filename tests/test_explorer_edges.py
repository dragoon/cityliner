import gzip
import json
from datetime import date
from pathlib import Path

import pytest

from citylines.explorer.export import export_feed
from citylines.explorer.publish import publish
from citylines.explorer.geometry import match_stops, shape_model
from test_explorer import feed, table, inflate


def export(feed, tmp_path, **kwargs):
    return export_feed(feed, "test", "Test", (0, .01), 2, date(2024, 1, 1), "default", tmp_path / "out", cache_dir=tmp_path / "cache", **kwargs)


def test_two_routes_share_geometry_without_losing_routes(feed, tmp_path):
    table(feed, "trips.txt", "trip_id,route_id,service_id,shape_id", [("a", "r", "base", "s"), ("b", "r2", "base", "s")])
    table(feed, "routes.txt", "route_id,route_short_name,route_type", [("r", "1", 3), ("r2", "2", 3)])
    table(feed, "stop_times.txt", "trip_id,stop_id,stop_sequence,arrival_time,departure_time,shape_dist_traveled",
          [(t, sid, i, tm, tm, d) for t in ["a", "b"] for sid, i, tm, d in [("a", 0, "08:00:00", 0), ("b", 1, "08:10:00", 1000), ("c", 2, "08:20:00", 2000)]])
    _, _, bundle = export(feed, tmp_path)
    g = json.loads(gzip.decompress((bundle / "geometry.json.gz").read_bytes()))
    assert len(g["sections"]) == 2
    assert set(g["sections"][0]["routes"]) == {"r", "r2"}
    assert next(v for f, v in inflate(bundle, "2024-01-01") if f["label"].startswith("08:00"))[0] == 2


def test_missing_intermediate_times_are_reported(feed, tmp_path):
    text = (feed / "stop_times.txt").read_text(encoding="utf-8-sig")
    (feed / "stop_times.txt").write_text(text.replace("09:20:00,09:20:00", ","))
    _, report, bundle = export(feed, tmp_path)
    assert report["counts"]["interpolated_stop_times"] == 1
    assert any(s["interpolated"] for s in json.loads(gzip.decompress((bundle / "geometry.json.gz").read_bytes()))["sections"])


def test_exact_frequency_replaces_template(feed, tmp_path):
    table(feed, "frequencies.txt", "trip_id,start_time,end_time,headway_secs,exact_times", [("frequency", "07:00:00", "08:00:00", 600, 1)])
    _, _, bundle = export(feed, tmp_path)
    g = json.loads(gzip.decompress((bundle / "geometry.json.gz").read_bytes()))
    sid = next(s["id"] for s in g["sections"] if s["mode"] == "subway" and s["fromStop"] == "a")
    frames = inflate(bundle, "2024-01-01")
    assert next(v for f, v in frames if f["label"].startswith("07:15"))[sid] == 4
    assert next(v for f, v in frames if f["label"].startswith("00:00")).get(sid, 0) == 0


def test_overlap_rules_rejected(feed, tmp_path):
    table(feed, "frequencies.txt", "trip_id,start_time,end_time,headway_secs,exact_times", [("frequency", "07:00:00", "08:00:00", 600, 0), ("frequency", "07:30:00", "08:30:00", 600, 0)])
    with pytest.raises(ValueError, match="Overlapping frequency"):
        export(feed, tmp_path)


def test_unsupported_trip_report_and_week_coverage(feed, tmp_path):
    text = (feed / "stop_times.txt").read_text(encoding="utf-8-sig")
    (feed / "stop_times.txt").write_text(text.replace("09:20:00,09:20:00", "bad,bad"))
    _, report, _ = export(feed, tmp_path)
    assert report["counts"]["invalid_trip_or_route"] == 1
    with pytest.raises(ValueError, match="outside feed coverage"):
        export_feed(feed, "test", "Test", (0, .01), 2, date(2025, 1, 1), "default", tmp_path / "bad", cache_dir=tmp_path / "cache")


def test_fingerprint_cache_and_local_publish(feed, tmp_path):
    first, _, first_bundle = export(feed, tmp_path)
    second, _, second_bundle = export(feed, tmp_path)
    assert first["bundle"] == second["bundle"] and first_bundle == second_bundle
    (feed / "routes.txt").write_text((feed / "routes.txt").read_text(encoding="utf-8-sig").replace("R1", "Renamed"))
    third, _, third_bundle = export(feed, tmp_path)
    assert third["feedFingerprint"] != first["feedFingerprint"]
    root = tmp_path / "gallery"
    publish(first_bundle, root)
    publish(third_bundle, root)
    catalog = json.loads((root / "catalog.json").read_text())
    assert len(catalog["cities"]) == 1
    assert (root / "data" / "test" / first["bundle"] / "manifest.json").exists()


def test_projection_without_shape_distance():
    rows = [(0, 0, 0, None), (1, 0, .01, None), (2, 0, .02, None)]
    line, lengths, distances = shape_model(rows, (0, 0))
    times = [(0, "a", 0, 0, None, 0), (1, "b", 100, 100, None, 0), (2, "c", 200, 200, None, 0)]
    positions = match_stops(times, line, lengths, distances, {"a": (0, 0), "b": (0, .01), "c": (0, .02)}, (0, 0))
    assert positions == pytest.approx(lengths)


def test_missing_optional_water_does_not_block(feed, tmp_path):
    bad_water = tmp_path / "water.json"
    bad_water.write_text('{"center":[10,10],"bounds":[],"polygons":[]}')
    _, report, _ = export(feed, tmp_path, water=bad_water)
    assert report["counts"]["water_cache_unavailable"] == 1
    _, report, _ = export(feed, tmp_path, water=tmp_path / "missing-water.json")
    assert report["counts"]["water_cache_unavailable"] == 1


def test_existing_poster_renderer(tmp_path):
    from citylines.generate_poster import Poster
    from citylines.gtfs.domain import RenderArea
    from citylines.util.colors import color_schemes
    (tmp_path / "data.lines").write_text("4\t3\t-100 -100,0 0,100 100\n")
    (tmp_path / "maxmin.lines").write_text("4\n1\n")
    output = tmp_path / "poster.pdf"
    Poster(RenderArea(400, 600), output, tmp_path, "compatibility", "", []).generate_single(color_schemes["default"])
    assert output.read_bytes().startswith(b"%PDF-") and output.stat().st_size > 1000


def test_section_peaks_use_the_entire_week(feed, tmp_path):
    _, _, bundle = export(feed, tmp_path)
    geometry = json.loads(gzip.decompress((bundle / "geometry.json.gz").read_bytes()))
    maxima = [0.] * len(geometry["sections"])
    for day in ("2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-06", "2024-01-07"):
        for _, values in inflate(bundle, day):
            for sid, count in values.items():
                maxima[sid] = max(maxima[sid], count)
    assert [s["peakDepartures"] for s in geometry["sections"]] == pytest.approx(maxima)

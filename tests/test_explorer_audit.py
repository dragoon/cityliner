import csv
from datetime import datetime
import gzip
import json
from zoneinfo import ZoneInfo

from scripts.audit_explorer import audit


def test_audit_preserves_unmatched_schedules_without_counting_them(tmp_path):
    feed, bundle = tmp_path / "feed", tmp_path / "bundle"
    feed.mkdir()
    bundle.mkdir()

    def write(name, fields, rows):
        with (feed / name).open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)

    write("trips.txt", ["trip_id", "route_id", "service_id", "shape_id"],
          [["matched", "r", "s", "shape"], ["unmatched", "r", "s", ""]])
    write("stop_times.txt", ["trip_id", "stop_sequence", "stop_id", "departure_time"],
          [[trip, seq, stop, clock] for trip, clock in [("matched", "07:00:00"), ("unmatched", "07:10:00")]
           for seq, stop in [(1, "a"), (2, "b")]])
    write("calendar_dates.txt", ["service_id", "date", "exception_type"],
          [["s", "20261014", "1"], ["s", "20261015", "1"]])
    section = {"id": 0, "mode": "rail", "fromStop": "a", "toStop": "b", "routes": ["r"],
               "estimated": False, "interpolated": False}
    (bundle / "geometry.json.gz").write_bytes(gzip.compress(json.dumps({"sections": [section]}).encode()))
    days = []
    for day in ["2026-10-14", "2026-10-15"]:
        frames = []
        for label in ["07:00", "07:05", "07:10", "08:00", "08:05", "08:10", "09:00", "23:00", "23:55"]:
            start = datetime.fromisoformat(day + "T" + label).replace(tzinfo=ZoneInfo("Europe/Zurich")).timestamp()
            frames.append({"label": label, "start": start, "end": start + 3600,
                           "changes": [[0, 1 if label == "07:00" else 0]]})
        filename = day + ".json.gz"
        (bundle / filename).write_bytes(gzip.compress(json.dumps({"frames": frames}).encode()))
        days.append({"date": day, "file": filename})
    (bundle / "manifest.json").write_text(json.dumps({"city": "zurich", "geometry": "geometry.json.gz",
                                                       "timezone": "Europe/Zurich", "dates": days}))
    result = audit(feed, bundle)
    assert result["passed"] == 18
    assert result["candidateMismatches"] == 0

"""Independent raw-CSV checks of sample exported stop-pair windows.

This does not call the exporter's schedule, calendar, or geometry functions.
Use archive weeks without DST transitions for this deliberately simple audit.
"""
import argparse
from collections import defaultdict
import csv
from datetime import date, datetime, time, timedelta
import gzip
import json
from pathlib import Path
from zoneinfo import ZoneInfo


def read(folder, name):
    path = folder / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def clock(value):
    if not value:
        return None
    h, m, s = map(int, value.split(":"))
    return h * 3600 + m * 60 + s


def audit(folder, bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    geometry = json.loads(gzip.decompress((bundle / manifest["geometry"]).read_bytes()))
    pairs = defaultdict(list)
    for s in geometry["sections"]:
        pairs[(s["mode"], s["fromStop"], s["toStop"])].append(s)
    # Prefer frequency-based metro plus conventional sections; only unambiguous,
    # consistently attributed pairs are audited.
    candidates = []
    ordered = sorted(pairs.items(), key=lambda item: not any(s["estimated"] for s in item[1]))
    for pair, sections in ordered:
        routes = {r for s in sections for r in s["routes"]}
        if len(routes) == 1 and not any(s["interpolated"] for s in sections):
            candidates.append((pair, sections, routes))
        if len(candidates) >= 30:
            break
    route_ids = {r for _, _, ids in candidates for r in ids}
    trips = {r["trip_id"]: r for r in read(folder, "trips.txt") if r["route_id"] in route_ids}
    stop_times = defaultdict(list)
    with (folder / "stop_times.txt").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["trip_id"] in trips:
                stop_times[r["trip_id"]].append(r)
    calendars = {r["service_id"]: r for r in read(folder, "calendar.txt")}
    exceptions = {(r["service_id"], r["date"]): r["exception_type"] for r in read(folder, "calendar_dates.txt")}
    frequencies = defaultdict(list)
    for r in read(folder, "frequencies.txt"):
        frequencies[r["trip_id"]].append(r)
    days = [date.fromisoformat(d["date"]) for d in manifest["dates"]]
    origins = {}
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    tz = ZoneInfo(manifest["timezone"])
    for sid in {t["service_id"] for t in trips.values()}:
        origins[sid] = []
        for delta in range(-5, 9):
            d = days[0] + timedelta(days=delta)
            key = d.strftime("%Y%m%d")
            cal = calendars.get(sid)
            active = bool(cal and cal["start_date"] <= key <= cal["end_date"] and cal[weekdays[d.weekday()]] == "1")
            if (sid, key) in exceptions:
                active = exceptions[(sid, key)] == "1"
            if active:
                origins[sid].append(datetime.combine(d, time(), tz).timestamp())
    departures = defaultdict(list)
    for tid, rows in stop_times.items():
        rows.sort(key=lambda r: int(r["stop_sequence"]))
        first = clock(rows[0].get("departure_time") or rows[0].get("arrival_time"))
        for a, b in zip(rows, rows[1:]):
            dep = clock(a.get("departure_time") or a.get("arrival_time"))
            if dep is not None:
                departures[(a["stop_id"], b["stop_id"], trips[tid]["route_id"])].append((tid, dep, first))
    checks, mismatches = [], []
    for day_info in manifest["dates"][:2]:
        data = json.loads(gzip.decompress((bundle / day_info["file"]).read_bytes()))
        current = {}
        frames = []
        for f in data["frames"]:
            current.update(f["changes"])
            if f["label"].startswith(("07:00", "08:00", "09:00", "23:00")):
                frames.append((f, current.copy()))
        for (mode, a, b), sections, route_ids in candidates:
            rid = next(iter(route_ids))
            sample_checks = []
            for frame, exported in frames:
                expected = 0.
                for tid, dep, first in departures[(a, b, rid)]:
                    for origin in origins[trips[tid]["service_id"]]:
                        if frequencies[tid]:
                            for rule in frequencies[tid]:
                                start, end, h = clock(rule["start_time"]), clock(rule["end_time"]), int(rule["headway_secs"])
                                offset = dep - first
                                if rule.get("exact_times") == "1":
                                    expected += sum(frame["start"] <= origin + t + offset < frame["end"] for t in range(start, end, h))
                                else:
                                    low, high = origin + start + offset, origin + end + offset
                                    expected += max(0, min(frame["end"], high) - max(frame["start"], low)) / h
                        else:
                            expected += frame["start"] <= origin + dep < frame["end"]
                actual = sum(exported.get(s["id"], 0) for s in sections)
                sample_checks.append({"date": day_info["date"], "window": frame["label"], "route": rid,
                                      "from": a, "to": b, "expected": round(expected, 4), "exported": round(actual, 4),
                                      "estimated": any(s["estimated"] for s in sections)})
            if all(abs(c["expected"] - c["exported"]) < .001 for c in sample_checks) and any(c["expected"] for c in sample_checks):
                checks.extend(sample_checks)
            else:
                mismatches.extend(sample_checks)
    if any(abs(c["expected"] - c["exported"]) >= .001 for c in mismatches):
        raise ValueError(f"Independent timetable mismatch: {mismatches[:8]}")
    if len(checks) < 16:
        raise ValueError(f"Insufficient successful independent checks: {len(checks)}. Investigate {mismatches[:8]}")
    return {"city": manifest["city"], "passed": len(checks), "frequencyChecks": sum(c["estimated"] for c in checks),
            "candidateMismatches": sum(abs(c["expected"]-c["exported"]) >= .001 for c in mismatches), "checks": checks}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gtfs", required=True, type=Path)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.gtfs, args.bundle)
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}))

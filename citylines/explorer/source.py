"""Bounded-memory GTFS reads and restartable disk-backed staging."""
import csv
import hashlib
import io
import math
import sqlite3
import zipfile
from pathlib import Path
from .schedule import seconds

FILES = ("agency.txt", "routes.txt", "stops.txt", "shapes.txt", "trips.txt",
         "stop_times.txt", "calendar.txt", "calendar_dates.txt", "frequencies.txt",
         "feed_info.txt", "attributions.txt")
REQUIRED = FILES[:6]


class Feed:
    def __init__(self, path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(self.path) if self.path.is_file() else None
        self.names = set(self.zip.namelist()) if self.zip else {p.name for p in self.path.glob("*.txt")}
        missing = set(REQUIRED) - self.names
        if missing:
            raise ValueError("GTFS is missing required files: " + ", ".join(sorted(missing)))
        if not {"calendar.txt", "calendar_dates.txt"} & self.names:
            raise ValueError("GTFS needs calendar.txt or calendar_dates.txt")

    def open(self, name):
        return self.zip.open(name) if self.zip else (self.path / name).open("rb")

    def rows(self, name, required=()):
        if name not in self.names:
            return
        with self.open(name) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not set(required) <= set(reader.fieldnames or []):
                raise ValueError(f"{name} is missing columns: {', '.join(sorted(set(required) - set(reader.fieldnames or [])))}")
            for row in reader:
                yield row

    def fingerprint(self):
        digest = hashlib.sha256()
        for name in FILES:
            if name not in self.names:
                continue
            digest.update(name.encode())
            with self.open(name) as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()

    def close(self):
        if self.zip:
            self.zip.close()


def optional_float(value):
    if not value:
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("Distances must be finite and nonnegative")
    return result


def coordinate(value, limit):
    result = float(value)
    if not math.isfinite(result) or not -limit <= result <= limit:
        raise ValueError("Coordinates must be finite and in geographic bounds")
    return result


def stage(feed, path):
    """Keep raw rows on disk, including stop times ordered only at query time."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA cache_size=-32768")
    db.execute("PRAGMA temp_store=FILE")
    db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT)")
    ready = db.execute("SELECT value FROM metadata WHERE key='ready'").fetchone()
    if ready:
        return db
    for table in ("shapes", "trips", "times", "invalid_trips"):
        db.execute(f"DROP TABLE IF EXISTS {table}")
    db.executescript("""
        CREATE TABLE shapes(id TEXT, seq INTEGER, lat REAL, lon REAL, distance REAL);
        CREATE TABLE trips(id TEXT PRIMARY KEY, route TEXT, service TEXT, shape TEXT, direction TEXT);
        CREATE TABLE times(trip TEXT, seq INTEGER, stop TEXT, arrival REAL, departure REAL, distance REAL, flex INTEGER);
        CREATE TABLE invalid_trips(id TEXT PRIMARY KEY);
    """)
    specifications = [
        ("shapes.txt", "shapes", ("shape_id", "shape_pt_sequence", "shape_pt_lat", "shape_pt_lon"),
         lambda r: (r["shape_id"], int(r["shape_pt_sequence"]), coordinate(r["shape_pt_lat"], 90), coordinate(r["shape_pt_lon"], 180), optional_float(r.get("shape_dist_traveled")))),
        ("trips.txt", "trips", ("trip_id", "route_id", "service_id"),
         lambda r: (r["trip_id"], r["route_id"], r["service_id"], r.get("shape_id", ""), r.get("direction_id", ""))),
        ("stop_times.txt", "times", ("trip_id", "stop_sequence", "stop_id"),
         lambda r: (r["trip_id"], int(r["stop_sequence"]), r.get("stop_id", ""), seconds(r.get("arrival_time")), seconds(r.get("departure_time")), optional_float(r.get("shape_dist_traveled")), int(bool(r.get("start_pickup_drop_off_window") or r.get("location_id") or r.get("location_group_id"))))),
    ]
    for filename, table, required, parse in specifications:
        print(f"Staging {filename}…", flush=True)
        batch = []
        for row in feed.rows(filename, required):
            try:
                batch.append(parse(row))
            except (ValueError, TypeError) as exc:
                if table != "times":
                    raise ValueError(f"Invalid {filename} row: {exc}") from exc
                db.execute("INSERT OR IGNORE INTO invalid_trips VALUES (?)", (row["trip_id"],))
                continue
            if len(batch) >= 20000:
                db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in batch[0])})", batch)
                db.commit()
                batch.clear()
        if batch:
            db.executemany(f"INSERT INTO {table} VALUES ({','.join('?' for _ in batch[0])})", batch)
        db.commit()
    db.executescript("""
        CREATE INDEX shape_order ON shapes(id,seq);
        CREATE INDEX trip_shape ON trips(shape);
        CREATE UNIQUE INDEX time_order ON times(trip,seq);
    """)
    db.execute("INSERT OR REPLACE INTO metadata VALUES ('ready', '1')")
    db.commit()
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return db

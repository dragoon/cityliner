"""Generate the small synthetic viewer demo without downloading any data."""
import csv
from datetime import date
from pathlib import Path
import tempfile

from citylines.explorer.export import export_feed
from citylines.explorer.publish import publish


def main():
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        feed = work / "feed"
        feed.mkdir()

        def table(name, columns, rows):
            with (feed / name).open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns.split(","))
                writer.writerows(rows)

        table("agency.txt", "agency_id,agency_name,agency_url,agency_timezone",
              [("demo", "Synthetic demonstration", "https://github.com/dragoon/cityliner", "UTC")])
        table("routes.txt", "route_id,route_short_name,route_type", [("bus", "B1", 3), ("tram", "T1", 0)])
        points = [("a", -.01, -.02), ("b", .01, 0), ("c", -.01, .02), ("d", -.02, 0), ("e", .02, 0)]
        table("stops.txt", "stop_id,stop_lat,stop_lon", points)
        table("shapes.txt", "shape_id,shape_pt_sequence,shape_pt_lat,shape_pt_lon",
              [("bus", i, lat, lon) for i, (_, lat, lon) in enumerate(points[:3])] +
              [("tram", i, lat, lon) for i, (_, lat, lon) in enumerate([points[3], points[1], points[4]])])
        trips, times = [], []
        for route, stops, hours in [("bus", ["a", "b", "c"], range(6, 23)), ("tram", ["d", "b", "e"], range(8, 20))]:
            for hour in hours:
                for minute in [0, 30]:
                    tid = f"{route}-{hour}-{minute}"
                    trips.append((tid, route, "daily", route))
                    for i, stop in enumerate(stops):
                        stamp = f"{hour:02}:{minute+i*10:02}:00"
                        times.append((tid, stamp, stamp, stop, i))
        table("trips.txt", "trip_id,route_id,service_id,shape_id", trips)
        table("stop_times.txt", "trip_id,arrival_time,departure_time,stop_id,stop_sequence", times)
        table("calendar.txt", "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date",
              [("daily", 1, 1, 1, 1, 1, 1, 1, "20240101", "20240107")])
        _, _, bundle = export_feed(feed, "demo", "Synthetic network", (0, 0), 4, date(2024, 1, 1), "cool", work / "out",
                                  attribution="Synthetic timetable for demonstrating Cityliner; no real transport service.", cache_dir=work / "cache")
        print(publish(bundle, Path("docs/explore")))


if __name__ == "__main__":
    main()

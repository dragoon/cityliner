"""Metric projection, ordered stop matching, and genuine line clipping."""
import math
from bisect import bisect_left
from shapely.geometry import LineString, Point, box
from shapely.ops import substring

R = 6371000


def project(lat, lon, center):
    # A local equirectangular projection in metres; independent of canvas size.
    return ((lon - center[1]) * math.pi / 180 * R * math.cos(math.radians(center[0])),
            -(lat - center[0]) * math.pi / 180 * R)


def bounds_for(radius):
    return [-radius * 1000, -radius * 1000, radius * 1000, radius * 1000]


def shape_model(rows, center):
    points = [project(r[1], r[2], center) for r in rows]
    line = LineString(points)
    if not math.isfinite(line.length) or line.length < .01:
        raise ValueError("Degenerate shape")
    cumulative = [0.0]
    for a, b in zip(points, points[1:]):
        cumulative.append(cumulative[-1] + math.dist(a, b))
    distances = [r[3] for r in rows]
    usable = all(v is not None and math.isfinite(v) for v in distances)
    usable = usable and all(b >= a for a, b in zip(distances, distances[1:]))
    usable = usable and distances[-1] > distances[0]
    return line, cumulative, distances if usable else None


def measured_position(value, distances, cumulative):
    if value < distances[0] or value > distances[-1]:
        raise ValueError("Stop distance lies outside its shape")
    i = min(max(1, bisect_left(distances, value)), len(distances) - 1)
    span = distances[i] - distances[i - 1]
    ratio = (value - distances[i - 1]) / span if span else 0
    return cumulative[i - 1] + ratio * (cumulative[i] - cumulative[i - 1])


def match_stops(rows, line, cumulative, distances, stops, center):
    positions = []
    use_distances = distances is not None and all(r[4] is not None for r in rows)
    previous = 0.0
    for row in rows:
        point = Point(project(*stops[row[1]], center))
        if use_distances:
            position = measured_position(row[4], distances, cumulative)
            if position + 0.01 < previous or line.interpolate(position).distance(point) > 300:
                raise ValueError("Inconsistent stop/shape distances")
        else:
            # Search only the remaining directed path so loops cannot jump back.
            tail = substring(line, previous, line.length)
            if tail.geom_type != "LineString" or tail.length < .01:
                position = previous
            else:
                position = previous + tail.project(point)
            if not math.isfinite(position):
                raise ValueError("Cannot project stop onto shape")
            if line.interpolate(position).distance(point) > 300:
                raise ValueError("Stop is more than 300 metres from ordered shape")
        positions.append(position)
        previous = position
    return positions


def interpolate_times(rows, positions):
    # row fields: sequence, stop_id, arrival, departure, shape_distance, flex
    arrivals = [r[2] if r[2] is not None else r[3] for r in rows]
    departures = [r[3] if r[3] is not None else r[2] for r in rows]
    estimated = 0
    anchors = [i for i, t in enumerate(departures) if t is not None]
    if not anchors or anchors[0] != 0 or anchors[-1] != len(rows) - 1:
        raise ValueError("Trip needs first and last stop times")
    for a, b in zip(anchors, anchors[1:]):
        if arrivals[b] < departures[a]:
            raise ValueError("Trip times run backwards")
        for i in range(a + 1, b):
            span = positions[b] - positions[a]
            ratio = ((positions[i] - positions[a]) / span) if span > 0 else (i - a) / (b - a)
            arrivals[i] = departures[i] = departures[a] + ratio * (arrivals[b] - departures[a])
            estimated += 1
    for i in range(len(rows)):
        if arrivals[i] > departures[i] or (i and arrivals[i] < departures[i - 1]):
            raise ValueError("Invalid stop time ordering")
    return departures, estimated


def clipped_paths(line, start, end, bounds):
    if end - start < .01:
        return []
    part = substring(line, start, end).intersection(box(*bounds))
    pieces = [part] if part.geom_type == "LineString" else getattr(part, "geoms", [])
    return [[[round(x, 1), round(y, 1)] for x, y in p.simplify(12).coords]
            for p in pieces if p.geom_type == "LineString" and p.length > .01]

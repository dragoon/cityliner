"""Calendar and absolute-time rules shared by the exporter and its tests."""
from datetime import date, datetime, time, timedelta, timezone
from bisect import bisect_right
from zoneinfo import ZoneInfo

UTC = timezone.utc
STEP = 300
WINDOW = 3600


def seconds(value):
    if not value:
        return None
    h, m, s = map(int, value.split(":"))
    if h < 0 or not 0 <= m < 60 or not 0 <= s < 60:
        raise ValueError(f"Invalid GTFS time: {value}")
    return h * 3600 + m * 60 + s


def service_origin(day, tz):
    # Arithmetic in UTC is essential: local noon minus 12 wall-clock hours is
    # incorrect on DST transition days. GTFS defines twelve elapsed hours.
    return datetime.combine(day, time(12), tz).astimezone(UTC).timestamp() - 43200


def active_services(day, calendars, exceptions):
    key = day.strftime("%Y%m%d")
    active = {sid for sid, start, end, weekdays in calendars
              if start <= key <= end and weekdays[day.weekday()] == "1"}
    for sid, kind in exceptions.get(key, []):
        if kind == 1:
            active.add(sid)
        elif kind == 2:
            active.discard(sid)
    return active


def day_windows(day, tz):
    start = datetime.combine(day, time(), tz).astimezone(UTC).timestamp()
    end = datetime.combine(day + timedelta(days=1), time(), tz).astimezone(UTC).timestamp()
    result = []
    while start < end:
        a = datetime.fromtimestamp(start, tz)
        b = datetime.fromtimestamp(start + WINDOW, tz)
        result.append({"start": int(start), "end": int(start + WINDOW),
                       "label": a.strftime("%H:%M %Z"),
                       "endLabel": b.strftime("%H:%M %Z"),
                       "endDate": b.date().isoformat(), "counts": []})
        start += STEP
    return result


def add_departure(values, starts, departure, weight=1):
    # Every rolling [start, start + hour) window that contains this departure.
    left = bisect_right(starts, departure - WINDOW)
    right = bisect_right(starts, departure)
    for index in range(left, right):
        values[index] += weight


def add_frequency(values, starts, origin, offset, start, end, headway, exact):
    if exact:
        departure = start
        while departure < end:
            add_departure(values, starts, origin + departure + offset)
            departure += headway
    else:
        a, b = origin + start + offset, origin + end + offset
        left = bisect_right(starts, a - WINDOW)
        right = bisect_right(starts, b)
        for index in range(left, right):
            overlap = max(0, min(starts[index] + WINDOW, b) - max(starts[index], a))
            values[index] += overlap / headway

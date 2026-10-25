from datetime import date
import json

import pytest

from citylines.explorer.export import export_feed
from scripts.audit_explorer import audit
from test_explorer import feed, table


@pytest.mark.parametrize("week", [date(2024, 3, 25), date(2024, 10, 21)])
def test_independent_audit_covers_dst_and_weekends(feed, tmp_path, week):
    table(feed, "agency.txt", "agency_id,agency_name,agency_url,agency_timezone", [("a", "Test", "https://example.com", "Europe/Berlin")])
    table(feed, "calendar.txt", "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date",
          [("base", 1, 1, 1, 1, 1, 1, 1, "20240101", "20241231")])
    _, _, bundle = export_feed(feed, "test", "Test", (0, .01), 2, week, "pastel", tmp_path / "bundles", cache_dir=tmp_path / "cache")
    result = audit(feed, bundle)
    assert {c["date"] for c in result["checks"]} == {d["date"] for d in json.loads((bundle / 'manifest.json').read_text())["dates"]}
    assert result["candidateMismatches"] == 0

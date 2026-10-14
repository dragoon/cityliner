import csv
from pathlib import Path
import zipfile
from scripts.subset_swiss_gtfs import subset


def test_swiss_subset_preserves_complete_trips_and_all_modes(tmp_path):
    archive = tmp_path / 'national.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('stops.txt', 'stop_id,stop_name,stop_lat,stop_lon\na,Near,0,0\nb,Far,0,0.1\nc,Further,0,0.2\n')
        z.writestr('routes.txt', 'route_id,route_type\nrail,109\nbus,700\nferry,1000\noutside,700\n')
        z.writestr('trips.txt', 'trip_id,route_id,service_id\nr,rail,s\nb,bus,s\nf,ferry,s\no,outside,x\n')
        z.writestr('stop_times.txt', 'trip_id,stop_id,stop_sequence\nr,a,1\nr,b,2\nb,a,1\nb,c,2\nf,b,1\nf,a,2\no,b,1\no,c,2\n')
        z.writestr('calendar.txt', 'service_id\ns\nx\n')
        z.writestr('agency.txt', 'agency_id\noperator\n')
        z.writestr('feed_info.txt', 'feed_version\n20261010\n')
    output = tmp_path / 'selected'
    subset(archive, output, (0,0), 1)
    def rows(name):
        with (output/name).open() as handle:
            return list(csv.DictReader(handle))
    assert {r['route_type'] for r in rows('routes.txt')} == {'109','700','1000'}
    assert {r['trip_id'] for r in rows('trips.txt')} == {'r','b','f'}
    assert len(rows('stop_times.txt')) == 6
    assert {r['stop_id'] for r in rows('stop_times.txt')} == {'a','b','c'}
    assert rows('calendar.txt') == [{'service_id':'s'}]
    assert rows('feed_info.txt') == [{'feed_version':'20261010'}]

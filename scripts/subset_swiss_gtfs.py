"""Select complete national-feed trips serving a buffered explorer area, all modes."""
import argparse
import csv
import io
import json
from pathlib import Path
import zipfile
from citylines.explorer.geometry import project


def subset(archive, output, center, radius, buffer=2):
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        def rows(name):
            with source.open(name) as raw, io.TextIOWrapper(raw, encoding='utf-8-sig', newline='') as handle:
                yield from csv.DictReader(handle)
        stops = {r['stop_id'] for r in rows('stops.txt') if r.get('stop_lat') and r.get('stop_lon') and max(map(abs, project(float(r['stop_lat']), float(r['stop_lon']), center))) <= (radius+buffer)*1000}
        print(f'Selecting complete trips serving {len(stops)} stops, all modes…', flush=True)
        trips = {r['trip_id'] for r in rows('stop_times.txt') if r['stop_id'] in stops}
        routes, services = set(), set()
        print(f'Writing {len(trips)} complete trips…', flush=True)
        def write(name, include):
            with source.open(name) as raw, io.TextIOWrapper(raw, encoding='utf-8-sig', newline='') as handle, (output/name).open('w', encoding='utf-8', newline='') as target:
                reader = csv.DictReader(handle)
                writer = csv.DictWriter(target, reader.fieldnames)
                writer.writeheader()
                for row in reader:
                    if include(row):
                        writer.writerow(row)
        def trip(row):
            if row['trip_id'] not in trips: return False
            routes.add(row['route_id']); services.add(row['service_id'])
            return True
        write('trips.txt', trip)
        for name, include in [('stop_times.txt', lambda r:r['trip_id'] in trips), ('frequencies.txt', lambda r:r['trip_id'] in trips), ('routes.txt', lambda r:r['route_id'] in routes), ('calendar.txt', lambda r:r['service_id'] in services), ('calendar_dates.txt', lambda r:r['service_id'] in services)]:
            if name in source.namelist(): write(name, include)
        for name in ['agency.txt','stops.txt','feed_info.txt','attributions.txt']:
            if name in source.namelist():
                with source.open(name) as raw, (output/name).open('wb') as target:
                    import shutil
                    shutil.copyfileobj(raw,target)
        info={'selection':'Complete trips with at least one stop inside the buffered square; no mode/operator filter', 'center':center,'radiusKm':radius,'bufferKm':buffer,'trips':len(trips),'routes':len(routes),'services':len(services)}
        (output/'subset-report.json').write_text(json.dumps(info,indent=2)+'\n')
        print(json.dumps(info), flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--center',required=True)
    parser.add_argument('--max-dist',type=float,default=20)
    args=parser.parse_args()
    subset(args.archive,args.output,tuple(map(float,args.center.split(','))),args.max_dist)

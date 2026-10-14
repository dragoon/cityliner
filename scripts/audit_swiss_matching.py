"""Report regional national-feed geometry coverage for an explicitly selected week."""
import argparse
from collections import defaultdict
import csv
from datetime import date,timedelta
import json
from pathlib import Path
import sqlite3
from citylines.explorer.schedule import active_services
from citylines.explorer.export import mode_for


def coverage(gtfs, database, week_start):
    def rows(name):
        with (gtfs/name).open(encoding='utf-8-sig',newline='') as f:
            yield from csv.DictReader(f)
    weekdays=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
    calendars=[(r['service_id'],r['start_date'],r['end_date'],''.join(r[d] for d in weekdays)) for r in rows('calendar.txt')]
    exceptions=defaultdict(list)
    for r in rows('calendar_dates.txt'):
        exceptions[r['date']].append((r['service_id'],int(r['exception_type'])))
    active=set()
    for i in range(7):active.update(active_services(week_start+timedelta(days=i),calendars,exceptions))
    with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as db:
        types=defaultdict(lambda:dict(trips=0,matchedTrips=0,activeWeekTrips=0,activeWeekMatchedTrips=0))
        for route_type,sid,matched,count in db.execute('SELECT route_type,service_id,shape_id IS NOT NULL,COUNT(*) FROM gtfs_trips GROUP BY route_type,service_id,shape_id IS NOT NULL'):
            values=types[mode_for(route_type)]
            values['trips']+=count;values['matchedTrips']+=count*matched
            if sid in active:
                values['activeWeekTrips']+=count;values['activeWeekMatchedTrips']+=count*matched
        missing=[dict(routeId=r,routeName=n,mode=mode_for(t),activeWeekUnmatchedTrips=count) for r,n,t,sid,count in db.execute('SELECT route_id,route_short_name,route_type,service_id,COUNT(*) FROM gtfs_trips WHERE shape_id IS NULL GROUP BY route_id,service_id') if sid in active]
        grouped={}
        for row in missing:
            key=row['routeId']
            if key not in grouped:grouped[key]=row
            else:grouped[key]['activeWeekUnmatchedTrips']+=row['activeWeekUnmatchedTrips']
        selection='Complete source trips in the supplied regional subset; no mode/operator filter.'
        subset_info=gtfs/'subset-report.json'
        if subset_info.exists():
            info=json.loads(subset_info.read_text())
            selection=(f"Complete source trips with at least one stop inside a buffered square extending "
                       f"{info['radiusKm']+info['bufferKm']:g} km from the center in each direction "
                       f"({info['radiusKm']:g} km map area plus {info['bufferKm']:g} km buffer). No mode/operator filter.")
        result={'weekStart':week_start.isoformat(),'selection':selection,'byMode':dict(types),'unmatchedActiveRoutes':sorted(grouped.values(),key=lambda r:-r['activeWeekUnmatchedTrips'])}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gtfs',type=Path,required=True);parser.add_argument('--database',type=Path,required=True)
    parser.add_argument('--week-start',type=date.fromisoformat,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=coverage(args.gtfs,args.database,args.week_start)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(result['byMode'],indent=2))

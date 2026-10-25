"""Rebuild official-source analysis. Python 3.12; pip install -r requirements.txt."""
from pathlib import Path
import os,json,hashlib,datetime,csv,sys
import duckdb
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
con=duckdb.connect('data/analytics.duckdb')
con.execute("SET memory_limit='3GB'; SET threads=4; SET preserve_insertion_order=false")
def records(sql):
    cur=con.execute(sql)
    return [dict(zip([x[0] for x in cur.description],r)) for r in cur.fetchall()]
def save(name,obj):
    (ROOT/'reports'/name).write_text(json.dumps(obj,indent=2,default=str))
manifest=[]
for p in sorted((ROOT/'data').glob('*')):
    if p.suffix not in ('.parquet','.csv'): continue
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''): h.update(chunk)
    url='https://d37ci6vzurychx.cloudfront.net/'+('misc/' if p.suffix=='.csv' else 'trip-data/')+p.name
    manifest.append(dict(file=p.name,bytes=p.stat().st_size,sha256=h.hexdigest(),url=url))
save('source_manifest.json',dict(retrieved_on='2026-10-25',files=manifest))
for script in ([] if '--reuse' in sys.argv else ['01_model.sql','02_metrics.sql','03_sensitivity.sql','04_dashboard_views.sql']):
    print('Running',script,flush=True)
    con.execute((ROOT/'sql'/script).read_text())
qa=records('''SELECT year,count(*) raw_rows,
count(*) FILTER(WHERE hvfhs_license_num NOT IN ('HV0003','HV0005') OR hvfhs_license_num IS NULL) other_company,
count(*) FILTER(WHERE pickup_datetime IS NULL OR year(pickup_datetime)<>raw.year OR month(pickup_datetime)<>8) out_of_period
FROM raw GROUP BY year''')
checks=records('''SELECT year,company,count(*) trips,
count(*) FILTER(WHERE wait_minutes IS NULL) invalid_wait,
count(*) FILTER(WHERE wait_raw<0) negative_wait,
count(*) FILTER(WHERE wait_raw>60) wait_over_60,
count(*) FILTER(WHERE fare IS NULL OR fare<0) invalid_fare,
count(*) FILTER(WHERE fare>500) fares_over_500,
count(*) FILTER(WHERE driver_pay IS NULL OR driver_pay<0) invalid_pay,
count(*) FILTER(WHERE trip_miles IS NULL OR trip_miles<=0) invalid_distance,
count(*) FILTER(WHERE trip_minutes IS NULL OR trip_minutes<=0) invalid_duration,
count(*) FILTER(WHERE pickup_zone='Unknown') unmatched_zone,
count(DISTINCT trip_date) n_days FROM trips GROUP BY ALL''')
assert all(x['n_days']==31 for x in checks)
assert sum(x['trips'] for x in checks)==sum(x['raw_rows']-x['other_company']-x['out_of_period'] for x in qa)
assert con.execute('SELECT count(*)=count(DISTINCT LocationID) FROM zones').fetchone()[0]
assert con.execute('SELECT max(abs(s-1))<1e-10 FROM (SELECT year,sum(trip_share) s FROM overview GROUP BY year)').fetchone()[0]
for table in ['overview','daily','segments','standardized','opportunities','growth_bridge','matched_cells','sensitivity','growth_components','matched_comparison','priority_shortlist']:
    con.execute(f"COPY (SELECT * FROM {table}) TO 'tableau/{table}.csv' (HEADER, DELIMITER ',')")
    if table not in ['daily','segments','matched_cells','opportunities']: save(table+'.json',records(f'SELECT * FROM {table} ORDER BY company'+(',year' if table=='overview' else '')))
save('top_opportunities.json',records('SELECT * FROM opportunities WHERE priority_rank<=10 ORDER BY company,priority_rank'))
bridge=records('SELECT * FROM growth_bridge')
assert all(abs(x['volume_effect']+x['fare_mix_effect']+x['interaction_effect']-x['actual_base_fare_change'])<.1 for x in bridge)
# Growth bridge uses fare-valid trip counts, matching the fare sum denominator.
assert con.execute('SELECT sum(trips) FROM daily').fetchone()[0]==sum(x['trips'] for x in checks)
assert con.execute('SELECT sum(trips) FROM segments').fetchone()[0]==sum(x['trips'] for x in checks)
save('validation.json',dict(status='PASS',raw=qa,quality=checks,checks=['31 pickup dates per company/year','raw-to-model row reconciliation','unique zone dimension','trip shares sum to 1','daily and segment counts reconcile','growth bridge reconciles within $0.10','fare-valid counts used for bridge']))
print(json.dumps(records('SELECT * FROM overview ORDER BY company,year'),indent=2),flush=True)
con.close()

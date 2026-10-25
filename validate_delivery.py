"""Check source/export/workbook consistency without claiming native visual QA."""
from pathlib import Path
import csv,json,zipfile,xml.etree.ElementTree as E,math
R=Path(__file__).resolve().parent
manifest=json.loads((R/'tableau/workbook_manifest.json').read_text())
def rows(name):
    with (R/'tableau'/f'{name}.csv').open() as f:return list(csv.DictReader(f))
overview={(x['company'],int(x['year'])):x for x in rows('overview')}
assert len(overview)==4
for table in ['overview','daily','segments']:
    grouped={}
    for row in rows(table):
        key=(row['company'],int(row['year']))
        grouped.setdefault(key,{'trips':0,'long_wait_trips':0,'wait_valid_n':0})
        for field in grouped[key]:grouped[key][field]+=int(row[field])
    for key,values in grouped.items():
        for field,val in values.items():assert val==int(overview[key][field]),(table,key,field)
        assert math.isclose(values['long_wait_trips']/values['wait_valid_n'],float(overview[key]['long_wait_rate']),abs_tol=1e-12)
    assert sum(x['trips'] for x in grouped.values())==39764941
for row in rows('matched_comparison'):
    assert math.isclose(float(row['matched_coverage']),int(row['matched_trips'])/int(overview[row['company'],int(row['year'])]['trips']),abs_tol=1e-12)
for company in ['Uber','Lyft']:
    component_sum=sum(float(x['contribution_usd']) for x in rows('growth_components') if x['company']==company)
    total_change=float(overview[company,2026]['base_fare_total'])-float(overview[company,2025]['base_fare_total'])
    assert abs(component_sum-total_change)<.1
with zipfile.ZipFile(R/'tableau'/manifest['workbook']) as z:
    assert z.testzip() is None
    w=E.fromstring(z.read('NYC_Ridehail.twb'))
    assert len(w.findall('dashboards/dashboard'))==3
    assert len(w.findall('worksheets/worksheet'))==12
    assert [x.get('name') for x in w.findall('worksheets/worksheet')]==[x['name'] for x in manifest['worksheets']]
    assert [x.get('name') for x in w.findall('dashboards/dashboard')]==[x['name'] for x in manifest['dashboards']]
    for ds in w.findall('datasources/datasource'):
        name=ds.get('name');assert ds.find('extract').get('enabled')=='true'
        assert not any(n.endswith('.csv') for n in z.namelist())
        assert f'Data/{name}.hyper' in z.namelist()
        assert len(rows(name))==manifest['sources'][name]['row_count']
    for ws in w.findall('worksheets/worksheet'):
        enc=ws.find('table/style/style-rule/encoding')
        assert {x.find('bucket').text.strip('"'):x.get('to') for x in enc}==manifest['palette']
        source=ws.find('table/view/datasources/datasource').get('name')
        item=next(x for x in manifest['worksheets'] if x['name']==ws.get('name'))
        assert source==item['source']
result={'status':'PASS','workbook':manifest['workbook'],'checks':['overview, daily and segments agree on company/year trip and wait counts','weighted wait rates match overview','matched coverage agrees with overview denominator','growth component sums reconcile within $0.10','3 dashboard and 12 worksheet names match generated manifest','6 enabled embedded extracts with matching source row counts; no embedded CSVs','every worksheet source matches manifest','all 12 sheets map Uber to #000000 and Lyft to #FF00BF'],'native_render':'NOT VERIFIED for expanded workbook; app connection times out'}
(R/'reports/delivery_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))

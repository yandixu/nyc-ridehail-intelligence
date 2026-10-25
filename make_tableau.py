"""Build the three-dashboard Tableau portfolio from validated CSV exports.

Each CSV has a separate datasource and embedded Hyper extract. No cross-grain joins.
Workbook manifest and worksheet map are generated from the same configuration.
"""
from pathlib import Path
import csv,copy,json,zipfile,xml.etree.ElementTree as E
from tableauhyperapi import HyperProcess,Connection,Telemetry,CreateMode,TableDefinition,TableName,SqlType,Inserter
R=Path(__file__).resolve().parent
COLORS={'Uber':'#000000','Lyft':'#FF00BF'}
SOURCE_NAMES=['overview','daily','segments','growth_components','matched_comparison','priority_shortlist']
DIMENSIONS={'company','year','trip_date','trip_day','borough','pickup_zone_id','pickup_zone','dropoff_zone_id','day_type','pickup_hour','priority_label','component','peer_group','distance_band'}
CALCS={
 'calc_long_wait_rate':('Long wait rate','SUM([long_wait_trips]) / SUM([wait_valid_n])',['long_wait_trips','wait_valid_n'],'p0.0%'),
 'calc_mean_wait':('Mean pickup wait (min)','SUM([wait_minutes_sum]) / SUM([wait_valid_n])',['wait_minutes_sum','wait_valid_n'],'n0.00'),
 'calc_mean_fare':('Mean base fare (USD)','SUM([base_fare_total]) / SUM([fare_valid_n])',['base_fare_total','fare_valid_n'],'c"$"#,##0.00'),
 'calc_wait_coverage':('Valid wait coverage','SUM([wait_valid_n]) / SUM([trips])',['wait_valid_n','trips'],'p0.0%')}
# All visual claims and sources come from this single configuration.
SPECS=[
 {'name':'01 Reported trips','source':'overview','metric':'trips','dims':['company','year'],'title':'Reported trips | August 2025 vs 2026'},
 {'name':'02 Reported trip share','source':'overview','metric':'trip_share','dims':['company','year'],'title':'Share of reported Uber and Lyft trips'},
 {'name':'03 Long pickup waits','source':'overview','metric':'calc_long_wait_rate','dims':['company','year'],'title':'Pickup waits over 10 minutes | valid waits only'},
 {'name':'04 Daily trip volume','source':'daily','metric':'trips','dims':['year'],'x':'trip_day','title':'Daily reported trips | day of August','mark':'Line'},
 {'name':'05 Borough pickup wait','source':'segments','metric':'calc_mean_wait','dims':['company','year','borough'],'title':'Mean pickup wait by borough | minutes'},
 {'name':'06 Hourly pickup wait','source':'segments','metric':'calc_mean_wait','dims':['year'],'x':'pickup_hour','title':'Mean pickup wait by pickup hour | minutes','mark':'Line'},
 {'name':'07 Tail pickup wait','source':'overview','metric':'p90_wait_minutes','dims':['company','year'],'title':'90th percentile pickup wait | minutes'},
 {'name':'08 Priority shortlist','source':'priority_shortlist','metric':'peer_excess_long_wait_trips','dims':['company','priority_label'],'title':'Top 10 segments per company | long waits above peer benchmark'},
 {'name':'09 Base-fare growth components','source':'growth_components','metric':'contribution_usd','dims':['company','component'],'title':'Change in valid base-fare total | USD contributions'},
 {'name':'10 Matched base fare','source':'matched_comparison','metric':'fixed_mix_fare','dims':['company','year'],'title':'Matched trips | fixed-mix mean base fare (USD)'},
 {'name':'11 Matched pickup wait','source':'matched_comparison','metric':'fixed_mix_wait','dims':['company','year'],'title':'Matched trips | fixed-mix mean pickup wait (min)'},
 {'name':'12 Matched coverage','source':'matched_comparison','metric':'matched_coverage','dims':['company','year'],'title':'Matched trips / all reported company-year trips'}]
DASHES=[
 {'name':'1 Growth and Service Health','sheets':[x['name'] for x in SPECS[:4]],'note':'Reported Uber/Lyft trips only. Shares exclude other mobility services. Long waits: >10 min among valid 0–60 min waits. Compare years within each company.'},
 {'name':'2 Service Diagnostics','sheets':[x['name'] for x in SPECS[4:8]],'note':'Black = Uber | Pink = Lyft. Priority: 2026 segments with ≥1,000 valid waits in both years; ranked by excess against same-company airport/non-airport peers. Benchmark excess is not achievable reduction.'},
 {'name':'3 Growth Drivers and Decision','sheets':[x['name'] for x in SPECS[8:]],'note':'Decision: investigate late-night LaGuardia pickup operations before a pilot. Fixed-mix results have limited coverage and are descriptive. Base fares are not platform revenue. No pilot impact or ROI measured.'}]
def el(parent,tag,text=None,**attrs):
    child=E.SubElement(parent,tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})
    if text is not None:child.text=text
    return child
w=E.Element('workbook',{'source-build':'2024.1.0','source-platform':'mac','version':'18.1'})
el(w,'preferences');sources=el(w,'datasources');sourceinfo={}
with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU,parameters={'log_dir':str(R/'reports')}) as proc:
    for name in SOURCE_NAMES:
        path=R/'tableau'/f'{name}.csv'
        with path.open() as f:
            reader=csv.DictReader(f);headers=reader.fieldnames;raw=list(reader)
        def infer(n):
            vals=[r[n] for r in raw if r[n]!='']
            if n in DIMENSIONS and n not in {'year','pickup_zone_id','dropoff_zone_id','pickup_hour','trip_day'}:return 'string'
            try:
                for v in vals:int(v)
                return 'integer'
            except ValueError:
                try:
                    for v in vals:float(v)
                    return 'real'
                except ValueError:return 'string'
        types={n:infer(n) for n in headers}
        d=el(sources,'datasource',caption=name,inline='true',name=name,version='18.1')
        c=el(d,'connection',**{'class':'textscan','directory':'Data','filename':f'{name}.csv','password':'','server':''})
        rel=el(c,'relation',name=f'{name}.csv',table=f'[{name}#csv]',type='table')
        cols=el(rel,'columns',character_set='UTF-8',header='yes',locale='en_US',separator=',')
        el(d,'aliases',enabled='yes');definitions={}
        for i,n in enumerate(headers):
            el(cols,'column',datatype=types[n],name=n,ordinal=i)
            dim=n in DIMENSIONS
            a=dict(caption=n.replace('_',' ').title(),datatype=types[n],name=f'[{n}]',role='dimension' if dim else 'measure',type='nominal' if dim else 'quantitative')
            if n in ['trip_share','matched_coverage','long_wait_rate','peer_long_wait_rate','prior_long_wait_rate','company_long_wait_rate']:a['default-format']='p0.0%'
            elif any(t in n for t in ['fare','usd']) and 'valid' not in n:a['default-format']='c"$"#,##0.00'
            elif types[n]=='integer':a['default-format']='n#,##0'
            elif types[n]=='real':a['default-format']='n#,##0.00'
            definitions[n]=el(d,'column',**a)
        for n,(caption,formula,required,fmt) in CALCS.items():
            if not all(k in headers for k in required):continue
            col=el(d,'column',caption=caption,datatype='real',name=f'[{n}]',role='measure',type='quantitative',default_format=fmt)
            el(col,'calculation',**{'class':'tableau','formula':formula});definitions[n]=col
        hp=R/'tableau'/f'{name}.hyper'
        sq={'string':SqlType.text(),'integer':SqlType.big_int(),'real':SqlType.double()}
        td=TableDefinition(TableName('Extract','Extract'),[TableDefinition.Column(n,sq[types[n]]) for n in headers])
        converted=[[None if r[n]=='' else r[n] if types[n]=='string' else int(r[n]) if types[n]=='integer' else float(r[n]) for n in headers] for r in raw]
        with Connection(proc.endpoint,str(hp),CreateMode.CREATE_AND_REPLACE) as hc:
            hc.catalog.create_schema('Extract');hc.catalog.create_table(td)
            with Inserter(hc,td) as ins:ins.add_rows(converted);ins.execute()
            assert hc.execute_scalar_query('SELECT COUNT(*) FROM "Extract"."Extract"')==len(raw)
            if name in ['overview','daily','segments']:
                assert hc.execute_scalar_query('SELECT SUM("trips") FROM "Extract"."Extract"')==39764941
        ex=el(d,'extract',count='-1',enabled='true',units='records')
        ec=el(ex,'connection',**{'class':'hyper','dbname':f'Data/{name}.hyper','schema':'Extract','tablename':'Extract','access_mode':'readonly','default-settings':'hyper','username':'tableau_internal_user','password':'','server':''})
        el(ec,'relation',name='Extract',table='[Extract].[Extract]',type='table')
        sourceinfo[name]={'definitions':definitions,'rows':len(raw),'fields':headers,'types':types}
worksheets=el(w,'worksheets')
for s in SPECS:
    name=s['source'];info=sourceinfo[name]
    ws=el(worksheets,'worksheet',name=s['name'])
    ft=el(el(el(ws,'layout-options'),'title'),'formatted-text');el(ft,'run',s['title'],fontsize='13',bold='true')
    t=el(ws,'table');view=el(t,'view');el(el(view,'datasources'),'datasource',caption=name,name=name)
    dep=el(view,'datasource-dependencies',datasource=name)
    for col in info['definitions'].values():dep.append(copy.deepcopy(col))
    refs={}
    for n in set(s['dims']+['company',s['metric']]+([s['x']] if 'x' in s else [])):
        isx=n==s.get('x');dim=n in DIMENSIONS;iscalc=n.startswith('calc_')
        der='None' if dim else 'User' if iscalc else 'Sum'
        suffix='qk' if isx or not dim else 'nk';typ='quantitative' if suffix=='qk' else 'nominal'
        prefix='none' if dim else 'usr' if iscalc else 'sum'
        inst=f'[{prefix}:{n}:{suffix}]'
        el(dep,'column-instance',column=f'[{n}]',derivation=der,name=inst,pivot='key',type=typ)
        refs[n]=f'[{name}].{inst}'
    el(view,'aggregation',value='true')
    style=el(t,'style');rule=el(style,'style-rule',element='mark')
    # Fixed semantic colors; never allow automatic palette reassignment.
    encoding=el(rule,'encoding',attr='color',field='[none:company:nk]',type='palette')
    for co,color in COLORS.items():el(el(encoding,'map',to=color),'bucket',f'"{co}"')
    el(rule,'format',attr='mark-labels-show',value='false' if s.get('mark')=='Line' else 'true')
    if s.get('mark')=='Line':
        a=el(style,'style-rule',element='axis');el(a,'format',attr='title',field=refs[s['x']],scope='cols',value='Day of August' if s['x']=='trip_day' else 'Pickup hour (NYC local time)')
    pane=el(el(t,'panes'),'pane',selection_relaxation_option='selection-relaxation-allow')
    el(el(pane,'view'),'breakdown',value='auto');el(pane,'mark',**{'class':s.get('mark','Bar')})
    enc=el(pane,'encodings');el(enc,'color',column=refs['company'])
    rows=[refs[n] for n in s['dims']]
    if 'x' in s:rows.append(refs[s['metric']]);cols_expr=refs[s['x']]
    else:cols_expr=refs[s['metric']]
    el(t,'rows','('+' / '.join(rows)+')' if len(rows)>1 else rows[0]);el(t,'cols',cols_expr)
dashboards=el(w,'dashboards')
for ds in DASHES:
    dash=el(dashboards,'dashboard',name=ds['name'])
    ft=el(el(el(dash,'layout-options'),'title'),'formatted-text');el(ft,'run',ds['name']+' | NYC Ride-Hailing',fontsize='20',bold='true')
    el(dash,'style');el(dash,'size',maxheight='1100',maxwidth='1560',minheight='1100',minwidth='1560')
    root=el(el(dash,'zones'),'zone',h='100000',id='0',type_v2='layout-basic',w='100000',x='0',y='0')
    el(root,'zone',h='6000',id='1',type_v2='title',w='98000',x='1000',y='1000')
    for i,sheet in enumerate(ds['sheets']):
        el(root,'zone',h='40000',id=str(i+2),name=sheet,w='48000',x=str(1000+(i%2)*50000),y=str(8000+(i//2)*42000))
    ft=el(el(root,'zone',h='7500',id='8',type_v2='text',w='98000',x='1000',y='92000'),'formatted-text')
    el(ft,'run','BLACK = UBER | PINK = LYFT. Source: NYC TLC, August 2025 & 2026. '+ds['note'],fontsize='10')
windows=el(w,'windows',source_height='72')
for s in SPECS:
    win=el(windows,'window',**{'class':'worksheet','name':s['name']});el(win,'cards');el(el(win,'viewpoint'),'zoom',type='entire-view')
for ds in DASHES:
    win=el(windows,'window',**{'class':'dashboard','maximized':'true','name':ds['name']})
    viewpoints=el(win,'viewpoints')
    for name in ds['sheets']:el(el(viewpoints,'viewpoint',name=name),'zoom',type='entire-view')
    el(win,'active',id='-1');el(el(win,'device-preview'),'device',is_portrait='false',name='Generic Desktop',type='Desktop')
E.indent(w);xml=E.tostring(w,encoding='utf-8',xml_declaration=True)
out=R/'tableau/NYC_Ridehail_Three_Dashboards.twbx'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('NYC_Ridehail.twb',xml)
    for source in SOURCE_NAMES:
        for ext in ['hyper']:z.write(R/'tableau'/f'{source}.{ext}',f'Data/{source}.{ext}')
manifest={'workbook':out.name,'palette':COLORS,'dashboards':DASHES,'worksheets':SPECS,'sources':{n:{'csv':n+'.csv','hyper':n+'.hyper','row_count':v['rows'],'fields':v['fields'],'calculated_fields':{k:val[1] for k,val in CALCS.items() if k in v['definitions']}} for n,v in sourceinfo.items()}}
(R/'tableau/workbook_manifest.json').write_text(json.dumps(manifest,indent=2))
lines=['# Actual workbook worksheet map','','Generated from the same configuration as NYC_Ridehail_Three_Dashboards.twbx.','','| Dashboard | Worksheet | CSV / embedded extract | Measure | Calculation |','|---|---|---|---|---|']
for ds in DASHES:
    for sheet in ds['sheets']:
        s=next(x for x in SPECS if x['name']==sheet);calc=CALCS[s['metric']][1] if s['metric'] in CALCS else 'SQL-precomputed; SUM at displayed source grain'
        lines.append(f"| {ds['name']} | {sheet} | {s['source']}.csv / .hyper | {s['metric']} | {calc} |")
lines+=['','Each CSV is a separate source. No physical joins or relationships multiply aggregate rows. All extracts are embedded. Both companies are explicitly labeled and use fixed colors. The workbook has selection/highlight and native tooltips, but no custom cross-dashboard filters or drill-through actions.','', '## Export roles','', '| CSV | Role |','|---|---|']
for p in sorted((R/'tableau').glob('*.csv')):lines.append(f"| {p.name} | {'Workbook input' if p.stem in SOURCE_NAMES else 'Audit / supporting analysis; not connected to a worksheet'} |")
(R/'tableau/WORKSHEET_MAP.md').write_text('\n'.join(lines)+'\n')
print(out);print('3 dashboards / 12 worksheets / 6 embedded extracts; source counts:',{n:v['rows'] for n,v in sourceinfo.items()})

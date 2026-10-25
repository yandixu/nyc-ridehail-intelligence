from pathlib import Path
import json,csv,base64,html
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
R=Path(__file__).resolve().parent
load=lambda n:json.loads((R/'reports'/n).read_text())
ov=load('overview.json'); std=load('standardized.json'); ops=load('top_opportunities.json'); qa=load('validation.json')
lookup={(x['company'],x['year']):x for x in ov}
colors={'Uber':'#000000','Lyft':'#FF00BF'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,2,figsize=(13,8.3),layout='constrained')
fig.patch.set_facecolor('#f5f7fa')
fig.suptitle('NYC ride-hailing | Growth came with longer pickup waits',fontsize=19,fontweight='bold',x=.03,ha='left')
for j,co in enumerate(['Uber','Lyft']):
    for k,y in enumerate([2025,2026]):
        r=lookup[co,y]; xpos=j+(k-.5)*.32
        axs[0,0].bar(xpos,r['trips']/1e6,width=.29,color=colors[co],alpha=.45 if k==0 else 1)
        axs[0,0].text(xpos,r['trips']/1e6+.2,f"{r['trips']/1e6:.2f}M",ha='center',fontsize=9)
        axs[0,1].bar(xpos,r['long_wait_rate'],width=.29,color=colors[co],alpha=.45 if k==0 else 1)
        axs[0,1].text(xpos,r['long_wait_rate']+.002,f"{r['long_wait_rate']:.1%}",ha='center',fontsize=9)
for ax in axs[0]:ax.set_xticks([0,1],['Uber','Lyft']);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
axs[0,0].set(title='Reported trips grew mainly at Uber',ylabel='Trips, millions',ylim=(0,17))
axs[0,1].set(title='More reported trips waited over 10 minutes',ylabel='Share of valid pickup waits',ylim=(0,.14));axs[0,1].yaxis.set_major_formatter(PercentFormatter(1))
axs[0,0].text(.02,.94,'Light = Aug 2025   Dark = Aug 2026',transform=axs[0,0].transAxes,fontsize=9,color='#54606e')
for i,s in enumerate(sorted(std,key=lambda x:x['company'],reverse=True)):
    co=s['company']; axs[1,0].plot([s['fixed_mix_wait_2025'],s['fixed_mix_wait_2026']],[i,i],color=colors[co],lw=3)
    axs[1,0].scatter([s['fixed_mix_wait_2025']],[i],color='white',edgecolors=colors[co],s=90,zorder=3)
    axs[1,0].scatter([s['fixed_mix_wait_2026']],[i],color=colors[co],s=90,zorder=3)
    axs[1,0].text(s['fixed_mix_wait_2026']+.03,i,f"+{s['fixed_mix_wait_2026']-s['fixed_mix_wait_2025']:.2f} min",va='center')
axs[1,0].set(yticks=[0,1],yticklabels=['Uber','Lyft'],title='Wait increase persists within matched trip cells',xlabel='Mean pickup wait, minutes',xlim=(3.8,6.1),ylim=(-.6,1.6))
axs[1,0].text(.01,.02,'Fixed 2025 mix; limited matched coverage. Open = 2025.',transform=axs[1,0].transAxes,fontsize=9,color='#54606e')
top=[x for x in ops if x['company']=='Uber' and x['priority_rank']<=5][::-1]
axs[1,1].barh([f"{x['pickup_zone'].replace(' Airport','')} · {x['pickup_hour']:02d}:00" for x in top],[x['peer_excess_long_wait_trips'] for x in top],color=colors['Uber'])
axs[1,1].set(title='Uber: late-night airport burden warrants investigation',xlabel='Long waits above airport-peer benchmark, count')
fig.text(.03,-.025,'Source: NYC TLC HVFHV, August 2025 and 2026. Reported trips only. Wait valid range 0–60 min. Descriptive comparisons; no causal or profit claims.',fontsize=9,color='#54606e')
fig.savefig(R/'reports/visual_summary.png',dpi=160,bbox_inches='tight');plt.close(fig)

table=['| Company | Trips 2025 → 2026 | Trip growth | Trip-share change | Mean base fare 2025 → 2026 | >10-min waits 2025 → 2026 |','|---|---:|---:|---:|---:|---:|']
for co in ['Uber','Lyft']:
    a,b=lookup[co,2025],lookup[co,2026]
    table.append(f"| {co} | {a['trips']:,} → {b['trips']:,} | {b['trips']/a['trips']-1:+.2%} | {(b['trip_share']-a['trip_share'])*100:+.2f} pp | ${a['avg_base_fare']:.2f} → ${b['avg_base_fare']:.2f} | {a['long_wait_rate']:.2%} → {b['long_wait_rate']:.2%} |")
matched=[]
for s in std:
    co=s['company'];matched.append(f"- **{co}:** fixed-mix mean fare changed {s['fixed_mix_fare_2026']/s['fixed_mix_fare_2025']-1:+.2%}; mean pickup wait increased {s['fixed_mix_wait_2026']-s['fixed_mix_wait_2025']:.2f} minutes. Matched coverage is {s['matched_trips_2025']/lookup[co,2025]['trips']:.1%} of 2025 and {s['matched_trips_2026']/lookup[co,2026]['trips']:.1%} of 2026 reported trips. These are within-company subsets, not directly comparable company pricing baskets.")
case='''# NYC Ride-Hailing Marketplace Intelligence

## Decision brief

**Prioritize investigation of late-night airport pickup operations while monitoring growth and rider/driver economics.** Uber gained reported-trip share but experienced a substantial increase in pickup delays. Lyft's reported volume was nearly flat despite higher mean base fares. Evidence supports a focused investigation and pilot proposal; it does not establish that driver shortages, pricing changes, or dispatch logic caused the delays.

This independent portfolio project analyzes **39,764,941 actual reported trips** across two complete months: August 2025 and August 2026. The latest month listed when sourced was August 2026. Geography is the NYC TLC reporting system, including some pickups outside the five boroughs; do not describe results as global Uber/Lyft performance.

## Commercial questions

1. Is growth coming from reported trip volume or higher average fare/mix?
2. Is service experience keeping pace with activity?
3. Which zone-hour segments justify operational investigation first?
4. Do headline changes persist when observed trip mix is held more constant?

## Results

'''+ '\n'.join(table)+ '\n\n'+'''Uber's valid base-fare total grew by **$37.31M**. The additive bridge attributes $33.79M to fare-valid volume, $3.22M to mean fare/mix, and $0.30M to their interaction. Lyft's total grew **$5.03M** despite a negative volume contribution (−$0.49M); mean fare/mix contributed $5.53M and interaction −$0.02M. These totals are base passenger fares, not company revenue or margin.

The stronger commercial interpretation is that Uber's activity growth coincided with service deterioration, while Lyft's higher mean fare did not coincide with volume growth. There is no evidence here to conclude that price changes caused demand changes. Uber's mean fare rose only 0.9% while its median was essentially flat; Lyft's mean rose 3.9% while its median was also nearly flat. Distribution and trip mix therefore deserve attention before attributing the headline change to broad price increases.

## Mix adjustment and robustness

'''+ '\n'.join(matched)+ '\n\n'+'''Cells match exact origin/destination zones, pickup hour, weekday/weekend, and distance band, require ≥100 unpooled valid observations in each year, and use fixed 2025 weights. This is descriptive standardization. It does not control all ride characteristics and covers a minority of trips. The direction of pickup-wait deterioration persists in both companies' matched subsets.

Primary mean fares retain long positive outliers; the ≤$500 sensitivity mean differs by less than five cents in every company/month. Extending the wait cap from 60 to 120 minutes leaves the direction of year-over-year deterioration unchanged. Negative waits are excluded and reported, not silently corrected. See validation.json and sensitivity.json for counts/results.

## Priority opportunity

For Uber, LaGuardia weekday pickups at **23:00–23:59** have 15,477 reported trips, 15,471 valid waits, and a **55.1%** long-wait rate, versus a **25.5%** same-company airport-peer baseline. This is roughly **4,571 long waits above the benchmark** in the month. For Lyft, the top segment is LaGuardia weekdays at **00:00–00:59**, with a 55.1% long-wait rate versus a 22.7% airport-peer baseline.

The peer benchmark separates airport/non-airport trips to reduce the obvious structural mismatch of comparing airport pickups with all city rides. It remains descriptive: airport, hour, route and operating conditions differ. Benchmark excess is not the number of delays that can be eliminated. The scoring rule uses ≥1,000 valid waits in both years, excludes tiny volatile segments, and ranks burden rather than the highest percentage alone. The full shortlist is in tableau/opportunities.csv.

## Recommended business action

**Stage 1 — diagnose.** Ask airport operations for driver queue length, dispatch acceptance, rider cancellations, driver online/idle time, flight-arrival patterns, pickup-location changes and incentive spending. Determine whether the bottleneck is airport access, queue management, driver participation, passenger readiness or dispatch. None of those causes is established by public trip data.

**Stage 2 — propose a constrained pilot.** If diagnosis indicates a controllable queue/dispatch issue, test a targeted operational change at LaGuardia late-night windows before considering broad subsidies or price changes. Use an airport/time-window switchback design rather than rider-level randomization because drivers and queues create spillovers. Plan washout periods and monitor neighboring times/zones. This design is proposed, not executed.

**Success metric:** long-wait rate among all eligible requests if internal data is available, alongside completion and cancellation rates. Public-data follow-up can monitor completed-trip waits only and must acknowledge selection bias. Guardrails: p90 wait, adjacent-zone service, rider price for comparable trips, driver net earnings including idle time, incentive cost per incremental completed trip, and access needs. Predefine a minimum worthwhile change and budget with operations; estimate sample size from internal request data and cluster variation. Do not invent an ROI or claim an achieved improvement.

## Data, workflow and validation

Official source: [NYC TLC trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), [HVFHV dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_hvfhs.pdf), and official taxi-zone lookup. Inputs downloaded October 25, 2026; URLs, byte sizes and SHA-256 hashes are recorded in reports/source_manifest.json. TLC notes that reported data may be inaccurate or incomplete.

Workflow actually executed: immutable Parquet inputs → DuckDB SQL trip model and zone join → metric-specific validity rules → daily/segment aggregates → fixed-mix comparison and growth bridge → reconciliation checks → CSV exports and Python visual report. SQL uses CTEs, joins, conditional aggregates, exact quantiles and window functions. Python orchestrates execution, hashing and chart/report generation.

Checks passed: 31 dates per company/month, raw/model row reconciliation, unique lookup keys, trip shares sum to one, daily/segment counts reconcile, and additive growth bridge reconciles within $0.10. These tests verify internal consistency, not source completeness. No customer or driver IDs exist, so retention, churn, unique riders, utilization, experiment effects, platform take rate and net profit cannot be calculated.

## Portfolio positioning

This project extends an Applied Data Scientist profile through business metric design, reproducible SQL pipelines, validation, analytical adjustment and operational decision support. It does not replace existing AI/ML or healthcare expertise. Explain the transition as transferring evidence discipline to commercial questions, then learning the company's marketplace economics.
'''
(R/'reports/CASE_STUDY.md').write_text(case)
encoded=base64.b64encode((R/'reports/visual_summary.png').read_bytes()).decode()
payload=json.dumps({'overview':ov,'opportunities':ops,'standardized':std})
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NYC Ride-Hailing Intelligence</title>
<style>body{margin:0;background:#f3f6fa;color:#172b43;font:16px system-ui}main{max-width:1180px;margin:36px auto;padding:24px}h1{font-size:36px;letter-spacing:-1px;margin-bottom:6px}.sub{color:#56677c}section{background:white;border-radius:14px;padding:24px;margin:22px 0;box-shadow:0 4px 20px #11223308}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{padding:18px;background:#edf5f8;border-radius:10px}.value{font-size:27px;font-weight:700;margin:8px 0}select{font:inherit;padding:8px 16px;margin:12px 12px 12px 0}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;border-bottom:1px solid #dde5ed;text-align:left}th{color:#57687c}img{width:100%;height:auto}small{color:#56677c}.scroll{overflow:auto}@media(max-width:700px){.cards{grid-template-columns:1fr 1fr}main{padding:12px}h1{font-size:28px}}</style>
<main><p class="sub">INDEPENDENT PORTFOLIO PROJECT · AUGUST 2025 VS AUGUST 2026</p><h1>Growth needs reliable pickups</h1><p>Marketplace intelligence from 39.8 million reported Uber and Lyft trips.</p>
<section><label>Company <select id="company"><option>Uber</option><option>Lyft</option></select></label><label>Period <select id="year"><option>2026</option><option>2025</option></select></label><div class="cards" id="cards"></div><p id="interpretation"></p><small>Shares cover reported Uber/Lyft trips in the source files. Base fares are not platform revenue. Waits include valid 0–60 minute request-to-pickup intervals.</small></section>
<section><h2>The growth–service tradeoff</h2><p class="sub">This comparison chart always shows both years and both companies; selectors above change the KPI cards and shortlist below.</p><img alt="Trips, long-wait rates, matched waits and airport opportunity burden" src="data:image/png;base64,ENCODED"></section>
<section><h2>Where to investigate first</h2><p>Top five eligible zone-hour segments for the selected company in August 2026. Ranked against same-company airport/non-airport peers.</p><div class="scroll"><table><thead><tr><th>Rank</th><th>Pickup zone</th><th>Window</th><th>Trips</th><th>Long waits</th><th>Peer rate</th><th>Above peer, count</th></tr></thead><tbody id="ops"></tbody></table></div><small>Minimum 1,000 valid waits in both years. Benchmark excess is descriptive, not achievable reduction or ROI. The period selector does not change this 2026 shortlist.</small></section>
<section><h2>Decision: diagnose late-night airport operations</h2><p>Inspect queues, driver availability, dispatch acceptance and pickup access before funding a targeted operational pilot. Track wait improvements alongside cancellations, comparable rider prices, driver net earnings and incentive costs.</p><p><strong>Evidence boundary:</strong> these trip records do not establish lost demand, causal pricing effects, customer retention, company revenue or profit.</p><h3>Matched-trip check</h3><div id="matched"></div><small>Fixed 2025 weights over matched unpooled route × day type × hour × distance-band cells, ≥100 observations each year. Limited coverage; no causal interpretation.</small></section>
<footer><p>Source: <a href="https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page">NYC TLC official trip records</a> · Downloaded October 25, 2026. Local HTML report generated using Python; this is not a Tableau workbook.</p></footer></main>
<script>const data=PAYLOAD;const money=x=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(x);const pct=x=>(100*x).toFixed(2)+'%';function render(){let co=document.querySelector('#company').value,y=+document.querySelector('#year').value,r=data.overview.find(x=>x.company===co&&x.year===y),a=data.overview.find(x=>x.company===co&&x.year===2025),b=data.overview.find(x=>x.company===co&&x.year===2026);document.querySelector('#cards').innerHTML=[['Reported trips',r.trips.toLocaleString()],['Trip share',pct(r.trip_share)],['Mean base fare',money(r.avg_base_fare)],['Waits over 10 min',pct(r.long_wait_rate)]].map(([label,val])=>`<div class="card">${label}<div class="value">${val}</div></div>`).join('');document.querySelector('#interpretation').textContent=`${co}: reported trips changed ${pct(b.trips/a.trips-1)} year over year; long-wait rate changed ${((b.long_wait_rate-a.long_wait_rate)*100).toFixed(2)} percentage points.`;document.querySelector('#ops').innerHTML=data.opportunities.filter(x=>x.company===co&&x.priority_rank<=5).map(x=>`<tr><td>${x.priority_rank}</td><td>${x.pickup_zone}</td><td>${x.day_type} ${String(x.pickup_hour).padStart(2,'0')}:00</td><td>${x.trips.toLocaleString()}</td><td>${pct(x.long_wait_rate)}</td><td>${pct(x.peer_long_wait_rate)}</td><td>${Math.round(x.peer_excess_long_wait_trips).toLocaleString()}</td></tr>`).join('');let s=data.standardized.find(x=>x.company===co);document.querySelector('#matched').textContent=`${co}: mean wait ${s.fixed_mix_wait_2025.toFixed(2)} → ${s.fixed_mix_wait_2026.toFixed(2)} min. Mean fare ${money(s.fixed_mix_fare_2025)} → ${money(s.fixed_mix_fare_2026)}. Coverage: ${pct(s.matched_trips_2025/a.trips)} of 2025 and ${pct(s.matched_trips_2026/b.trips)} of 2026 trips.`;}document.querySelectorAll('select').forEach(el=>el.addEventListener('change',render));render();</script></html>'''.replace('ENCODED',encoded).replace('PAYLOAD',payload)
(R/'reports/dashboard.html').write_text(page)
print('Report, chart and local interactive dashboard generated.')

# NYC Ride-Hailing Marketplace Intelligence

## Decision brief

**Prioritize investigation of late-night airport pickup operations while monitoring growth and rider/driver economics.** Uber gained reported-trip share but experienced a substantial increase in pickup delays. Lyft's reported volume was nearly flat despite higher mean base fares. Evidence supports a focused investigation and pilot proposal; it does not establish that driver shortages, pricing changes, or dispatch logic caused the delays.

This independent portfolio project analyzes **39,764,941 actual reported trips** across two complete months: August 2025 and August 2026. The latest month listed when sourced was August 2026. Geography is the NYC TLC reporting system, including some pickups outside the five boroughs; do not describe results as global Uber/Lyft performance.

## Commercial questions

1. Is growth coming from reported trip volume or higher average fare/mix?
2. Is service experience keeping pace with activity?
3. Which zone-hour segments justify operational investigation first?
4. Do headline changes persist when observed trip mix is held more constant?

## Results

| Company | Trips 2025 → 2026 | Trip growth | Trip-share change | Mean base fare 2025 → 2026 | >10-min waits 2025 → 2026 |
|---|---:|---:|---:|---:|---:|
| Uber | 13,558,357 → 14,800,058 | +9.16% | +1.86 pp | $27.22 → $27.46 | 5.00% → 11.64% |
| Lyft | 5,713,104 → 5,693,422 | -0.34% | -1.86 pp | $24.69 → $25.66 | 4.34% → 6.47% |

Uber's valid base-fare total grew by **$37.31M**. The additive bridge attributes $33.79M to fare-valid volume, $3.22M to mean fare/mix, and $0.30M to their interaction. Lyft's total grew **$5.03M** despite a negative volume contribution (−$0.49M); mean fare/mix contributed $5.53M and interaction −$0.02M. These totals are base passenger fares, not company revenue or margin.

The stronger commercial interpretation is that Uber's activity growth coincided with service deterioration, while Lyft's higher mean fare did not coincide with volume growth. There is no evidence here to conclude that price changes caused demand changes. Uber's mean fare rose only 0.9% while its median was essentially flat; Lyft's mean rose 3.9% while its median was also nearly flat. Distribution and trip mix therefore deserve attention before attributing the headline change to broad price increases.

## Mix adjustment and robustness

- **Lyft:** fixed-mix mean fare changed +10.09%; mean pickup wait increased 0.69 minutes. Matched coverage is 5.3% of 2025 and 6.0% of 2026 reported trips. These are within-company subsets, not directly comparable company pricing baskets.
- **Uber:** fixed-mix mean fare changed +1.15%; mean pickup wait increased 0.76 minutes. Matched coverage is 16.0% of 2025 and 16.8% of 2026 reported trips. These are within-company subsets, not directly comparable company pricing baskets.

Cells match exact origin/destination zones, pickup hour, weekday/weekend, and distance band, require ≥100 unpooled valid observations in each year, and use fixed 2025 weights. This is descriptive standardization. It does not control all ride characteristics and covers a minority of trips. The direction of pickup-wait deterioration persists in both companies' matched subsets.

Primary mean fares retain long positive outliers; the ≤$500 sensitivity mean differs by less than five cents in every company/month. Extending the wait cap from 60 to 120 minutes leaves the direction of year-over-year deterioration unchanged. Negative waits are excluded and reported, not silently corrected. The rebuild generates local validation and sensitivity outputs with the detailed counts. These data exports are intentionally not versioned here.

## Priority opportunity

For Uber, LaGuardia weekday pickups at **23:00–23:59** have 15,477 reported trips, 15,471 valid waits, and a **55.1%** long-wait rate, versus a **25.5%** same-company airport-peer baseline. This is roughly **4,571 long waits above the benchmark** in the month. For Lyft, the top segment is LaGuardia weekdays at **00:00–00:59**, with a 55.1% long-wait rate versus a 22.7% airport-peer baseline.

The peer benchmark separates airport/non-airport trips to reduce the obvious structural mismatch of comparing airport pickups with all city rides. It remains descriptive: airport, hour, route and operating conditions differ. Benchmark excess is not the number of delays that can be eliminated. The scoring rule uses ≥1,000 valid waits in both years, excludes tiny volatile segments, and ranks burden rather than the highest percentage alone. The rebuild generates the full shortlist locally; the Tableau dashboard includes its top 10 segments per company.

## Recommended business action

**Stage 1 — diagnose.** Ask airport operations for driver queue length, dispatch acceptance, rider cancellations, driver online/idle time, flight-arrival patterns, pickup-location changes and incentive spending. Determine whether the bottleneck is airport access, queue management, driver participation, passenger readiness or dispatch. None of those causes is established by public trip data.

**Stage 2 — propose a constrained pilot.** If diagnosis indicates a controllable queue/dispatch issue, test a targeted operational change at LaGuardia late-night windows before considering broad subsidies or price changes. Use an airport/time-window switchback design rather than rider-level randomization because drivers and queues create spillovers. Plan washout periods and monitor neighboring times/zones. This design is proposed, not executed.

**Success metric:** long-wait rate among all eligible requests if internal data is available, alongside completion and cancellation rates. Public-data follow-up can monitor completed-trip waits only and must acknowledge selection bias. Guardrails: p90 wait, adjacent-zone service, rider price for comparable trips, driver net earnings including idle time, incentive cost per incremental completed trip, and access needs. Predefine a minimum worthwhile change and budget with operations; estimate sample size from internal request data and cluster variation. Do not invent an ROI or claim an achieved improvement.

## Data, workflow and validation

Official source: [NYC TLC trip records](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), [HVFHV dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_hvfhs.pdf), and official taxi-zone lookup. Inputs downloaded October 25, 2026; URLs, byte sizes and SHA-256 hashes are recorded in reports/source_manifest.json. TLC notes that reported data may be inaccurate or incomplete.

Workflow actually executed: immutable Parquet inputs → DuckDB SQL trip model and zone join → metric-specific validity rules → daily/segment aggregates → fixed-mix comparison and growth bridge → reconciliation checks → CSV exports and Python visual report. SQL uses CTEs, joins, conditional aggregates, exact quantiles and window functions. Python orchestrates execution, hashing and chart/report generation.

Checks passed: 31 dates per company/month, raw/model row reconciliation, unique lookup keys, trip shares sum to one, daily/segment counts reconcile, and additive growth bridge reconciles within $0.10. These tests verify internal consistency, not source completeness. No customer or driver IDs exist, so retention, churn, unique riders, utilization, experiment effects, platform take rate and net profit cannot be calculated.


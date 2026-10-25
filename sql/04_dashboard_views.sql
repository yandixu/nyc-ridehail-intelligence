-- Presentation views preserve explicit lineage to the validated analytical tables.
-- They do not change the analysis or re-filter raw trips.
CREATE OR REPLACE TABLE growth_components AS
SELECT company,'1 Volume' component,volume_effect contribution_usd FROM growth_bridge
UNION ALL SELECT company,'2 Fare and mix',fare_mix_effect FROM growth_bridge
UNION ALL SELECT company,'3 Interaction',interaction_effect FROM growth_bridge;

CREATE OR REPLACE TABLE matched_comparison AS
SELECT s.company,2025 AS year,s.fixed_mix_fare_2025 fixed_mix_fare,
 s.fixed_mix_wait_2025 fixed_mix_wait,s.matched_trips_2025 matched_trips,
 o.trips all_reported_trips,s.matched_trips_2025::DOUBLE/o.trips matched_coverage
FROM standardized s JOIN overview o ON s.company=o.company AND o.year=2025
UNION ALL
SELECT s.company,2026,s.fixed_mix_fare_2026,s.fixed_mix_wait_2026,s.matched_trips_2026,
 o.trips,s.matched_trips_2026::DOUBLE/o.trips
FROM standardized s JOIN overview o ON s.company=o.company AND o.year=2026;

CREATE OR REPLACE TABLE priority_shortlist AS
SELECT *,lpad(priority_rank::VARCHAR,2,'0')||' | '||pickup_zone||' | '||day_type||' '||
 lpad(pickup_hour::VARCHAR,2,'0')||':00' priority_label
FROM opportunities WHERE priority_rank<=10;

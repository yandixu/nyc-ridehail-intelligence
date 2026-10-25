CREATE OR REPLACE TABLE overview AS
SELECT year,company,count(*) trips,
  count(*)::DOUBLE/sum(count(*)) OVER(PARTITION BY year) trip_share,
  count(wait_minutes) wait_valid_n, avg(wait_minutes) avg_wait_minutes,
  quantile_cont(wait_minutes,.5) median_wait_minutes,
  quantile_cont(wait_minutes,.9) p90_wait_minutes,
  count(*) FILTER(WHERE wait_minutes>10) long_wait_trips,
  count(*) FILTER(WHERE wait_minutes>10)::DOUBLE/nullif(count(wait_minutes),0) long_wait_rate,
  count(valid_fare) fare_valid_n,sum(valid_fare) base_fare_total,avg(valid_fare) avg_base_fare,
  quantile_cont(valid_fare,.5) median_base_fare,
  avg(CASE WHEN fare BETWEEN 0 AND 500 THEN fare END) avg_fare_cap500_sensitivity,
  count(valid_driver_pay) pay_valid_n,sum(valid_driver_pay) driver_pay_total,
  avg(valid_driver_pay) avg_driver_pay,
  sum(CASE WHEN trip_minutes>0 AND valid_driver_pay IS NOT NULL THEN valid_driver_pay END)
    /nullif(sum(CASE WHEN trip_minutes>0 AND valid_driver_pay IS NOT NULL THEN trip_minutes END),0)*60
    driver_pay_per_engaged_hour,
  avg(CASE WHEN trip_miles>0 THEN trip_miles END) avg_miles,
  count(*) FILTER(WHERE shared_request_flag='Y') shared_requests,
  count(*) FILTER(WHERE shared_request_flag='Y' AND shared_match_flag='Y') shared_matches
FROM trips GROUP BY year,company;

CREATE OR REPLACE TABLE daily AS
SELECT year, company,trip_date,day(trip_date) trip_day,count(*) trips,count(wait_minutes) wait_valid_n,
 sum(wait_minutes) wait_minutes_sum,count(*) FILTER(WHERE wait_minutes>10) long_wait_trips,
 count(valid_fare) fare_valid_n,sum(valid_fare) base_fare_total
FROM trips GROUP BY ALL;

CREATE OR REPLACE TABLE segments AS
SELECT year,company,borough,pickup_zone_id,pickup_zone,day_type,pickup_hour,count(*) trips,
 count(wait_minutes) wait_valid_n,sum(wait_minutes) wait_minutes_sum,
 count(*) FILTER(WHERE wait_minutes>10) long_wait_trips,
 quantile_cont(wait_minutes,.9) p90_wait_minutes,
 count(valid_fare) fare_valid_n,sum(valid_fare) base_fare_total,
 count(valid_driver_pay) pay_valid_n,sum(valid_driver_pay) driver_pay_total
FROM trips GROUP BY ALL;

-- Matched, unpooled, same-company year comparisons. Fixed 2025 cell weights.
-- Exact route x hour x weekday/weekend x distance band; >=100 trips in each year.
CREATE OR REPLACE TABLE cells AS
SELECT year,company,pickup_zone_id,dropoff_zone_id,day_type,pickup_hour,distance_band,
 count(*) n,avg(valid_fare) avg_fare,avg(wait_minutes) avg_wait
FROM trips WHERE shared_request_flag='N' AND distance_band<>'Invalid'
  AND valid_fare IS NOT NULL AND wait_minutes IS NOT NULL
GROUP BY ALL;
CREATE OR REPLACE TABLE matched_cells AS
SELECT a.company,a.pickup_zone_id,a.dropoff_zone_id,a.day_type,a.pickup_hour,a.distance_band,
 a.n n_2025,b.n n_2026,a.avg_fare fare_2025,b.avg_fare fare_2026,
 a.avg_wait wait_2025,b.avg_wait wait_2026
FROM cells a JOIN cells b USING(company,pickup_zone_id,dropoff_zone_id,day_type,pickup_hour,distance_band)
WHERE a.year=2025 AND b.year=2026 AND a.n>=100 AND b.n>=100;
CREATE OR REPLACE TABLE standardized AS
SELECT company,count(*) matched_cells,sum(n_2025) matched_trips_2025,sum(n_2026) matched_trips_2026,
 sum(fare_2025*n_2025)/sum(n_2025) fixed_mix_fare_2025,
 sum(fare_2026*n_2025)/sum(n_2025) fixed_mix_fare_2026,
 sum(wait_2025*n_2025)/sum(n_2025) fixed_mix_wait_2025,
 sum(wait_2026*n_2025)/sum(n_2025) fixed_mix_wait_2026
FROM matched_cells GROUP BY company;

-- Descriptive prioritization, not a forecast of recovered demand or ROI.
CREATE OR REPLACE TABLE opportunities AS
WITH peer AS (
 SELECT company,CASE WHEN pickup_zone_id IN (1,132,138) THEN 'Airport' ELSE 'Other' END peer_group,
 sum(long_wait_trips)::DOUBLE/sum(wait_valid_n) peer_long_wait_rate
 FROM segments WHERE year=2026 GROUP BY ALL
), paired AS (
 SELECT b.*,a.trips prior_trips,a.long_wait_trips::DOUBLE/nullif(a.wait_valid_n,0) prior_long_wait_rate,
 b.long_wait_trips::DOUBLE/nullif(b.wait_valid_n,0) long_wait_rate,
 b.wait_minutes_sum/nullif(b.wait_valid_n,0) avg_wait_minutes,
 o.long_wait_rate company_long_wait_rate,p.peer_group,p.peer_long_wait_rate,
 greatest(0,b.long_wait_trips-b.wait_valid_n*p.peer_long_wait_rate) peer_excess_long_wait_trips,
 greatest(0,b.long_wait_trips-b.wait_valid_n*o.long_wait_rate) excess_long_wait_trips
 FROM segments b JOIN segments a USING(company,pickup_zone_id,day_type,pickup_hour)
 JOIN overview o ON b.company=o.company AND b.year=o.year
 JOIN peer p ON b.company=p.company AND p.peer_group=CASE WHEN b.pickup_zone_id IN (1,132,138) THEN 'Airport' ELSE 'Other' END
 WHERE b.year=2026 AND a.year=2025 AND b.wait_valid_n>=1000 AND a.wait_valid_n>=1000
)
SELECT *,dense_rank() OVER(PARTITION BY company ORDER BY peer_excess_long_wait_trips DESC) priority_rank
FROM paired;

CREATE OR REPLACE TABLE growth_bridge AS
SELECT b.company,a.trips trips_2025,b.trips trips_2026,
 (b.fare_valid_n-a.fare_valid_n)*a.avg_base_fare volume_effect,
 a.fare_valid_n*(b.avg_base_fare-a.avg_base_fare) fare_mix_effect,
 (b.fare_valid_n-a.fare_valid_n)*(b.avg_base_fare-a.avg_base_fare) interaction_effect,
 b.base_fare_total-a.base_fare_total actual_base_fare_change
FROM overview a JOIN overview b USING(company) WHERE a.year=2025 AND b.year=2026;

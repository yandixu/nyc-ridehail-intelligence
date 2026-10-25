-- DuckDB SQL. Run from project root after downloading official files.
CREATE OR REPLACE VIEW raw AS
SELECT *, regexp_extract(filename, '(202[56])-08', 1)::INTEGER AS year
FROM read_parquet('data/fhvhv_tripdata_202*-08.parquet', filename=true, union_by_name=true);

CREATE OR REPLACE TABLE zones AS SELECT * FROM read_csv('data/taxi_zone_lookup.csv', header=true);
CREATE OR REPLACE TABLE trips AS
SELECT r.year, CASE hvfhs_license_num WHEN 'HV0003' THEN 'Uber' ELSE 'Lyft' END company,
  pickup_datetime::DATE trip_date, hour(pickup_datetime) pickup_hour,
  CASE WHEN isodow(pickup_datetime) IN (6,7) THEN 'Weekend' ELSE 'Weekday' END day_type,
  PULocationID pickup_zone_id, DOLocationID dropoff_zone_id,
  coalesce(z.Borough,'Unknown') borough, coalesce(z.Zone,'Unknown') pickup_zone,
  trip_miles, trip_time / 60.0 trip_minutes,
  base_passenger_fare fare, driver_pay,
  date_diff('second',request_datetime,pickup_datetime)/60.0 wait_raw,
  CASE WHEN date_diff('second',request_datetime,pickup_datetime) BETWEEN 0 AND 3600
    THEN date_diff('second',request_datetime,pickup_datetime)/60.0 END wait_minutes,
  CASE WHEN base_passenger_fare >= 0 THEN base_passenger_fare END valid_fare,
  CASE WHEN driver_pay >= 0 THEN driver_pay END valid_driver_pay,
  CASE WHEN trip_miles > 0 AND trip_miles <= 2 THEN '0–2 mi'
       WHEN trip_miles <= 5 AND trip_miles > 2 THEN '2–5 mi'
       WHEN trip_miles <= 10 AND trip_miles > 5 THEN '5–10 mi'
       WHEN trip_miles > 10 THEN '10+ mi' ELSE 'Invalid' END distance_band,
  shared_request_flag, shared_match_flag
FROM raw r LEFT JOIN zones z ON r.PULocationID=z.LocationID
WHERE hvfhs_license_num IN ('HV0003','HV0005')
  AND pickup_datetime >= make_date(r.year,8,1)
  AND pickup_datetime < make_date(r.year,9,1);

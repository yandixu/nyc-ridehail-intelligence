CREATE OR REPLACE TABLE sensitivity AS
SELECT year,company,
 avg(CASE WHEN wait_raw BETWEEN 0 AND 120 THEN wait_raw END) avg_wait_cap120,
 count(*) FILTER(WHERE wait_raw>10 AND wait_raw<=120)::DOUBLE/
 nullif(count(*) FILTER(WHERE wait_raw BETWEEN 0 AND 120),0) long_wait_rate_cap120
FROM trips GROUP BY ALL;

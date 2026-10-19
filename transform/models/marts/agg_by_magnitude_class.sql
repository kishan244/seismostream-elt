{{ config(materialized='table') }}

select
    magnitude_class,
    count(*)                  as quake_count,
    round(avg(magnitude), 2)  as avg_magnitude,
    round(avg(depth_km), 1)   as avg_depth_km,
    sum(energy_joules)        as total_energy_joules
from {{ ref('stg_earthquakes') }}
group by 1
order by min(magnitude)

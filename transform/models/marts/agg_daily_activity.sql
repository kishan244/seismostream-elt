{{ config(materialized='table') }}

select
    occurred_at::date                              as activity_date,
    count(*)                                       as quake_count,
    round(max(magnitude), 1)                       as max_magnitude,
    round(avg(magnitude), 2)                       as avg_magnitude,
    sum(case when tsunami_flag then 1 else 0 end)  as tsunami_count,
    sum(energy_joules)                             as total_energy_joules
from {{ ref('stg_earthquakes') }}
group by 1
order by 1

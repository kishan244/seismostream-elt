{{ config(materialized='table') }}

select
    id,
    occurred_at,
    occurred_at::date  as occurred_date,
    magnitude,
    magnitude_class,
    energy_joules,
    place,
    latitude,
    longitude,
    depth_km,
    significance,
    tsunami_flag,
    alert,
    status
from {{ ref('stg_earthquakes') }}
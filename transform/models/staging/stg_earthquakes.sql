{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'earthquakes') }}
)

select
    id,
    cast(time as timestamp)        as occurred_at,
    cast(updated as timestamp)     as updated_at,
    mag                            as magnitude,
    mag_type,
    place,
    longitude,
    latitude,
    depth_km,
    significance,
    coalesce(tsunami, 0) = 1       as tsunami_flag,
    alert,
    status,
    felt,
    event_type,
    url,
    case
        when mag < 2 then 'micro'
        when mag < 4 then 'minor'
        when mag < 5 then 'light'
        when mag < 6 then 'moderate'
        when mag < 7 then 'strong'
        when mag < 8 then 'major'
        else 'great'
    end                            as magnitude_class,
    -- seismic energy in joules (Gutenberg-Richter: log10(E) = 1.5*M + 4.8)
    pow(10, 1.5 * mag + 4.8)       as energy_joules
from source
where mag is not null
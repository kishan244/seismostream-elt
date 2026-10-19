-- Returns any rows that are physically impossible. 0 rows = test passes.
select *
from {{ ref('stg_earthquakes') }}
where latitude  not between -90 and 90
   or longitude not between -180 and 180
   or magnitude < -1
   or magnitude > 10
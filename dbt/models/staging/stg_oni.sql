-- Vista sobre la tabla noaa_oni_mensual de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'noaa_oni_mensual') }}

-- Vista sobre la tabla ideam_estaciones de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'ideam_estaciones') }}

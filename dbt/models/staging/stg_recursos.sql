-- Vista sobre la tabla xm_recursos de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_recursos') }}

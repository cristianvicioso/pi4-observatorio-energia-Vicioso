-- Vista sobre la tabla divipola_municipios de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'divipola_municipios') }}

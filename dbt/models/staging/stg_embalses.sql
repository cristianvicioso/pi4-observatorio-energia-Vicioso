-- Vista sobre la tabla xm_embalses_diario de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_embalses_diario') }}

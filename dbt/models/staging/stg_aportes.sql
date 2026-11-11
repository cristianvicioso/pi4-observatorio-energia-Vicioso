-- Vista sobre la tabla xm_aportes_diario de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_aportes_diario') }}

-- Vista sobre la tabla xm_demanda_horaria de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_demanda_horaria') }}

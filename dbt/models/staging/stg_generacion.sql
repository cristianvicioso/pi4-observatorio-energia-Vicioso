-- Vista sobre la tabla xm_generacion_horaria de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_generacion_horaria') }}

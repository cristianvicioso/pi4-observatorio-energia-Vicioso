-- Vista sobre la tabla xm_precio_bolsa_horario de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'xm_precio_bolsa_horario') }}

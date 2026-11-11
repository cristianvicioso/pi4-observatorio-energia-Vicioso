-- Vista sobre la tabla ideam_temperatura_diaria de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'ideam_temperatura_diaria') }}

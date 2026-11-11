-- Vista sobre la tabla trm_diaria de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'trm_diaria') }}

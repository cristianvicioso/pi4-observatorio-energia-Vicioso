-- Vista sobre la tabla enerandes_ventas de la capa plata (ya limpia y validada con pandera)
select *
from {{ source('plata', 'enerandes_ventas') }}

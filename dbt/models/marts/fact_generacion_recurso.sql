-- fact_generacion_recurso
-- Grano: una fila por FECHA x HORA x PLANTA (recurso de generacion de XM).
select
    cast(strftime(fecha, '%Y%m%d') as integer)  as fecha_id,
    hora,
    codigo_recurso                              as recurso_id,
    generacion_kwh
from {{ ref('stg_generacion') }}

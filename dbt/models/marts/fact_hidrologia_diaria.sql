-- fact_hidrologia_diaria
-- Grano: una fila por FECHA para todo el SIN: volumen util total de los embalses y
-- aportes hidricos totales de los rios (kWh).
with embalses as (
    select fecha, sum(volumen_util_kwh) as volumen_util_kwh, count(*) as embalses_reportados
    from {{ ref('stg_embalses') }}
    group by fecha
),

aportes as (
    select fecha, sum(aportes_kwh) as aportes_kwh, count(*) as rios_reportados
    from {{ ref('stg_aportes') }}
    group by fecha
)

select
    cast(strftime(coalesce(e.fecha, a.fecha), '%Y%m%d') as integer)    as fecha_id,
    e.volumen_util_kwh,
    a.aportes_kwh,
    e.embalses_reportados,
    a.rios_reportados
from embalses as e
full outer join aportes as a
    on e.fecha = a.fecha

-- fact_mercado_horario
-- Grano: una fila por FECHA x HORA del Sistema Interconectado Nacional (2023-01-01 a 2026-09-30).
-- Une el precio de bolsa y la demanda comercial de esa hora, y agrega la TRM del dia
-- para expresar el precio tambien en dolares.
select
    cast(strftime(coalesce(p.fecha, d.fecha), '%Y%m%d') as integer)    as fecha_id,
    coalesce(p.hora, d.hora)                                            as hora,
    p.precio_bolsa_cop_kwh,
    d.demanda_kwh,
    t.trm_cop_usd,
    p.precio_bolsa_cop_kwh * 1000 / t.trm_cop_usd                       as precio_bolsa_usd_mwh
from {{ ref('stg_precio_bolsa') }} as p
full outer join {{ ref('stg_demanda') }} as d
    on p.fecha = d.fecha and p.hora = d.hora
left join {{ ref('stg_trm') }} as t
    on t.fecha = coalesce(p.fecha, d.fecha)

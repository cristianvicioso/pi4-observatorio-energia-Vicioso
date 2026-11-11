-- Pregunta: ¿cuánto sube el precio de bolsa cuando hay El Niño frente a La Niña o Neutral?
-- Tablas: fact_mercado_horario + dim_fecha (fase ENSO del mes)
select
    f.fase_enso,
    count(distinct f.periodo)                       as meses,
    round(avg(m.precio_bolsa_cop_kwh), 1)           as precio_promedio_cop_kwh,
    round(median(m.precio_bolsa_cop_kwh), 1)        as precio_mediano_cop_kwh,
    round(max(m.precio_bolsa_cop_kwh), 1)           as precio_maximo_cop_kwh,
    round(avg(m.precio_bolsa_usd_mwh), 1)           as precio_promedio_usd_mwh,
    round(sum(m.demanda_kwh) / 1e9 / count(distinct f.periodo), 2) as demanda_mensual_twh
from main.fact_mercado_horario as m
join main.dim_fecha as f
    on f.fecha_id = m.fecha_id
group by f.fase_enso
order by precio_promedio_cop_kwh desc;

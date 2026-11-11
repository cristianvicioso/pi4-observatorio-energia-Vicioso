-- Pregunta: cuando llueve menos en Antioquia, ¿bajan los aportes hídricos y sube el precio de bolsa?
-- Tablas: fact_clima_diario + fact_hidrologia_diaria + fact_mercado_horario + dim_fecha
with lluvia as (
    -- precipitación media diaria de las estaciones de Antioquia, sumada en el mes
    select f.periodo, sum(c.lluvia_media_mm) as lluvia_mm
    from (
        select fecha_id, avg(precipitacion_mm) as lluvia_media_mm
        from main.fact_clima_diario
        where precipitacion_mm is not null
        group by fecha_id
    ) as c
    join main.dim_fecha as f on f.fecha_id = c.fecha_id
    group by f.periodo
),

hidrologia as (
    select f.periodo,
           sum(h.aportes_kwh) / 1e9          as aportes_twh,
           avg(h.volumen_util_kwh) / 1e9     as volumen_util_twh
    from main.fact_hidrologia_diaria as h
    join main.dim_fecha as f on f.fecha_id = h.fecha_id
    group by f.periodo
),

precio as (
    select f.periodo, f.fase_enso, avg(m.precio_bolsa_cop_kwh) as precio_bolsa_cop_kwh
    from main.fact_mercado_horario as m
    join main.dim_fecha as f on f.fecha_id = m.fecha_id
    group by f.periodo, f.fase_enso
)

select
    p.periodo,
    p.fase_enso,
    round(l.lluvia_mm, 0)               as lluvia_antioquia_mm,
    round(h.aportes_twh, 2)             as aportes_twh,
    round(h.volumen_util_twh, 2)        as volumen_util_embalses_twh,
    round(p.precio_bolsa_cop_kwh, 1)    as precio_bolsa_cop_kwh
from precio as p
left join lluvia as l on l.periodo = p.periodo
left join hidrologia as h on h.periodo = p.periodo
order by p.periodo;

-- Correlación (una sola fila): corr(lluvia, precio) y corr(aportes, precio)
-- select corr(lluvia_antioquia_mm, precio_bolsa_cop_kwh), corr(aportes_twh, precio_bolsa_cop_kwh) from (<consulta de arriba>);

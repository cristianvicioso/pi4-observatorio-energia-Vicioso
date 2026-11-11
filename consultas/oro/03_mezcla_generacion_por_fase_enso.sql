-- Pregunta: ¿cómo cambia la mezcla de generación (hidráulica, térmica, solar...) con la fase ENSO?
-- Tablas: fact_generacion_recurso + dim_recurso + dim_fecha
with generacion as (
    select
        f.fase_enso,
        r.tipo_generacion,
        sum(g.generacion_kwh)   as generacion_kwh
    from main.fact_generacion_recurso as g
    join main.dim_recurso as r on r.recurso_id = g.recurso_id
    join main.dim_fecha as f on f.fecha_id = g.fecha_id
    group by f.fase_enso, r.tipo_generacion
)

select
    fase_enso,
    tipo_generacion,
    round(generacion_kwh / 1e9, 2)                                                      as generacion_twh,
    round(100 * generacion_kwh / sum(generacion_kwh) over (partition by fase_enso), 1) as participacion_pct
from generacion
order by fase_enso, participacion_pct desc;

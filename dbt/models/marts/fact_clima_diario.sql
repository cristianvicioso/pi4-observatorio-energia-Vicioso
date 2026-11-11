-- fact_clima_diario
-- Grano: una fila por FECHA x ESTACION del IDEAM en Antioquia.
-- Une la precipitacion (mm) y la temperatura (C) de la estacion ese dia;
-- una estacion puede medir solo una de las dos.
with clima as (
    select
        coalesce(p.fecha, t.fecha)                      as fecha,
        coalesce(p.codigo_estacion, t.codigo_estacion)  as estacion_id,
        p.precipitacion_mm,
        t.temp_media_c,
        t.temp_min_c,
        t.temp_max_c
    from {{ ref('stg_precipitacion') }} as p
    full outer join {{ ref('stg_temperatura') }} as t
        on p.fecha = t.fecha and p.codigo_estacion = t.codigo_estacion
)

select
    cast(strftime(c.fecha, '%Y%m%d') as integer)    as fecha_id,
    c.estacion_id,
    e.municipio_id,
    c.precipitacion_mm,
    c.temp_media_c,
    c.temp_min_c,
    c.temp_max_c
from clima as c
join {{ ref('dim_estacion') }} as e
    on e.estacion_id = c.estacion_id

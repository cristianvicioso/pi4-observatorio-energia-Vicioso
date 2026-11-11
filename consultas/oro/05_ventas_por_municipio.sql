-- Pregunta: ¿en qué municipios crecen más las ventas de energía de EnerAndes?
-- Compara enero-septiembre de cada año (2026 solo tiene datos hasta septiembre).
-- Tablas: fact_ventas_mensual + dim_municipio + dim_fecha
with ventas as (
    select
        mu.municipio,
        f.anio,
        sum(v.energia_kwh)  as energia_kwh,
        sum(v.clientes)     as clientes_mes
    from main.fact_ventas_mensual as v
    join main.dim_municipio as mu on mu.municipio_id = v.municipio_id
    join main.dim_fecha as f on f.fecha_id = v.fecha_id
    where f.mes <= 9
    group by mu.municipio, f.anio
)

select
    municipio,
    round(sum(energia_kwh) filter (where anio = 2023) / 1e6, 1)    as gwh_2023,
    round(sum(energia_kwh) filter (where anio = 2024) / 1e6, 1)    as gwh_2024,
    round(sum(energia_kwh) filter (where anio = 2025) / 1e6, 1)    as gwh_2025,
    round(sum(energia_kwh) filter (where anio = 2026) / 1e6, 1)    as gwh_2026,
    round(100 * (sum(energia_kwh) filter (where anio = 2026)
               / sum(energia_kwh) filter (where anio = 2023) - 1), 1) as crecimiento_2023_2026_pct
from ventas
group by municipio
order by crecimiento_2023_2026_pct desc;

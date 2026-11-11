-- dim_recurso: las plantas de generacion (ListadoRecursos de XM).
-- Las plantas que aparecen en la generacion pero no en el catalogo se agregan como
-- 'SIN CATALOGO' para no perder su generacion (ver docs/reporte_calidad.md).
with catalogo as (
    select
        codigo_recurso                  as recurso_id,
        nombre_recurso,
        tipo_generacion,
        fuente_energia,
        despacho,
        clasificacion,
        codigo_agente,
        cast(fecha_operacion as date)   as fecha_operacion,
        estado,
        true                            as en_catalogo
    from {{ ref('stg_recursos') }}
),

sin_catalogo as (
    select distinct
        g.codigo_recurso                as recurso_id,
        'SIN CATALOGO'                  as nombre_recurso,
        'NO INFORMADO'                  as tipo_generacion,
        'NO INFORMADO'                  as fuente_energia,
        'NO INFORMADO'                  as despacho,
        'NO INFORMADO'                  as clasificacion,
        'NO INFORMADO'                  as codigo_agente,
        cast(null as date)              as fecha_operacion,
        'NO INFORMADO'                  as estado,
        false                           as en_catalogo
    from {{ ref('stg_generacion') }} as g
    where g.codigo_recurso not in (select recurso_id from catalogo)
)

select * from catalogo
union all
select * from sin_catalogo

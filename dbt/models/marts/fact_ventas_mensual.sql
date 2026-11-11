-- fact_ventas_mensual
-- Grano: una fila por MES x MUNICIPIO x SEGMENTO x TIPO DE COMPRA (2023-01 a 2026-09).
-- El mes se une a dim_fecha por su primer dia (2024-03 -> 20240301).
select
    cast(replace(v.periodo, '-', '') || '01' as integer)   as fecha_id,
    v.divipola                                              as municipio_id,
    s.segmento_id,
    v.tipo_compra,
    v.energia_kwh,
    v.valor_cop,
    v.clientes,
    v.valor_cop / nullif(v.energia_kwh, 0)                  as tarifa_media_cop_kwh,
    v.energia_kwh / nullif(v.clientes, 0)                   as consumo_por_cliente_kwh
from {{ ref('stg_ventas') }} as v
join {{ ref('dim_segmento') }} as s
    on v.segmento = s.segmento

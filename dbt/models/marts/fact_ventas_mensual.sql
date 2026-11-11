-- Tabla de HECHOS: las ventas de energia.
-- Grano: un mes, un municipio, un segmento y un tipo de compra.

select
    -- Llave a dim_mes: '2023-04' -> 202304 (igual que en dim_mes).
    -- v. indica que la columna viene de la tabla v (las ventas)
    cast(replace(v.periodo, '-', '') as integer)    as mes_id,
    -- Llave a dim_municipio: el codigo DIVIPOLA
    v.divipola                                      as municipio_id,
    -- Llave a dim_segmento: el numero del segmento (viene de la tabla s)
    s.segmento_id,
    -- Un dato descriptivo que se deja en el hecho: Bolsa o Contrato
    v.tipo_compra,
    -- Las MEDIDAS: los numeros que se suman en el dashboard
    v.energia_kwh,
    v.valor_cop,
    v.clientes
-- De donde: el modelo stg_ventas, con el nombre corto v
from {{ ref('stg_ventas') }} as v
-- join = unir con otra tabla: dim_segmento, con el nombre corto s...
join {{ ref('dim_segmento') }} as s
    -- ...en las filas donde el segmento es el mismo. Asi cada venta recibe su segmento_id
    on v.segmento = s.segmento
-- Dimension MES: una fila por cada mes que tiene ventas.
-- Grano: un mes.
-- ref('stg_ventas') es el modelo stg_ventas.sql: dbt lo crea primero y luego este.

-- select distinct = traer las filas SIN repetir: cada mes aparece una sola vez
select distinct
    -- replace quita el guion: '2023-04' -> '202304'; cast(... as integer) lo vuelve
    -- numero: 202304. "as mes_id" le pone ese nombre a la columna (la llave)
    cast(replace(periodo, '-', '') as integer)      as mes_id,
    -- El periodo como texto: '2023-04'
    periodo,
    -- left(periodo, 4) toma los 4 primeros caracteres: '2023' -> 2023
    cast(left(periodo, 4) as integer)               as anio,
    -- right(periodo, 2) toma los 2 ultimos: '04' -> 4
    cast(right(periodo, 2) as integer)              as mes,
    -- El trimestre: (mes + 2) dividido 3, sin decimales (//).
    -- Ejemplo: enero (1+2)//3 = 1; abril (4+2)//3 = 2; diciembre (12+2)//3 = 4
    (cast(right(periodo, 2) as integer) + 2) // 3   as trimestre
-- De donde: el modelo stg_ventas
from {{ ref('stg_ventas') }}
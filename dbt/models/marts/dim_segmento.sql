-- Dimension SEGMENTO: una fila por segmento de cliente.
-- Grano: un segmento.

select
    -- row_number() numera las filas 1, 2, 3, 4, en orden alfabetico del segmento
    -- (over (order by segmento)). Ese numero es la llave: segmento_id
    row_number() over (order by segmento)   as segmento_id,
    -- El nombre del segmento: Comercial, Industrial, No informado, Residencial
    segmento
-- De donde: una subconsulta (entre parentesis) que trae cada segmento una sola vez
from (select distinct segmento from {{ ref('stg_ventas') }})
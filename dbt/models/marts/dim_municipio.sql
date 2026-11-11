-- Dimension MUNICIPIO: una fila por municipio, con su codigo DIVIPOLA.
-- Grano: un municipio.

-- select distinct = sin repetir: cada municipio aparece una sola vez (15 filas)
select distinct
    -- La llave: el codigo DANE de 5 digitos ('05001'), con el nombre municipio_id
    divipola    as municipio_id,
    -- El nombre oficial del municipio
    municipio
-- De donde: el modelo stg_ventas
from {{ ref('stg_ventas') }}
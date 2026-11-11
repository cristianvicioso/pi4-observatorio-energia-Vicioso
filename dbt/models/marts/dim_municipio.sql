-- dim_municipio: los 125 municipios de Antioquia (DIVIPOLA del DANE).
-- atendido_enerandes marca los 15 donde EnerAndes vende energia.
select
    divipola            as municipio_id,
    municipio,
    departamento,
    latitud,
    longitud,
    atendido_enerandes
from {{ ref('stg_municipios') }}

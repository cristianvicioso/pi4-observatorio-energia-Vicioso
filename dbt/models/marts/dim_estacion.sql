-- dim_estacion: estaciones del IDEAM en Antioquia, cada una con su municipio (DIVIPOLA).
select
    codigo_estacion     as estacion_id,
    nombre_estacion,
    divipola            as municipio_id,
    latitud,
    longitud
from {{ ref('stg_estaciones') }}

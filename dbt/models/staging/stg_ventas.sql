-- Staging: lee la tabla de ventas de la capa plata, sin cambiarla.
-- En SQL, lo que va despues de -- es un comentario.
-- dbt reemplaza source('plata', 'enerandes_ventas') por la ruta
-- data/silver/enerandes_ventas.parquet (la dice sources.yml).
-- Se crea como VISTA (dbt_project.yml): los demas modelos leen de aqui.

-- select * = traer todas las columnas
select *
-- from = de donde: la tabla de ventas de la capa plata
from {{ source('plata', 'enerandes_ventas') }}
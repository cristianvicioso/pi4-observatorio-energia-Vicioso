-- Prueba generica: el grano de una tabla de hechos no se repite.
-- Uso en schema.yml:
--   data_tests:
--     - grano_unico:
--         arguments:
--           columnas: [fecha_id, hora]
-- Falla si alguna combinacion de esas columnas aparece mas de una vez.
{% test grano_unico(model, columnas) %}
select {{ columnas | join(', ') }}, count(*) as veces
from {{ model }}
group by {{ columnas | join(', ') }}
having count(*) > 1
{% endtest %}

-- Pregunta: ¿cuánta energía compra EnerAndes en bolsa cada año y cuánto le costaría
-- al precio de bolsa promedio de cada mes, frente a lo que factura?
-- Tablas: fact_ventas_mensual + fact_mercado_horario + dim_fecha
with precio_mes as (
    select f.periodo, avg(m.precio_bolsa_cop_kwh) as precio_bolsa_cop_kwh
    from main.fact_mercado_horario as m
    join main.dim_fecha as f on f.fecha_id = m.fecha_id
    group by f.periodo
),

ventas_mes as (
    select
        f.anio,
        f.periodo,
        v.tipo_compra,
        sum(v.energia_kwh)  as energia_kwh,
        sum(v.valor_cop)    as valor_cop
    from main.fact_ventas_mensual as v
    join main.dim_fecha as f on f.fecha_id = v.fecha_id
    group by f.anio, f.periodo, v.tipo_compra
)

select
    v.anio,
    round(sum(v.energia_kwh) filter (where v.tipo_compra = 'Bolsa') / 1e6, 1)       as energia_bolsa_gwh,
    round(100 * sum(v.energia_kwh) filter (where v.tipo_compra = 'Bolsa')
          / sum(v.energia_kwh), 1)                                                   as pct_energia_en_bolsa,
    round(sum(v.energia_kwh * p.precio_bolsa_cop_kwh) filter (where v.tipo_compra = 'Bolsa') / 1e9, 1)
                                                                                     as costo_bolsa_mil_millones_cop,
    round(sum(v.valor_cop) filter (where v.tipo_compra = 'Bolsa') / 1e9, 1)         as facturado_bolsa_mil_millones_cop,
    round(avg(p.precio_bolsa_cop_kwh), 1)                                            as precio_bolsa_promedio_cop_kwh
from ventas_mes as v
join precio_mes as p on p.periodo = v.periodo
group by v.anio
order by v.anio;

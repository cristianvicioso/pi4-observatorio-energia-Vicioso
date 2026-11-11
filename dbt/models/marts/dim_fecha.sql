-- dim_fecha: un dia del calendario (2023-01-01 a 2026-12-31) con su mes, trimestre,
-- dia de la semana y la fase ENSO del mes (ONI de NOAA).
with dias as (
    select cast(d as date) as fecha
    from generate_series(date '2023-01-01', date '2026-12-31', interval 1 day) as t(d)
)

select
    cast(strftime(d.fecha, '%Y%m%d') as integer)            as fecha_id,
    d.fecha,
    year(d.fecha)                                           as anio,
    month(d.fecha)                                          as mes,
    case month(d.fecha)
        when 1 then 'Enero' when 2 then 'Febrero' when 3 then 'Marzo'
        when 4 then 'Abril' when 5 then 'Mayo' when 6 then 'Junio'
        when 7 then 'Julio' when 8 then 'Agosto' when 9 then 'Septiembre'
        when 10 then 'Octubre' when 11 then 'Noviembre' else 'Diciembre'
    end                                                     as nombre_mes,
    strftime(d.fecha, '%Y-%m')                              as periodo,
    quarter(d.fecha)                                        as trimestre,
    day(d.fecha)                                            as dia,
    isodow(d.fecha)                                         as dia_semana,      -- 1 = lunes ... 7 = domingo
    case isodow(d.fecha)
        when 1 then 'Lunes' when 2 then 'Martes' when 3 then 'Miércoles'
        when 4 then 'Jueves' when 5 then 'Viernes' when 6 then 'Sábado' else 'Domingo'
    end                                                     as nombre_dia,
    isodow(d.fecha) >= 6                                    as es_fin_de_semana,
    o.oni,
    coalesce(o.fase_enso, 'Sin dato')                       as fase_enso
from dias as d
left join {{ ref('stg_oni') }} as o
    on o.periodo = strftime(d.fecha, '%Y-%m')

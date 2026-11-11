# Diccionario de datos - capa oro

Base: `data/observatorio.duckdb`, esquema `main`. Los tipos son los de DuckDB.
La columna **Origen** dice de qué tabla de la capa plata (`data/silver/`) y de qué fuente sale
cada dato, o cómo se calcula.

## dim_fecha

Un día del calendario, de 2023-01-01 a 2026-12-31 (1.461 filas).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | Llave. Fecha como entero AAAAMMDD (20240315) | Calculada en dbt a partir de `fecha` |
| `fecha` | DATE | Día del calendario | Generada en dbt (`generate_series`) |
| `anio` | BIGINT | Año (2023 a 2026) | `year(fecha)` |
| `mes` | BIGINT | Mes (1 a 12) | `month(fecha)` |
| `nombre_mes` | VARCHAR | Nombre del mes en español (Enero ... Diciembre) | Calculada en dbt |
| `periodo` | VARCHAR | Mes en formato AAAA-MM; sirve para unir datos mensuales | `strftime(fecha, '%Y-%m')` |
| `trimestre` | BIGINT | Trimestre del año (1 a 4) | `quarter(fecha)` |
| `dia` | BIGINT | Día del mes (1 a 31) | `day(fecha)` |
| `dia_semana` | BIGINT | Día de la semana ISO: 1 = lunes ... 7 = domingo | `isodow(fecha)` |
| `nombre_dia` | VARCHAR | Nombre del día (Lunes ... Domingo) | Calculada en dbt |
| `es_fin_de_semana` | BOOLEAN | `true` si es sábado o domingo | `dia_semana >= 6` |
| `oni` | DOUBLE | Índice ONI del mes (anomalía de temperatura del Pacífico, °C) | `noaa_oni_mensual.oni` (NOAA, trimestre móvil asignado a su mes central) |
| `fase_enso` | VARCHAR | El Niño (ONI ≥ 0,5), La Niña (ONI ≤ -0,5), Neutral o `Sin dato` (meses sin ONI publicado) | `noaa_oni_mensual.fase_enso` |

## dim_municipio

Un municipio de Antioquia (125 filas).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `municipio_id` | VARCHAR | Llave. Código DIVIPOLA de 5 dígitos (05001 = Medellín) | `divipola_municipios.divipola` (DANE, datos.gov.co `gdxc-w37w`) |
| `municipio` | VARCHAR | Nombre oficial del municipio | `divipola_municipios.municipio` (de MAYÚSCULA a nombre propio) |
| `departamento` | VARCHAR | Siempre `Antioquia` | `divipola_municipios.departamento` |
| `latitud` | DOUBLE | Latitud de la cabecera municipal | `divipola_municipios.latitud` (coma decimal convertida) |
| `longitud` | DOUBLE | Longitud de la cabecera municipal | `divipola_municipios.longitud` |
| `atendido_enerandes` | BOOLEAN | `true` en los 15 municipios donde EnerAndes vende energía | Calculada en plata: el código está en las ventas de EnerAndes |

## dim_segmento

Un segmento de cliente de EnerAndes (4 filas).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `segmento_id` | BIGINT | Llave sustituta (1 a 4) | `row_number()` en dbt |
| `segmento` | VARCHAR | Residencial, Comercial, Industrial o No informado | `enerandes_ventas.segmento` (unificado en plata: `RESID.`, `IND`...) |

## dim_recurso

Una planta (recurso) de generación del SIN (2.523 filas).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `recurso_id` | VARCHAR | Llave. Código del recurso en XM | `xm_recursos.codigo_recurso` (API XM `ListadoRecursos`, campo `Code`) |
| `nombre_recurso` | VARCHAR | Nombre de la planta; `SIN CATALOGO` si no está en ListadoRecursos | `xm_recursos.nombre_recurso` (`Name`) |
| `tipo_generacion` | VARCHAR | HIDRAULICA, TERMICA, SOLAR, EOLICA, COGENERADOR o NO INFORMADO | `xm_recursos.tipo_generacion` (`Type`, unificado a MAYÚSCULA) |
| `fuente_energia` | VARCHAR | Combustible o recurso primario (AGUA, GAS, CARBON, RAD SOLAR...) | `xm_recursos.fuente_energia` (`EnerSource`) |
| `despacho` | VARCHAR | Si la planta es despachada centralmente por XM | `xm_recursos.despacho` (`Disp`) |
| `clasificacion` | VARCHAR | Clasificación del recurso (NORMAL, FILO DE AGUA, ...) | `xm_recursos.clasificacion` (`RecType`) |
| `codigo_agente` | VARCHAR | Código de la empresa que representa la planta | `xm_recursos.codigo_agente` (`CompanyCode`) |
| `fecha_operacion` | DATE | Fecha de entrada en operación | `xm_recursos.fecha_operacion` (`OperStartdate`) |
| `estado` | VARCHAR | Estado de la planta (OPERACION, ...) | `xm_recursos.estado` (`State`) |
| `en_catalogo` | BOOLEAN | `false` si la planta genera pero no está en ListadoRecursos | Calculada en dbt |

## dim_estacion

Una estación meteorológica del IDEAM en Antioquia.

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `estacion_id` | VARCHAR | Llave. Código de la estación en el IDEAM | `ideam_estaciones.codigo_estacion` (campo `codigoestacion`) |
| `nombre_estacion` | VARCHAR | Nombre de la estación (el más frecuente si la fuente trae varios) | `ideam_estaciones.nombre_estacion` |
| `municipio_id` | VARCHAR | Municipio donde está la estación (DIVIPOLA) | `ideam_estaciones.divipola`: el nombre del municipio del IDEAM se cruza con DIVIPOLA |
| `latitud` | DOUBLE | Latitud de la estación | `ideam_estaciones.latitud` |
| `longitud` | DOUBLE | Longitud de la estación | `ideam_estaciones.longitud` |

## fact_ventas_mensual

**Grano:** un mes x municipio x segmento x tipo de compra de EnerAndes (2023-01 a 2026-09).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | FK a `dim_fecha`: primer día del mes (20240301) | `enerandes_ventas.periodo` (4 formatos del Excel unificados a AAAA-MM) |
| `municipio_id` | VARCHAR | FK a `dim_municipio` (DIVIPOLA) | `enerandes_ventas.divipola` (32 formas de escribir 15 municipios unificadas) |
| `segmento_id` | BIGINT | FK a `dim_segmento` | Unión con `dim_segmento` por nombre |
| `tipo_compra` | VARCHAR | Bolsa o Contrato (dimensión degenerada) | `enerandes_ventas.tipo_compra` |
| `energia_kwh` | DOUBLE | Energía vendida en kWh | `enerandes_ventas.energia_kwh` (la hoja 2024 en MWh se multiplicó por 1.000) |
| `valor_cop` | DOUBLE | Valor facturado en pesos; puede estar vacío (no se inventa) | `enerandes_ventas.valor_cop` |
| `clientes` | BIGINT | Número de clientes facturados en el mes | `enerandes_ventas.clientes` |
| `tarifa_media_cop_kwh` | DOUBLE | Valor facturado / energía (COP por kWh) | Calculada en dbt |
| `consumo_por_cliente_kwh` | DOUBLE | Energía / clientes (kWh por cliente al mes) | Calculada en dbt |

## fact_mercado_horario

**Grano:** una fecha x hora del Sistema Interconectado Nacional (2023-01-01 a 2026-09-30).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | FK a `dim_fecha` | `xm_precio_bolsa_horario.fecha` / `xm_demanda_horaria.fecha` |
| `hora` | BIGINT | Hora del día, 1 a 24 (la hora 1 va de 00:00 a 01:00) | Columnas `Hour01..Hour24` de XM pasadas a filas |
| `precio_bolsa_cop_kwh` | DOUBLE | Precio de bolsa nacional (COP/kWh) | `xm_precio_bolsa_horario` (XM, métrica `PrecBolsNaci`) |
| `demanda_kwh` | DOUBLE | Demanda comercial del SIN (kWh) | `xm_demanda_horaria` (XM, métrica `DemaCome`) |
| `trm_cop_usd` | DOUBLE | TRM del día (COP por USD) | `trm_diaria` (fuente propia, Superfinanciera) |
| `precio_bolsa_usd_mwh` | DOUBLE | Precio de bolsa en USD/MWh = precio x 1.000 / TRM | Calculada en dbt |

## fact_generacion_recurso

**Grano:** una fecha x hora x planta con generación reportada (2023-01-01 a 2026-09-30).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | FK a `dim_fecha` | `xm_generacion_horaria.fecha` |
| `hora` | BIGINT | Hora del día, 1 a 24 | Columnas `Hour01..Hour24` de XM pasadas a filas |
| `recurso_id` | VARCHAR | FK a `dim_recurso` | `xm_generacion_horaria.codigo_recurso` |
| `generacion_kwh` | DOUBLE | Generación real de la planta en esa hora (kWh) | `xm_generacion_horaria` (XM, métrica `Gene`, entidad Recurso) |

## fact_hidrologia_diaria

**Grano:** una fecha para todo el SIN (2023-01-01 a 2026-09-30).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | FK a `dim_fecha` | `xm_embalses_diario.fecha` / `xm_aportes_diario.fecha` |
| `volumen_util_kwh` | DOUBLE | Volumen útil total de los embalses, en energía (kWh) | Suma de `xm_embalses_diario.volumen_util_kwh` (XM, `VoluUtilDiarEner`) |
| `aportes_kwh` | DOUBLE | Aportes hídricos totales de los ríos, en energía (kWh) | Suma de `xm_aportes_diario.aportes_kwh` (XM, `AporEner`) |
| `embalses_reportados` | BIGINT | Cuántos embalses reportaron ese día | Conteo en dbt |
| `rios_reportados` | BIGINT | Cuántos ríos reportaron ese día | Conteo en dbt |

## fact_clima_diario

**Grano:** una fecha x estación del IDEAM en Antioquia (2023-01-01 a 2026-07-31; el IDEAM no tiene datos posteriores).

| Columna | Tipo | Descripción | Origen |
|---|---|---|---|
| `fecha_id` | INTEGER | FK a `dim_fecha` | `ideam_precipitacion_diaria.fecha` / `ideam_temperatura_diaria.fecha` |
| `estacion_id` | VARCHAR | FK a `dim_estacion` | `codigo_estacion` de las tablas del IDEAM |
| `municipio_id` | VARCHAR | FK a `dim_municipio` (municipio de la estación) | `dim_estacion.municipio_id` |
| `precipitacion_mm` | DOUBLE | Lluvia del día (mm). Vacía si la estación no mide lluvia | `ideam_precipitacion_diaria` (IDEAM `s54a-sgyg`, suma de las observaciones del día) |
| `temp_media_c` | DOUBLE | Temperatura media del día (°C). Vacía si la estación no mide temperatura | `ideam_temperatura_diaria` (IDEAM `sbwg-7ju4`, promedio de las observaciones) |
| `temp_min_c` | DOUBLE | Temperatura mínima del día (°C) | `ideam_temperatura_diaria` (mínimo de las observaciones) |
| `temp_max_c` | DOUBLE | Temperatura máxima del día (°C) | `ideam_temperatura_diaria` (máximo de las observaciones) |

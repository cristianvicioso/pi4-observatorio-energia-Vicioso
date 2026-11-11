# Observatorio de Energía y Clima - EnerAndes

Pipeline de datos en Python, pandera y dbt que integra las ventas de EnerAndes con el mercado
eléctrico (XM), el clima (IDEAM), el fenómeno de El Niño/La Niña (NOAA) y la TRM.
Está organizado en tres capas:

| Capa | Dónde | Qué tiene |
|---|---|---|
| **Bronce** | `data/bronze/` | Los datos tal cual llegan de cada fuente (Parquet) |
| **Plata** | `data/silver/` | Datos limpios y validados con pandera, más archivos de cuarentena |
| **Oro** | `data/observatorio.duckdb` | Esquema estrella construido con dbt: 5 hechos y 6 dimensiones |

`data/bronze/`, `data/silver/` y el archivo `.duckdb` **no se suben a GitHub**: se reconstruyen con los comandos de abajo.

---

## Integrante y roles

- **Estudiante:** Cristian Vicioso. **Modalidad:** trabajo individual.
- **Data Engineer:** extractores (`src/extract/`), orquestación (`src/pipeline.py`, `src/transformar.py`).
- **Data Quality Analyst:** reglas de limpieza (`src/silver/`), esquemas de pandera (`src/quality/esquemas.py`) y reporte de calidad.
- **Analytics Engineer:** modelo dimensional en dbt (`dbt/`), pruebas de pytest y de dbt.
- **BI Analyst:** consultas de negocio sobre la capa oro (`consultas/oro/`).

Bitácora: [`docs/bitacoras/vicioso_cristian.md`](docs/bitacoras/vicioso_cristian.md).

---

## Fuentes

| Fuente | Cómo se obtiene | Datos |
|---|---|---|
| **EnerAndes** | Excel interno `data/ventas_enerandes_2023_2026.xlsx` (4 hojas) | Ventas mensuales por municipio, segmento y tipo de compra |
| **XM** | API `servapibi.xm.com.co` | Precio de bolsa, demanda y generación por planta (horarios); embalses y aportes (diarios); catálogo de plantas |
| **IDEAM** | datos.gov.co (Socrata/SoQL) | Precipitación y temperatura diarias por estación en Antioquia |
| **NOAA** | `oni.ascii.txt` del CPC | Índice ONI por trimestre móvil |
| **Fuente propia: TRM** | datos.gov.co `mcec-87by` | Tasa de cambio COP/USD |
| Referencia: DIVIPOLA | datos.gov.co `gdxc-w37w` | Códigos DANE de los municipios de Antioquia |

Periodo del observatorio: **2023-01-01 a 2026-09-30**.

---

## Cómo ejecutarlo

```bash
git clone https://github.com/cristianvicioso/pi4-observatorio-energia-Vicioso.git
cd pi4-observatorio-energia-Vicioso
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

python -m src.pipeline          # 1. capa bronce: descarga las fuentes (unos 40 min, sobre todo por el IDEAM)
python -m src.transformar       # 2. capas plata y oro: limpia todo, valida con pandera y ejecuta dbt build
python -m pytest                # pruebas de las reglas de limpieza
python -m src.consultar         # ejecuta las consultas de consultas/oro/
```

`python -m src.transformar` hace, en orden:

1. Ejecuta la limpieza de cada fuente (`src/silver/*.py`). Cada programa valida su tabla con
   pandera **antes** de guardarla en `data/silver/`; si una regla falla, no guarda nada.
2. Escribe `docs/reporte_calidad.md` con la métrica antes → después de cada regla.
3. Ejecuta `dbt build` (modelos y pruebas de dbt) y deja la capa oro en `data/observatorio.duckdb`.

---

## Estructura

```
src/
  extract/            capa bronce: un extractor por fuente
  silver/             capa plata: enerandes, xm, ideam, noaa, trm, divipola (+ comun.py)
  quality/            esquemas.py (pandera, uno por tabla) y reporte.py (reporte de calidad)
  pipeline.py         python -m src.pipeline     -> bronce
  transformar.py      python -m src.transformar  -> plata + oro
  consultar.py        python -m src.consultar    -> resultados de consultas/oro/
dbt/models/
  staging/            vistas sobre las tablas de plata (sources.yml)
  marts/              dimensiones y hechos + schema.yml (grano y pruebas)
dbt/tests/generic/    prueba grano_unico
consultas/oro/        consultas SQL de negocio
docs/                 perfilamiento, reporte de calidad, modelo dimensional, diccionario, bitácora
tests/                pruebas de pytest
```

---

## Capa plata: calidad

- **13 tablas**, cada una con su esquema de pandera (tipos, rangos, valores aceptados y llave única).
- **Cuarentena**: las filas que no se pueden corregir quedan en `data/silver/*_cuarentena.parquet`
  con el motivo. No se borran.
- **Reporte**: [`docs/reporte_calidad.md`](docs/reporte_calidad.md). Tiene una tabla por fuente con
  el problema, la regla aplicada y la métrica antes → después.

Las 4 hojas del Excel de EnerAndes tienen encabezados distintos, títulos y notas, filas TOTAL,
fechas en 4 formatos (`2024-03`, `mar-24`, `03/2024`, `01/03/2026`), energía en kWh y MWh,
municipios mal escritos, duplicados, celdas vacías y negativos. Se unen en una sola tabla:
**4.184 filas en bronce → 4.007 limpias + 43 en cuarentena**.

**Pruebas:** `python -m pytest` ejecuta 22 pruebas. Las 7 de la clase están en
`tests/test_limpieza.py` y las 12 nuevas de la EA2, en `tests/test_reglas_ea2.py`: MWh → kWh,
fechas `mar-24` y `03/2024`, `01/03/2026` como marzo, fase ENSO, trimestre → mes central,
XM de 24 columnas a filas, entre otras.

---

## Capa oro: modelo dimensional

- Diagrama y grano de cada hecho: [`docs/modelo_dimensional.md`](docs/modelo_dimensional.md)
- Diccionario de datos: [`docs/diccionario_datos.md`](docs/diccionario_datos.md)

| Hechos | Grano |
|---|---|
| `fact_ventas_mensual` | mes x municipio x segmento x tipo de compra (2023-2026) |
| `fact_mercado_horario` | fecha x hora (precio de bolsa y demanda) |
| `fact_generacion_recurso` | fecha x hora x planta |
| `fact_hidrologia_diaria` | fecha (embalses y aportes del SIN) |
| `fact_clima_diario` | fecha x estación del IDEAM |

Dimensiones: `dim_fecha` (día, mes, trimestre, día de la semana y fase ENSO), `dim_municipio`,
`dim_segmento`, `dim_recurso`, `dim_estacion`.

---

## Consultas de negocio (capa oro)

Archivos en [`consultas/oro/`](consultas/oro/). Los resultados se obtuvieron con `python -m src.consultar` sobre los datos descargados el 2026-11-11.

### 1. ¿Cuánto sube el precio de bolsa con El Niño?

[`01_precio_bolsa_por_fase_enso.sql`](consultas/oro/01_precio_bolsa_por_fase_enso.sql)

| fase_enso | meses | precio_promedio_cop_kwh | precio_mediano_cop_kwh | precio_maximo_cop_kwh | precio_promedio_usd_mwh | demanda_mensual_twh |
|---|---|---|---|---|---|---|
| El Niño | 16 | 667.1 | 646.3 | 1,846.7 | 177.8 | 7.12 |
| Neutral | 25 | 412.1 | 271.5 | 2,675.6 | 97.8 | 6.93 |
| La Niña | 4 | 260.4 | 243.8 | 1,079.2 | 63.6 | 7.09 |

**Lectura:** Con El Niño el precio de bolsa promedio (667 COP/kWh) es **2,6 veces** el de La Niña (260 COP/kWh) y un 62 % mayor que en meses neutrales, aunque la demanda casi no cambia. El precio horario más alto (2.676 COP/kWh, el 6 de noviembre de 2024) se dio en un mes neutral, y octubre de 2024 tuvo el promedio mensual más alto (1.529 COP/kWh) con aportes bajos: la fase ENSO no lo explica todo.

### 2. ¿Cuánto expone a EnerAndes su compra en bolsa?

[`02_exposicion_enerandes_a_bolsa.sql`](consultas/oro/02_exposicion_enerandes_a_bolsa.sql)

| anio | energia_bolsa_gwh | pct_energia_en_bolsa | costo_bolsa_mil_millones_cop | facturado_bolsa_mil_millones_cop | precio_bolsa_promedio_cop_kwh |
|---|---|---|---|---|---|
| 2023 | 159.3 | 22.1 | 88.8 | 140 | 557.8 |
| 2024 | 164 | 22.3 | 110.1 | 155.7 | 676.2 |
| 2025 | 171.8 | 22.3 | 41 | 180.3 | 241.3 |
| 2026 | 130.7 | 22 | 63.1 | 148.6 | 476.4 |

**Lectura:** EnerAndes compra alrededor del **22 % de su energía en bolsa** todos los años. Con el precio de bolsa de cada mes, ese componente le habría costado 110 mil millones de COP en 2024 (El Niño de enero a abril y precios altos al final del año) frente a 41 mil millones en 2025 (Neutral y La Niña): el mismo volumen comprado en bolsa costó 2,7 veces más.

### 3. ¿Cómo cambia la mezcla de generación con la fase ENSO?

[`03_mezcla_generacion_por_fase_enso.sql`](consultas/oro/03_mezcla_generacion_por_fase_enso.sql)

| fase_enso | tipo_generacion | generacion_twh | participacion_pct |
|---|---|---|---|
| El Niño | HIDRAULICA | 74.05 | 65.2 |
| El Niño | TERMICA | 33.15 | 29.2 |
| El Niño | SOLAR | 4.92 | 4.3 |
| El Niño | COGENERADOR | 1.14 | 1 |
| El Niño | EOLICA | 0.25 | 0.2 |
| El Niño | NO INFORMADO | 0.07 | 0.1 |
| La Niña | HIDRAULICA | 23.23 | 82 |
| La Niña | TERMICA | 3.41 | 12 |
| La Niña | SOLAR | 1.33 | 4.7 |
| La Niña | COGENERADOR | 0.29 | 1 |
| La Niña | EOLICA | 0.05 | 0.2 |
| La Niña | NO INFORMADO | 0.01 | 0 |
| Neutral | HIDRAULICA | 132.67 | 76.7 |
| Neutral | TERMICA | 30.25 | 17.5 |
| Neutral | SOLAR | 7.96 | 4.6 |
| Neutral | COGENERADOR | 1.69 | 1 |
| Neutral | EOLICA | 0.33 | 0.2 |
| Neutral | NO INFORMADO | 0.09 | 0 |

**Lectura:** Con La Niña el 82 % de la energía es hidráulica y el 12 % térmica; con El Niño la hidráulica baja al 65 % y la térmica sube al **29 %**. El reemplazo de agua por combustibles explica buena parte del alza del precio de la consulta 1. `NO INFORMADO` son las plantas que generan pero no están en ListadoRecursos.

### 4. Cuando llueve menos, ¿bajan los aportes y sube el precio?

[`04_lluvia_aportes_y_precio_mensual.sql`](consultas/oro/04_lluvia_aportes_y_precio_mensual.sql)

<details><summary>Ver los 45 meses</summary>

| periodo | fase_enso | lluvia_antioquia_mm | aportes_twh | volumen_util_embalses_twh | precio_bolsa_cop_kwh |
|---|---|---|---|---|---|
| 2023-01 | La Niña | 75 | 5.96 | 13.96 | 372 |
| 2023-02 | Neutral | 37 | 3.38 | 11.89 | 526.7 |
| 2023-03 | Neutral | 124 | 7.88 | 10.92 | 293.5 |
| 2023-04 | Neutral | 118 | 7.4 | 10.86 | 227 |
| 2023-05 | Neutral | 148 | 6.81 | 11.02 | 569.7 |
| 2023-06 | El Niño | 106 | 7.06 | 12.68 | 462.2 |
| 2023-07 | El Niño | 141 | 7.25 | 14.09 | 521.6 |
| 2023-08 | El Niño | 162 | 5.71 | 14.88 | 529.8 |
| 2023-09 | El Niño | 94 | 3.56 | 13.79 | 1,015 |
| 2023-10 | El Niño | 99 | 4.63 | 12.72 | 1,015.4 |
| 2023-11 | El Niño | 103 | 6.15 | 13.06 | 504.5 |
| 2023-12 | El Niño | 50 | 3.64 | 12.49 | 656.2 |
| 2024-01 | El Niño | 8 | 2.32 | 11.05 | 558.7 |
| 2024-02 | El Niño | 40 | 2.32 | 8.71 | 568.7 |
| 2024-03 | El Niño | 35 | 2.18 | 6.39 | 622.8 |
| 2024-04 | El Niño | 60 | 3.99 | 5.32 | 748.7 |
| 2024-05 | Neutral | 277 | 8.73 | 6.61 | 291.5 |
| 2024-06 | Neutral | 90 | 9.86 | 8.93 | 280.7 |
| 2024-07 | Neutral | 28 | 7.27 | 10.3 | 285.1 |
| 2024-08 | Neutral | 94 | 4.52 | 9.95 | 567.4 |
| 2024-09 | Neutral | 55 | 3.7 | 8.95 | 873.7 |
| 2024-10 | Neutral | 147 | 4.79 | 9.21 | 1,529.1 |
| 2024-11 | Neutral | 465 | 7.39 | 10.76 | 1,046.4 |
| 2024-12 | Neutral | 274 | 4.55 | 11.4 | 741 |
| 2025-01 | Neutral | 235 | 4.08 | 11.29 | 519.7 |
| 2025-02 | Neutral | 31 | 4.68 | 9.76 | 428.7 |
| 2025-03 | Neutral | 128 | 6.34 | 8.87 | 228.5 |
| 2025-04 | Neutral | 261 | 9.71 | 9.22 | 140.6 |
| 2025-05 | Neutral | 218 | 12.54 | 11.6 | 126.7 |
| 2025-06 | Neutral | 262 | 11.48 | 13.51 | 112.5 |
| 2025-07 | Neutral | 209 | 9.36 | 14.15 | 134.9 |
| 2025-08 | Neutral | 280 | 6.77 | 14.15 | 241.4 |
| 2025-09 | Neutral | 259 | 5.96 | 14.2 | 293.7 |
| 2025-10 | La Niña | 330 | 7.19 | 14.12 | 170.9 |
| 2025-11 | La Niña | 236 | 6.96 | 14.45 | 219 |
| 2025-12 | La Niña | 144 | 5.68 | 14.11 | 278.5 |
| 2026-01 | Neutral | 217 | 5.94 | 13.34 | 212.4 |
| 2026-02 | Neutral | 204 | 6.46 | 12.66 | 124.4 |
| 2026-03 | Neutral | 139 | 5.2 | 11.42 | 220.2 |
| 2026-04 | Neutral | 224 | 6.3 | 10.61 | 269 |
| 2026-05 | El Niño | 200 | 6.66 | 11.1 | 505 |
| 2026-06 | El Niño | 201 | 6.39 | 12.42 | 546.3 |
| 2026-07 | El Niño | 219 | 6.18 | 13.78 | 789.8 |
| 2026-08 | El Niño |  | 5.11 | 13.78 | 943.5 |
| 2026-09 | El Niño |  | 4.1 | 13.7 | 677 |

</details>

**Lectura:** Los meses con menos aportes hídricos tienen precios más altos: la correlación aportes–precio es **-0,55**. La lluvia de las estaciones de Antioquia casi no se correlaciona con el precio (-0,16), porque el precio depende de los aportes de todo el SIN y no solo de Antioquia, y porque la cobertura del IDEAM entre 2023-09 y 2024-10 es baja (ver el reporte de calidad). El IDEAM llega solo hasta 2026-07.

### 5. ¿En qué municipios crecen más las ventas de EnerAndes?

[`05_ventas_por_municipio.sql`](consultas/oro/05_ventas_por_municipio.sql)

| municipio | gwh_2023 | gwh_2024 | gwh_2025 | gwh_2026 | crecimiento_2023_2026_pct |
|---|---|---|---|---|---|
| Caucasia | 10.9 | 11.9 | 13 | 13.2 | 20.8 |
| Turbo | 13.2 | 15 | 15.4 | 15.5 | 17 |
| Sabaneta | 21 | 22.6 | 22.8 | 23.8 | 13.4 |
| Santa Fé de Antioquia | 4.7 | 4.9 | 5.1 | 5.3 | 12.5 |
| Bello | 59.1 | 62.9 | 67.1 | 66.2 | 12.1 |
| Girardota | 9.6 | 9.9 | 10.3 | 10.5 | 9.7 |
| Marinilla | 9.6 | 10 | 10 | 10.5 | 9.5 |
| Apartadó | 19.3 | 20.1 | 20.5 | 21.2 | 9.5 |
| Medellín | 241.6 | 240.5 | 256.3 | 264.3 | 9.4 |
| La Estrella | 12.2 | 11.9 | 12.7 | 13.4 | 9.4 |
| Itagüí | 46.2 | 47.5 | 49.2 | 50.6 | 9.4 |
| Rionegro | 29.2 | 30 | 30.1 | 31.8 | 8.8 |
| Copacabana | 12.2 | 12.5 | 12.5 | 13.1 | 8.1 |
| Caldas | 11.9 | 12.6 | 12.9 | 12.7 | 6.8 |
| Envigado | 40.9 | 42.4 | 43.6 | 43 | 5.1 |

**Lectura:** Comparando enero a septiembre de cada año, Caucasia (+20,8 %) y Turbo (+17 %) son los municipios que más crecen. Medellín concentra el 44 % de la energía vendida y crece un 9,4 %.


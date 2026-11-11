# Bitácora - Cristian Vicioso

Trabajo individual. Roles: Data Engineer, Data Quality Analyst, Analytics Engineer y BI Analyst.

---

## Evidencia 1 - Capa bronce (2026-10-28)

- Extractores de XM, IDEAM, NOAA, TRM y del Excel de EnerAndes (`src/extract/`).
- Perfilamiento de los datos en `docs/perfilamiento.md`.
- Pruebas de pytest del pipeline y de las ventanas de fechas.
- Tag `ea1`.

---

## Evidencia 2 - Calidad (capa plata) y modelo dimensional (capa oro)

### 2026-11-11 - Código base de la clase (PR #1)

- Integré el código del encuentro AAA: limpieza de la hoja 2023 (`src/silver/enerandes.py`),
  esquema de pandera `ESQUEMA_VENTAS`, 7 pruebas en `tests/test_limpieza.py` y el proyecto dbt
  con `fact_ventas_mensual`, `dim_mes`, `dim_municipio` y `dim_segmento`.

### 2026-11-11 - Revisión de la capa bronce

Antes de ampliar la capa plata revisé qué había en `data/bronze/`. Hallazgos:

- **XM no tenía datos reales.** El extractor usaba `conexion.xm.com.co`, que no responde, y
  ante el error guardaba un registro de relleno (1 fila con valor 0). Lo cambié a la API
  correcta (`servapibi.xm.com.co`). Ahora se descargan el precio de bolsa, la demanda, la
  generación por planta, los embalses, los aportes y ListadoRecursos (2.512 plantas).
- **La TRM también tenía relleno.** El ID del dataset estaba mal (`32sa-2p3f`; el correcto es
  `mcec-87by`).
- **IDEAM.** El extractor de la EA1 (`src/extract/ideam_socrata.py`) **se dejó sin cambios**.
  Con su tiempo de espera de 5 segundos, la API casi nunca alcanza a responder y el extractor
  guarda 2 filas de relleno; además, solo trae temperatura. Para la EA2 creé un extractor aparte,
  `src/extract/ideam_ea2.py`. Trae precipitación y temperatura de Antioquia, agregadas por día y
  estación en la consulta SoQL y con el municipio de cada estación. Pide ventanas de 10 días,
  4 a la vez, y guarda cada ventana apenas llega para retomar si se corta: un mes de 2025 tardaba
  más de 5 minutos y la primera descarga se cayó en enero de 2025.
- **NOAA quedaba en una sola columna.** Cambié al archivo oficial `oni.ascii.txt`, que trae los
  trimestres móviles (DJF, JFM...).
- **El Excel solo leía la hoja 2023.** Ahora se guardan las 4 hojas, cada una en su archivo de
  bronce y sin interpretar nada.
- **Error en `generar_ventanas_fechas`.** Usaba `while actual < fin`, así que perdía el último
  día cuando la última ventana terminaba un día antes. Lo cambié a `<=`.
- En los extractores que corregí (XM, NOAA, TRM) quité los datos de relleno: si la fuente falla,
  el programa falla. Es mejor un error visible que un dato falso en la capa plata.

### 2026-11-11 - Capa plata

- **EnerAndes (4 hojas)**: la fila de encabezado se busca sola (las hojas 2025 y 2026 tienen
  título y notas arriba) y cada encabezado se mapea a un nombre estándar. Las fechas se leen en
  4 formatos; `01/03/2026` se lee como día/mes/año (marzo). La energía en MWh de la hoja 2024
  pasa a kWh. Una fecha de un año distinto al de su hoja va a cuarentena. Resultado: 4.007 filas
  limpias y 43 en cuarentena, con el motivo y la fila del Excel.
- **XM**: `horas_a_filas()` pasa las 24 columnas a una fila por fecha y hora.
  - Decisión: las horas vacías de generación (2,8 millones) **no** van a cuarentena. Revisé
    los datos: el 80 % son plantas solares de noche y el resto, plantas apagadas. No son
    errores sino ausencia de registro, así que se descartan y se documentan sin convertirlas en 0.
  - Decisión: el volumen útil negativo de un embalse **no** es un error (el embalse está por
    debajo de su mínimo técnico), así que se conserva.
- **NOAA**: cada trimestre móvil se asigna a su mes central (DJF → enero) y se calcula la fase
  ENSO con ±0,5.
- **IDEAM**: cada estación queda asociada a su municipio por el código DIVIPOLA. Para eso
  agregué la tabla de referencia DIVIPOLA del DANE (125 municipios de Antioquia).
- **TRM (fuente propia)**: la TRM se expande a un valor por día, porque la del viernes vale
  para el fin de semana.
- Cada tabla se valida con su esquema de pandera antes de guardarse (13 esquemas en
  `src/quality/esquemas.py`).
- El reporte de calidad (`docs/reporte_calidad.md`) se genera solo, a partir de las métricas
  de cada programa de limpieza.
- 12 pruebas nuevas en `tests/test_reglas_ea2.py`.

### 2026-11-11 - Capa oro

- dbt ampliado a 5 hechos y 6 dimensiones. `dim_mes` se reemplazó por `dim_fecha` (diaria, con
  la fase ENSO). Agregué la prueba genérica `grano_unico` para comprobar que el grano de cada
  hecho no se repite.
- Decisión: `fact_ventas_mensual` se une a `dim_fecha` por el primer día del mes, porque las
  ventas son mensuales.
- Decisión: las 14 plantas que generan pero no están en ListadoRecursos se agregan a
  `dim_recurso` con `en_catalogo = false`. Si no, su generación se perdería o fallaría la
  prueba `relationships`.
- `python -m src.transformar` construye plata y oro con un solo comando.
- `data/silver/` y `*.duckdb` quedaron fuera de git (estaban subidos desde la clase).

### Aprendizajes

- Hay que revisar la capa bronce antes de construir encima. Los datos de relleno pasaban todas
  las pruebas porque eran "válidos", pero eran falsos.
- La cuarentena es para filas con errores que no se pueden corregir, no para cualquier vacío.
  Un vacío puede significar "no pasó nada" (una planta solar de noche).

### 2026-11-11 - Resultados y entrega

- PR #2 (`feature/ea2-plata-oro-completa`) fusionado en `main`: bronce, plata y oro.
- La descarga del IDEAM (EA2) trajo 37.916 filas de precipitación y 21.938 de temperatura
  (77 y 49 estaciones). La fuente tiene huecos: pocas estaciones entre 2023-09 y 2024-10, meses
  de temperatura sin datos (2023-12 a 2024-02) y nada después de 2026-07. Lo documenté en el
  reporte de calidad en lugar de rellenar valores.
- `python -m src.transformar` desde una base vacía: 13 tablas de plata validadas con pandera,
  85 filas en cuarentena, 86 reglas en el reporte y `dbt build` con PASS=76 y ERROR=0.
  `python -m pytest`: 22 pruebas pasan.
- Hallazgos de las consultas: con El Niño el precio de bolsa promedio es 2,6 veces el de La Niña,
  y la generación térmica sube del 12 % al 29 %. Los aportes hídricos se correlacionan con el
  precio (-0,55). EnerAndes compra cerca del 22 % de su energía en bolsa todos los años.
- Documentación (modelo dimensional, diccionario, consultas y README) en un segundo PR, y luego
  el tag `ea2`.

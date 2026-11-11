# Reporte de calidad - capa plata

_Generado automaticamente por `python -m src.transformar` el 2026-11-11 18:18. No editar a mano: se reescribe en cada ejecucion._

Cada tabla de la capa plata se valida con un esquema de pandera (`src/quality/esquemas.py`) antes de guardarse: si una regla falla, la tabla no se guarda. Las filas que no se pueden corregir no se borran: quedan en un archivo `*_cuarentena.parquet` en `data/silver/` con el motivo.

## Resumen

| Fuente | Tabla(s) plata | Filas bronce | Filas plata | Filas en cuarentena | Reglas |
|---|---|---:|---:|---:|---:|
| EnerAndes - ventas 2023 a 2026 (Excel, 4 hojas) | `enerandes_ventas` | 4.184 | 4.007 | 43 | 21 |
| XM - mercado mayorista (API servapibi) | `xm_precio_bolsa_horario, xm_demanda_horaria, xm_generacion_horaria, xm_embalses_diario, xm_aportes_diario, xm_recursos` | 526.085 | 7.748.691 | 0 | 36 |
| IDEAM - precipitacion y temperatura (Antioquia) | `ideam_precipitacion_diaria, ideam_temperatura_diaria, ideam_estaciones` | 59.854 | 59.812 | 42 | 14 |
| NOAA - indice ONI | `noaa_oni_mensual` | 921 | 921 | 0 | 6 |
| Fuente propia - TRM (Superfinanciera) | `trm_diaria` | 884 | 1.369 | 0 | 6 |
| Referencia - DIVIPOLA Antioquia (DANE) | `divipola_municipios` | 125 | 125 | 0 | 3 |
| **Total** | | | | **85** | **86** |

## EnerAndes - ventas 2023 a 2026 (Excel, 4 hojas)

- Filas en bronce: 4.184
- Filas en plata: 4.007
- Filas en cuarentena: 43
  - energia vacia: 25
  - energia negativa: 18

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 1 | Titulo y notas antes del encabezado | Buscar la fila de encabezado y descartar las de arriba | 6 | 0 | 2025: 3 · 2026: 3 |
| 2 | Encabezados distintos entre hojas (nombres de columna) | Mapear cada encabezado a un nombre estandar | 29 | 8 | - |
| 3 | Filas de totales | Eliminarlas (no son una venta) | 4 | 0 | 2023: 1 · 2024: 1 · 2025: 1 · 2026: 1 |
| 4 | Filas duplicadas | Dejar una sola copia | 120 | 0 | 2023: 32 · 2024: 32 · 2025: 32 · 2026: 24 |
| 5 | Fecha DD/MM/AAAA (hoja 2026): riesgo de leer 01/03 como 3 de enero | Leer como dia/mes/anio: 01/03/2026 -> 2026-03 | 810 | 0 | 2026: 810 |
| 6 | Fechas en formatos distintos (AAAA-MM, mmm-AA, MM/AAAA, DD/MM/AAAA) | Convertir todas a AAAA-MM | 4 | 1 | MM/AAAA: 1456 · AAAA-MM: 1424 · DD/MM/AAAA: 810 · mmm-AA: 360 |
| 7 | Fecha ilegible | Pasar la fila a cuarentena | 0 | 0 | - |
| 8 | Fecha de un anio distinto al de la hoja | Pasar la fila a cuarentena | 0 | 0 | - |
| 9 | Energia en MWh mezclada con kWh (hoja 2024) | Multiplicar por 1.000 y dejar todo en kWh | 337 | 0 | 2024: 337 |
| 10 | Segmento escrito de varias formas | Unificar a Residencial, Comercial e Industrial | 6 | 3 | - |
| 11 | Segmento vacio | Marcarlo como 'No informado' | 28 | 0 | 2023: 14 · 2024: 3 · 2025: 6 · 2026: 5 |
| 12 | Tipo de compra escrito de varias formas | Unificar a Bolsa y Contrato | 4 | 2 | - |
| 13 | Municipio no reconocido o vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 14 | Municipio escrito de varias formas | Unificar con el codigo DIVIPOLA | 32 | 15 | - |
| 15 | Energia vacia | Pasar la fila a cuarentena | 25 | 0 | 2023: 9 · 2024: 6 · 2025: 5 · 2026: 5 |
| 16 | Energia negativa | Pasar la fila a cuarentena | 18 | 0 | 2023: 7 · 2024: 3 · 2025: 4 · 2026: 4 |
| 17 | Valor facturado o clientes negativos | Pasar la fila a cuarentena | 0 | 0 | - |
| 18 | Clientes vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 19 | Valor facturado vacio | Dejarlo vacio y documentarlo (no se inventa) | 28 | 28 | 2023: 7 · 2024: 11 · 2025: 4 · 2026: 6 |
| 20 | Misma venta escrita de dos formas (duplicado tras normalizar) | Dejar una sola copia | 0 | 0 | - |
| 21 | Llave repetida con valores distintos | Pasar ambas filas a cuarentena | 0 | 0 | - |

## XM - mercado mayorista (API servapibi)

- Filas en bronce: 526.085
- Filas en plata: 7.748.691
- Filas en cuarentena: 0

Las filas de bronce son anchas (un dia con 24 horas); las de plata son una por hora, por eso plata tiene unas 24 veces mas filas.

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 22 | precio: 24 columnas por hora (Hour01..Hour24) en una fila por dia | Pasar a una fila por fecha y hora | 1.369 | 32.856 | 1,369 filas x 24 horas |
| 23 | precio: valores horarios como texto | Convertir a numero | 32.856 | 0 | - |
| 24 | precio: hora sin valor (celda vacia) | Pasar la fila a cuarentena | 0 | 0 | - |
| 25 | precio: valor negativo | Pasar la fila a cuarentena | 0 | 0 | - |
| 26 | precio: valor por encima del maximo fisico (10,000) | Pasar la fila a cuarentena | 0 | 0 | - |
| 27 | precio: fila repetida (ventanas de consulta que se cruzan) | Dejar una sola copia | 0 | 0 | - |
| 28 | precio: dias del periodo sin datos | Documentar (no se inventan valores) | 0 | 0 | - |
| 29 | demanda: 24 columnas por hora (Hour01..Hour24) en una fila por dia | Pasar a una fila por fecha y hora | 1.369 | 32.856 | 1,369 filas x 24 horas |
| 30 | demanda: valores horarios como texto | Convertir a numero | 32.856 | 0 | - |
| 31 | demanda: hora sin valor (celda vacia) | Pasar la fila a cuarentena | 0 | 0 | - |
| 32 | demanda: valor negativo | Pasar la fila a cuarentena | 0 | 0 | - |
| 33 | demanda: valor por encima del maximo fisico (20,000,000) | Pasar la fila a cuarentena | 0 | 0 | - |
| 34 | demanda: fila repetida (ventanas de consulta que se cruzan) | Dejar una sola copia | 0 | 0 | - |
| 35 | demanda: dias del periodo sin datos | Documentar (no se inventan valores) | 0 | 0 | - |
| 36 | generacion: 24 columnas por hora (Hour01..Hour24) en una fila por dia | Pasar a una fila por fecha y hora | 433.844 | 10.412.256 | 433,844 filas x 24 horas |
| 37 | generacion: valores horarios como texto | Convertir a numero | 10.412.256 | 0 | - |
| 38 | generacion: hora vacia (la planta no genero: solares de noche, plantas apagadas) | Descartar: no es una medicion (no se inventa un 0) | 2.818.777 | 0 | - |
| 39 | generacion: valor negativo | Pasar la fila a cuarentena | 0 | 0 | - |
| 40 | generacion: valor por encima del maximo fisico (2,500,000) | Pasar la fila a cuarentena | 0 | 0 | - |
| 41 | generacion: fila repetida (ventanas de consulta que se cruzan) | Dejar una sola copia | 0 | 0 | - |
| 42 | embalse: fecha y valor como texto | Convertir a fecha y a numero | 32.472 | 0 | - |
| 43 | embalse: nombres con espacios o minusculas | Quitar espacios y pasar a MAYUSCULA | 0 | 0 | - |
| 44 | embalse: fecha, nombre o valor vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 45 | embalse: volumen util negativo (embalse por debajo del minimo tecnico) | Conservarlo: es un dato real de XM, no un error | 0 | 0 | - |
| 46 | embalse: fila repetida | Dejar una sola copia | 0 | 0 | - |
| 47 | embalse: mismo dia y embalse con dos valores | Pasar ambas a cuarentena | 0 | 0 | - |
| 48 | rio: fecha y valor como texto | Convertir a fecha y a numero | 54.519 | 0 | - |
| 49 | rio: nombres con espacios o minusculas | Quitar espacios y pasar a MAYUSCULA | 0 | 0 | - |
| 50 | rio: fecha, nombre o valor vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 51 | rio: valor negativo | Pasar la fila a cuarentena | 0 | 0 | - |
| 52 | rio: fila repetida | Dejar una sola copia | 0 | 0 | - |
| 53 | rio: mismo dia y rio con dos valores | Pasar ambas a cuarentena | 0 | 0 | - |
| 54 | Recursos: columnas en ingles (Code, Type, EnerSource...) | Renombrar a espanol | 9 | 0 | - |
| 55 | Recursos: codigo de planta repetido | Dejar la primera aparicion | 3 | 0 | - |
| 56 | Recursos: tipo de generacion vacio | Marcarlo como 'NO INFORMADO' | 0 | 0 | - |
| 57 | Generacion de plantas que no estan en ListadoRecursos | Conservarla; dim_recurso las marca como 'SIN CATALOGO' | 14 | 14 | 3AL6, 3E98, 3IJF, 3IRI, 3KL4, 3KOD, 3PKH, 3PKN, 3RKN, 3RKP ... |

## IDEAM - precipitacion y temperatura (Antioquia)

- Filas en bronce: 59.854
- Filas en plata: 59.812
- Filas en cuarentena: 42
  - precipitacion: precipitacion fuera de rango: 15
  - temperatura: temperatura fuera de rango: 27

Bronce ya viene agregado por dia y estacion en la consulta SoQL (los datasets completos tienen cientos de millones de registros). Limitacion de la fuente: entre 2023-09 y 2024-10 reportan muy pocas estaciones automaticas de Antioquia, y el dataset llega solo hasta 2026-07; los promedios de clima de esos meses son menos representativos.

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 58 | precipitacion: fecha y valores como texto | Convertir a fecha y a numero | 37.916 | 0 | - |
| 59 | precipitacion: fecha, estacion o valor vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 60 | precipitacion: negativa o mayor a 300 mm en un dia | Pasar la fila a cuarentena | 15 | 0 | - |
| 61 | precipitacion: municipio de la estacion no esta en DIVIPOLA | Pasar la fila a cuarentena | 0 | 0 | - |
| 62 | precipitacion: mismo dia y estacion en varias filas (cambio de nombre o coordenadas) | Consolidar en una fila por dia y estacion | 0 | 0 | - |
| 63 | precipitacion: meses sin ninguna medicion en la fuente (2023-01 a 2026-09) | Documentar (no se inventan valores) | 2 | 2 | 2026-08, 2026-09 |
| 64 | temperatura: fecha y valores como texto | Convertir a fecha y a numero | 21.938 | 0 | - |
| 65 | temperatura: fecha, estacion o valor vacio | Pasar la fila a cuarentena | 0 | 0 | - |
| 66 | temperatura: fuera de -5 a 45 C | Pasar la fila a cuarentena | 27 | 0 | - |
| 67 | temperatura: municipio de la estacion no esta en DIVIPOLA | Pasar la fila a cuarentena | 0 | 0 | - |
| 68 | temperatura: mismo dia y estacion en varias filas (cambio de nombre o coordenadas) | Consolidar en una fila por dia y estacion | 0 | 0 | - |
| 69 | temperatura: meses sin ninguna medicion en la fuente (2023-01 a 2026-09) | Documentar (no se inventan valores) | 5 | 5 | 2023-12, 2024-01, 2024-02, 2026-08, 2026-09 |
| 70 | estaciones: la misma estacion con varios nombres o coordenadas | Quedarse con el valor mas frecuente | 33 | 0 | - |
| 71 | estaciones: municipio escrito en MAYUSCULA y sin codigo | Asociar cada estacion a su municipio con el codigo DIVIPOLA | 78 | 0 | 78 estaciones en 53 municipios |

## NOAA - indice ONI

- Filas en bronce: 921
- Filas en plata: 921
- Filas en cuarentena: 0

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 72 | Valores ONI y anio como texto | Convertir a numero | 921 | 0 | - |
| 73 | Trimestre o anio no reconocido | Pasar la fila a cuarentena | 0 | 0 | - |
| 74 | ONI vacio o fuera de rango fisico (-5 a 5) | Pasar la fila a cuarentena | 0 | 0 | - |
| 75 | Trimestres moviles (DJF, JFM, ...) en vez de meses | Asignar cada trimestre a su mes central (DJF -> enero) | 12 | 0 | 12 trimestres -> 12 meses |
| 76 | Mes repetido | Dejar una sola copia | 0 | 0 | - |
| 77 | Fase ENSO no viene en la fuente | Calcularla: El Niño si ONI >= 0,5; La Niña si <= -0,5; si no Neutral | 921 | 0 | Neutral: 448 · La Niña: 238 · El Niño: 235 |

## Fuente propia - TRM (Superfinanciera)

- Filas en bronce: 884
- Filas en plata: 1.369
- Filas en cuarentena: 0

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 78 | TRM y fechas de vigencia como texto | Convertir a numero y a fecha | 884 | 0 | - |
| 79 | Vigencia vacia o al reves (hasta < desde) | Pasar la fila a cuarentena | 0 | 0 | - |
| 80 | TRM vacia o fuera de rango (1,000 a 10,000 COP/USD) | Pasar la fila a cuarentena | 0 | 0 | - |
| 81 | Una TRM vale para varios dias (fines de semana y festivos) | Expandir a una fila por dia | 212 | 0 | 884 vigencias -> 1,371 dias |
| 82 | Dia con dos TRM (vigencias que se cruzan) | Pasar ambas a cuarentena | 0 | 0 | - |
| 83 | Dias del periodo sin TRM | Documentar (no se inventan valores) | 0 | 0 | - |

## Referencia - DIVIPOLA Antioquia (DANE)

- Filas en bronce: 125
- Filas en plata: 125
- Filas en cuarentena: 0

| # | Problema | Regla aplicada | Antes | Despues | Detalle |
|---|---|---|---:|---:|---|
| 84 | Nombres de municipio en MAYUSCULA | Pasar a nombre propio ('Santa Fe de Antioquia') | 125 | 0 | - |
| 85 | Latitud y longitud con coma decimal ('6,2466') | Convertir a numero con punto | 125 | 0 | - |
| 86 | Codigo DIVIPOLA repetido | Dejar una sola copia | 0 | 0 | - |

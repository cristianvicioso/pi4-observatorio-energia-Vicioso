# Perfilamiento de Datos - Capa Bronce

## Resumen de Fuentes Ingestadas
| Dataset | Filas | Columnas | Tipos de Datos | % Nulos | Duplicados | Rango de Fechas / Alcance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `xm_generacion.parquet` | 1 | 5 | object, float64 | 0.0% | 0 | 2024-01-01 a 2026-09-30 |
| `xm_listado_recursos.parquet` | 2 | 5 | object | 0.0% | 0 | Catálogo de Recursos |
| `ideam_temperatura.parquet` | 2 | 7 | object, float64 | 0.0% | 0 | 2025-01-01 a Actual |
| `trm_colombia.parquet` | 2 | 5 | object, float64 | 0.0% | 0 | Histórico TRM |
| `noaa_oni_index.parquet` | 83 | 15 | object, float64 | 1.8% | 0 | Histórico ONI NOAA |
| `enerandes_ventas.parquet` | 1113 | 8 | object, float64 | 0.4% | 0 | Ventas 2023 - 2026 |

## Hallazgos de Calidad de Datos (5 Mínimos Requeridos)

1. **Estructura No Categórica en NOAA ONI:** El archivo original de NOAA no contiene encabezados estandarizados por columnas de texto (utiliza índices numéricos implícitos), requiriendo un casteo forzado a string en el proceso de ingesta.
2. **Inconsistencia en Tipos de Datos Monetarios (TRM):** Los valores flotantes de la tasa de cambio TRM provienen tipados como cadenas de texto (`string`) desde el endpoint de Socrata, requiriendo posterior conversión en capa Silver.
3. **Formatos Hetérogeneos en Estampas de Tiempo:** La fuente IDEAM utiliza precisión milimétrica ISO (`YYYY-MM-DDTHH:MM:SS.MMM`), mientras que XM estructura sus rangos exclusivamente por fechas de calendario (`YYYY-MM-DD`).
4. **Registros Nulos en Catálogo EnerAndes:** El dataset interno de EnerAndes presenta un 0.4% de registros con observaciones nulas en la columna de zona/segmento de ventas.
5. **Agregación por Lote en Datos Climáticos:** Las consultas SoQL a la API de IDEAM deben agruparse en servidor a nivel de estación y fecha para mitigar el consumo de memoria y descartar registros incompletos.
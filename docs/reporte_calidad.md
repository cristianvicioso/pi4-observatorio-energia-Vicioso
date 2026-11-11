# Reporte de calidad: ventas de EnerAndes (hoja 2023)

- Filas en bronce: 1,113
- Filas en plata: 1,064
- Filas en cuarentena: 16

| # | Problema | Regla aplicada | Antes | Despues |
|---|---|---|---|---|
| 1 | Filas de totales | Eliminarlas | 1 | 0 |
| 2 | Filas duplicadas | Dejar una sola copia | 32 | 0 |
| 3 | Segmento escrito de varias formas | Unificar a 3 valores | 6 | 3 |
| 4 | Segmento vacio | Marcarlo como 'No informado' | 14 | 0 |
| 5 | Tipo de compra escrito de varias formas | Unificar a Bolsa y Contrato | 4 | 2 |
| 6 | Municipio escrito de varias formas | Unificar con el codigo DIVIPOLA | 31 | 15 |
| 7 | Energia vacia o negativa | Pasar la fila a cuarentena | 16 | 0 |
| 8 | Valor facturado vacio | Dejarlo vacio y documentarlo | 7 | 7 |

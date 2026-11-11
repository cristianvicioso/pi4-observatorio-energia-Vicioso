"""
Extractor del Excel interno de EnerAndes (ventas 2023 a 2026).

El libro tiene 4 hojas (Ventas 2023 ... Ventas 2026) y cada una tiene un
formato distinto: encabezados con otros nombres, titulos y notas en las
primeras filas, una columna de unidad (solo 2024), etc.

En bronce NO se interpreta nada: cada hoja se lee completa, sin encabezado y
como texto (header=None, dtype=str), y se guarda en su propio archivo con
columnas col_0, col_1, ... Asi el titulo, las notas y el encabezado quedan
como filas, igual que en el Excel. La capa plata (src/silver/enerandes.py)
se encarga de encontrar el encabezado y unificar las 4 hojas.
"""
from pathlib import Path

import pandas as pd

from src import config

ARCHIVO = config.RAIZ / "data" / "ventas_enerandes_2023_2026.xlsx"


def extraer_enerandes_excel(ruta: Path = ARCHIVO) -> dict[str, pd.DataFrame]:
    """Devuelve {'2023': hoja_2023, '2024': ...} con cada hoja tal cual."""
    if not Path(ruta).exists():
        raise FileNotFoundError(f"No se encontro el Excel de EnerAndes en {ruta}")
    # sheet_name=None lee TODAS las hojas: devuelve {nombre_hoja: tabla}
    hojas = pd.read_excel(ruta, sheet_name=None, header=None, dtype=str)
    resultado = {}
    for nombre, hoja in hojas.items():
        anio = nombre.split()[-1]          # 'Ventas 2024' -> '2024'
        hoja.columns = [f"col_{i}" for i in range(hoja.shape[1])]
        resultado[anio] = hoja
    return resultado

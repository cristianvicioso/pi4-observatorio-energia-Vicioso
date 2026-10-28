import os
import pandas as pd

def extraer_enerandes_excel(filepath: str = "data/ventas_enerandes_2023_2026.xlsx") -> pd.DataFrame:
    """Extrae el Excel interno de EnerAndes si existe en la carpeta data."""
    if not os.path.exists(filepath):
        print(f"⚠️ Archivo {filepath} no encontrado. Se omitirá temporalmente.")
        return pd.DataFrame()
    df = pd.read_excel(filepath)
    return df
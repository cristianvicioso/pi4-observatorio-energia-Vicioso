from datetime import datetime
from pathlib import Path

import pandas as pd

from src import config


def guardar_bronze_y_sample(df: pd.DataFrame, nombre_archivo: str, raiz: Path | None = None) -> None:
    """Guarda el DataFrame en Parquet (capa bronce) y una muestra CSV de 200 filas.

    raiz permite guardar en otra carpeta (las pruebas usan una carpeta temporal
    para no ensuciar data/). Si no se indica, se usa la raiz del proyecto.
    """
    if df is None or df.empty:
        print(f"⚠️ Warning: El DataFrame para {nombre_archivo} está vacío.")
        return

    raiz = Path(raiz) if raiz is not None else config.RAIZ
    dir_bronze = raiz / "data" / "bronze"
    dir_sample = raiz / "data" / "sample"
    dir_bronze.mkdir(parents=True, exist_ok=True)
    dir_sample.mkdir(parents=True, exist_ok=True)

    # Metadatos de linaje obligatorios de la capa bronce
    df = df.copy()
    df["_fuente_origen"] = nombre_archivo
    df["_fecha_ingesta"] = datetime.now().isoformat()

    # 1. Parquet crudo en la capa bronce
    parquet_path = dir_bronze / f"{nombre_archivo}.parquet"
    df.to_parquet(parquet_path, index=False)

    # 2. Muestra CSV con las primeras 200 filas
    df.head(200).to_csv(dir_sample / f"{nombre_archivo}_sample.csv", index=False)

    print(f"✅ Guardado exitoso: {parquet_path.relative_to(raiz)} ({len(df):,} filas)")

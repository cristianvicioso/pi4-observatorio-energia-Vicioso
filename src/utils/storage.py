import os
import pandas as pd
from datetime import datetime

def guardar_bronze_y_sample(df: pd.DataFrame, nombre_archivo: str) -> None:
    """Guarda DataFrame en formato Parquet (Bronze) y Muestra CSV (200 filas)."""
    if df is None or df.empty:
        print(f"⚠️ Warning: El DataFrame para {nombre_archivo} está vacío.")
        return

    # Inyectar metadatos obligatorios de capa bronce
    df["_fuente_origen"] = nombre_archivo
    df["_fecha_ingesta"] = datetime.now().isoformat()

    os.makedirs("data/bronze", exist_ok=True)
    os.makedirs("data/sample", exist_ok=True)

    # 1. Guardar Parquet crudo en capa bronce
    parquet_path = f"data/bronze/{nombre_archivo}.parquet"
    df.to_parquet(parquet_path, index=False)
    
    # 2. Guardar muestra CSV con las primeras 200 filas
    sample_path = f"data/sample/{nombre_archivo}_sample.csv"
    df.head(200).to_csv(sample_path, index=False)
    
    print(f"✅ Guardado exitoso: {parquet_path} ({len(df)} filas)")
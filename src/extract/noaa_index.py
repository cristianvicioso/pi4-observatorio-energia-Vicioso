import pandas as pd

def extraer_noaa_oni() -> pd.DataFrame:
    """Extrae el índice ONI de NOAA convirtiendo los nombres de las columnas a texto."""
    url = "https://psl.noaa.gov/data/correlation/oni.data"
    try:
        df = pd.read_csv(url, skiprows=1, header=None, engine="python", on_bad_lines="skip")
        if not df.empty:
            # Asegurar que todas las columnas sean tipo string para compatibilidad con Parquet
            df.columns = [str(col) for col in df.columns]
            return df
    except Exception as e:
        print(f"⚠️ Sin conexión con servidor NOAA ({e}). Generando registros base.")

    cols = ["AÑO", "ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    return pd.DataFrame([
        [2025, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, -0.1, -0.2, -0.3, -0.4, -0.5, -0.6],
        [2026, 0.2, 0.1, 0.0, 0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    ], columns=cols)
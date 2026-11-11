"""
Capa PLATA: indice ONI de NOAA -> un valor por mes con la fase ENSO.

El ONI viene por trimestres moviles: DJF = diciembre, enero y febrero; JFM =
enero, febrero y marzo; ... Cada trimestre se asigna a su MES CENTRAL
(DJF -> enero, JFM -> febrero, ..., NDJ -> diciembre) para dejar un valor por mes.
El anio (YR) del archivo ya es el del mes central: 'DJF 1950' -> enero de 1950.

Fase ENSO:
  ONI >= 0.5   -> El Niño
  ONI <= -0.5  -> La Niña
  en otro caso -> Neutral

Uso:
    python -m src.silver.noaa
"""
import pandas as pd

from src.quality.esquemas import ESQUEMA_NOAA_ONI
from src.quality.reporte import Metricas, guardar_metricas
from src.silver.comun import a_numero, leer_bronce, separar, unir_cuarentena, validar_y_guardar
from src.utils import log

# Trimestre movil -> numero de su mes central
MES_CENTRAL = {"DJF": 1, "JFM": 2, "FMA": 3, "MAM": 4, "AMJ": 5, "MJJ": 6,
               "JJA": 7, "JAS": 8, "ASO": 9, "SON": 10, "OND": 11, "NDJ": 12}

UMBRAL_ENSO = 0.5


def fase_enso(oni: float) -> str:
    """0.7 -> 'El Niño'   -0.5 -> 'La Niña'   0.2 -> 'Neutral'."""
    if oni >= UMBRAL_ENSO:
        return "El Niño"
    if oni <= -UMBRAL_ENSO:
        return "La Niña"
    return "Neutral"


def trimestre_a_mes(bronce: pd.DataFrame) -> pd.DataFrame:
    """Columnas SEAS, YR, ANOM -> anio, mes, periodo (AAAA-MM), trimestre, oni."""
    df = pd.DataFrame({
        "trimestre": bronce["SEAS"].astype(str).str.strip().str.upper(),
        "anio": a_numero(bronce["YR"]),
        "oni": a_numero(bronce["ANOM"]),
        "temperatura_mar_c": a_numero(bronce["TOTAL"]) if "TOTAL" in bronce else None,
    })
    df["mes"] = df["trimestre"].map(MES_CENTRAL)
    return df


def limpiar(bronce: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    m = Metricas()
    cuarentena: list[pd.DataFrame] = []

    df = trimestre_a_mes(bronce)
    m.medir("Valores ONI y anio como texto", "Convertir a numero",
            int(bronce["ANOM"].map(lambda v: isinstance(v, str)).sum()), 0)

    malo = df["mes"].isna() | df["anio"].isna()
    m.medir("Trimestre o anio no reconocido", "Pasar la fila a cuarentena", int(malo.sum()), 0)
    df = separar(df, malo, "trimestre o anio no reconocido", cuarentena)

    sin_oni = df["oni"].isna() | ~df["oni"].between(-5, 5)
    m.medir("ONI vacio o fuera de rango fisico (-5 a 5)", "Pasar la fila a cuarentena",
            int(sin_oni.sum()), 0)
    df = separar(df, sin_oni, "ONI vacio o fuera de rango", cuarentena)

    df["anio"] = df["anio"].astype(int)
    df["mes"] = df["mes"].astype(int)
    m.medir("Trimestres moviles (DJF, JFM, ...) en vez de meses",
            "Asignar cada trimestre a su mes central (DJF -> enero)",
            df["trimestre"].nunique(), 0, "12 trimestres -> 12 meses")
    df["periodo"] = df["anio"].astype(str) + "-" + df["mes"].astype(str).str.zfill(2)

    repetido = df.duplicated(subset=["periodo"])
    m.medir("Mes repetido", "Dejar una sola copia", int(repetido.sum()), 0)
    df = df[~repetido]

    df["fase_enso"] = df["oni"].map(fase_enso)
    m.medir("Fase ENSO no viene en la fuente", "Calcularla: El Niño si ONI >= 0,5; La Niña si <= -0,5; si no Neutral",
            len(df), 0, " · ".join(f"{k}: {v}" for k, v in df["fase_enso"].value_counts().items()))

    columnas = ["periodo", "anio", "mes", "trimestre", "oni", "temperatura_mar_c", "fase_enso"]
    return (df[columnas].sort_values("periodo").reset_index(drop=True),
            unir_cuarentena(cuarentena), m.filas)


def main() -> dict:
    bronce = leer_bronce("noaa_oni_index")
    limpias, cuarentena, metricas = limpiar(bronce)
    validar_y_guardar(limpias, "noaa_oni_mensual", ESQUEMA_NOAA_ONI, cuarentena)
    resumen = {"fuente": "NOAA - indice ONI", "tabla": "noaa_oni_mensual",
               "filas_bronce": len(bronce), "filas_plata": len(limpias),
               "filas_cuarentena": len(cuarentena),
               "motivos_cuarentena": cuarentena["motivo"].value_counts().to_dict(),
               "metricas": metricas}
    guardar_metricas("noaa", resumen)
    log(f"NOAA: {len(limpias):,} meses ({limpias['periodo'].min()} a {limpias['periodo'].max()})")
    return resumen


if __name__ == "__main__":
    main()

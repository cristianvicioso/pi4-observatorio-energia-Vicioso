"""
Funciones que comparten los programas de limpieza de la capa plata.
"""
import unicodedata

import pandas as pd
import pandera.pandas as pa

from src import config
from src.utils import log

# Palabras que van en minuscula dentro de un nombre propio ('Santa Fe de Antioquia')
MINUSCULAS = {"de", "del", "la", "las", "los", "el", "y", "e"}


def sin_tildes(texto) -> str:
    """'Itagüí' -> 'itagui': minuscula, sin espacios a los lados y sin tildes."""
    letras = unicodedata.normalize("NFD", str(texto).strip().lower())
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


def nombre_propio(texto) -> str | None:
    """'SANTA FE DE  ANTIOQUIA ' -> 'Santa Fe de Antioquia' (conserva las tildes)."""
    if pd.isna(texto):
        return None
    palabras = str(texto).split()
    return " ".join(p.lower() if i > 0 and p.lower() in MINUSCULAS else p.capitalize()
                    for i, p in enumerate(palabras))


def a_numero(serie: pd.Series) -> pd.Series:
    """Texto -> numero. Acepta coma decimal ('6,2466'). Lo que no es numero queda vacio."""
    texto = serie.astype("string").str.strip().str.replace(",", ".", regex=False)
    return pd.to_numeric(texto.replace({"": None}), errors="coerce")


def leer_bronce(nombre: str) -> pd.DataFrame:
    """Lee data/bronze/<nombre>.parquet sin las columnas de linaje (_fuente_origen, ...)."""
    df = pd.read_parquet(config.DIR_BRONZE / f"{nombre}.parquet")
    return df.drop(columns=[c for c in df.columns if c.startswith("_")])


def validar_y_guardar(tabla: pd.DataFrame, nombre: str, esquema: pa.DataFrameSchema,
                      cuarentena: pd.DataFrame | None = None) -> None:
    """Valida con pandera y SOLO si pasa guarda data/silver/<nombre>.parquet.
    La cuarentena (si hay) se guarda en data/silver/<nombre>_cuarentena.parquet."""
    esquema.validate(tabla, lazy=True)
    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    tabla.to_parquet(config.DIR_SILVER / f"{nombre}.parquet", index=False)
    if cuarentena is not None:
        cuarentena.to_parquet(config.DIR_SILVER / f"{nombre}_cuarentena.parquet", index=False)
    extra = f" ({len(cuarentena):,} en cuarentena)" if cuarentena is not None else ""
    log(f"   {nombre}: {len(tabla):,} filas validadas con pandera y guardadas{extra}")


def separar(df: pd.DataFrame, mascara: pd.Series, motivo: str,
            cuarentena: list[pd.DataFrame]) -> pd.DataFrame:
    """Saca de df las filas marcadas, las agrega a la lista de cuarentena con su
    motivo y devuelve df sin ellas."""
    malas = df[mascara].copy()
    if len(malas):
        malas["motivo"] = motivo
        cuarentena.append(malas)
    return df[~mascara]


def unir_cuarentena(partes: list[pd.DataFrame]) -> pd.DataFrame:
    if not partes:
        return pd.DataFrame({"motivo": pd.Series(dtype="string")})
    df = pd.concat(partes, ignore_index=True)
    # Parquet necesita un tipo por columna: los textos se dejan como texto
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype("string")
    return df

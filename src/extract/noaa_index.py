"""
Extractor del indice ONI (Oceanic Nino Index) de NOAA.

Archivo oficial: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
Viene por trimestres moviles: una fila por (SEAS, YR) con la temperatura del
mar (TOTAL) y su anomalia (ANOM), que es el valor ONI.

    SEAS  YR   TOTAL   ANOM
     DJF 1950  25.01  -1.32
     JFM 1950  25.36  -1.20

En bronce se guarda tal cual (como texto). La capa plata asigna cada trimestre
a su mes central y calcula la fase ENSO (src/silver/noaa.py).
"""
import io

import pandas as pd
import requests

URL_ONI = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


def extraer_noaa_oni() -> pd.DataFrame:
    res = requests.get(URL_ONI, timeout=60)
    res.raise_for_status()
    # sep=r"\s+": las columnas estan separadas por uno o mas espacios
    return pd.read_csv(io.StringIO(res.text), sep=r"\s+", dtype=str)

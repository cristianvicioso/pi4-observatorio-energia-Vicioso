"""
Referencia: codigos DIVIPOLA (DANE) de los municipios de Antioquia.

Dataset gdxc-w37w de datos.gov.co. Se usa para dar a cada estacion del IDEAM
y a cada municipio de EnerAndes su codigo oficial, y asi unirlos en la
dimension dim_municipio de la capa oro.
"""
import pandas as pd
import requests

URL_DIVIPOLA = "https://www.datos.gov.co/resource/gdxc-w37w.json"


def extraer_divipola_antioquia() -> pd.DataFrame:
    params = {"$where": "cod_dpto='05'", "$limit": 1000}
    res = requests.get(URL_DIVIPOLA, params=params, timeout=60)
    res.raise_for_status()
    return pd.DataFrame(res.json())

"""
Fuente propia: TRM (Tasa Representativa del Mercado, COP por USD).

Dataset de la Superintendencia Financiera en datos.gov.co: mcec-87by.
Cada fila es una TRM con su vigencia (vigenciadesde a vigenciahasta). La TRM
del viernes suele cubrir sabado, domingo y lunes festivo, por eso una fila puede
valer para varios dias; la capa plata la expande a un valor por dia.
"""
import pandas as pd
import requests

URL_TRM = "https://www.datos.gov.co/resource/mcec-87by.json"
FECHA_INI = "2023-01-01"
FECHA_FIN = "2026-09-30"


def extraer_trm_fuente_propia(fecha_ini: str = FECHA_INI, fecha_fin: str = FECHA_FIN) -> pd.DataFrame:
    params = {
        # Se toma desde unos dias antes para cubrir el 1 de enero (festivo)
        "$where": (f"vigenciahasta >= '{fecha_ini}T00:00:00' "
                   f"AND vigenciadesde <= '{fecha_fin}T23:59:59'"),
        "$order": "vigenciadesde",
        "$limit": 50000,
    }
    res = requests.get(URL_TRM, params=params, timeout=120)
    res.raise_for_status()
    return pd.DataFrame(res.json())

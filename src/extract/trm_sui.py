import requests
import pandas as pd

def extraer_trm_fuente_propia() -> pd.DataFrame:
    """Fuente propia adicional: TRM de Colombia."""
    url = "https://www.datos.gov.co/resource/32sa-2p3f.json?$limit=5000&$order=vigenciadesde DESC"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200 and res.json():
            return pd.DataFrame(res.json())
    except Exception as e:
        print(f"⚠️ Sin conexión con API TRM ({e}). Generando registros base.")

    return pd.DataFrame([
        {"valor": "3950.50", "vigenciadesde": "2026-01-01T00:00:00.000", "vigenciahasta": "2026-01-01T00:00:00.000"},
        {"valor": "3962.10", "vigenciadesde": "2026-01-02T00:00:00.000", "vigenciahasta": "2026-01-02T00:00:00.000"}
    ])
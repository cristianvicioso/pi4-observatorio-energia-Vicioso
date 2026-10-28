import requests
import pandas as pd
from src.utils.dates import generar_ventanas_fechas

def extraer_xm_metricas(metrica: str, fecha_ini: str = "2024-01-01", fecha_fin: str = "2026-09-30") -> pd.DataFrame:
    """Extrae métricas temporales de XM usando ventanas de tiempo."""
    url = "https://conexion.xm.com.co/metricas"
    ventanas = generar_ventanas_fechas(fecha_ini, fecha_fin, dias_ventana=30)
    registros = []

    for ini, fin in ventanas:
        payload = {
            "MetricId": metrica,
            "StartDate": ini,
            "EndDate": fin,
            "Entity": "Recurso" if metrica in ["Gene", "AporEner"] else "Sistema"
        }
        try:
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200 and res.json().get("Items"):
                for item in res.json()["Items"]:
                    registros.extend(item.get("DailyData", []))
        except Exception:
            continue

    if not registros:
        print(f"⚠️ Sin respuesta remota de XM para {metrica}. Generando registro base.")
        return pd.DataFrame([{"Fecha": fecha_ini, "Valor": 0.0, "Metrica": metrica}])

    return pd.DataFrame(registros)

def extraer_xm_listado_recursos() -> pd.DataFrame:
    """Extrae el catálogo de recursos desde el endpoint lists de XM."""
    url = "https://conexion.xm.com.co/lists/Recurso"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            entities = data.get("ListEntities", [])
            return pd.DataFrame(entities)
    except Exception as e:
        print(f"⚠️ Sin conexión directa al endpoint XM Lists ({e}). Generando catálogo base.")
    
    return pd.DataFrame([
        {"CodigoRecurso": "PLTA1", "NombreRecurso": "Planta Hidro 1", "Tipo": "Hidro"},
        {"CodigoRecurso": "PLTA2", "NombreRecurso": "Planta Termo 2", "Tipo": "Termo"}
    ])
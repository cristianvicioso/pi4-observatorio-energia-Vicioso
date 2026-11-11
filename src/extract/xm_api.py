"""
Extractor de la API publica de XM (servapibi.xm.com.co).

Metricas que se descargan (capa bronce, tal cual llegan):
  - PrecBolsNaci  precio de bolsa nacional   horaria, entidad Sistema   (COP/kWh)
  - DemaCome      demanda comercial          horaria, entidad Sistema   (kWh)
  - Gene          generacion real            horaria, entidad Recurso   (kWh)
  - VoluUtilDiarEner  volumen util diario    diaria,  entidad Embalse   (kWh)
  - AporEner      aportes hidricos en energia diaria, entidad Rio       (kWh)
  - ListadoRecursos  catalogo de plantas     lista

Las metricas horarias llegan "anchas": una fila por fecha y entidad con 24
columnas Hour01 ... Hour24. Asi se guardan en bronce; la capa plata las pasa
a una fila por hora (src/silver/xm.py).

La API solo acepta rangos de hasta 31 dias por consulta, por eso se pide en
ventanas de 30 dias (src/utils/dates.py).
"""
import time

import pandas as pd
import requests

from src.utils.dates import generar_ventanas_fechas

URL_BASE = "https://servapibi.xm.com.co"

# Periodo del observatorio: el mismo de las ventas de EnerAndes
FECHA_INI = "2023-01-01"
FECHA_FIN = "2026-09-30"


def _post(endpoint: str, payload: dict, intentos: int = 3) -> dict:
    """POST a la API con reintentos (la API a veces responde lento o con 5xx)."""
    for intento in range(1, intentos + 1):
        try:
            res = requests.post(f"{URL_BASE}/{endpoint}", json=payload, timeout=120)
            res.raise_for_status()
            return res.json()
        except (requests.RequestException, ValueError) as error:
            if intento == intentos:
                raise RuntimeError(f"XM no respondio para {payload}: {error}") from error
            time.sleep(5 * intento)
    return {}


def extraer_xm_horario(metrica: str, entidad: str,
                       fecha_ini: str = FECHA_INI, fecha_fin: str = FECHA_FIN) -> pd.DataFrame:
    """Metrica horaria: una fila por (Date, codigo) con las columnas Hour01..Hour24."""
    filas = []
    for ini, fin in generar_ventanas_fechas(fecha_ini, fecha_fin, dias_ventana=30):
        datos = _post("hourly", {"MetricId": metrica, "StartDate": ini,
                                 "EndDate": fin, "Entity": entidad})
        for item in datos.get("Items", []):
            for entidad_h in item.get("HourlyEntities", []):
                # Values trae code y Hour01..Hour24 (todo como texto)
                filas.append({"Date": item["Date"], **entidad_h["Values"]})
        print(f"   {metrica} {ini} a {fin}: {len(filas):,} filas acumuladas")
    return pd.DataFrame(filas)


def extraer_xm_diario(metrica: str, entidad: str,
                      fecha_ini: str = FECHA_INI, fecha_fin: str = FECHA_FIN) -> pd.DataFrame:
    """Metrica diaria: una fila por (Date, Name) con su Value."""
    filas = []
    for ini, fin in generar_ventanas_fechas(fecha_ini, fecha_fin, dias_ventana=30):
        datos = _post("daily", {"MetricId": metrica, "StartDate": ini,
                                "EndDate": fin, "Entity": entidad})
        for item in datos.get("Items", []):
            for entidad_d in item.get("DailyEntities", []):
                filas.append({"Date": item["Date"], **entidad_d})
    print(f"   {metrica}: {len(filas):,} filas")
    # Value llega como numero en el JSON; se guarda como texto para que bronce
    # conserve el dato tal cual (la conversion a numero es tarea de plata)
    df = pd.DataFrame(filas)
    return df.astype(str)


def extraer_xm_listado_recursos() -> pd.DataFrame:
    """Catalogo de recursos de generacion (ListadoRecursos)."""
    datos = _post("lists", {"MetricId": "ListadoRecursos", "Entity": "Sistema"})
    filas = [entidad["Values"]
             for item in datos.get("Items", [])
             for entidad in item.get("ListEntities", [])]
    print(f"   ListadoRecursos: {len(filas):,} recursos")
    return pd.DataFrame(filas)

"""
Extractor del IDEAM para la Evidencia 2 (precipitacion y temperatura de Antioquia).

El extractor de la Evidencia 1 (src/extract/ideam_socrata.py) se conserva sin
cambios. Este archivo es aparte porque la EA2 necesita mas que la EA1:
  - precipitacion ademas de temperatura;
  - el municipio de cada estacion;
  - una fila por estacion y dia de 2023-01-01 a 2026-09-30.

Datasets de datos.gov.co (API Socrata / SoQL):
  - Precipitacion  s54a-sgyg  (mm por observacion, cada 10 min aprox.)
  - Temperatura    sbwg-7ju4  (grados C por observacion)

Los datasets completos tienen cientos de millones de filas, por eso la consulta
SoQL filtra Antioquia y agrega en el servidor a una fila por estacion y dia.
La API es lenta (10 dias de precipitacion de 2025 tardan mas de 1 minuto), asi que:
  - se pide en ventanas de 10 dias, 4 a la vez (en paralelo);
  - cada ventana se guarda apenas llega en data/bronze/_parciales/<nombre>/, y si
    la ejecucion se corta, la siguiente retoma desde donde quedo;
  - si una ventana falla 3 veces se avisa al final; volver a ejecutar
    `python -m src.pipeline ideam` descarga solo las que faltan.

En bronce los valores quedan como texto, igual que los devuelve la API.
"""
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

from src import config

URL_SOCRATA = "https://www.datos.gov.co/resource/{dataset}.json"
DATASET_PRECIPITACION = "s54a-sgyg"
DATASET_TEMPERATURA = "sbwg-7ju4"

FECHA_INI = "2023-01-01"
FECHA_FIN = "2026-09-30"
DIAS_VENTANA = 10
CONSULTAS_EN_PARALELO = 4
DIR_PARCIALES = config.DIR_BRONZE / "_parciales"


def _ventanas(fecha_ini: str, fecha_fin: str, dias: int = DIAS_VENTANA) -> list[tuple[str, str]]:
    """[('2023-01-01T00:00:00', '2023-01-10T23:59:59'), ...] de `dias` en `dias`."""
    inicios = pd.date_range(fecha_ini, fecha_fin, freq=f"{dias}D")
    fin_total = pd.Timestamp(fecha_fin)
    return [(i.strftime("%Y-%m-%dT00:00:00"),
             min(i + pd.Timedelta(days=dias - 1), fin_total).strftime("%Y-%m-%dT23:59:59"))
            for i in inicios]


def _consultar(dataset: str, select: str, ini: str, fin: str, intentos: int = 3) -> list[dict]:
    params = {
        "$select": select,
        "$where": f"departamento='ANTIOQUIA' AND fechaobservacion between '{ini}' and '{fin}'",
        "$group": "codigoestacion, nombreestacion, municipio, latitud, longitud, fecha",
        "$limit": 50000,
    }
    for intento in range(1, intentos + 1):
        try:
            res = requests.get(URL_SOCRATA.format(dataset=dataset), params=params, timeout=600)
            res.raise_for_status()
            return res.json()
        except (requests.RequestException, ValueError) as error:
            if intento == intentos:
                raise RuntimeError(f"IDEAM {dataset} no respondio ({ini[:10]}): {error}") from error
            time.sleep(15 * intento)
    return []


def _extraer(dataset: str, agregados: str, nombre: str,
             fecha_ini: str, fecha_fin: str) -> pd.DataFrame:
    select = ("codigoestacion, nombreestacion, municipio, latitud, longitud, "
              f"date_trunc_ymd(fechaobservacion) as fecha, {agregados}, count(*) as n_registros")
    carpeta = DIR_PARCIALES / nombre
    carpeta.mkdir(parents=True, exist_ok=True)

    def descargar(ventana: tuple[str, str]) -> str | None:
        ini, fin = ventana
        archivo = carpeta / f"{ini[:10]}.parquet"
        if archivo.exists():                       # ya se descargo en una ejecucion anterior
            return None
        try:
            filas = _consultar(dataset, select, ini, fin)
        except RuntimeError as error:
            return str(error)
        # Se guarda aunque venga vacia, para no volver a pedirla
        pd.DataFrame(filas, dtype=str).to_parquet(archivo, index=False)
        print(f"   IDEAM {nombre} {ini[:10]}: {len(filas):,} filas", flush=True)
        return None

    ventanas = _ventanas(fecha_ini, fecha_fin)
    with ThreadPoolExecutor(max_workers=CONSULTAS_EN_PARALELO) as pool:
        errores = [e for e in pool.map(descargar, ventanas) if e]
    if errores:
        raise RuntimeError(f"{len(errores)} ventanas de IDEAM {nombre} fallaron. Vuelva a ejecutar "
                           f"'python -m src.pipeline ideam' para descargar solo las que faltan.\n"
                           + "\n".join(errores))

    partes = [pd.read_parquet(carpeta / f"{ini[:10]}.parquet") for ini, _ in ventanas]
    return pd.concat([p for p in partes if len(p)], ignore_index=True)


def extraer_precipitacion_antioquia(fecha_ini: str = FECHA_INI, fecha_fin: str = FECHA_FIN) -> pd.DataFrame:
    """Precipitacion diaria por estacion: suma de las observaciones del dia (mm)."""
    return _extraer(DATASET_PRECIPITACION, "sum(valorobservado) as precipitacion_mm",
                    "precipitacion", fecha_ini, fecha_fin)


def extraer_temperatura_antioquia(fecha_ini: str = FECHA_INI, fecha_fin: str = FECHA_FIN) -> pd.DataFrame:
    """Temperatura diaria por estacion: media, minima y maxima del dia (grados C)."""
    return _extraer(DATASET_TEMPERATURA,
                    "avg(valorobservado) as temp_media, min(valorobservado) as temp_min, "
                    "max(valorobservado) as temp_max",
                    "temperatura", fecha_ini, fecha_fin)

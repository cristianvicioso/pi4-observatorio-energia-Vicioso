"""
Capa PLATA de la tabla de referencia DIVIPOLA (DANE): municipios de Antioquia.

Sirve para dos cosas:
  - dar a cada estacion del IDEAM el codigo de su municipio (src/silver/ideam.py)
  - construir dim_municipio en la capa oro con todos los municipios de Antioquia

Uso:
    python -m src.silver.divipola
"""
import pandas as pd

from src.quality.esquemas import ESQUEMA_DIVIPOLA
from src.quality.reporte import Metricas, guardar_metricas
from src.silver.comun import a_numero, leer_bronce, nombre_propio, sin_tildes, validar_y_guardar
from src.silver.enerandes import MUNICIPIOS
from src.utils import log


def limpiar(bronce: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    m = Metricas()
    df = pd.DataFrame({
        "divipola": bronce["cod_mpio"].astype(str).str.strip().str.zfill(5),
        "municipio": bronce["nom_mpio"].map(nombre_propio),
        "departamento": bronce["dpto"].map(nombre_propio),
        "latitud": a_numero(bronce["latitud"]),
        "longitud": a_numero(bronce["longitud"]),
    })
    m.medir("Nombres de municipio en MAYUSCULA", "Pasar a nombre propio ('Santa Fe de Antioquia')",
            int((bronce["nom_mpio"] == bronce["nom_mpio"].str.upper()).sum()), 0)
    m.medir("Latitud y longitud con coma decimal ('6,2466')", "Convertir a numero con punto",
            int(bronce["latitud"].astype(str).str.contains(",").sum()), 0)
    repetido = df.duplicated(subset=["divipola"])
    m.medir("Codigo DIVIPOLA repetido", "Dejar una sola copia", int(repetido.sum()), 0)
    df = df[~repetido]
    # Municipios donde EnerAndes vende energia
    codigos_enerandes = {codigo for codigo, _ in MUNICIPIOS.values()}
    df["atendido_enerandes"] = df["divipola"].isin(codigos_enerandes)
    df["clave"] = df["municipio"].map(sin_tildes)
    return df.sort_values("divipola").reset_index(drop=True), m.filas


def main() -> dict:
    bronce = leer_bronce("divipola_municipios")
    limpias, metricas = limpiar(bronce)
    validar_y_guardar(limpias, "divipola_municipios", ESQUEMA_DIVIPOLA)
    resumen = {"fuente": "Referencia - DIVIPOLA Antioquia (DANE)", "tabla": "divipola_municipios",
               "filas_bronce": len(bronce), "filas_plata": len(limpias), "filas_cuarentena": 0,
               "metricas": metricas}
    guardar_metricas("divipola", resumen)
    log(f"DIVIPOLA: {len(limpias)} municipios ({int(limpias['atendido_enerandes'].sum())} de EnerAndes)")
    return resumen


if __name__ == "__main__":
    main()

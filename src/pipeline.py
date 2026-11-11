"""
Capa BRONCE: descarga todas las fuentes y las guarda tal cual en data/bronze/.

Uso:
    python -m src.pipeline              # todas las fuentes
    python -m src.pipeline xm noaa      # solo algunas (xm, ideam, noaa, trm, enerandes, divipola)
"""
import sys

from src.extract.divipola import extraer_divipola_antioquia
from src.extract.enerandes_excel import extraer_enerandes_excel
from src.extract.ideam_ea2 import extraer_precipitacion_antioquia, extraer_temperatura_antioquia
from src.extract.ideam_socrata import extraer_ideam_temperatura
from src.extract.noaa_index import extraer_noaa_oni
from src.extract.trm_sui import extraer_trm_fuente_propia
from src.extract.xm_api import extraer_xm_diario, extraer_xm_horario, extraer_xm_listado_recursos
from src.utils.storage import guardar_bronze_y_sample


def bronce_xm() -> None:
    print("-> XM: precio de bolsa, demanda y generacion (horarias)")
    guardar_bronze_y_sample(extraer_xm_horario("PrecBolsNaci", "Sistema"), "xm_precio_bolsa")
    guardar_bronze_y_sample(extraer_xm_horario("DemaCome", "Sistema"), "xm_demanda")
    guardar_bronze_y_sample(extraer_xm_horario("Gene", "Recurso"), "xm_generacion")
    print("-> XM: embalses y aportes (diarios) y catalogo de recursos")
    guardar_bronze_y_sample(extraer_xm_diario("VoluUtilDiarEner", "Embalse"), "xm_embalses")
    guardar_bronze_y_sample(extraer_xm_diario("AporEner", "Rio"), "xm_aportes")
    guardar_bronze_y_sample(extraer_xm_listado_recursos(), "xm_listado_recursos")


def bronce_ideam() -> None:
    # Extractor de la Evidencia 1, sin cambios
    print("-> IDEAM (EA1): temperatura")
    guardar_bronze_y_sample(extraer_ideam_temperatura(), "ideam_temperatura")
    # Extractor de la Evidencia 2 (archivo aparte): precipitacion y temperatura
    # diarias por estacion en Antioquia, con el municipio de cada estacion
    print("-> IDEAM (EA2): precipitacion y temperatura diarias de Antioquia")
    guardar_bronze_y_sample(extraer_precipitacion_antioquia(), "ideam_precipitacion_antioquia")
    guardar_bronze_y_sample(extraer_temperatura_antioquia(), "ideam_temperatura_antioquia")


def bronce_noaa() -> None:
    print("-> NOAA: indice ONI")
    guardar_bronze_y_sample(extraer_noaa_oni(), "noaa_oni_index")


def bronce_trm() -> None:
    print("-> Fuente propia: TRM")
    guardar_bronze_y_sample(extraer_trm_fuente_propia(), "trm_colombia")


def bronce_divipola() -> None:
    print("-> Referencia: DIVIPOLA de Antioquia (DANE)")
    guardar_bronze_y_sample(extraer_divipola_antioquia(), "divipola_municipios")


def bronce_enerandes() -> None:
    print("-> EnerAndes: las 4 hojas del Excel")
    for anio, hoja in extraer_enerandes_excel().items():
        guardar_bronze_y_sample(hoja, f"enerandes_ventas_{anio}")


FUENTES = {
    "enerandes": bronce_enerandes,
    "divipola": bronce_divipola,
    "noaa": bronce_noaa,
    "trm": bronce_trm,
    "xm": bronce_xm,
    "ideam": bronce_ideam,
}


def ejecutar_pipeline(fuentes: list[str] | None = None) -> None:
    print("🚀 Capa bronce - Observatorio Energia y Clima")
    for nombre in fuentes or list(FUENTES):
        FUENTES[nombre]()
    print("✅ Bronce listo en data/bronze/ (muestras en data/sample/)")


if __name__ == "__main__":
    ejecutar_pipeline(sys.argv[1:] or None)

"""
Construye las capas PLATA y ORO con un solo comando.

    python -m src.transformar

1. Limpia todas las fuentes de data/bronze/ (cada programa valida su tabla con
   pandera antes de guardarla en data/silver/).
2. Escribe docs/reporte_calidad.md con las metricas antes/despues de cada regla.
3. Ejecuta `dbt build`: crea el esquema estrella en data/observatorio.duckdb y
   corre todas las pruebas de dbt.

Requisito: que exista la capa bronce (python -m src.pipeline).
Opciones:
    python -m src.transformar --solo-plata    # sin dbt
"""
import shutil
import subprocess
import sys

from src import config
from src.quality.reporte import escribir_reporte
from src.silver import divipola, enerandes, ideam, noaa, trm, xm
from src.utils import log

# Orden: divipola antes que ideam (ideam la usa para asignar el municipio a cada estacion)
PASOS_PLATA = [
    ("EnerAndes", enerandes.main),
    ("DIVIPOLA", divipola.main),
    ("NOAA", noaa.main),
    ("TRM", trm.main),
    ("XM", xm.main),
    ("IDEAM", ideam.main),
]


def construir_plata() -> None:
    for nombre, paso in PASOS_PLATA:
        log(f"=== Plata: {nombre}")
        paso()
    escribir_reporte()
    log("Reporte de calidad: docs/reporte_calidad.md")


def construir_oro() -> None:
    dbt = shutil.which("dbt")
    if dbt is None:
        raise SystemExit("No se encontro el comando dbt. Instale las dependencias: pip install -r requirements.txt")
    log("=== Oro: dbt build")
    # Se ejecuta desde la raiz del proyecto: profiles.yml y sources.yml usan rutas
    # relativas a ella (data/observatorio.duckdb y data/silver/*.parquet)
    resultado = subprocess.run(
        [dbt, "build", "--project-dir", "dbt", "--profiles-dir", "dbt"], cwd=config.RAIZ)
    if resultado.returncode != 0:
        raise SystemExit("dbt build termino con errores")
    log("Capa oro lista en data/observatorio.duckdb")


def main(argumentos: list[str]) -> None:
    construir_plata()
    if "--solo-plata" not in argumentos:
        construir_oro()


if __name__ == "__main__":
    main(sys.argv[1:])

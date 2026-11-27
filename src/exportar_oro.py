"""
Exporta las tablas de la capa ORO a archivos Parquet.

Lee data/observatorio.duckdb (lo crea dbt build) y guarda cada tabla del
esquema estrella en data/gold/<tabla>.parquet. Esos archivos los usa el
dashboard, y en GitHub Actions se publican como artefacto de la ejecucion.

Uso:
    python -m src.exportar_oro
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
from pathlib import Path    # Path: rutas de archivos y carpetas que sirven en Windows y en Linux

import duckdb               # duckdb: la base de datos donde dbt dejo la capa oro

from src import config      # config: las rutas del proyecto (config.RAIZ es la carpeta raiz)
from src.utils import log   # log: escribe un mensaje con la hora al inicio

# Lista con los nombres de las tablas del esquema estrella que crea dbt
# (los archivos .sql de dbt/models/marts/). Se exporta una por una
TABLAS_ORO = [
    "dim_fecha", "dim_municipio", "dim_segmento", "dim_recurso", "dim_estacion",
    "fact_ventas_mensual", "fact_mercado_horario", "fact_generacion_recurso",
    "fact_hidrologia_diaria", "fact_clima_diario",
]


# ---------------------------------------------------------------------------
# EXPORTAR
# ---------------------------------------------------------------------------
# Funcion que recibe: la ruta de la base (ruta_db), la carpeta donde se
# guardan los Parquet (carpeta) y la lista de tablas (tablas).
# Devuelve (->) una lista con las rutas de los archivos creados
def exportar(ruta_db: Path, carpeta: Path, tablas: list[str]) -> list[Path]:
    """Guarda cada tabla de la base ruta_db en carpeta/<tabla>.parquet.
    Devuelve la lista de archivos creados."""
    # Crea la carpeta de salida. parents=True crea tambien las carpetas de
    # arriba si faltan; exist_ok=True evita el error si ya existe
    carpeta.mkdir(parents=True, exist_ok=True)
    # Abre la base de datos. str() convierte la ruta en texto, que es lo que
    # pide duckdb. read_only=True: solo lectura, exportar no cambia nada
    con = duckdb.connect(str(ruta_db), read_only=True)
    # Lista vacia donde se van guardando las rutas de los archivos creados
    archivos = []
    # Recorre la lista de tablas: en cada vuelta, tabla vale un nombre
    for tabla in tablas:
        # Arma la ruta del archivo: carpeta / "dim_fecha.parquet", por ejemplo
        archivo = carpeta / f"{tabla}.parquet"
        # Ejecuta en DuckDB la instruccion COPY: copia toda la tabla al archivo
        # en formato Parquet. as_posix() escribe la ruta con "/" en vez de "\"
        con.execute(f"COPY {tabla} TO '{archivo.as_posix()}' (FORMAT parquet)")
        # Cuenta las filas de la tabla. fetchone() trae la primera fila del
        # resultado y [0] su primer valor: el numero de filas
        filas = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
        # Muestra el nombre del archivo (34 espacios, a la izquierda: <34)
        # y las filas (10 espacios, a la derecha: >10), para que queden en columnas
        log(f"   {archivo.name:<34}{filas:>10} filas")
        # Agrega la ruta del archivo a la lista de archivos creados
        archivos.append(archivo)
    # Cierra la conexion con la base: libera el archivo .duckdb
    con.close()
    # Devuelve la lista de archivos creados (la prueba la revisa)
    return archivos


# ---------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
# Funcion que se ejecuta con python -m src.exportar_oro. No recibe nada (sin
# parametros) y no devuelve nada (-> None)
def main() -> None:
    # Mensaje de inicio
    log("Exportando la capa oro a Parquet")
    # Llama a exportar() con las rutas reales del proyecto:
    # la base data/observatorio.duckdb, la carpeta data/gold y las tablas oro
    archivos = exportar(config.RAIZ / "data" / "observatorio.duckdb",
                        config.RAIZ / "data" / "gold", TABLAS_ORO)
    # Mensaje final con cuantos archivos se crearon. len() cuenta la lista
    log(f"Listo: {len(archivos)} archivos en data/gold/")


# __name__ vale "__main__" solo cuando se ejecuta este archivo
# (python -m src.exportar_oro). Si la prueba lo importa, main() no se ejecuta
if __name__ == "__main__":
    # Ejecuta el programa principal
    main()

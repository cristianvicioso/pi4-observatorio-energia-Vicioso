"""
Prueba automatica de la exportacion de la capa oro.

Crea una base DuckDB pequena en una carpeta temporal, con dos tablas de
ejemplo, la exporta y comprueba que quede un Parquet por tabla con sus filas.
No necesita internet ni data/observatorio.duckdb: se ejecuta en un segundo.

Uso:
    python -m pytest -v
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import duckdb           # duckdb: para crear una base de datos de ejemplo
import pandas as pd     # pandas: para leer los Parquet que crea la exportacion

from src.exportar_oro import exportar   # la funcion que se va a probar


# ---------------------------------------------------------------------------
# PRUEBA
# ---------------------------------------------------------------------------
# Una prueba es una funcion cuyo nombre empieza por test_: pytest la busca y
# la ejecuta sola. tmp_path lo da pytest: una carpeta temporal nueva para esta
# prueba, que se borra sola. Asi la prueba no toca los datos reales
def test_exporta_un_parquet_por_tabla(tmp_path):
    # --- 1. Preparar: una base con dos tablas de ejemplo ---
    # La ruta de la base de ejemplo, dentro de la carpeta temporal
    ruta_db = tmp_path / "ejemplo.duckdb"
    # Crea la base (el archivo no existe: duckdb lo crea) y se conecta
    con = duckdb.connect(str(ruta_db))
    # Crea la tabla dim_mes con 3 filas: range(3) da 0, 1 y 2, y
    # t(mes_id) le pone a esa columna el nombre mes_id
    con.execute("CREATE TABLE dim_mes AS SELECT * FROM range(3) t(mes_id)")
    # Crea la tabla dim_segmento con 2 filas. UNION ALL junta los dos SELECT:
    # una fila con 'Residencial' y otra con 'Industrial'
    con.execute("CREATE TABLE dim_segmento AS SELECT 'Residencial' AS segmento "
                "UNION ALL SELECT 'Industrial'")
    # Cierra la base, para que exportar() la pueda abrir
    con.close()

    # --- 2. Ejecutar: exportar las dos tablas a la carpeta gold ---
    # Llama a la funcion que se prueba y guarda la lista de archivos creados
    archivos = exportar(ruta_db, tmp_path / "gold", ["dim_mes", "dim_segmento"])

    # --- 3. Comprobar: assert detiene la prueba si la condicion es falsa ---
    # Se creo un archivo por tabla, con el nombre de la tabla.
    # [a.name for a in archivos] arma la lista de los nombres de los archivos
    assert [a.name for a in archivos] == ["dim_mes.parquet", "dim_segmento.parquet"]
    # El archivo de dim_mes tiene 3 filas: len() cuenta las filas de la tabla leida
    assert len(pd.read_parquet(tmp_path / "gold" / "dim_mes.parquet")) == 3
    # El archivo de dim_segmento tiene 2 filas
    assert len(pd.read_parquet(tmp_path / "gold" / "dim_segmento.parquet")) == 2

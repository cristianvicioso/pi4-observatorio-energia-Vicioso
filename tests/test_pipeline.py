from src.utils.storage import guardar_bronze_y_sample
import pandas as pd


def test_guardar_bronze_y_sample(tmp_path):
    # tmp_path es una carpeta temporal que crea pytest: asi la prueba no ensucia data/
    df_test = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    guardar_bronze_y_sample(df_test, "test_archivo", raiz=tmp_path)
    assert (tmp_path / "data" / "sample" / "test_archivo_sample.csv").exists()
    bronce = pd.read_parquet(tmp_path / "data" / "bronze" / "test_archivo.parquet")
    # La capa bronce agrega las dos columnas de linaje
    assert {"_fuente_origen", "_fecha_ingesta"}.issubset(bronce.columns)

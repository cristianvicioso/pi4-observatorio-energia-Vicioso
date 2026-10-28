import os
import pandas as pd
from src.utils.storage import guardar_bronze_y_sample

def test_guardar_bronze_y_sample():
    df_test = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    guardar_bronze_y_sample(df_test, "test_archivo")
    assert os.path.exists("data/sample/test_archivo_sample.csv")
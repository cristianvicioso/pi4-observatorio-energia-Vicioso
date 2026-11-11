"""
Capa PLATA de la fuente propia: TRM (pesos por dolar) -> un valor por dia.

La fuente trae una fila por vigencia: la TRM del viernes vale para sabado,
domingo y el lunes festivo (vigenciadesde a vigenciahasta). Para poder cruzarla
con el precio de bolsa, que es diario/horario, se expande a una fila por dia.

Uso:
    python -m src.silver.trm
"""
import pandas as pd

from src.quality.esquemas import ESQUEMA_TRM
from src.quality.reporte import Metricas, guardar_metricas
from src.silver.comun import a_numero, leer_bronce, separar, unir_cuarentena, validar_y_guardar
from src.utils import log

FECHA_INI = "2023-01-01"
FECHA_FIN = "2026-09-30"
RANGO_TRM = (1_000, 10_000)   # COP por USD: fuera de esto es un error de digitacion


def expandir_vigencias(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por cada dia entre vigenciadesde y vigenciahasta.
    (2023-01-06 a 2023-01-09, 4900) -> 4 filas: 06, 07, 08 y 09 de enero con 4900."""
    dias = [pd.date_range(d, h, freq="D") for d, h in zip(df["desde"], df["hasta"])]
    expandida = df.assign(fecha=dias).explode("fecha")
    expandida["fecha"] = pd.to_datetime(expandida["fecha"])
    return expandida[["fecha", "trm_cop_usd"]]


def limpiar(bronce: pd.DataFrame, fecha_ini: str = FECHA_INI,
            fecha_fin: str = FECHA_FIN) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    m = Metricas()
    cuarentena: list[pd.DataFrame] = []

    df = pd.DataFrame({
        "trm_cop_usd": a_numero(bronce["valor"]),
        "desde": pd.to_datetime(bronce["vigenciadesde"], errors="coerce").dt.normalize(),
        "hasta": pd.to_datetime(bronce["vigenciahasta"], errors="coerce").dt.normalize(),
        "unidad": bronce.get("unidad"),
    })
    m.medir("TRM y fechas de vigencia como texto", "Convertir a numero y a fecha", len(df), 0)

    mala_fecha = df["desde"].isna() | df["hasta"].isna() | (df["hasta"] < df["desde"])
    m.medir("Vigencia vacia o al reves (hasta < desde)", "Pasar la fila a cuarentena",
            int(mala_fecha.sum()), 0)
    df = separar(df, mala_fecha, "vigencia invalida", cuarentena)

    fuera = df["trm_cop_usd"].isna() | ~df["trm_cop_usd"].between(*RANGO_TRM)
    m.medir(f"TRM vacia o fuera de rango ({RANGO_TRM[0]:,} a {RANGO_TRM[1]:,} COP/USD)",
            "Pasar la fila a cuarentena", int(fuera.sum()), 0)
    df = separar(df, fuera, "TRM vacia o fuera de rango", cuarentena)

    if df["unidad"].notna().any():
        otra_unidad = df["unidad"].fillna("COP").str.upper() != "COP"
        df = separar(df, otra_unidad, "unidad distinta de COP", cuarentena)

    varios_dias = (df["hasta"] - df["desde"]).dt.days > 0
    diaria = expandir_vigencias(df)
    m.medir("Una TRM vale para varios dias (fines de semana y festivos)",
            "Expandir a una fila por dia", int(varios_dias.sum()), 0,
            f"{len(df):,} vigencias -> {len(diaria):,} dias")

    diaria = diaria[diaria["fecha"].between(fecha_ini, fecha_fin)]
    repetido = diaria.duplicated(subset=["fecha"], keep=False)
    m.medir("Dia con dos TRM (vigencias que se cruzan)", "Pasar ambas a cuarentena",
            int(repetido.sum()), 0)
    diaria = separar(diaria, repetido, "dia con dos TRM", cuarentena)

    esperados = pd.date_range(fecha_ini, fecha_fin, freq="D")
    faltan = len(set(esperados) - set(diaria["fecha"]))
    m.medir("Dias del periodo sin TRM", "Documentar (no se inventan valores)", faltan, faltan)

    diaria["trm_cop_usd"] = diaria["trm_cop_usd"].astype(float)
    cuarentena_df = unir_cuarentena(cuarentena)
    for col in ["desde", "hasta", "fecha"]:
        if col in cuarentena_df:
            cuarentena_df[col] = pd.to_datetime(cuarentena_df[col])
    return diaria.sort_values("fecha").reset_index(drop=True), cuarentena_df, m.filas


def main() -> dict:
    bronce = leer_bronce("trm_colombia")
    limpias, cuarentena, metricas = limpiar(bronce)
    validar_y_guardar(limpias, "trm_diaria", ESQUEMA_TRM, cuarentena)
    resumen = {"fuente": "Fuente propia - TRM (Superfinanciera)", "tabla": "trm_diaria",
               "filas_bronce": len(bronce), "filas_plata": len(limpias),
               "filas_cuarentena": len(cuarentena),
               "motivos_cuarentena": cuarentena["motivo"].value_counts().to_dict(),
               "metricas": metricas}
    guardar_metricas("trm", resumen)
    log(f"TRM: {len(limpias):,} dias")
    return resumen


if __name__ == "__main__":
    main()

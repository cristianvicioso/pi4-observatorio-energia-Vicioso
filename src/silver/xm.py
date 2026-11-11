"""
Capa PLATA de XM: mercado mayorista de energia.

Tablas que produce (data/silver/):
  - xm_precio_bolsa_horario   fecha, hora, precio_bolsa_cop_kwh
  - xm_demanda_horaria        fecha, hora, demanda_kwh
  - xm_generacion_horaria     fecha, hora, codigo_recurso, generacion_kwh
  - xm_embalses_diario        fecha, embalse, volumen_util_kwh
  - xm_aportes_diario         fecha, rio, aportes_kwh
  - xm_recursos               catalogo de plantas (ListadoRecursos)

Las metricas horarias llegan con 24 columnas (Hour01 ... Hour24) por fecha.
horas_a_filas() las pasa a una fila por fecha y hora, con el valor como numero.

Uso:
    python -m src.silver.xm
"""
import pandas as pd

from src import config
from src.quality import esquemas
from src.quality.reporte import Metricas, guardar_metricas
from src.silver.comun import a_numero, leer_bronce, separar, unir_cuarentena, validar_y_guardar
from src.utils import log

HORAS = [f"Hour{h:02d}" for h in range(1, 25)]   # Hour01 ... Hour24
FECHA_INI = "2023-01-01"
FECHA_FIN = "2026-09-30"

# Nombres de ListadoRecursos -> nombres de la capa plata
COLUMNAS_RECURSOS = {
    "Code": "codigo_recurso", "Name": "nombre_recurso", "Type": "tipo_generacion",
    "Disp": "despacho", "RecType": "clasificacion", "CompanyCode": "codigo_agente",
    "EnerSource": "fuente_energia", "OperStartdate": "fecha_operacion", "State": "estado",
}


# ---------------------------------------------------------------------------
# 24 columnas -> una fila por hora
# ---------------------------------------------------------------------------
def horas_a_filas(ancha: pd.DataFrame, columnas_id: list[str], nombre_valor: str) -> pd.DataFrame:
    """Pasa la tabla ancha de XM a una fila por fecha y hora.

        Date        code     Hour01  Hour02 ... Hour24
        2024-01-01  Sistema  251.9   251.9  ... 281.9

    queda como

        fecha       code     hora  <nombre_valor>
        2024-01-01  Sistema  1     251.9
        2024-01-01  Sistema  2     251.9
        ...
        2024-01-01  Sistema  24    281.9

    'hora' es un numero de 1 a 24 (Hour01 es la hora 1: de 00:00 a 01:00) y el
    valor queda como numero (los textos vacios quedan como NaN).
    """
    ancha = ancha.copy()
    for col in HORAS:                       # si una hora no vino, se crea vacia
        if col not in ancha.columns:
            ancha[col] = None
    larga = ancha.melt(id_vars=columnas_id, value_vars=HORAS,
                       var_name="hora", value_name=nombre_valor)
    larga["hora"] = larga["hora"].str[4:].astype(int)        # 'Hour07' -> 7
    larga[nombre_valor] = a_numero(larga[nombre_valor]).astype(float)
    larga = larga.rename(columns={"Date": "fecha"})
    larga["fecha"] = pd.to_datetime(larga["fecha"], errors="coerce")
    return larga


def dias_faltantes(fechas: pd.Series, ini: str = FECHA_INI, fin: str = FECHA_FIN) -> int:
    return len(set(pd.date_range(ini, fin, freq="D")) - set(fechas.dropna().unique()))


# ---------------------------------------------------------------------------
# Metricas horarias: precio, demanda y generacion
# ---------------------------------------------------------------------------
def limpiar_horaria(bronce: pd.DataFrame, nombre_valor: str, rango: tuple[float, float],
                    por_recurso: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, Metricas]:
    m = Metricas()
    cuarentena: list[pd.DataFrame] = []
    etiqueta = nombre_valor.split("_")[0]

    columnas_id = ["Date", "code"]
    df = horas_a_filas(bronce, columnas_id, nombre_valor)
    m.medir(f"{etiqueta}: 24 columnas por hora (Hour01..Hour24) en una fila por dia",
            "Pasar a una fila por fecha y hora", len(bronce), len(df),
            f"{len(bronce):,} filas x 24 horas")
    m.medir(f"{etiqueta}: valores horarios como texto", "Convertir a numero",
            int(bronce[[c for c in HORAS if c in bronce]].map(lambda v: isinstance(v, str)).sum().sum()), 0)

    if por_recurso:
        df["codigo_recurso"] = df["code"].astype(str).str.strip().str.upper()
        llave = ["fecha", "hora", "codigo_recurso"]
    else:
        llave = ["fecha", "hora"]

    sin_fecha = df["fecha"].isna()
    df = separar(df, sin_fecha, "fecha ilegible", cuarentena)

    vacio = df[nombre_valor].isna()
    if por_recurso:
        # En la generacion, XM deja la celda vacia cuando la planta no genero esa hora
        # (el 80 % son plantas solares de noche). No es un error que corregir: es
        # ausencia de registro. Se descarta y se documenta; no va a cuarentena.
        m.medir(f"{etiqueta}: hora vacia (la planta no genero: solares de noche, plantas apagadas)",
                "Descartar: no es una medicion (no se inventa un 0)", int(vacio.sum()), 0)
        df = df[~vacio]
    else:
        m.medir(f"{etiqueta}: hora sin valor (celda vacia)", "Pasar la fila a cuarentena",
                int(vacio.sum()), 0)
        df = separar(df, vacio, "valor vacio", cuarentena)

    negativo = df[nombre_valor] < 0
    m.medir(f"{etiqueta}: valor negativo", "Pasar la fila a cuarentena", int(negativo.sum()), 0)
    df = separar(df, negativo, "valor negativo", cuarentena)

    fuera = df[nombre_valor] > rango[1]
    m.medir(f"{etiqueta}: valor por encima del maximo fisico ({rango[1]:,.0f})",
            "Pasar la fila a cuarentena", int(fuera.sum()), 0)
    df = separar(df, fuera, "valor fuera de rango", cuarentena)

    repetida = df.duplicated(subset=llave + [nombre_valor])
    m.medir(f"{etiqueta}: fila repetida (ventanas de consulta que se cruzan)", "Dejar una sola copia",
            int(repetida.sum()), 0)
    df = df[~repetida]
    choque = df.duplicated(subset=llave, keep=False)
    df = separar(df, choque, "llave repetida con valores distintos", cuarentena)

    if not por_recurso:
        faltan = dias_faltantes(df["fecha"])
        m.medir(f"{etiqueta}: dias del periodo sin datos", "Documentar (no se inventan valores)",
                faltan, faltan)

    limpias = df[llave + [nombre_valor]].sort_values(llave).reset_index(drop=True)
    limpias["hora"] = limpias["hora"].astype(int)
    return limpias, unir_cuarentena(cuarentena), m


# ---------------------------------------------------------------------------
# Metricas diarias: embalses y aportes
# ---------------------------------------------------------------------------
def limpiar_diaria(bronce: pd.DataFrame, entidad: str, nombre_valor: str,
                   permitir_negativos: bool) -> tuple[pd.DataFrame, pd.DataFrame, Metricas]:
    m = Metricas()
    cuarentena: list[pd.DataFrame] = []
    etiqueta = entidad
    df = pd.DataFrame({
        "fecha": pd.to_datetime(bronce["Date"], errors="coerce"),
        entidad: bronce["Name"].astype("string").str.strip().str.upper(),
        nombre_valor: a_numero(bronce["Value"]).astype(float),
    })
    m.medir(f"{etiqueta}: fecha y valor como texto", "Convertir a fecha y a numero", len(df), 0)
    m.medir(f"{etiqueta}: nombres con espacios o minusculas", "Quitar espacios y pasar a MAYUSCULA",
            int((bronce["Name"].astype(str) != df[entidad].astype(str)).sum()), 0)

    malo = df["fecha"].isna() | df[entidad].isna() | df[nombre_valor].isna()
    m.medir(f"{etiqueta}: fecha, nombre o valor vacio", "Pasar la fila a cuarentena", int(malo.sum()), 0)
    df = separar(df, malo, "fecha, nombre o valor vacio", cuarentena)

    if permitir_negativos:
        negativos = int((df[nombre_valor] < 0).sum())
        m.medir(f"{etiqueta}: volumen util negativo (embalse por debajo del minimo tecnico)",
                "Conservarlo: es un dato real de XM, no un error", negativos, negativos)
    else:
        negativo = df[nombre_valor] < 0
        m.medir(f"{etiqueta}: valor negativo", "Pasar la fila a cuarentena", int(negativo.sum()), 0)
        df = separar(df, negativo, "valor negativo", cuarentena)

    llave = ["fecha", entidad]
    repetida = df.duplicated(subset=llave + [nombre_valor])
    m.medir(f"{etiqueta}: fila repetida", "Dejar una sola copia", int(repetida.sum()), 0)
    df = df[~repetida]
    choque = df.duplicated(subset=llave, keep=False)
    m.medir(f"{etiqueta}: mismo dia y {entidad} con dos valores", "Pasar ambas a cuarentena",
            int(choque.sum()), 0)
    df = separar(df, choque, "llave repetida con valores distintos", cuarentena)

    df[entidad] = df[entidad].astype(str)
    return df.sort_values(llave).reset_index(drop=True), unir_cuarentena(cuarentena), m


# ---------------------------------------------------------------------------
# Catalogo de plantas
# ---------------------------------------------------------------------------
def limpiar_recursos(bronce: pd.DataFrame) -> tuple[pd.DataFrame, Metricas]:
    m = Metricas()
    df = bronce.rename(columns=COLUMNAS_RECURSOS)[list(COLUMNAS_RECURSOS.values())].copy()
    m.medir("Recursos: columnas en ingles (Code, Type, EnerSource...)", "Renombrar a espanol",
            len(COLUMNAS_RECURSOS), 0)
    for col in df.columns:
        if col != "fecha_operacion":
            df[col] = df[col].astype("string").str.strip().str.upper()
    df["fecha_operacion"] = pd.to_datetime(df["fecha_operacion"], errors="coerce")
    sin_codigo = df["codigo_recurso"].isna() | (df["codigo_recurso"] == "")
    df = df[~sin_codigo]
    repetido = df.duplicated(subset=["codigo_recurso"])
    m.medir("Recursos: codigo de planta repetido", "Dejar la primera aparicion", int(repetido.sum()), 0)
    df = df[~repetido]
    sin_tipo = df["tipo_generacion"].isna()
    m.medir("Recursos: tipo de generacion vacio", "Marcarlo como 'NO INFORMADO'", int(sin_tipo.sum()), 0)
    df["tipo_generacion"] = df["tipo_generacion"].fillna("NO INFORMADO")
    for col in df.columns:
        if col != "fecha_operacion":
            df[col] = df[col].fillna("NO INFORMADO").astype(str)
    return df.sort_values("codigo_recurso").reset_index(drop=True), m


# ---------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def main() -> dict:
    metricas: list[dict] = []
    filas_bronce = filas_plata = filas_cuarentena = 0
    motivos: dict[str, int] = {}

    def registrar(bronce, limpias, cuarentena, m):
        nonlocal filas_bronce, filas_plata, filas_cuarentena
        filas_bronce += len(bronce)
        filas_plata += len(limpias)
        filas_cuarentena += len(cuarentena)
        metricas.extend(m.filas)
        if "motivo" in cuarentena:
            for motivo, n in cuarentena["motivo"].value_counts().items():
                motivos[motivo] = motivos.get(motivo, 0) + int(n)

    horarias = [
        ("xm_precio_bolsa", "xm_precio_bolsa_horario", "precio_bolsa_cop_kwh", (0, 10_000), False,
         esquemas.ESQUEMA_XM_PRECIO),
        ("xm_demanda", "xm_demanda_horaria", "demanda_kwh", (0, 20_000_000), False,
         esquemas.ESQUEMA_XM_DEMANDA),
        ("xm_generacion", "xm_generacion_horaria", "generacion_kwh", (0, 2_500_000), True,
         esquemas.ESQUEMA_XM_GENERACION),
    ]
    for origen, destino, valor, rango, por_recurso, esquema in horarias:
        bronce = leer_bronce(origen)
        limpias, cuarentena, m = limpiar_horaria(bronce, valor, rango, por_recurso)
        validar_y_guardar(limpias, destino, esquema, cuarentena)
        registrar(bronce, limpias, cuarentena, m)

    diarias = [
        ("xm_embalses", "xm_embalses_diario", "embalse", "volumen_util_kwh", True,
         esquemas.ESQUEMA_XM_EMBALSES),
        ("xm_aportes", "xm_aportes_diario", "rio", "aportes_kwh", False,
         esquemas.ESQUEMA_XM_APORTES),
    ]
    for origen, destino, entidad, valor, negativos, esquema in diarias:
        bronce = leer_bronce(origen)
        limpias, cuarentena, m = limpiar_diaria(bronce, entidad, valor, negativos)
        validar_y_guardar(limpias, destino, esquema, cuarentena)
        registrar(bronce, limpias, cuarentena, m)

    bronce = leer_bronce("xm_listado_recursos")
    recursos, m = limpiar_recursos(bronce)
    validar_y_guardar(recursos, "xm_recursos", esquemas.ESQUEMA_XM_RECURSOS)
    registrar(bronce, recursos, pd.DataFrame(), m)

    # Plantas que generan pero no estan en el catalogo (se documentan; dbt las agrega
    # a dim_recurso como 'SIN CATALOGO' para no perder su generacion)
    generacion = pd.read_parquet(config.DIR_SILVER / "xm_generacion_horaria.parquet", columns=["codigo_recurso"])
    sin_catalogo = sorted(set(generacion["codigo_recurso"]) - set(recursos["codigo_recurso"]))
    metricas.append({"problema": "Generacion de plantas que no estan en ListadoRecursos",
                     "regla aplicada": "Conservarla; dim_recurso las marca como 'SIN CATALOGO'",
                     "antes": len(sin_catalogo), "despues": len(sin_catalogo),
                     "detalle": ", ".join(sin_catalogo[:10]) + (" ..." if len(sin_catalogo) > 10 else "")})

    resumen = {"fuente": "XM - mercado mayorista (API servapibi)",
               "tabla": "xm_precio_bolsa_horario, xm_demanda_horaria, xm_generacion_horaria, "
                        "xm_embalses_diario, xm_aportes_diario, xm_recursos",
               "filas_bronce": filas_bronce, "filas_plata": filas_plata,
               "filas_cuarentena": filas_cuarentena, "motivos_cuarentena": motivos,
               "nota": "Las filas de bronce son anchas (un dia con 24 horas); las de plata son "
                       "una por hora, por eso plata tiene unas 24 veces mas filas.",
               "metricas": metricas}
    guardar_metricas("xm", resumen)
    log(f"XM: {filas_plata:,} filas en plata, {filas_cuarentena:,} en cuarentena")
    return resumen


if __name__ == "__main__":
    main()

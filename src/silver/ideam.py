"""
Capa PLATA del IDEAM: precipitacion y temperatura diarias de Antioquia.

Lee el bronce del extractor de la EA2 (src/extract/ideam_ea2.py):
  data/bronze/ideam_precipitacion_antioquia.parquet y ideam_temperatura_antioquia.parquet

Tablas que produce (data/silver/):
  - ideam_precipitacion_diaria   fecha, codigo_estacion, precipitacion_mm, n_registros
  - ideam_temperatura_diaria     fecha, codigo_estacion, temp_media_c, temp_min_c, temp_max_c, n_registros
  - ideam_estaciones             codigo_estacion, nombre_estacion, municipio, divipola, latitud, longitud

Cada estacion queda con su municipio y el codigo DIVIPOLA del DANE, para unirla
con dim_municipio en la capa oro.

Uso:
    python -m src.silver.ideam
"""
import pandas as pd

from src import config
from src.quality import esquemas
from src.quality.reporte import Metricas, guardar_metricas
from src.silver.comun import (a_numero, leer_bronce, nombre_propio, separar, sin_tildes,
                              unir_cuarentena, validar_y_guardar)
from src.utils import log

# Nombre del municipio en el IDEAM (sin tildes, minuscula) -> nombre en DIVIPOLA
ALIAS_MUNICIPIO_IDEAM = {
    "el carmen de viboral": "carmen de viboral",
    "el santuario": "el santuario",
    "san vicente": "san vicente ferrer",
    "santa fe de antioquia": "santa fe de antioquia",
    "santafe de antioquia": "santa fe de antioquia",
    "san pedro": "san pedro de los milagros",
    "san andres": "san andres de cuerquia",
    "san andres de cuerquia": "san andres de cuerquia",
    "puerto nare (la magdalena)": "puerto nare",
    "puerto nare(la magdalena)": "puerto nare",
    "yondo (casabe)": "yondo",
    "medellin d.e.": "medellin",
}

RANGO_PRECIPITACION = (0, 300)     # mm en un dia
RANGO_TEMPERATURA = (-5, 45)       # grados C en Antioquia (incluye paramos)


def clave_municipio_ideam(texto) -> str | None:
    if pd.isna(texto):
        return None
    clave = " ".join(sin_tildes(texto).split())
    return ALIAS_MUNICIPIO_IDEAM.get(clave, clave)


def preparar(bronce: pd.DataFrame, valores: list[str]) -> pd.DataFrame:
    """Tipos correctos: fecha como fecha y valores como numero."""
    df = pd.DataFrame({
        "fecha": pd.to_datetime(bronce["fecha"], errors="coerce").dt.normalize(),
        "codigo_estacion": bronce["codigoestacion"].astype("string").str.strip(),
        "nombre_estacion": bronce["nombreestacion"].astype("string").str.strip(),
        "municipio_fuente": bronce["municipio"].astype("string").str.strip(),
        "latitud": a_numero(bronce["latitud"]),
        "longitud": a_numero(bronce["longitud"]),
        "n_registros": a_numero(bronce["n_registros"]),
    })
    for col in valores:
        df[col] = a_numero(bronce[col]).astype(float)
    return df


def consolidar(df: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Une las filas del mismo dia y estacion que la API separo porque la estacion
    cambio de nombre o de coordenadas ese dia (son observaciones distintas del dia)."""
    llave = ["fecha", "codigo_estacion"]
    if tipo == "precipitacion":
        return df.groupby(llave, as_index=False).agg(
            precipitacion_mm=("precipitacion_mm", "sum"), n_registros=("n_registros", "sum"))
    df = df.assign(suma=df["temp_media_c"] * df["n_registros"])
    agrupada = df.groupby(llave, as_index=False).agg(
        suma=("suma", "sum"), n_registros=("n_registros", "sum"),
        temp_min_c=("temp_min_c", "min"), temp_max_c=("temp_max_c", "max"))
    agrupada["temp_media_c"] = agrupada["suma"] / agrupada["n_registros"]
    return agrupada.drop(columns="suma")


def limpiar_medicion(bronce: pd.DataFrame, tipo: str, municipios: pd.DataFrame,
                     m: Metricas) -> tuple[pd.DataFrame, pd.DataFrame]:
    cuarentena: list[pd.DataFrame] = []
    if tipo == "precipitacion":
        renombre = {"precipitacion_mm": "precipitacion_mm"}
    else:
        renombre = {"temp_media": "temp_media_c", "temp_min": "temp_min_c", "temp_max": "temp_max_c"}
    bronce = bronce.rename(columns=renombre)
    valores = list(renombre.values())
    df = preparar(bronce, valores)
    m.medir(f"{tipo}: fecha y valores como texto", "Convertir a fecha y a numero", len(df), 0)

    vacio = df["fecha"].isna() | df["codigo_estacion"].isna() | df[valores].isna().any(axis=1)
    m.medir(f"{tipo}: fecha, estacion o valor vacio", "Pasar la fila a cuarentena", int(vacio.sum()), 0)
    df = separar(df, vacio, "fecha, estacion o valor vacio", cuarentena)

    if tipo == "precipitacion":
        fuera = ~df["precipitacion_mm"].between(*RANGO_PRECIPITACION)
        m.medir(f"precipitacion: negativa o mayor a {RANGO_PRECIPITACION[1]} mm en un dia",
                "Pasar la fila a cuarentena", int(fuera.sum()), 0)
        df = separar(df, fuera, "precipitacion fuera de rango", cuarentena)
    else:
        fuera = ~(df["temp_min_c"].between(*RANGO_TEMPERATURA) & df["temp_max_c"].between(*RANGO_TEMPERATURA))
        m.medir(f"temperatura: fuera de {RANGO_TEMPERATURA[0]} a {RANGO_TEMPERATURA[1]} C",
                "Pasar la fila a cuarentena", int(fuera.sum()), 0)
        df = separar(df, fuera, "temperatura fuera de rango", cuarentena)

    # Municipio de la estacion -> DIVIPOLA
    claves = df["municipio_fuente"].map(clave_municipio_ideam)
    df["divipola"] = claves.map(dict(zip(municipios["clave"], municipios["divipola"])))
    sin_municipio = df["divipola"].isna()
    m.medir(f"{tipo}: municipio de la estacion no esta en DIVIPOLA",
            "Pasar la fila a cuarentena", int(sin_municipio.sum()), 0,
            ", ".join(sorted(df.loc[sin_municipio, "municipio_fuente"].dropna().unique())[:8]) or "-")
    df = separar(df, sin_municipio, "municipio no reconocido", cuarentena)

    repetida = df.duplicated(subset=["fecha", "codigo_estacion"], keep=False)
    m.medir(f"{tipo}: mismo dia y estacion en varias filas (cambio de nombre o coordenadas)",
            "Consolidar en una fila por dia y estacion", int(repetida.sum()), 0)
    medicion = consolidar(df, tipo)
    medicion["n_registros"] = medicion["n_registros"].astype(int)
    columnas = ["fecha", "codigo_estacion"] + valores + ["n_registros"]
    medicion = medicion[columnas].sort_values(["fecha", "codigo_estacion"]).reset_index(drop=True)
    for col in ["codigo_estacion"]:
        medicion[col] = medicion[col].astype(str)
    return medicion, df, unir_cuarentena(cuarentena)


def construir_estaciones(observaciones: pd.DataFrame, municipios: pd.DataFrame,
                         m: Metricas) -> pd.DataFrame:
    """Una fila por estacion: el nombre, municipio y coordenadas mas frecuentes."""
    def mas_frecuente(serie):
        moda = serie.dropna().mode()
        return moda.iloc[0] if len(moda) else None

    variantes = observaciones.groupby("codigo_estacion")[["nombre_estacion", "latitud", "longitud"]].nunique()
    m.medir("estaciones: la misma estacion con varios nombres o coordenadas",
            "Quedarse con el valor mas frecuente", int((variantes > 1).any(axis=1).sum()), 0)
    estaciones = observaciones.groupby("codigo_estacion", as_index=False).agg(
        nombre_estacion=("nombre_estacion", mas_frecuente),
        divipola=("divipola", mas_frecuente),
        latitud=("latitud", mas_frecuente),
        longitud=("longitud", mas_frecuente),
    )
    estaciones["nombre_estacion"] = estaciones["nombre_estacion"].map(
        lambda n: " ".join(str(n).split()))
    estaciones = estaciones.merge(municipios[["divipola", "municipio"]], on="divipola", how="left")
    columnas = ["codigo_estacion", "nombre_estacion", "municipio", "divipola", "latitud", "longitud"]
    estaciones = estaciones[columnas]
    for col in ["codigo_estacion", "nombre_estacion", "municipio", "divipola"]:
        estaciones[col] = estaciones[col].astype(str)
    return estaciones.sort_values("codigo_estacion").reset_index(drop=True)


def main() -> dict:
    municipios = pd.read_parquet(config.DIR_SILVER / "divipola_municipios.parquet")
    m = Metricas()
    filas_bronce = filas_cuarentena = filas_plata = 0
    motivos: dict[str, int] = {}
    observaciones = []
    for tipo, origen, destino, esquema in [
        ("precipitacion", "ideam_precipitacion_antioquia", "ideam_precipitacion_diaria",
         esquemas.ESQUEMA_IDEAM_PRECIPITACION),
        ("temperatura", "ideam_temperatura_antioquia", "ideam_temperatura_diaria",
         esquemas.ESQUEMA_IDEAM_TEMPERATURA),
    ]:
        bronce = leer_bronce(origen)
        medicion, validas, cuarentena = limpiar_medicion(bronce, tipo, municipios, m)
        validar_y_guardar(medicion, destino, esquema, cuarentena)
        observaciones.append(validas)
        filas_bronce += len(bronce)
        filas_plata += len(medicion)
        filas_cuarentena += len(cuarentena)
        for motivo, n in cuarentena["motivo"].value_counts().items():
            motivos[f"{tipo}: {motivo}"] = int(n)

    estaciones = construir_estaciones(pd.concat(observaciones), municipios, m)
    validar_y_guardar(estaciones, "ideam_estaciones", esquemas.ESQUEMA_IDEAM_ESTACIONES)
    m.medir("estaciones: municipio escrito en MAYUSCULA y sin codigo",
            "Asociar cada estacion a su municipio con el codigo DIVIPOLA", len(estaciones), 0,
            f"{len(estaciones)} estaciones en {estaciones['divipola'].nunique()} municipios")

    resumen = {"fuente": "IDEAM - precipitacion y temperatura (Antioquia)",
               "tabla": "ideam_precipitacion_diaria, ideam_temperatura_diaria, ideam_estaciones",
               "filas_bronce": filas_bronce, "filas_plata": filas_plata,
               "filas_cuarentena": filas_cuarentena, "motivos_cuarentena": motivos,
               "nota": "Bronce ya viene agregado por dia y estacion en la consulta SoQL "
                       "(los datasets completos tienen cientos de millones de registros).",
               "metricas": m.filas}
    guardar_metricas("ideam", resumen)
    log(f"IDEAM: {filas_plata:,} filas en plata, {len(estaciones)} estaciones, "
        f"{filas_cuarentena:,} en cuarentena")
    return resumen


if __name__ == "__main__":
    main()

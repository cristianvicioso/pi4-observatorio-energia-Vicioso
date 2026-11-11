"""
Reglas de calidad de la capa plata, escritas con pandera.

Un ESQUEMA es la lista de condiciones que una tabla limpia DEBE cumplir:
que columnas tiene, de que tipo es cada una y que valores acepta.
Si una sola fila no cumple, pandera detiene el programa y dice cual fila
y cual regla fallo. Asi, ningun dato sucio llega a la capa oro.

Este archivo SOLO GUARDA las reglas: no revisa nada por si solo.
Quien las usa es OTRO archivo: src/silver/enerandes.py (la limpieza).
Ese archivo, despues de limpiar, escribe estas dos lineas:

    from src.quality.esquemas import ESQUEMA_VENTAS
    ESQUEMA_VENTAS.validate(limpias, lazy=True)

  - La primera trae las reglas de este archivo (la variable ESQUEMA_VENTAS).
  - La segunda revisa la tabla limpia con esas reglas.
    Si una regla falla, el programa se detiene y la tabla NO se guarda.
    lazy=True: revisa toda la tabla y muestra TODOS los errores juntos
    (sin lazy=True, se detiene en el primer error y no se sabe si hay mas).

Las reglas van en un archivo aparte para escribirlas una sola vez:
las usan la limpieza (enerandes.py) y las pruebas (tests/).
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
# pandera: libreria para revisar que una tabla de pandas cumpla reglas.
# .pandas es la parte de pandera para tablas de pandas; "as pa" le da el nombre corto pa
import pandera.pandas as pa
# Column: las reglas de UNA columna (su tipo y sus condiciones)
# Check: una condicion, por ejemplo ">= 0" o "esta en esta lista"
from pandera.pandas import Check, Column

# ---------------------------------------------------------------------------
# VALORES ACEPTADOS en las columnas de categorias
# ---------------------------------------------------------------------------
# Los unicos 4 valores que puede tener la columna segmento
SEGMENTOS = ["Residencial", "Comercial", "Industrial", "No informado"]
# Los unicos 2 valores que puede tener la columna tipo_compra
TIPOS_COMPRA = ["Bolsa", "Contrato"]

# ---------------------------------------------------------------------------
# EL ESQUEMA de la tabla limpia
# ---------------------------------------------------------------------------
# pa.DataFrameSchema(...) crea el esquema. Recibe un diccionario
# {nombre de columna: Column(tipo, condicion)} y algunas reglas de toda la tabla
ESQUEMA_VENTAS = pa.DataFrameSchema(
    {
        # periodo: texto (str) que cumpla el patron AAAA-MM con un mes de 01 a 12.
        # r"^\d{4}-(0[1-9]|1[0-2])$" es una expresion regular (un patron de texto):
        #   ^ inicio, \d{4} cuatro digitos, - un guion, (0[1-9]|1[0-2]) del 01 al 12, $ fin
        # Ejemplo: '2023-04' cumple; '2023-13' y 'TOTAL' no cumplen
        "periodo": Column(str, Check.str_matches(r"^\d{4}-(0[1-9]|1[0-2])$")),
        # divipola: texto de exactamente 5 digitos (^\d{5}$). '05001' cumple; '5001' no
        "divipola": Column(str, Check.str_matches(r"^\d{5}$")),
        # municipio: texto, sin condicion extra (el nombre oficial ya viene de MUNICIPIOS)
        "municipio": Column(str),
        # segmento: texto que este en la lista SEGMENTOS (.isin = "esta en")
        "segmento": Column(str, Check.isin(SEGMENTOS)),
        # tipo_compra: texto que este en la lista TIPOS_COMPRA: solo Bolsa o Contrato
        "tipo_compra": Column(str, Check.isin(TIPOS_COMPRA)),
        # energia_kwh: numero con decimales (float) mayor o igual a 0 (ge = greater or equal)
        "energia_kwh": Column(float, Check.ge(0)),
        # valor_cop: numero >= 0; nullable=True permite celdas vacias (regla 9 de la limpieza)
        "valor_cop": Column(float, Check.ge(0), nullable=True),
        # clientes: numero entero (int) mayor o igual a 0
        "clientes": Column(int, Check.ge(0)),
        "hoja": Column(str, Check.isin(["2023", "2024", "2025", "2026", "sin_hoja"])),
    },
    # unique: no puede haber dos filas con el mismo periodo, municipio, segmento y tipo
    # de compra; si las hay, es una venta repetida
    unique=["periodo", "divipola", "segmento", "tipo_compra"],
    # strict=True: la tabla no puede traer columnas que no esten en este esquema
    strict=True,
)

# ===========================================================================
# EVIDENCIA 2: un esquema por cada tabla de la capa plata
# ===========================================================================
# Regla comun: todas las tablas tienen una LLAVE UNICA (unique=[...]) y
# strict=True (no se aceptan columnas de mas ni de menos).

FASES_ENSO = ["El Niño", "La Niña", "Neutral"]
TRIMESTRES = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ",
              "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]

# --- NOAA: un ONI por mes con su fase ENSO ---------------------------------
ESQUEMA_NOAA_ONI = pa.DataFrameSchema(
    {
        "periodo": Column(str, Check.str_matches(r"^\d{4}-(0[1-9]|1[0-2])$"), unique=True),
        "anio": Column(int, Check.in_range(1950, 2100)),
        "mes": Column(int, Check.in_range(1, 12)),
        "trimestre": Column(str, Check.isin(TRIMESTRES)),
        "oni": Column(float, Check.in_range(-5, 5)),
        "temperatura_mar_c": Column(float, Check.in_range(20, 32), nullable=True),
        "fase_enso": Column(str, Check.isin(FASES_ENSO)),
    },
    # La fase debe ser coherente con el ONI (regla entre columnas)
    checks=Check(lambda df: ((df["oni"] >= 0.5) == (df["fase_enso"] == "El Niño"))
                 & ((df["oni"] <= -0.5) == (df["fase_enso"] == "La Niña")),
                 error="la fase ENSO no corresponde al ONI"),
    strict=True,
)

# --- Fuente propia: TRM diaria ----------------------------------------------
ESQUEMA_TRM = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]", unique=True),
        "trm_cop_usd": Column(float, Check.in_range(1_000, 10_000)),
    },
    strict=True,
)

# --- Referencia: municipios de Antioquia (DIVIPOLA) --------------------------
ESQUEMA_DIVIPOLA = pa.DataFrameSchema(
    {
        "divipola": Column(str, Check.str_matches(r"^05\d{3}$"), unique=True),
        "municipio": Column(str),
        "departamento": Column(str, Check.eq("Antioquia")),
        "latitud": Column(float, Check.in_range(5, 9)),
        "longitud": Column(float, Check.in_range(-78, -73)),
        "atendido_enerandes": Column(bool),
        "clave": Column(str, unique=True),
    },
    strict=True,
)

# --- XM: una fila por fecha y hora ------------------------------------------
HORA = Column(int, Check.in_range(1, 24))

ESQUEMA_XM_PRECIO = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": HORA,
        "precio_bolsa_cop_kwh": Column(float, Check.in_range(0, 10_000)),
    },
    unique=["fecha", "hora"],
    strict=True,
)

ESQUEMA_XM_DEMANDA = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": HORA,
        "demanda_kwh": Column(float, Check.in_range(0, 20_000_000)),
    },
    unique=["fecha", "hora"],
    strict=True,
)

ESQUEMA_XM_GENERACION = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "hora": HORA,
        "codigo_recurso": Column(str, Check.str_matches(r"^[A-Z0-9]+$")),
        "generacion_kwh": Column(float, Check.in_range(0, 2_500_000)),
    },
    unique=["fecha", "hora", "codigo_recurso"],
    strict=True,
)

# --- XM: una fila por dia y embalse / rio -----------------------------------
ESQUEMA_XM_EMBALSES = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "embalse": Column(str),
        # Puede ser negativo: el embalse esta por debajo de su minimo tecnico
        "volumen_util_kwh": Column(float),
    },
    unique=["fecha", "embalse"],
    strict=True,
)

ESQUEMA_XM_APORTES = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "rio": Column(str),
        "aportes_kwh": Column(float, Check.ge(0)),
    },
    unique=["fecha", "rio"],
    strict=True,
)

# --- XM: catalogo de plantas -------------------------------------------------
ESQUEMA_XM_RECURSOS = pa.DataFrameSchema(
    {
        "codigo_recurso": Column(str, Check.str_matches(r"^[A-Z0-9]+$"), unique=True),
        "nombre_recurso": Column(str),
        "tipo_generacion": Column(str, Check.isin(
            ["HIDRAULICA", "TERMICA", "SOLAR", "EOLICA", "COGENERADOR", "NO INFORMADO"])),
        "despacho": Column(str),
        "clasificacion": Column(str),
        "codigo_agente": Column(str),
        "fuente_energia": Column(str),
        "fecha_operacion": Column("datetime64[ns]", nullable=True),
        "estado": Column(str),
    },
    strict=True,
)

# --- IDEAM: una fila por dia y estacion --------------------------------------
CODIGO_ESTACION = Column(str, Check.str_matches(r"^\d{8,10}$"))

ESQUEMA_IDEAM_PRECIPITACION = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "codigo_estacion": CODIGO_ESTACION,
        "precipitacion_mm": Column(float, Check.in_range(0, 300)),
        "n_registros": Column(int, Check.gt(0)),
    },
    unique=["fecha", "codigo_estacion"],
    strict=True,
)

ESQUEMA_IDEAM_TEMPERATURA = pa.DataFrameSchema(
    {
        "fecha": Column("datetime64[ns]"),
        "codigo_estacion": CODIGO_ESTACION,
        "temp_media_c": Column(float, Check.in_range(-5, 45)),
        "temp_min_c": Column(float, Check.in_range(-5, 45)),
        "temp_max_c": Column(float, Check.in_range(-5, 45)),
        "n_registros": Column(int, Check.gt(0)),
    },
    unique=["fecha", "codigo_estacion"],
    # La minima no puede ser mayor que la media ni la media mayor que la maxima
    checks=Check(lambda df: (df["temp_min_c"] <= df["temp_media_c"] + 1e-9)
                 & (df["temp_media_c"] <= df["temp_max_c"] + 1e-9),
                 error="temp_min <= temp_media <= temp_max"),
    strict=True,
)

ESQUEMA_IDEAM_ESTACIONES = pa.DataFrameSchema(
    {
        "codigo_estacion": Column(str, Check.str_matches(r"^\d{8,10}$"), unique=True),
        "nombre_estacion": Column(str),
        "municipio": Column(str),
        "divipola": Column(str, Check.str_matches(r"^05\d{3}$")),
        "latitud": Column(float, Check.in_range(5, 9), nullable=True),
        "longitud": Column(float, Check.in_range(-78, -73), nullable=True),
    },
    strict=True,
)

"""
Capa PLATA: limpia la hoja 2023 del Excel de ventas de EnerAndes.

Lee data/bronze/enerandes_ventas_2023.parquet (tal cual llego), aplica las
reglas de limpieza una por una y MIDE cada problema antes y despues.
Luego valida el resultado con pandera (src/quality/esquemas.py) y guarda:
  - data/silver/enerandes_ventas.parquet       las filas limpias
  - data/silver/enerandes_cuarentena.parquet   las filas que no se pueden usar
  - docs/reporte_calidad.md                    la tabla de metricas antes y despues

En bronce no se modifica nada: aqui se trabaja sobre una copia.

Uso:
    python -m src.silver.enerandes
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import unicodedata      # unicodedata: separa una letra de su tilde (para quitar tildes)

import pandas as pd     # pandas: tablas

from src import config                           # rutas de las carpetas
from src.quality.esquemas import ESQUEMA_VENTAS  # las reglas que debe cumplir la tabla limpia
from src.utils import log                        # mensajes con hora

# columnas de linaje que agrego la capa bronce (nombres viejos y actuales)
LINAJE = ["_fuente", "_origen", "_extraido_en", "_fuente_origen", "_fecha_ingesta"]

# Encabezados de la hoja 2023 -> nombres estandar de la capa plata
COLUMNAS_2023 = {
    "Fecha": "periodo",
    "Municipio": "municipio",
    "Segmento": "segmento",
    "Tipo_Compra": "tipo_compra",
    "Energia_kWh": "energia_kwh",
    "Valor_COP": "valor_cop",
    "Clientes": "clientes",
}

# Municipio (escrito sin tildes y en minuscula) -> (codigo DIVIPOLA, nombre oficial)
MUNICIPIOS = {
    "medellin": ("05001", "Medellín"),
    "santa fe de antioquia": ("05042", "Santa Fe de Antioquia"),
    "apartado": ("05045", "Apartadó"),
    "bello": ("05088", "Bello"),
    "caldas": ("05129", "Caldas"),
    "caucasia": ("05154", "Caucasia"),
    "copacabana": ("05212", "Copacabana"),
    "envigado": ("05266", "Envigado"),
    "girardota": ("05308", "Girardota"),
    "itagui": ("05360", "Itagüí"),
    "la estrella": ("05380", "La Estrella"),
    "marinilla": ("05440", "Marinilla"),
    "rionegro": ("05615", "Rionegro"),
    "sabaneta": ("05631", "Sabaneta"),
    "turbo": ("05837", "Turbo"),
}
# Otras formas de escribir el mismo municipio -> la forma de la lista de arriba
ALIAS_MUNICIPIO = {
    "rio negro": "rionegro",
    "rionegro (ant)": "rionegro",
    "medellin d.e.": "medellin",
    "sta fe de antioquia": "santa fe de antioquia",
    "santafe de antioquia": "santa fe de antioquia",
}
# Formas de escribir el segmento y el tipo de compra -> valor estandar
SEGMENTOS = {"residencial": "Residencial", "resid.": "Residencial",
             "comercial": "Comercial", "industrial": "Industrial", "ind": "Industrial"}
TIPOS_COMPRA = {"bolsa": "Bolsa", "contrato": "Contrato", "contratos": "Contrato"}


# ---------------------------------------------------------------------------
# FUNCIONES DE APOYO
# ---------------------------------------------------------------------------
def sin_tildes(texto: str) -> str:
    """'Itagüí' -> 'itagui': minuscula, sin espacios a los lados y sin tildes."""
    # texto.strip() quita los espacios de los lados: ' ITAGÜÍ ' -> 'ITAGÜÍ'
    # .lower() lo pasa a minuscula: 'ITAGÜÍ' -> 'itagüí'
    # normalize("NFD", ...) separa cada letra de su tilde: 'í' queda como 'i' + tilde
    letras = unicodedata.normalize("NFD", texto.strip().lower())
    # (c for c in letras if ...) recorre las letras una por una y salta las tildes
    # (las tildes son de la categoria "Mn"); "".join(...) las vuelve a unir en un texto
    return "".join(c for c in letras if unicodedata.category(c) != "Mn")


def clave_municipio(texto) -> str | None:
    """Convierte cualquier forma de escribir el municipio en la clave de MUNICIPIOS."""
    # pd.isna(texto) es True si la celda esta vacia: no hay municipio que buscar
    if pd.isna(texto):
        # None significa "sin valor"
        return None
    # Quita espacios, mayusculas y tildes: ' Rio Negro ' -> 'rio negro'
    clave = sin_tildes(texto)
    # .get(clave, clave) busca la clave en ALIAS_MUNICIPIO:
    # si la encuentra ('rio negro'), devuelve su valor ('rionegro');
    # si no la encuentra ('bello'), devuelve la misma clave ('bello')
    return ALIAS_MUNICIPIO.get(clave, clave)


# ---------------------------------------------------------------------------
# LIMPIEZA: las 9 reglas, en orden
# ---------------------------------------------------------------------------
def limpiar(bronce: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Aplica las reglas en orden. Devuelve (limpias, cuarentena, metricas)."""
    # metricas es una lista vacia. Cada regla le agrega una fila del reporte de calidad
    metricas = []

    # medir() es una funcion dentro de la funcion. Ejemplo:
    #   medir("Filas duplicadas", "Dejar una sola copia", 32, 0)
    # agrega a metricas: {"problema": "Filas duplicadas", "regla aplicada": "Dejar una
    # sola copia", "antes": 32, "despues": 0}
    def medir(problema: str, regla: str, antes: int, despues: int) -> None:
        metricas.append({"problema": problema, "regla aplicada": regla,
                         "antes": antes, "despues": despues})

    # La tabla de bronce tiene 10 columnas: col_0 ... col_6 y las 3 de linaje
    # (_fuente, _origen, _extraido_en). .drop(columns=LINAJE) quita esas 3.
    # errors="ignore": si alguna de las 3 no existe, no da error.
    # df es la tabla con la que se trabaja de aqui en adelante
    df = bronce.drop(columns=LINAJE, errors="ignore")

    # ------------------------------------------------------------------
    # Regla 1. La primera fila es el encabezado
    # ------------------------------------------------------------------
    # Asi esta df ahora:
    #        col_0      col_1      col_2        col_3  ...
    #   0    Fecha  Municipio   Segmento  Tipo_Compra  ...   <- el encabezado
    #   1  2023-04 Copacabana Industrial        Bolsa  ...   <- la primera venta
    # df.iloc[0] es la fila de la posicion 0; .tolist() la vuelve una lista:
    #   encabezado = ['Fecha', 'Municipio', 'Segmento', 'Tipo_Compra', ...]
    # OJO: si bronce ya trae los encabezados como nombres de columna
    # ('Fecha', 'Municipio', ...), no hay que tomar la primera fila: esa ya es una venta.
    if set(COLUMNAS_2023).issubset(df.columns):
        # Solo se renombran: 'Fecha' -> 'periodo', 'Municipio' -> 'municipio', ...
        df = df.rename(columns=COLUMNAS_2023).copy()
    else:
        encabezado = df.iloc[0].tolist()
        # df.iloc[1:] son las filas desde la posicion 1 hasta el final: todas menos el
        # encabezado. .copy() hace una copia, para trabajar sobre ella sin danar bronce
        df = df.iloc[1:].copy()
        # Para cada nombre del encabezado busca su nombre estandar en COLUMNAS_2023:
        #   'Fecha' -> 'periodo', 'Municipio' -> 'municipio', 'Segmento' -> 'segmento' ...
        df.columns = [COLUMNAS_2023.get(nombre, nombre) for nombre in encabezado]
    # ------------------------------------------------------------------
    # Regla 2. La fila TOTAL al final de la hoja: no es una venta
    # ------------------------------------------------------------------
    # df["periodo"] es la columna periodo: '2023-04', '2023-09', ..., 'TOTAL'
    # .str.upper() la pasa a mayuscula y .str.strip() le quita los espacios
    # (por si dijera ' total '). == "TOTAL" compara cada fila con 'TOTAL'.
    # El resultado es una columna de True/False, una respuesta por fila:
    #   '2023-04' -> False,  '2023-09' -> False,  ...,  'TOTAL' -> True
    es_total = df["periodo"].str.upper().str.strip() == "TOTAL"
    # .sum() suma la columna: cada True vale 1 y cada False vale 0.
    # Aqui da 1, porque hay 1 fila TOTAL. int() lo vuelve un numero entero normal
    medir("Filas de totales", "Eliminarlas", int(es_total.sum()), 0)
    # ~ invierte cada respuesta: True -> False y False -> True.
    # ~es_total es True en las filas que NO son total.
    # df[ columna de True/False ] devuelve solo las filas que dicen True.
    # Resultado: df ya no tiene la fila TOTAL
    df = df[~es_total]

    # ------------------------------------------------------------------
    # Regla 3. Filas repetidas exactamente iguales
    # ------------------------------------------------------------------
    # .duplicated() revisa fila por fila: True si la fila es igual a otra que ya
    # aparecio antes (la primera vez que aparece queda en False).
    # .sum() cuenta los True: aqui da 32 copias. antes guarda ese 32
    antes = int(df.duplicated().sum())
    # .drop_duplicates() borra las 32 copias y deja la primera de cada una
    df = df.drop_duplicates()
    # Vuelve a contar las copias: ahora da 0
    medir("Filas duplicadas", "Dejar una sola copia", antes, int(df.duplicated().sum()))

    # ------------------------------------------------------------------
    # Regla 4. Segmento escrito de varias formas o vacio
    # ------------------------------------------------------------------
    # df["segmento"] es la columna segmento. Tiene estos valores distintos:
    #   'Industrial', 'Comercial', 'Residencial', 'RESID.', 'Comercial ', 'IND'
    #   (y algunas celdas vacias)
    # .nunique() cuenta cuantos valores DISTINTOS hay, sin contar los vacios: 6.
    # antes guarda ese 6
    antes = df["segmento"].nunique()
    # .map(...) recorre la columna y cambia cada celda por lo que diga la funcion.
    # lambda s: ... es esa funcion, escrita en una linea; s es el valor de la celda:
    #   si s no esta vacio (pd.notna(s)):
    #       sin_tildes(s) lo limpia:         'RESID.' -> 'resid.'
    #       SEGMENTOS.get(...) lo busca:     'resid.' -> 'Residencial'
    #   si s esta vacio: devuelve None (sigue vacio)
    # Ejemplos:  'RESID.' -> 'Residencial'   'IND' -> 'Industrial'
    #            'Comercial ' -> 'Comercial'  (vacio) -> None
    df["segmento"] = df["segmento"].map(lambda s: SEGMENTOS.get(sin_tildes(s)) if pd.notna(s) else None)
    # .isna() da True en cada celda vacia; .sum() las cuenta: 14
    vacios = int(df["segmento"].isna().sum())
    # .fillna("No informado") escribe 'No informado' en cada celda vacia
    df["segmento"] = df["segmento"].fillna("No informado")
    # Valores distintos despues: Residencial, Comercial, Industrial y No informado = 4.
    # El - 1 descuenta 'No informado', que no es un segmento real: queda 3
    medir("Segmento escrito de varias formas", "Unificar a 3 valores", antes, df["segmento"].nunique() - 1)
    # Habia 14 vacios; despues, 0
    medir("Segmento vacio", "Marcarlo como 'No informado'", vacios, 0)

    # ------------------------------------------------------------------
    # Regla 5. Tipo de compra escrito de varias formas
    # ------------------------------------------------------------------
    # Valores distintos de tipo_compra: 'Bolsa', 'Contrato', 'CONTRATOS', 'bolsa'.
    # .nunique() da 4; antes guarda ese 4
    antes = df["tipo_compra"].nunique()
    # A cada celda t: sin_tildes la limpia y TIPOS_COMPRA.get la cambia:
    #   'CONTRATOS' -> 'contratos' -> 'Contrato'
    #   'bolsa'     -> 'bolsa'     -> 'Bolsa'
    df["tipo_compra"] = df["tipo_compra"].map(lambda t: TIPOS_COMPRA.get(sin_tildes(t)))
    # Valores distintos despues: 'Bolsa' y 'Contrato' = 2
    medir("Tipo de compra escrito de varias formas", "Unificar a Bolsa y Contrato",
          antes, df["tipo_compra"].nunique())

    # ------------------------------------------------------------------
    # Regla 6. Municipio escrito de varias formas: se cambia por su codigo DIVIPOLA
    # ------------------------------------------------------------------
    # La columna municipio tiene 31 formas distintas de escribir 15 municipios:
    #   'Medellin', 'medellin', 'Medellín', 'Medellín ', 'Medellín D.E.',
    #   'Bello', 'BELLO', 'Bello ', 'Rio Negro', 'Rionegro', 'Rionegro (Ant)', ...
    # .nunique() las cuenta: 31. antes guarda ese 31
    antes = df["municipio"].nunique()
    # .map(clave_municipio) le aplica a cada celda la funcion clave_municipio,
    # que deja una sola forma por municipio:
    #   'Medellín D.E.' -> 'medellin'    'BELLO' -> 'bello'    'Rio Negro' -> 'rionegro'
    # claves es una columna nueva con esas formas
    claves = df["municipio"].map(clave_municipio)
    # Con cada clave c busca en MUNICIPIOS, que guarda (codigo, nombre oficial):
    #   MUNICIPIOS['rionegro'] = ('05615', 'Rionegro')
    # [0] toma el primero, el codigo: '05615'.
    # df["divipola"] = ... crea la columna divipola con esos codigos
    df["divipola"] = claves.map(lambda c: MUNICIPIOS[c][0])
    # [1] toma el segundo, el nombre oficial: 'Rionegro'.
    # Se escribe encima de la columna municipio
    df["municipio"] = claves.map(lambda c: MUNICIPIOS[c][1])
    # Valores distintos despues: los 15 municipios reales
    medir("Municipio escrito de varias formas", "Unificar con el codigo DIVIPOLA",
          antes, df["municipio"].nunique())

    # ------------------------------------------------------------------
    # Regla 7. Los numeros llegaron como texto: se convierten a numero
    # ------------------------------------------------------------------
    # for col in [...] repite lo de adentro 3 veces, una con cada columna:
    # primero col = "energia_kwh", luego "valor_cop" y luego "clientes"
    for col in ["energia_kwh", "valor_cop", "clientes"]:
        # pd.to_numeric convierte el texto en numero: '98240' -> 98240.0
        # errors="coerce": si una celda no es un numero, queda vacia (NaN)
        # en vez de detener el programa con un error
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # .astype(int) quita los decimales: 2.0 -> 2. Los clientes son personas
    df["clientes"] = df["clientes"].astype(int)

    # ------------------------------------------------------------------
    # Regla 8. Energia vacia o negativa: no se puede adivinar -> cuarentena
    # ------------------------------------------------------------------
    # df["energia_kwh"].isna()  -> True si la energia esta vacia
    # (df["energia_kwh"] < 0)   -> True si la energia es negativa
    # |                         -> significa "o": True si pasa cualquiera de las dos
    # malas es una columna de True/False. Ejemplo:
    #   98240 -> False    NaN (vacia) -> True    -594733 -> True    74785 -> False
    malas = df["energia_kwh"].isna() | (df["energia_kwh"] < 0)
    # df[malas] devuelve solo las filas que dicen True: las 16 malas.
    # Se guardan aparte en cuarentena: no se borran
    cuarentena = df[malas]
    # ~malas invierte: True en las filas buenas. df[~malas] devuelve solo esas,
    # y se guardan otra vez en df: desde aqui df ya no tiene las 16 malas
    df = df[~malas]
    # .sum() cuenta los True de malas: 16
    medir("Energia vacia o negativa", "Pasar la fila a cuarentena", int(malas.sum()), 0)

    # ------------------------------------------------------------------
    # Regla 9. Valor facturado vacio: se deja vacio (no se inventa un valor)
    # ------------------------------------------------------------------
    # .isna() da True en cada valor vacio y .sum() los cuenta: 7.
    # No se corrige nada: solo se cuenta para que quede en el reporte
    vacios = int(df["valor_cop"].isna().sum())
    # Antes 7, despues 7: no hay como saber el valor real
    medir("Valor facturado vacio", "Dejarlo vacio y documentarlo", vacios, vacios)

    # ------------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------------
    # El orden en que quedan las columnas en la capa plata
    orden = ["periodo", "divipola", "municipio", "segmento", "tipo_compra",
             "energia_kwh", "valor_cop", "clientes"]
    # df[orden] pone las columnas en ese orden.
    # .reset_index(drop=True) vuelve a numerar las filas 0, 1, 2, ... sin huecos
    # (quedaron huecos donde estaban las filas borradas).
    # return devuelve 3 cosas: la tabla limpia, la cuarentena y la lista de metricas
    return df[orden].reset_index(drop=True), cuarentena, metricas


# ---------------------------------------------------------------------------
# REPORTE DE CALIDAD
# ---------------------------------------------------------------------------
def escribir_reporte(metricas: list[dict], filas_bronce: int, filas_plata: int, filas_cuarentena: int) -> None:
    """Escribe docs/reporte_calidad.md con la tabla de metricas antes y despues."""
    # Lista con las primeras lineas del reporte: el titulo, el conteo de filas
    # y el encabezado de la tabla.
    # f"...{filas_bronce:,}" mete el numero dentro del texto; :, le pone separador de miles
    lineas = [
        "# Reporte de calidad: ventas de EnerAndes (hoja 2023)\n",
        f"- Filas en bronce: {filas_bronce:,}",
        f"- Filas en plata: {filas_plata:,}",
        f"- Filas en cuarentena: {filas_cuarentena:,}\n",
        "| # | Problema | Regla aplicada | Antes | Despues |",
        "|---|---|---|---|---|",
    ]
    # Recorre las metricas; enumerate(..., start=1) da tambien su numero: 1, 2, 3...
    # n es el numero y m es el diccionario de la metrica
    for n, m in enumerate(metricas, start=1):
        # Agrega una fila de la tabla con los datos de esa regla
        lineas.append(f"| {n} | {m['problema']} | {m['regla aplicada']} | {m['antes']} | {m['despues']} |")
    # .mkdir crea la carpeta docs/; parents=True crea tambien las carpetas de arriba
    # si faltan; exist_ok=True no da error si ya existe
    config.DIR_DOCS.mkdir(parents=True, exist_ok=True)
    # "\n".join(lineas) une las lineas con un salto de linea entre cada una;
    # .write_text(...) escribe ese texto en docs/reporte_calidad.md
    (config.DIR_DOCS / "reporte_calidad.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def main() -> None:
    # Lee el archivo Parquet de bronce y lo guarda en la tabla bronce
    bronce = pd.read_parquet(config.DIR_BRONZE / "enerandes_ventas.parquet")
    # len(bronce) es el numero de filas; log lo muestra con la hora
    log(f"Bronce: {len(bronce):,} filas")
    # Llama a limpiar(); como devuelve tres cosas, se reciben en tres variables
    limpias, cuarentena, metricas = limpiar(bronce)

    # Revisa la tabla limpia con las reglas de pandera.
    # Si una regla falla, el programa se detiene aqui y no guarda nada;
    # lazy=True: revisa todo y muestra TODOS los errores juntos
    ESQUEMA_VENTAS.validate(limpias, lazy=True)
    # Si llego a esta linea, la tabla cumplio todas las reglas
    log("Validacion con pandera: OK")

    # Crea la carpeta data/silver/ si no existe
    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    # .to_parquet guarda la tabla en un archivo Parquet;
    # index=False: no guarda la columna de numeros de fila
    limpias.to_parquet(config.DIR_SILVER / "enerandes_ventas.parquet", index=False)
    cuarentena.to_parquet(config.DIR_SILVER / "enerandes_cuarentena.parquet", index=False)
    # Escribe docs/reporte_calidad.md
    escribir_reporte(metricas, len(bronce), len(limpias), len(cuarentena))

    # Muestra la tabla de metricas en la terminal, alineada en columnas:
    # :<42 ocupa 42 espacios alineado a la izquierda; :>7 ocupa 7 alineado a la derecha
    print(f"   {'problema':<42}{'antes':>7}{'despues':>9}")
    # Una linea por cada regla
    for m in metricas:
        print(f"   {m['problema']:<42}{m['antes']:>7}{m['despues']:>9}")
    log(f"Plata: {len(limpias):,} filas limpias y {len(cuarentena)} en cuarentena")
    log("Reporte en docs/reporte_calidad.md")


# __name__ vale "__main__" solo cuando se ejecuta este archivo
# (python -m src.silver.enerandes). Si otro archivo lo importa (las pruebas),
# main() no se ejecuta: solo se usan sus funciones
if __name__ == "__main__":
    main()
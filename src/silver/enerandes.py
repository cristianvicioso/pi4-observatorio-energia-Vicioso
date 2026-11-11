"""
Capa PLATA: limpia las 4 hojas del Excel de ventas de EnerAndes (2023 a 2026)
y las une en una sola tabla.

Lee data/bronze/enerandes_ventas_{2023..2026}.parquet (cada hoja tal cual llego,
con columnas col_0, col_1, ...), aplica las reglas de limpieza una por una y MIDE
cada problema antes y despues. Valida el resultado con pandera y guarda:
  - data/silver/enerandes_ventas.parquet       las filas limpias de las 4 hojas
  - data/silver/enerandes_cuarentena.parquet   las filas que no se pueden corregir,
                                               con el motivo y la fila del Excel

Problemas que resuelve (ver docs/reporte_calidad.md):
  - cada hoja tiene encabezados distintos ('Fecha', 'PERIODO', 'mes', 'Fecha corte'...)
  - las hojas 2025 y 2026 traen titulo y notas en las primeras filas
  - cada hoja termina con una fila TOTAL
  - fechas en 4 formatos: 2024-03, mar-24, 03/2024 y 01/03/2026 (dia/mes/anio)
  - la hoja 2024 mezcla energia en kWh y en MWh (columna UNIDAD)
  - municipios, segmentos y tipos de compra escritos de varias formas
  - filas duplicadas, celdas vacias y energias negativas

Uso:
    python -m src.silver.enerandes
"""
# ---------------------------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------------------------
import re               # re: expresiones regulares, para reconocer los formatos de fecha

import pandas as pd     # pandas: tablas

from src import config                           # rutas de las carpetas
from src.quality.esquemas import ESQUEMA_VENTAS  # las reglas que debe cumplir la tabla limpia
from src.quality.reporte import guardar_metricas  # guarda las metricas para el reporte
from src.silver.comun import sin_tildes          # 'Itagüí' -> 'itagui' (compartida con las demas fuentes)
from src.utils import log                        # mensajes con hora

HOJAS = ["2023", "2024", "2025", "2026"]

# Encabezado (sin tildes y en minuscula) de cualquiera de las 4 hojas -> nombre estandar
COLUMNAS = {
    # periodo de la venta
    "fecha": "periodo", "periodo": "periodo", "mes": "periodo", "fecha corte": "periodo",
    # municipio
    "municipio": "municipio", "ciudad": "municipio",
    # segmento del cliente
    "segmento": "segmento", "segmento cliente": "segmento", "tipo cliente": "segmento",
    # tipo de compra de la energia
    "tipo_compra": "tipo_compra", "modalidad": "tipo_compra", "tipo compra": "tipo_compra",
    "compra": "tipo_compra",
    # energia (en kWh, salvo la hoja 2024 que trae la unidad aparte)
    "energia_kwh": "energia", "energia": "energia", "consumo (kwh)": "energia", "kwh": "energia",
    "unidad": "unidad",
    # valor facturado en pesos
    "valor_cop": "valor_cop", "valor ($)": "valor_cop", "facturado": "valor_cop",
    "total facturado cop": "valor_cop",
    # numero de clientes
    "clientes": "clientes", "num clientes": "clientes", "usuarios": "clientes",
    "clientes activos": "clientes",
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

# Abreviatura del mes (espanol e ingles) -> numero, para fechas como 'mar-24'
MESES = {"ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5,
         "jun": 6, "jul": 7, "ago": 8, "aug": 8, "sep": 9, "sept": 9, "oct": 10,
         "nov": 11, "dic": 12, "dec": 12}

# Factor para pasar cada unidad de energia a kWh
FACTOR_KWH = {"kwh": 1, "mwh": 1000}


# ---------------------------------------------------------------------------
# FUNCIONES DE APOYO
# ---------------------------------------------------------------------------
def clave_municipio(texto) -> str | None:
    """Convierte cualquier forma de escribir el municipio en la clave de MUNICIPIOS."""
    if pd.isna(texto):
        return None
    clave = sin_tildes(texto)
    return ALIAS_MUNICIPIO.get(clave, clave)


def formato_fecha(texto) -> str:
    """Patron de una fecha, para contar cuantos formatos hay.
    '2024-03' -> 'AAAA-MM', 'mar-24' -> 'mmm-AA', '03/2024' -> 'MM/AAAA',
    '01/03/2026' -> 'DD/MM/AAAA'."""
    if pd.isna(texto):
        return "vacia"
    t = str(texto).strip().lower()
    if re.fullmatch(r"\d{4}-\d{1,2}", t):
        return "AAAA-MM"
    if re.fullmatch(r"[a-z]{3,4}-\d{2}", t):
        return "mmm-AA"
    if re.fullmatch(r"\d{1,2}/\d{4}", t):
        return "MM/AAAA"
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", t):
        return "DD/MM/AAAA"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}( 00:00:00)?", t):
        return "AAAA-MM-DD"
    return "otro"


def parsear_periodo(texto) -> str | None:
    """Lee una fecha en cualquiera de los formatos del Excel y devuelve 'AAAA-MM'.

    '2024-03' -> '2024-03'      'mar-24' -> '2024-03'      '03/2024' -> '2024-03'
    '01/03/2026' -> '2026-03'   (dia/mes/anio: es MARZO, no el 3 de enero)
    Si no se puede leer, devuelve None (la fila va a cuarentena).
    """
    if pd.isna(texto):
        return None
    t = str(texto).strip().lower()
    anio = mes = None
    if m := re.fullmatch(r"(\d{4})-(\d{1,2})", t):                 # 2024-03
        anio, mes = int(m[1]), int(m[2])
    elif m := re.fullmatch(r"([a-z]{3,4})-(\d{2})", t):            # mar-24
        if m[1] in MESES:
            anio, mes = 2000 + int(m[2]), MESES[m[1]]
    elif m := re.fullmatch(r"(\d{1,2})/(\d{4})", t):               # 03/2024
        anio, mes = int(m[2]), int(m[1])
    elif m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", t):     # 01/03/2026 = dia/mes/anio
        anio, mes = int(m[3]), int(m[2])
    elif m := re.fullmatch(r"(\d{4})-(\d{2})-\d{2}( 00:00:00)?", t):  # fecha completa de Excel
        anio, mes = int(m[1]), int(m[2])
    if anio is None or not 1 <= mes <= 12:
        return None
    return f"{anio:04d}-{mes:02d}"


def a_kwh(energia: float, unidad) -> float | None:
    """Pasa la energia a kWh segun su unidad: 2683.655 MWh -> 2683655.0 kWh.
    Sin columna de unidad (unidad vacia) se asume kWh, como dice el encabezado de
    esas hojas. Si la unidad no se reconoce, devuelve None (va a cuarentena)."""
    if pd.isna(energia):
        return None
    factor = 1 if pd.isna(unidad) else FACTOR_KWH.get(sin_tildes(unidad))
    if factor is None:
        return None
    # round(..., 3): 2683.655 * 1000 da 2683655.0000000005 por la aritmetica decimal
    return round(float(energia) * factor, 3)


def fila_encabezado(hoja: pd.DataFrame) -> int:
    """Posicion de la fila que tiene el encabezado: la primera en la que al menos
    4 celdas son nombres de columna conocidos. Las filas de arriba son titulo y notas."""
    for posicion in range(min(len(hoja), 20)):
        celdas = [sin_tildes(c) for c in hoja.iloc[posicion] if pd.notna(c)]
        if sum(c in COLUMNAS for c in celdas) >= 4:
            return posicion
    raise ValueError("No se encontro la fila de encabezado en las primeras 20 filas")


def normalizar_hoja(hoja: pd.DataFrame, anio: str | None) -> tuple[pd.DataFrame, int, list[str]]:
    """Deja una hoja con los nombres estandar de columna.

    Devuelve (tabla, filas de titulo/notas quitadas, encabezados originales).
    Agrega 'hoja' (de que hoja viene) y 'fila_excel' (numero de fila en el Excel,
    para poder ubicar en el archivo original cada fila de la cuarentena)."""
    hoja = hoja.drop(columns=[c for c in hoja.columns if str(c).startswith("_")])
    # Si bronce ya traia los encabezados como nombres de columna, se usan esos
    if sum(sin_tildes(c) in COLUMNAS for c in hoja.columns) >= 4:
        encabezado, inicio, titulos = list(hoja.columns), 0, 0
    else:
        titulos = fila_encabezado(hoja)
        encabezado, inicio = hoja.iloc[titulos].tolist(), titulos + 1
    datos = hoja.iloc[inicio:].copy()
    datos.columns = [COLUMNAS.get(sin_tildes(n), sin_tildes(n)) for n in encabezado]
    datos = datos.dropna(how="all")          # filas totalmente vacias (separadores)
    datos["hoja"] = anio if anio else "sin_hoja"
    # +1 porque Excel cuenta desde 1; +inicio por las filas de arriba
    datos["fila_excel"] = [i + 1 for i in datos.index]
    if "unidad" not in datos.columns:
        datos["unidad"] = None
    encabezados = [str(n).strip() for n in encabezado if pd.notna(n)]
    return datos, titulos, encabezados


# ---------------------------------------------------------------------------
# LIMPIEZA
# ---------------------------------------------------------------------------
def limpiar(bronce) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Aplica las reglas en orden. Devuelve (limpias, cuarentena, metricas).

    bronce puede ser una sola hoja (DataFrame) o un diccionario {'2023': hoja, ...}.
    """
    hojas = bronce if isinstance(bronce, dict) else {None: bronce}
    metricas = []
    cuarentenas = []

    def por_hoja(mascara) -> str:
        """'2023: 7 · 2024: 3' cuantas filas marca la mascara en cada hoja."""
        conteo = df.loc[mascara, "hoja"].value_counts().sort_index()
        return " · ".join(f"{h}: {n}" for h, n in conteo.items() if n) or "-"

    def medir(problema, regla, antes, despues, detalle="-"):
        metricas.append({"problema": problema, "regla aplicada": regla,
                         "antes": antes, "despues": despues, "detalle": detalle})

    def a_cuarentena(mascara, motivo):
        """Saca de df las filas marcadas y las guarda en la cuarentena con su motivo."""
        nonlocal df
        malas = df[mascara].copy()
        malas["motivo"] = motivo
        cuarentenas.append(malas)
        df = df[~mascara]

    # ------------------------------------------------------------------
    # Reglas 1 y 2. Titulos/notas en las primeras filas y encabezados distintos
    # ------------------------------------------------------------------
    partes, titulos, encabezados = [], {}, set()
    for anio, hoja in hojas.items():
        datos, n_titulos, nombres = normalizar_hoja(hoja, anio)
        partes.append(datos)
        titulos[anio] = n_titulos
        encabezados.update(nombres)
    df = pd.concat(partes, ignore_index=True)
    columnas_std = {"periodo", "municipio", "segmento", "tipo_compra", "energia",
                    "unidad", "valor_cop", "clientes"}
    medir("Titulo y notas antes del encabezado", "Buscar la fila de encabezado y descartar las de arriba",
          sum(titulos.values()), 0,
          " · ".join(f"{h}: {n}" for h, n in titulos.items() if n) or "-")
    medir("Encabezados distintos entre hojas (nombres de columna)",
          "Mapear cada encabezado a un nombre estandar", len(encabezados),
          len(columnas_std & set(df.columns)))

    # ------------------------------------------------------------------
    # Regla 3. Filas TOTAL al final de cada hoja
    # ------------------------------------------------------------------
    es_total = df["periodo"].astype(str).str.strip().str.upper() == "TOTAL"
    medir("Filas de totales", "Eliminarlas (no son una venta)", int(es_total.sum()), 0,
          por_hoja(es_total))
    df = df[~es_total]

    # ------------------------------------------------------------------
    # Regla 4. Filas repetidas exactamente iguales (dentro de la misma hoja)
    # ------------------------------------------------------------------
    datos_originales = [c for c in df.columns if c != "fila_excel"]
    duplicada = df.duplicated(subset=datos_originales)
    medir("Filas duplicadas", "Dejar una sola copia", int(duplicada.sum()), 0, por_hoja(duplicada))
    df = df[~duplicada]

    # ------------------------------------------------------------------
    # Regla 5. Fechas en 4 formatos -> AAAA-MM
    # ------------------------------------------------------------------
    formatos = df["periodo"].map(formato_fecha)
    dd_mm = formatos == "DD/MM/AAAA"
    medir("Fecha DD/MM/AAAA (hoja 2026): riesgo de leer 01/03 como 3 de enero",
          "Leer como dia/mes/anio: 01/03/2026 -> 2026-03", int(dd_mm.sum()), 0, por_hoja(dd_mm))
    df["periodo"] = df["periodo"].map(parsear_periodo)
    medir("Fechas en formatos distintos (AAAA-MM, mmm-AA, MM/AAAA, DD/MM/AAAA)",
          "Convertir todas a AAAA-MM", formatos.nunique(), df["periodo"].dropna().map(formato_fecha).nunique(),
          " · ".join(f"{f}: {n}" for f, n in formatos.value_counts().items()))
    sin_fecha = df["periodo"].isna()
    medir("Fecha ilegible", "Pasar la fila a cuarentena", int(sin_fecha.sum()), 0, por_hoja(sin_fecha))
    a_cuarentena(sin_fecha, "fecha ilegible")
    # La fecha debe ser del anio de su hoja (una venta de 2023 en la hoja 2025 es un error)
    otro_anio = (df["hoja"] != "sin_hoja") & (df["periodo"].str[:4] != df["hoja"])
    medir("Fecha de un anio distinto al de la hoja", "Pasar la fila a cuarentena",
          int(otro_anio.sum()), 0, por_hoja(otro_anio))
    a_cuarentena(otro_anio, "fecha fuera del anio de la hoja")

    # ------------------------------------------------------------------
    # Regla 6. Numeros como texto -> numero; energia en MWh -> kWh
    # ------------------------------------------------------------------
    for col in ["energia", "valor_cop", "clientes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    en_mwh = df["unidad"].map(lambda u: pd.notna(u) and sin_tildes(u) == "mwh")
    df["energia_kwh"] = [a_kwh(e, u) for e, u in zip(df["energia"], df["unidad"])]
    medir("Energia en MWh mezclada con kWh (hoja 2024)", "Multiplicar por 1.000 y dejar todo en kWh",
          int(en_mwh.sum()), 0, por_hoja(en_mwh))
    unidad_mala = df["energia"].notna() & df["energia_kwh"].isna()
    a_cuarentena(unidad_mala, "unidad de energia desconocida")

    # ------------------------------------------------------------------
    # Regla 7. Segmento escrito de varias formas o vacio
    # ------------------------------------------------------------------
    antes = df["segmento"].nunique()
    df["segmento"] = df["segmento"].map(lambda s: SEGMENTOS.get(sin_tildes(s)) if pd.notna(s) else None)
    vacios = df["segmento"].isna()
    medir("Segmento escrito de varias formas", "Unificar a Residencial, Comercial e Industrial",
          antes, df["segmento"].nunique())
    medir("Segmento vacio", "Marcarlo como 'No informado'", int(vacios.sum()), 0, por_hoja(vacios))
    df["segmento"] = df["segmento"].fillna("No informado")

    # ------------------------------------------------------------------
    # Regla 8. Tipo de compra escrito de varias formas
    # ------------------------------------------------------------------
    antes = df["tipo_compra"].nunique()
    df["tipo_compra"] = df["tipo_compra"].map(
        lambda t: TIPOS_COMPRA.get(sin_tildes(t)) if pd.notna(t) else None)
    medir("Tipo de compra escrito de varias formas", "Unificar a Bolsa y Contrato",
          antes, df["tipo_compra"].nunique())
    sin_tipo = df["tipo_compra"].isna()
    a_cuarentena(sin_tipo, "tipo de compra vacio o desconocido")

    # ------------------------------------------------------------------
    # Regla 9. Municipio escrito de varias formas -> codigo DIVIPOLA
    # ------------------------------------------------------------------
    antes = df["municipio"].nunique()
    claves = df["municipio"].map(clave_municipio)
    desconocido = ~claves.isin(MUNICIPIOS.keys())
    medir("Municipio no reconocido o vacio", "Pasar la fila a cuarentena",
          int(desconocido.sum()), 0, por_hoja(desconocido))
    a_cuarentena(desconocido, "municipio no reconocido")
    claves = claves[~desconocido]
    df["divipola"] = claves.map(lambda c: MUNICIPIOS[c][0])
    df["municipio"] = claves.map(lambda c: MUNICIPIOS[c][1])
    medir("Municipio escrito de varias formas", "Unificar con el codigo DIVIPOLA",
          antes, df["municipio"].nunique())

    # ------------------------------------------------------------------
    # Regla 10. Energia vacia o negativa: no se puede adivinar -> cuarentena
    # ------------------------------------------------------------------
    vacia = df["energia_kwh"].isna()
    medir("Energia vacia", "Pasar la fila a cuarentena", int(vacia.sum()), 0, por_hoja(vacia))
    a_cuarentena(vacia, "energia vacia")
    negativa = df["energia_kwh"] < 0
    medir("Energia negativa", "Pasar la fila a cuarentena", int(negativa.sum()), 0, por_hoja(negativa))
    a_cuarentena(negativa, "energia negativa")

    # ------------------------------------------------------------------
    # Regla 11. Valor facturado o clientes negativos -> cuarentena
    # ------------------------------------------------------------------
    otros_negativos = (df["valor_cop"] < 0) | (df["clientes"] < 0)
    medir("Valor facturado o clientes negativos", "Pasar la fila a cuarentena",
          int(otros_negativos.sum()), 0, por_hoja(otros_negativos))
    a_cuarentena(otros_negativos, "valor o clientes negativos")

    # ------------------------------------------------------------------
    # Regla 12. Clientes vacios -> cuarentena (no se puede calcular el consumo por cliente)
    # ------------------------------------------------------------------
    sin_clientes = df["clientes"].isna()
    medir("Clientes vacio", "Pasar la fila a cuarentena", int(sin_clientes.sum()), 0, por_hoja(sin_clientes))
    a_cuarentena(sin_clientes, "clientes vacio")
    df["clientes"] = df["clientes"].astype(int)

    # ------------------------------------------------------------------
    # Regla 13. Valor facturado vacio: se deja vacio (no se inventa un valor)
    # ------------------------------------------------------------------
    sin_valor = df["valor_cop"].isna()
    medir("Valor facturado vacio", "Dejarlo vacio y documentarlo (no se inventa)",
          int(sin_valor.sum()), int(sin_valor.sum()), por_hoja(sin_valor))

    # ------------------------------------------------------------------
    # Regla 14. Llave repetida tras normalizar: la misma venta escrita distinto
    # (por ejemplo 'jun-24' y '06/2024', o 'Medellin' y 'Medellín')
    # ------------------------------------------------------------------
    llave = ["periodo", "divipola", "segmento", "tipo_compra"]
    valores = llave + ["energia_kwh", "valor_cop", "clientes"]
    copia = df.duplicated(subset=valores)
    medir("Misma venta escrita de dos formas (duplicado tras normalizar)", "Dejar una sola copia",
          int(copia.sum()), 0, por_hoja(copia))
    df = df[~copia]
    choque = df.duplicated(subset=llave, keep=False)
    medir("Llave repetida con valores distintos", "Pasar ambas filas a cuarentena",
          int(choque.sum()), 0, por_hoja(choque))
    a_cuarentena(choque, "llave repetida con valores distintos")

    # ------------------------------------------------------------------
    # Resultado
    # ------------------------------------------------------------------
    orden = ["periodo", "divipola", "municipio", "segmento", "tipo_compra",
             "energia_kwh", "valor_cop", "clientes", "hoja"]
    limpias = df[orden].sort_values(["periodo", "divipola", "segmento", "tipo_compra"])
    columnas_cuarentena = ["hoja", "fila_excel", "motivo", "periodo", "municipio", "segmento",
                           "tipo_compra", "energia", "unidad", "energia_kwh", "valor_cop", "clientes"]
    cuarentena = (pd.concat(cuarentenas, ignore_index=True) if cuarentenas
                  else pd.DataFrame(columns=columnas_cuarentena))
    cuarentena = cuarentena.reindex(columns=columnas_cuarentena)
    for col in ["periodo", "municipio", "segmento", "tipo_compra", "unidad", "hoja", "motivo"]:
        cuarentena[col] = cuarentena[col].astype("string")
    return limpias.reset_index(drop=True), cuarentena.reset_index(drop=True), metricas


# ---------------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ---------------------------------------------------------------------------
def main() -> dict:
    hojas = {anio: pd.read_parquet(config.DIR_BRONZE / f"enerandes_ventas_{anio}.parquet")
             for anio in HOJAS}
    filas_bronce = sum(len(h) for h in hojas.values())
    log(f"EnerAndes bronce: {filas_bronce:,} filas en {len(hojas)} hojas")
    limpias, cuarentena, metricas = limpiar(hojas)

    # Si una regla falla, el programa se detiene aqui y NO guarda nada
    ESQUEMA_VENTAS.validate(limpias, lazy=True)
    log("Validacion con pandera: OK")

    config.DIR_SILVER.mkdir(parents=True, exist_ok=True)
    limpias.to_parquet(config.DIR_SILVER / "enerandes_ventas.parquet", index=False)
    cuarentena.to_parquet(config.DIR_SILVER / "enerandes_cuarentena.parquet", index=False)

    resumen = {
        "fuente": "EnerAndes - ventas 2023 a 2026 (Excel, 4 hojas)",
        "tabla": "enerandes_ventas",
        "filas_bronce": filas_bronce,
        "filas_plata": len(limpias),
        "filas_cuarentena": len(cuarentena),
        "motivos_cuarentena": cuarentena["motivo"].value_counts().to_dict(),
        "metricas": metricas,
    }
    guardar_metricas("enerandes", resumen)
    for m in metricas:
        print(f"   {m['problema'][:60]:<62}{m['antes']:>7}{m['despues']:>9}")
    log(f"Plata: {len(limpias):,} filas limpias y {len(cuarentena)} en cuarentena")
    return resumen


if __name__ == "__main__":
    main()

"""
Pruebas de las reglas de limpieza agregadas en la Evidencia 2.

Cada prueba arma sus propios datos de ejemplo (pequenos, escritos aqui mismo),
no usa internet ni los archivos de data/ y sigue el patron
Arrange (preparar) -> Act (ejecutar) -> Assert (comprobar).

Uso:
    python -m pytest -v
"""
import pandas as pd
import pandera.errors
import pytest

from src.quality.esquemas import ESQUEMA_NOAA_ONI
from src.silver import noaa, trm, xm
from src.silver.enerandes import a_kwh, limpiar, parsear_periodo


# ---------------------------------------------------------------------------
# EnerAndes: unidades y fechas
# ---------------------------------------------------------------------------
def test_mwh_se_convierte_a_kwh():
    # Arrange / Act: la misma energia en MWh, en kWh, sin unidad y con una unidad rara
    en_mwh = a_kwh(2683.655, "MWh")
    en_kwh = a_kwh(500, "kWh")
    sin_unidad = a_kwh(500, None)
    unidad_rara = a_kwh(1, "GWh")
    # Assert: MWh se multiplica por 1.000 (sin errores de decimales), kWh queda igual,
    # sin unidad se asume kWh y una unidad desconocida no se adivina (None -> cuarentena)
    assert en_mwh == 2_683_655.0
    assert en_kwh == 500
    assert sin_unidad == 500
    assert unidad_rara is None


def test_fechas_mar24_y_03_2024_quedan_como_aaaa_mm():
    # Los 3 formatos de la hoja 2024 deben dar el mismo mes
    assert parsear_periodo("mar-24") == "2024-03"
    assert parsear_periodo("03/2024") == "2024-03"
    assert parsear_periodo("2024-03") == "2024-03"
    # Abreviaturas en espanol que no coinciden con el ingles
    assert parsear_periodo("ago-24") == "2024-08"
    assert parsear_periodo("dic-24") == "2024-12"


def test_fecha_2026_se_lee_como_dia_mes_anio():
    # 01/03/2026 es el 1 de MARZO (dia/mes/anio), no el 3 de enero
    assert parsear_periodo("01/03/2026") == "2026-03"
    assert parsear_periodo("01/09/2026") == "2026-09"


def test_fecha_ilegible_devuelve_none():
    # Mes 13, texto y celda vacia: no se adivina, la fila ira a cuarentena
    assert parsear_periodo("13/2024") is None
    assert parsear_periodo("TOTAL") is None
    assert parsear_periodo(None) is None


def test_hoja_2024_con_titulo_y_mwh_queda_en_kwh():
    # Arrange: hoja tipo 2024 en miniatura, con titulo arriba, columna UNIDAD,
    # una fila en MWh, fechas en 3 formatos y la fila TOTAL
    filas = [
        ["EnerAndes - Reporte 2024", None, None, None, None, None, None, None],
        [None, None, None, None, None, None, None, None],
        ["PERIODO", "MUNICIPIO", "SEGMENTO CLIENTE", "MODALIDAD", "ENERGIA", "UNIDAD", "VALOR ($)", "NUM CLIENTES"],
        ["jun-24", "Bello", "Residencial", "Contrato", "2683.655", "MWh", "2528411585", "16773"],
        ["07/2024", "Bello", "Residencial", "Contrato", "2700000", "kWh", "2600000000", "16800"],
        ["2024-08", "Bello", "Residencial", "Contrato", "2750000", "kWh", "2650000000", "16900"],
        ["TOTAL", None, None, None, None, None, None, None],
    ]
    hoja = pd.DataFrame(filas, columns=[f"col_{i}" for i in range(8)])
    # Act
    limpias, cuarentena, _ = limpiar({"2024": hoja})
    # Assert: 3 ventas, todas en kWh, con los meses 06, 07 y 08
    assert list(limpias["periodo"]) == ["2024-06", "2024-07", "2024-08"]
    assert limpias.iloc[0]["energia_kwh"] == 2_683_655.0
    assert len(cuarentena) == 0


def test_fecha_de_otro_anio_que_la_hoja_va_a_cuarentena():
    # Una venta de 2023 escrita en la hoja 2025 es un error de digitacion
    filas = [
        ["mes", "municipio", "segmento", "tipo compra", "consumo (kWh)", "facturado", "usuarios"],
        ["06/2025", "Turbo", "Comercial", "Bolsa", "1000", "900000", "10"],
        ["06/2023", "Turbo", "Comercial", "Bolsa", "1000", "900000", "10"],
    ]
    hoja = pd.DataFrame(filas, columns=[f"col_{i}" for i in range(7)])
    limpias, cuarentena, _ = limpiar({"2025": hoja})
    assert len(limpias) == 1
    assert cuarentena.iloc[0]["motivo"] == "fecha fuera del anio de la hoja"


# ---------------------------------------------------------------------------
# NOAA: fase ENSO y trimestre -> mes central
# ---------------------------------------------------------------------------
def test_fase_enso_segun_el_oni():
    # Los umbrales +-0,5 se incluyen en El Niño y La Niña
    assert noaa.fase_enso(0.5) == "El Niño"
    assert noaa.fase_enso(2.1) == "El Niño"
    assert noaa.fase_enso(-0.5) == "La Niña"
    assert noaa.fase_enso(0.49) == "Neutral"
    assert noaa.fase_enso(-0.49) == "Neutral"


def test_trimestre_movil_va_a_su_mes_central():
    # Arrange: 3 trimestres moviles como vienen en el archivo de NOAA
    bronce = pd.DataFrame({"SEAS": ["DJF", "JFM", "NDJ"], "YR": ["2024", "2024", "2024"],
                           "TOTAL": ["28.1", "27.9", "26.0"], "ANOM": ["1.80", "1.50", "-0.60"]})
    # Act
    limpias, _, _ = noaa.limpiar(bronce)
    # Assert: DJF -> enero, JFM -> febrero, NDJ -> diciembre, con su fase
    assert list(limpias["periodo"]) == ["2024-01", "2024-02", "2024-12"]
    assert list(limpias["fase_enso"]) == ["El Niño", "El Niño", "La Niña"]


def test_pandera_rechaza_fase_enso_incoherente():
    limpias, _, _ = noaa.limpiar(pd.DataFrame(
        {"SEAS": ["DJF"], "YR": ["2024"], "TOTAL": ["28.1"], "ANOM": ["1.80"]}))
    limpias.loc[0, "fase_enso"] = "Neutral"          # ONI 1,8 no puede ser Neutral
    with pytest.raises(pandera.errors.SchemaErrors):
        ESQUEMA_NOAA_ONI.validate(limpias, lazy=True)


# ---------------------------------------------------------------------------
# XM: 24 columnas -> una fila por hora
# ---------------------------------------------------------------------------
def test_xm_24_columnas_pasan_a_una_fila_por_hora():
    # Arrange: un dia de precio de bolsa como lo entrega XM (texto, 24 columnas)
    fila = {"Date": "2024-01-01", "code": "Sistema"}
    fila.update({f"Hour{h:02d}": str(100 + h) for h in range(1, 25)})
    ancha = pd.DataFrame([fila])
    # Act
    larga = xm.horas_a_filas(ancha, ["Date", "code"], "precio_bolsa_cop_kwh")
    # Assert: 24 filas, horas 1..24, el valor de Hour07 en la hora 7 y como numero
    assert len(larga) == 24
    assert sorted(larga["hora"]) == list(range(1, 25))
    assert larga.loc[larga["hora"] == 7, "precio_bolsa_cop_kwh"].iloc[0] == 107.0
    assert larga["precio_bolsa_cop_kwh"].dtype == float
    assert larga["fecha"].iloc[0] == pd.Timestamp("2024-01-01")


def test_xm_generacion_negativa_va_a_cuarentena_y_vacia_se_descarta():
    # Arrange: dos plantas; la segunda tiene una hora negativa (error) y una vacia
    # (la planta no genero: no es un error, se descarta sin ir a cuarentena)
    base = {f"Hour{h:02d}": "10" for h in range(1, 25)}
    planta_b = dict(base, Hour03="-5", Hour04="")
    ancha = pd.DataFrame([{"Date": "2024-01-01", "code": "plta1", **base},
                          {"Date": "2024-01-01", "code": "PLTB", **planta_b}])
    # Act
    limpias, cuarentena, _ = xm.limpiar_horaria(ancha, "generacion_kwh", (0, 2_500_000), por_recurso=True)
    # Assert: 48 horas - 2 malas = 46; el codigo se paso a mayuscula
    assert len(limpias) == 46
    assert list(cuarentena["motivo"]) == ["valor negativo"]
    assert "PLTA1" in set(limpias["codigo_recurso"])


# ---------------------------------------------------------------------------
# Fuente propia: TRM
# ---------------------------------------------------------------------------
def test_trm_del_viernes_se_expande_al_fin_de_semana():
    # Arrange: la TRM del viernes 5 de enero vale hasta el lunes 8 (festivo)
    bronce = pd.DataFrame({"valor": ["4900.5", "4950"],
                           "unidad": ["COP", "COP"],
                           "vigenciadesde": ["2024-01-05T00:00:00.000", "2024-01-09T00:00:00.000"],
                           "vigenciahasta": ["2024-01-08T00:00:00.000", "2024-01-09T00:00:00.000"]})
    # Act
    diaria, _, _ = trm.limpiar(bronce, "2024-01-05", "2024-01-09")
    # Assert: 5 dias seguidos, del 5 al 8 con la misma TRM
    assert len(diaria) == 5
    assert diaria["trm_cop_usd"].tolist() == [4900.5, 4900.5, 4900.5, 4900.5, 4950.0]

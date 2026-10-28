from src.utils.dates import generar_ventanas_fechas

def test_generar_ventanas_fechas():
    resultado = generar_ventanas_fechas("2024-01-01", "2024-01-10", dias_ventana=5)
    assert len(resultado) == 2
    assert resultado[0] == ("2024-01-01", "2024-01-05")

def test_ventanas_limite_mes():
    resultado = generar_ventanas_fechas("2024-01-01", "2024-01-31", dias_ventana=30)
    assert resultado[0][0] == "2024-01-01"
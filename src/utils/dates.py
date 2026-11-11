from datetime import datetime, timedelta
from typing import List, Tuple

def generar_ventanas_fechas(fecha_inicio: str, fecha_fin: str, dias_ventana: int = 30) -> List[Tuple[str, str]]:
    """Particiona un rango amplio de fechas en ventanas pequeñas de N días."""
    fmt = "%Y-%m-%d"
    inicio = datetime.strptime(fecha_inicio, fmt)
    fin = datetime.strptime(fecha_fin, fmt)
    
    ventanas = []
    actual = inicio
    # <= (y no <): si no, el ultimo dia del rango se pierde cuando la ultima
    # ventana termina justo un dia antes de fin
    while actual <= fin:
        siguiente = min(actual + timedelta(days=dias_ventana - 1), fin)
        ventanas.append((actual.strftime(fmt), siguiente.strftime(fmt)))
        actual = siguiente + timedelta(days=1)
        
    return ventanas
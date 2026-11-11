from datetime import datetime

def log(mensaje: str):
    """Imprime un mensaje en consola precedido por la hora actual [HH:MM:SS]."""
    hora_actual = datetime.now().strftime("%H:%M:%S")
    print(f"[{hora_actual}] {mensaje}")
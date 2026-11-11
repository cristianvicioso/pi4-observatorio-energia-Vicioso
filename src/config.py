from pathlib import Path

# Define la raíz del proyecto (un nivel arriba de la carpeta src)
RAIZ = Path(__file__).resolve().parent.parent

# Rutas de las carpetas de datos
DIR_BRONZE = RAIZ / "data" / "bronze"
DIR_SILVER = RAIZ / "data" / "silver"
DIR_GOLD = RAIZ / "data" / "gold"
DIR_DOCS = RAIZ / "docs"
DIR_SILVER = RAIZ / "data" / "silver"       # capa plata: los datos ya limpios
DIR_DOCS = RAIZ / "docs"                    # documentacion: perfilamiento, reporte de calidad

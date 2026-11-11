"""
Ejecuta las consultas de consultas/oro/ sobre la capa oro y muestra el
resultado como tabla Markdown (asi se copiaron al README).

Uso:
    python -m src.consultar                 # todas
    python -m src.consultar 01 03           # solo las que empiezan por 01 y 03
"""
import sys

import duckdb

from src import config

DIR_CONSULTAS = config.RAIZ / "consultas" / "oro"
BASE = config.RAIZ / "data" / "observatorio.duckdb"


def a_markdown(nombres: list[str], filas: list[tuple]) -> str:
    def celda(v):
        if isinstance(v, float):
            return f"{v:,.2f}".rstrip("0").rstrip(".") if abs(v) < 1e15 else str(v)
        return "" if v is None else str(v)
    lineas = ["| " + " | ".join(nombres) + " |", "|" + "---|" * len(nombres)]
    lineas += ["| " + " | ".join(celda(v) for v in fila) + " |" for fila in filas]
    return "\n".join(lineas)


def main(prefijos: list[str]) -> None:
    con = duckdb.connect(str(BASE), read_only=True)
    for archivo in sorted(DIR_CONSULTAS.glob("*.sql")):
        if prefijos and not any(archivo.name.startswith(p) for p in prefijos):
            continue
        sql = archivo.read_text(encoding="utf-8")
        resultado = con.execute(sql)
        nombres = [d[0] for d in resultado.description]
        print(f"\n### {archivo.name}\n")
        print(a_markdown(nombres, resultado.fetchall()))
    con.close()


if __name__ == "__main__":
    main(sys.argv[1:])

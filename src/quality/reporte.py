"""
Reporte de calidad de la capa plata.

Cada programa de limpieza (src/silver/*.py) guarda sus metricas en
data/silver/_metricas/<fuente>.json con guardar_metricas(). Al final,
escribir_reporte() junta todas y escribe docs/reporte_calidad.md con una
tabla por fuente: problema, regla aplicada y metrica antes -> despues.

Uso:
    python -m src.quality.reporte
"""
import json
from datetime import datetime

from src import config

DIR_METRICAS = config.DIR_SILVER / "_metricas"

# Orden en que salen las fuentes en el reporte
ORDEN = ["enerandes", "xm", "ideam", "noaa", "trm", "divipola"]


class Metricas:
    """Lista de reglas medidas. Uso: m.medir('Filas duplicadas', 'Dejar una copia', 120, 0)."""

    def __init__(self) -> None:
        self.filas: list[dict] = []

    def medir(self, problema: str, regla: str, antes, despues, detalle: str = "-") -> None:
        self.filas.append({"problema": problema, "regla aplicada": regla,
                           "antes": antes, "despues": despues, "detalle": detalle})


def guardar_metricas(nombre: str, resumen: dict) -> None:
    DIR_METRICAS.mkdir(parents=True, exist_ok=True)
    (DIR_METRICAS / f"{nombre}.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _num(valor) -> str:
    return f"{valor:,}".replace(",", ".") if isinstance(valor, int) else str(valor)


def _tabla_resumen(resumenes: list[dict]) -> list[str]:
    lineas = ["| Fuente | Tabla(s) plata | Filas bronce | Filas plata | Filas en cuarentena | Reglas |",
              "|---|---|---:|---:|---:|---:|"]
    for r in resumenes:
        lineas.append(f"| {r['fuente']} | `{r['tabla']}` | {_num(r['filas_bronce'])} | "
                      f"{_num(r['filas_plata'])} | {_num(r['filas_cuarentena'])} | {len(r['metricas'])} |")
    total = sum(len(r["metricas"]) for r in resumenes)
    cuarentena = sum(r["filas_cuarentena"] for r in resumenes)
    lineas.append(f"| **Total** | | | | **{_num(cuarentena)}** | **{total}** |")
    return lineas


def escribir_reporte() -> None:
    resumenes = []
    for nombre in ORDEN:
        archivo = DIR_METRICAS / f"{nombre}.json"
        if archivo.exists():
            resumenes.append(json.loads(archivo.read_text(encoding="utf-8")))

    lineas = [
        "# Reporte de calidad - capa plata",
        "",
        f"_Generado automaticamente por `python -m src.transformar` el "
        f"{datetime.now():%Y-%m-%d %H:%M}. No editar a mano: se reescribe en cada ejecucion._",
        "",
        "Cada tabla de la capa plata se valida con un esquema de pandera "
        "(`src/quality/esquemas.py`) antes de guardarse: si una regla falla, la tabla no se guarda. "
        "Las filas que no se pueden corregir no se borran: quedan en un archivo `*_cuarentena.parquet` "
        "en `data/silver/` con el motivo.",
        "",
        "## Resumen",
        "",
        *_tabla_resumen(resumenes),
        "",
    ]
    numero = 1
    for r in resumenes:
        lineas += [f"## {r['fuente']}", "",
                   f"- Filas en bronce: {_num(r['filas_bronce'])}",
                   f"- Filas en plata: {_num(r['filas_plata'])}",
                   f"- Filas en cuarentena: {_num(r['filas_cuarentena'])}"]
        for motivo, n in r.get("motivos_cuarentena", {}).items():
            lineas.append(f"  - {motivo}: {_num(n)}")
        if r.get("nota"):
            lineas += ["", r["nota"]]
        lineas += ["", "| # | Problema | Regla aplicada | Antes | Despues | Detalle |",
                   "|---|---|---|---:|---:|---|"]
        for m in r["metricas"]:
            lineas.append(f"| {numero} | {m['problema']} | {m['regla aplicada']} | "
                          f"{_num(m['antes'])} | {_num(m['despues'])} | {m.get('detalle', '-')} |")
            numero += 1
        lineas.append("")

    config.DIR_DOCS.mkdir(parents=True, exist_ok=True)
    (config.DIR_DOCS / "reporte_calidad.md").write_text("\n".join(lineas), encoding="utf-8")


if __name__ == "__main__":
    escribir_reporte()

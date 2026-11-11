"""12 · Láminas (PRD §6.15). `make laminas`. Escribe laminas/laminas.pptx (5 láminas, 16:9).

Las cifras se leen de salida/ y reporte/tablas/; el archivo es un punto de partida que el alumno
edita en PowerPoint.
"""
from __future__ import annotations

import sys

from mtx import config, laminas


def main() -> int:
    ruta = laminas.generar(config.RAIZ / "laminas" / "laminas.pptx")
    print(f"{ruta.relative_to(config.RAIZ)} generado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

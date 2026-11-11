"""11 · Reporte PDF (PRD §6.14, D21). `make reporte`.

Regenera las tablas compactas de `reporte/tablas/` desde `salida/`, actualiza la sección de
resultados del README entre sus marcadores, sustituye los marcadores `<!-- tabla:X -->` de
`reporte/reporte.md` en una copia (`reporte/_compilado.md`) y la compila con pandoc y XeLaTeX.
Nunca sobrescribe la prosa de `reporte/reporte.md`.

Falla (código 1) si faltan valoraciones del alumno, si el PDF no tiene entre 4 y 6 páginas o si
no se pudo compilar; aun así deja las tablas y el borrador para revisar.
"""
from __future__ import annotations

import json
import sys

import yaml

from mtx import config, reporte, respuestas

MD = reporte.DIR_REPORTE / "reporte.md"
COMPILADO = reporte.DIR_REPORTE / "_compilado.md"
PDF = reporte.DIR_REPORTE / "reporte.pdf"
ENCABEZADO = reporte.DIR_REPORTE / "encabezado.tex"
VALORACIONES = config.DIR_ANOTACIONES / "valoraciones.yaml"
HASHES = config.DIR_SALIDA / "10_tablas_hash.json"


def main() -> int:
    problemas = []
    tablas = reporte.escribir_tablas()
    if reporte.actualizar_readme(config.RAIZ / "README.md", reporte.bloque_readme()):
        print("README: sección de resultados actualizada.")
    else:
        print("AVISO: README.md sin marcadores de resultados; no se tocó.")

    texto, faltan = reporte.sustituir_tablas(MD.read_text(encoding="utf-8"), tablas)
    if faltan:
        problemas.append(f"Marcadores sin tabla: {faltan}")
    if "```" in texto:
        problemas.append("El reporte contiene bloques de código (prohibido por el enunciado)")
    COMPILADO.write_text(texto, encoding="utf-8", newline="\n")

    val = yaml.safe_load(VALORACIONES.read_text(encoding="utf-8")) if VALORACIONES.exists() else {}
    hashes = json.loads(HASHES.read_text(encoding="utf-8"))
    pend = respuestas.validar_valoraciones(val or {}, hashes)
    if pend:
        problemas.append(f"[VALIDAR] valoraciones del alumno pendientes ({len(pend)} de 10)")

    ok, msg = reporte.compilar(COMPILADO, PDF, ENCABEZADO)
    if not ok:
        problemas.append(f"No se compiló el PDF: {msg}")
    else:
        n = reporte.contar_paginas(PDF)
        print(f"reporte/reporte.pdf: {n} páginas.")
        if not 4 <= n <= 6:
            problemas.append(f"El PDF tiene {n} páginas; deben ser entre 4 y 6")
    for p in problemas:
        print("PROBLEMA:", p)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

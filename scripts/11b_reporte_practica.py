"""11b · Reporte con el formato de prácticas de Arturo (skill `practicas-arturo`).

Convierte `reporte/reporte.md` (prosa aprobada, sin cambios de texto) al spec de la skill, genera
`reporte/reporte.docx` con su `generar_practica.py` (portada con marco y logo, índice, numeración
desde la primera sección, ecuaciones nativas de Word) y lo exporta a `reporte/reporte.pdf` con
Microsoft Word. Requiere Node.js con el paquete `docx`, pandoc y Word (Windows).

Uso: python scripts/11b_reporte_practica.py --skill <ruta de la skill practicas-arturo>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from mtx import reporte

PORTADA = {"titulo": "Análisis de las Mañaneras 2018-2024", "materia": "Minería de Textos",
           "fecha": "11 de noviembre de 2026", "autores": ["Arturo Jaramillo Salmerón"]}
DIR = reporte.DIR_REPORTE / "practica"
DOCX = reporte.DIR_REPORTE / "reporte.docx"
PDF = reporte.DIR_REPORTE / "reporte.pdf"


def word_a_pdf(docx: Path, pdf: Path) -> None:
    """Actualiza campos (índice) y exporta a PDF con Word por COM."""
    ps = (f"$w = New-Object -ComObject Word.Application; $w.Visible = $false; "
          f"$d = $w.Documents.Open('{docx}'); $d.Fields.Update() | Out-Null; "
          f"foreach ($t in $d.TablesOfContents) {{ $t.Update() }}; "
          f"$d.SaveAs2('{pdf}', 17); $d.Close($false); $w.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", required=True, type=Path)
    ap.add_argument("--python", default=sys.executable)
    a = ap.parse_args()
    DIR.mkdir(parents=True, exist_ok=True)
    md = (reporte.DIR_REPORTE / "reporte.md").read_text(encoding="utf-8")
    spec = reporte.spec_practica(md, reporte.escribir_tablas(), PORTADA)
    (DIR / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n",
                                   encoding="utf-8", newline="\n")
    r = subprocess.run([a.python, str(a.skill / "scripts" / "generar_practica.py"),
                        str(DIR / "spec.json"), "-o", str(DOCX)], check=False)
    if r.returncode != 0:
        return r.returncode
    word_a_pdf(DOCX.resolve(), PDF.resolve())
    n = reporte.contar_paginas(PDF)
    print(f"reporte/reporte.pdf: {n} páginas en total (portada e índice incluidos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tablas compactas del reporte, bloque de resultados del README y compilación (PRD §6.14, D21).

Las tablas salen de `salida/` (nunca se escriben cifras a mano). `reporte/reporte.md` contiene la
prosa aprobada por el alumno y marcadores `<!-- tabla:NOMBRE -->`; la compilación los sustituye en
una copia (`reporte/_compilado.md`) para que la prosa no se regenere nunca.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from . import config

DIR_REPORTE = config.RAIZ / "reporte"
DIR_TABLAS = DIR_REPORTE / "tablas"
PROMEDIO = "PROMEDIO (MAP = AP)"
NOMBRES_IR = {"tfidf_con_filtro": "TF-IDF con filtro", "bm25_con_filtro": "BM25 con filtro",
              "tfidf_sin_filtro": "TF-IDF sin filtro", "bm25_sin_filtro": "BM25 sin filtro"}
NOMBRES_IE = {"regla": "Reglas", "modelo": "Modelo", "combinado": "Combinado"}
MARCADOR = re.compile(r"<!--\s*tabla:([\w-]+)\s*-->")
INICIO_README, FIN_README = "<!-- resultados:inicio -->", "<!-- resultados:fin -->"


def _md(df: pd.DataFrame, alinear: str | None = None) -> str:
    """Tabla Markdown de tubos (pandoc la convierte en tabla con booktabs)."""
    cols = list(df.columns)
    al = alinear or "l" + "r" * (len(cols) - 1)
    sep = ["---:" if a == "r" else ":---" for a in al]
    filas = ["| " + " | ".join(map(str, cols)) + " |", "| " + " | ".join(sep) + " |"]
    filas += ["| " + " | ".join(str(v) for v in f) + " |" for f in df.itertuples(index=False)]
    return "\n".join(filas) + "\n"


def _f(x, d: int = 3) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{float(x):.{d}f}"


def _miles(n) -> str:
    return f"{int(n):,}"


def tabla_corpus(s: Path = config.DIR_SALIDA) -> str:
    est = json.loads((s / "01_estadisticas_corpus.json").read_text(encoding="utf-8"))
    lim = json.loads((s / "01_limpieza.json").read_text(encoding="utf-8"))
    ind = json.loads((config.DIR_DATA / "indice_meta.json").read_text(encoding="utf-8"))
    rep = pd.read_csv(s / "01_fechas_reparadas.csv")
    filas = [("Discursos en el snapshot", _miles(est["discursos"])),
             ("Periodo", f"{est['fecha_min']} a {est['fecha_max']}"),
             ("Discursos excluidos (duplicados y casi duplicados)", lim["discursos_excluidos"]),
             ("Fechas reparadas", len(rep)),
             ("Acotaciones eliminadas", _miles(lim["acotaciones_eliminadas"])),
             ("Pasajes indexados (N)", _miles(ind["N"])),
             ("Vocabulario (stems)", _miles(ind["vocabulario"])),
             ("Longitud media de pasaje (avgdl, tokens)", _f(ind["avgdl"], 1))]
    return _md(pd.DataFrame(filas, columns=["Concepto", "Valor"]))


def tabla_ir(s: Path = config.DIR_SALIDA) -> str:
    of = pd.read_csv(s / "resultados_ir.csv")
    ve = pd.read_csv(s / "05_resultados_ir_ventana.csv")
    po, pv = (d[d["query_id"] == PROMEDIO].set_index("modelo") for d in (of, ve))
    filas = [(NOMBRES_IR[m], _f(po.loc[m, "P@5"]), _f(po.loc[m, "P@10"]), _f(po.loc[m, "AP"]),
              _f(pv.loc[m, "AP"])) for m in NOMBRES_IR]
    return _md(pd.DataFrame(filas, columns=["Variante", "P@5", "P@10", "MAP oficial",
                                            "MAP con ventana"]))


def tabla_ir_consulta(s: Path = config.DIR_SALIDA) -> str:
    g = pd.read_csv(s / "05_ir_ganador_por_consulta.csv")
    g["ganador"] = g["ganador"].map({"bm25_con_filtro": "BM25", "tfidf_con_filtro": "TF-IDF",
                                     "empate": "empate"})
    g["sigla_o_nombre_propio"] = g["sigla_o_nombre_propio"].map({True: "sí", False: "no"})
    df = g[["query_id", "ap_tfidf_con_filtro", "ap_bm25_con_filtro", "ganador", "longitud",
            "terminos_df_alto", "sigla_o_nombre_propio"]].copy()
    for c in ("ap_tfidf_con_filtro", "ap_bm25_con_filtro"):
        df[c] = df[c].map(_f)
    df.columns = ["Consulta", "AP TF-IDF", "AP BM25", "Gana", "Longitud", "Términos df alto",
                  "Sigla o nombre propio"]
    return _md(df, "lrrllrl")


def tabla_ie(s: Path = config.DIR_SALIDA) -> str:
    d = pd.read_csv(s / "09_ie_detalle.csv")
    filas = []
    for tipo in ("PER", "ORG", "LOC", "FECHA", "MONTO", "TODOS"):
        fila = [tipo, int(d[(d["tipo"] == tipo) & (d["metodo"] == "combinado")]["soporte"].iloc[0])]
        for m in NOMBRES_IE:
            x = d[(d["tipo"] == tipo) & (d["metodo"] == m)].iloc[0]
            fila.append("s/c" if x["estado"] == "sin_cobertura" else
                        f"{_f(x['precision'], 2)} / {_f(x['recall'], 2)} / {_f(x['f1'], 2)}")
        filas.append(fila)
    return _md(pd.DataFrame(filas, columns=["Tipo", "Gold", *(f"{n} P / R / F1"
                                                              for n in NOMBRES_IE.values())]),
               "lrrrr")


def tabla_errores(s: Path = config.DIR_SALIDA) -> str:
    r = pd.read_csv(s / "09_resumen_errores.csv", keep_default_na=False)
    base = r[r["subcategoria"] == ""].groupby("categoria")["n"].sum()
    sub = r[r["subcategoria"] != ""].groupby(["categoria", "subcategoria"])["n"].sum()
    filas = [(c, int(n), "; ".join(f"{sc}: {int(v)}" for (cc, sc), v in sub.items() if cc == c))
             for c, n in base.sort_values(ascending=False).items()]
    return _md(pd.DataFrame(filas, columns=["Categoría", "Errores", "Subcasos"]), "lrl")


def tabla_respuestas(s: Path = config.DIR_SALIDA) -> str:
    r = pd.read_csv(s / "respuestas.csv", dtype=str)
    t = r.groupby(["query_id", "estado"]).size().unstack(fill_value=0)
    for e in ("respaldado_en_texto", "ambiguo", "contradictorio", "no_encontrado"):
        if e not in t:
            t[e] = 0
    t = t.loc[sorted(t.index, key=lambda q: int(q[1:]))].reset_index()
    t = t[["query_id", "respaldado_en_texto", "ambiguo", "contradictorio", "no_encontrado"]]
    t.columns = ["Consulta", "Respaldado", "Ambiguo", "Contradictorio", "Sin evidencia"]
    return _md(t)


TABLAS = {"corpus": tabla_corpus, "ir": tabla_ir, "ir_consulta": tabla_ir_consulta,
          "ie": tabla_ie, "errores": tabla_errores, "respuestas": tabla_respuestas}


def escribir_tablas(destino: Path = DIR_TABLAS) -> dict[str, str]:
    destino.mkdir(parents=True, exist_ok=True)
    out = {}
    for nombre, fn in TABLAS.items():
        out[nombre] = fn()
        (destino / f"{nombre}.md").write_text(out[nombre], encoding="utf-8", newline="\n")
    return out


def sustituir_tablas(md: str, tablas: dict[str, str]) -> tuple[str, list[str]]:
    """Reemplaza `<!-- tabla:X -->` por la tabla X; devuelve el texto y los marcadores sin tabla."""
    faltan = []

    def rep(m: re.Match) -> str:
        if m.group(1) not in tablas:
            faltan.append(m.group(1))
            return m.group(0)
        return "\n" + tablas[m.group(1)]
    return MARCADOR.sub(rep, md), faltan


def bloque_readme(s: Path = config.DIR_SALIDA) -> str:
    return ("Cifras autogeneradas por `scripts/11_reporte.py` desde `salida/`; no se editan a mano.\n\n"
            "Recuperación (`salida/resultados_ir.csv`, oficial, y `salida/05_resultados_ir_ventana.csv`):\n\n"
            + tabla_ir(s) + "\nExtracción (`salida/09_ie_detalle.csv`; s/c = el NER no cubre el tipo):\n\n"
            + tabla_ie(s))


def actualizar_readme(readme: Path, bloque: str) -> bool:
    """Reescribe solo lo que está entre los marcadores; False si el README no los tiene."""
    texto = readme.read_text(encoding="utf-8")
    if INICIO_README not in texto or FIN_README not in texto:
        return False
    a, resto = texto.split(INICIO_README, 1)
    _, b = resto.split(FIN_README, 1)
    readme.write_text(f"{a}{INICIO_README}\n{bloque}{FIN_README}{b}", encoding="utf-8",
                      newline="\n")
    return True


def compilar(md: Path, pdf: Path, encabezado: Path) -> tuple[bool, str]:
    """pandoc + XeLaTeX. Devuelve (ok, mensaje)."""
    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False, "Falta pandoc (Windows: winget install JohnMacFarlane.Pandoc)"
    if not shutil.which("xelatex"):
        return False, "Falta xelatex (Windows: MiKTeX)"
    p = subprocess.run([pandoc, md.name, "-o", str(pdf), "--pdf-engine=xelatex",
                        "-H", str(encabezado), "-V", "geometry:margin=2.2cm", "-V", "lang=es-MX",
                        "-V", "fontsize=10pt", "-V", "mainfont=Arial",
                        "--resource-path", str(md.parent)],
                       cwd=md.parent, capture_output=True, text=True, check=False)
    return p.returncode == 0, (p.stderr or p.stdout)[-2000:]


def contar_paginas(pdf: Path) -> int:
    from pypdf import PdfReader
    return len(PdfReader(str(pdf)).pages)

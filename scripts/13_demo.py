"""13 · Demo en terminal (PRD §6.16). `make demo Q=Q3` o `make demo CONSULTA="texto"`.

Con `--q`: solo lee artefactos congelados (ranking.csv, entidades enriquecidas, tablas de
respuesta); no recalcula índices, métricas ni entidades. Con `--consulta`: carga el índice, ordena
con TF-IDF y BM25 y extrae entidades solo con reglas (sin NER en caliente); lo avisa en pantalla y
no muestra métricas del experimento, porque esa consulta no tiene juicios ni gold.

Uso sin make:
    .venv/Scripts/python.exe scripts/13_demo.py --q Q3
    .venv/Scripts/python.exe scripts/13_demo.py --consulta "refinería de Dos Bocas" --desde 2019-01-01 --hasta 2022-12-31
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mtx import config, consultas

COLOR = {"PER": "magenta", "ORG": "cyan", "LOC": "green", "FECHA": "yellow", "MONTO": "red"}
NOMBRES = {"tfidf_con_filtro": "TF-IDF con filtro", "bm25_con_filtro": "BM25 con filtro",
           "tfidf": "TF-IDF", "bm25": "BM25"}


def resaltar(texto: str, ents: list[tuple[int, int, str, str]], inicio_cuerpo: int) -> Text:
    """Pasaje con las entidades coloreadas por tipo (subrayadas si las dio el modelo)."""
    t = Text(texto)
    t.stylize("dim", 0, inicio_cuerpo)
    for ini, fin, tipo, metodo in ents:
        estilo = f"bold {COLOR.get(tipo, 'white')}" + (" underline" if metodo != "regla" else "")
        t.stylize(estilo, ini, fin)
    return t


def tabla_lado_a_lado(c: Console, tops: dict[str, pd.DataFrame], textos: dict[str, str]) -> None:
    for modelo, df in tops.items():
        tab = Table(title=NOMBRES.get(modelo, modelo), show_lines=False, expand=True)
        for col in ("#", "pasaje", "fecha", "pos.", "puntaje", "inicio del texto"):
            tab.add_column(col, overflow="fold", no_wrap=col != "inicio del texto")
        for f in df.itertuples(index=False):
            tab.add_row(str(f.rango), str(f.passage_id), str(f.fecha)[:10], str(f.posicion),
                        f"{float(f.puntaje):.4f}", " ".join(textos[f.passage_id].split())[:100])
        c.print(tab)


def demo_consulta_oficial(c: Console, qid: str) -> None:
    cons = consultas.cargar().set_index("query_id")
    if qid not in cons.index:
        c.print(f"[red]{qid} no está en data/consultas.csv[/red]")
        sys.exit(1)
    q = cons.loc[qid]
    mejor = json.loads((config.DIR_DATA / "mejor_modelo.json").read_text(encoding="utf-8"))["modelo"]
    c.print(Panel(f"[bold]{qid}[/bold] · {q['consulta']}\nVentana: {q['desde']} a {q['hasta']}\n"
                  f"Pregunta: {q['pregunta_extraccion']}\nModelo para extracción: {mejor} "
                  "(fijado por MAP oficial)", title="1 · Consulta"))
    rk = pd.read_csv(config.RAIZ / "ranking.csv", dtype={"passage_id": str})
    rk = rk[rk["query_id"] == qid]
    ids = list(rk["passage_id"].unique())
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "inicio_cuerpo"],
                          filters=[("passage_id", "in", ids)]).set_index("passage_id")
    textos = pas["texto"].to_dict()
    c.rule("2 · Top-10 de TF-IDF y BM25 con filtro (ranking.csv)")
    tops = {m: rk[rk["modelo"] == m].sort_values("rango")
            for m in ("tfidf_con_filtro", "bm25_con_filtro")}
    tabla_lado_a_lado(c, tops, textos)
    comunes = set(tops["tfidf_con_filtro"]["passage_id"]) & set(tops["bm25_con_filtro"]["passage_id"])
    c.print(f"Pasajes en ambos top-10: {len(comunes)} de 10.")

    c.rule(f"3 · Entidades del top-10 de {NOMBRES.get(mejor, mejor)} (entidades.csv)")
    ent = pd.read_csv(config.DIR_SALIDA / "entidades_enriquecidas.csv", dtype={"passage_id": str})
    ent = ent[ent["query_id"] == qid]
    leyenda = Text("Tipos: ")
    for tipo, col in COLOR.items():
        leyenda.append(f"{tipo} ", style=f"bold {col}")
    leyenda.append("· subrayado = lo dio el modelo (modelo o ambos) · gris = marca de interlocutor")
    c.print(leyenda)
    for f in rk[rk["modelo"] == mejor].sort_values("rango").head(3).itertuples(index=False):
        e = ent[ent["passage_id"] == f.passage_id]
        spans = [(int(x.inicio), int(x.fin), x.tipo, x.metodo) for x in e.itertuples(index=False)]
        c.print(Panel(resaltar(textos[f.passage_id], spans, int(pas.loc[f.passage_id, "inicio_cuerpo"])),
                      title=f"#{f.rango} · {f.passage_id} · {len(spans)} entidades", expand=True))
    resumen = ent.groupby(["tipo", "metodo"]).size().unstack(fill_value=0)
    tab = Table(title="Entidades del top-10 por tipo y método")
    tab.add_column("tipo")
    for m in resumen.columns:
        tab.add_column(m, justify="right")
    for tipo, fila in resumen.iterrows():
        tab.add_row(Text(tipo, style=COLOR.get(tipo, "")), *(str(int(v)) for v in fila))
    c.print(tab)

    c.rule("4 · Tabla de respuesta con evidencia (salida/tablas_respuesta)")
    md = (config.DIR_SALIDA / "tablas_respuesta" / f"{qid}.md").read_text(encoding="utf-8")
    c.print(Markdown(md))


def demo_consulta_libre(c: Console, texto: str, desde: str | None, hasta: str | None) -> None:
    from mtx import indice, ranking, reglas
    c.print(Panel(f"Consulta libre: [bold]{texto}[/bold]\nVentana: {desde or '—'} a {hasta or '—'}\n"
                  "[yellow]Aviso: consulta fuera del experimento. No tiene juicios ni gold, así que "
                  "no se muestran MAP ni F1. Las entidades salen solo de reglas y gazetteers "
                  "(sin NER en caliente).[/yellow]", title="1 · Consulta"))
    t0 = time.perf_counter()
    ind = indice.cargar(config.DIR_DATA / "indice.pkl")
    tfidf = ranking.cargar_tfidf(config.DIR_DATA / "tfidf.pkl", config.DIR_DATA / "tfidf_X.npz")
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "doc_id", "fecha", "posicion", "texto",
                                   "inicio_cuerpo"])
    pas = pas.set_index("passage_id").loc[ind.ids].reset_index()
    b = ranking.Buscador(ind, tfidf, pas)
    c.print(f"Índice cargado en {time.perf_counter() - t0:.1f} s.")
    tops = {}
    for m in ("tfidf", "bm25"):
        df, estado = b.buscar(texto, desde, hasta, modelo=m)
        tops[m] = df
        for a in estado["avisos"]:
            c.print(f"[yellow]{NOMBRES[m]}: {a}[/yellow]")
    c.print(f"Tokens de la consulta: {estado['tokens']}")
    textos = dict(zip(pas["passage_id"], pas["texto"], strict=True))
    c.rule("2 · Top-10 de TF-IDF y BM25")
    tabla_lado_a_lado(c, tops, textos)
    c.rule("3 · Entidades por reglas en los tres primeros de BM25")
    gaz = reglas.cargar_gazetteer()
    cuerpos = dict(zip(pas["passage_id"], pas["inicio_cuerpo"], strict=True))
    for f in tops["bm25"].head(3).itertuples(index=False):
        es = reglas.extraer_reglas(textos[f.passage_id], int(cuerpos[f.passage_id]), gaz)
        spans = [(e.inicio, e.fin, e.tipo, "regla") for e in es]
        c.print(Panel(resaltar(textos[f.passage_id], spans, int(cuerpos[f.passage_id])),
                      title=f"#{f.rango} · {f.passage_id} · {len(spans)} entidades"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--q", help="ID de una consulta oficial (Q1 a Q10)")
    g.add_argument("--consulta", help="texto de una consulta libre")
    ap.add_argument("--desde")
    ap.add_argument("--hasta")
    a = ap.parse_args()
    c = Console(width=140)
    t0 = time.perf_counter()
    if a.q:
        demo_consulta_oficial(c, a.q.upper())
    else:
        demo_consulta_libre(c, a.consulta, a.desde, a.hasta)
    c.rule(f"Tiempo total: {time.perf_counter() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Métricas del Examen 1. Se entrega a los alumnos para que todos calculen igual.

Tarea A (IR):
    python evaluar.py ir  juicios_relevancia.csv  ranking.csv  -> resultados_ir.csv
      juicios_relevancia.csv: query_id, doc_id, passage_id, relevante (0/1)
      ranking.csv:            query_id, modelo, rango, passage_id   (top-10 por consulta y modelo)

Tarea B (IE):
    python evaluar.py ie  gold_entidades.csv  entidades.csv        -> resultados_ie.csv
      gold_entidades.csv: passage_id, tipo, texto, inicio, fin
      entidades.csv:      query_id, doc_id, passage_id, tipo, texto, inicio, fin, metodo
      Solo se evalúan los pasajes que aparecen en el gold. Coincidencia exacta de (tipo, inicio, fin).
"""
from __future__ import annotations

import sys

import pandas as pd


def precision_en_k(rel: list[int], k: int) -> float:
    rel_k = rel[:k]
    return sum(rel_k) / k if rel_k else 0.0


def average_precision(rel: list[int], total_relevantes: int) -> float:
    """AP = promedio de la precisión en cada posición relevante, dividido entre el total de
    relevantes conocidos (los del pool), como en la sesión 2. MAP = promedio de AP entre consultas."""
    aciertos, suma = 0, 0.0
    for i, r in enumerate(rel, start=1):
        if r:
            aciertos += 1
            suma += aciertos / i
    return suma / total_relevantes if total_relevantes else 0.0


def evaluar_ir(juicios_path: str, ranking_path: str, salida: str = "resultados_ir.csv"):
    jz = pd.read_csv(juicios_path)
    rk = pd.read_csv(ranking_path).sort_values(["query_id", "modelo", "rango"])
    rel = {(r.query_id, r.passage_id): int(r.relevante) for r in jz.itertuples(index=False)}
    total_rel = jz[jz.relevante == 1].groupby("query_id").size().to_dict()

    filas = []
    for (qid, modelo), g in rk.groupby(["query_id", "modelo"], sort=False):
        r = [rel.get((qid, p), 0) for p in g.passage_id]  # pasaje no juzgado = no relevante
        n_rel = total_rel.get(qid, 0)
        filas.append({"query_id": qid, "modelo": modelo, "P@5": precision_en_k(r, 5),
                      "P@10": precision_en_k(r, 10), "AP": round(average_precision(r, n_rel), 4),
                      "relevantes_recuperados": sum(r), "relevantes_en_pool": n_rel,
                      "no_juzgados": sum(1 for p in g.passage_id if (qid, p) not in rel)})
    res = pd.DataFrame(filas)
    prom = res.groupby("modelo")[["P@5", "P@10", "AP"]].mean().round(4).reset_index()
    prom.insert(0, "query_id", "PROMEDIO (MAP = AP)")
    res = pd.concat([res, prom], ignore_index=True)
    res.to_csv(salida, index=False)
    print(res.to_string(index=False))
    return res


def evaluar_ie(gold_path: str, pred_path: str, salida: str = "resultados_ie.csv"):
    gold = pd.read_csv(gold_path)
    pred = pd.read_csv(pred_path)
    pred = pred[pred.passage_id.isin(gold.passage_id.unique())]
    tipos = sorted(set(gold.tipo) | set(pred.tipo))
    G = {(r.passage_id, r.tipo, int(r.inicio), int(r.fin)) for r in gold.itertuples(index=False)}

    def prf(P: set, Gs: set):
        tp = len(P & Gs)
        p = tp / len(P) if P else 0.0
        r = tp / len(Gs) if Gs else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        return round(p, 4), round(r, 4), round(f, 4), tp, len(P), len(Gs)

    filas = []
    metodos = ["regla", "modelo", "combinado"]
    for metodo in metodos:
        sub = pred if metodo == "combinado" else pred[pred.metodo.isin([metodo, "ambos"])]
        P_all = {(r.passage_id, r.tipo, int(r.inicio), int(r.fin)) for r in sub.itertuples(index=False)}
        for tipo in tipos + ["TODOS"]:
            Pt = P_all if tipo == "TODOS" else {x for x in P_all if x[1] == tipo}
            Gt = G if tipo == "TODOS" else {x for x in G if x[1] == tipo}
            p, r, f, tp, npred, ngold = prf(Pt, Gt)
            filas.append({"metodo": metodo, "tipo": tipo, "precision": p, "recall": r, "f1": f,
                          "tp": tp, "predichas": npred, "gold": ngold})
    res = pd.DataFrame(filas)
    res.to_csv(salida, index=False)
    print(res.to_string(index=False))
    return res


if __name__ == "__main__":
    if len(sys.argv) < 4 or sys.argv[1] not in ("ir", "ie"):
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "ir":
        evaluar_ir(sys.argv[2], sys.argv[3])
    else:
        evaluar_ie(sys.argv[2], sys.argv[3])

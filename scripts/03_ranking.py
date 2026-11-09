"""03 · Ranking TF-IDF y BM25, con y sin filtro de fecha (PRD §6.4). `make ranking`.

Entrada: data/indice.pkl, data/tfidf.pkl, data/tfidf_X.npz, data/tokens.parquet (por su hash),
data/pasajes.parquet y data/consultas.csv. No lee juicios ni gold.
Salidas: salida/ranking.csv (copia idéntica en la raíz) y salida/03_ranking_detalle.csv,
03_solape_modelos.csv, 03_excluidos_por_filtro.csv.
"""
from __future__ import annotations

import shutil

import numpy as np
import pandas as pd

from mtx import adaptadores_kit, config, consultas, indice, ranking

COLUMNAS = ["query_id", "modelo", "variante", "rango", "passage_id", "doc_id", "fecha",
            "posicion", "puntaje"]
TOKENS_PARQUET = config.DIR_DATA / "tokens.parquet"
ORDEN_MODELOS = ["tfidf_con_filtro", "bm25_con_filtro", "tfidf_sin_filtro", "bm25_sin_filtro"]


def formato_ranking(r: pd.DataFrame) -> pd.DataFrame:
    """Aplica el contrato de `ranking.csv`: 9 columnas, fecha ISO o vacía, puntaje con 6 decimales."""
    out = r[COLUMNAS].copy()
    out["fecha"] = out["fecha"].dt.strftime("%Y-%m-%d").fillna("")
    out["puntaje"] = out["puntaje"].map(lambda x: f"{x:.6f}")
    return out


def validar(r: pd.DataFrame, cons: pd.DataFrame) -> list[str]:
    """Comprueba claves únicas y el conteo de filas; devuelve las excepciones a 400 filas."""
    assert not r.duplicated(["query_id", "modelo", "rango"]).any(), "rango repetido"
    assert not r.duplicated(["query_id", "modelo", "passage_id"]).any(), "pasaje repetido"
    excepciones = []
    for q in cons["query_id"]:
        for m in ORDEN_MODELOS:
            n = int(((r["query_id"] == q) & (r["modelo"] == m)).sum())
            if n != ranking.K:
                excepciones.append(f"{q} {m}: {n} filas")
    return excepciones


def solape(r: pd.DataFrame, cons: pd.DataFrame) -> pd.DataFrame:
    def top(q, m):
        return set(r[(r["query_id"] == q) & (r["modelo"] == m)]["passage_id"])

    def docs(q, m):
        return r[(r["query_id"] == q) & (r["modelo"] == m)]["doc_id"].nunique()

    filas = []
    for q in cons["query_id"]:
        fila = {
            "query_id": q,
            "tfidf_vs_bm25_con_filtro": len(top(q, "tfidf_con_filtro") & top(q, "bm25_con_filtro")),
            "tfidf_vs_bm25_sin_filtro": len(top(q, "tfidf_sin_filtro") & top(q, "bm25_sin_filtro")),
            "tfidf_con_vs_sin_filtro": len(top(q, "tfidf_con_filtro") & top(q, "tfidf_sin_filtro")),
            "bm25_con_vs_sin_filtro": len(top(q, "bm25_con_filtro") & top(q, "bm25_sin_filtro")),
        }
        for m in ORDEN_MODELOS:
            fila[f"discursos_distintos_{m}"] = docs(q, m)
        filas.append(fila)
    return pd.DataFrame(filas)


def excluidos(r: pd.DataFrame, cons: pd.DataFrame, buscador: ranking.Buscador) -> pd.DataFrame:
    """Del top-10 sin filtro, cuántos caen fuera de la ventana o tienen fecha desconocida."""
    filas = []
    for c in cons.itertuples(index=False):
        elegibles = ranking.mascara_fecha(buscador.fecha, c.desde, c.hasta)
        for modelo in ranking.MODELOS:
            t = r[(r["query_id"] == c.query_id) & (r["modelo"] == f"{modelo}_sin_filtro")]
            fuera = t[~t["fecha"].notna() | ~pd.Series(
                [bool(elegibles[buscador.pasajes.index[buscador.pasajes["passage_id"] == p][0]])
                 for p in t["passage_id"]], index=t.index)]
            filas.append({
                "query_id": c.query_id, "modelo": f"{modelo}_sin_filtro",
                "ventana": f"{c.desde} a {c.hasta}", "pasajes_elegibles": int(elegibles.sum()),
                "pasajes_excluidos_por_filtro": int((~elegibles).sum()),
                "top10_fuera_de_ventana": int(fuera["fecha"].notna().sum()),
                "top10_fecha_desconocida": int(fuera["fecha"].isna().sum()),
                "rangos_afectados": ";".join(map(str, fuera["rango"])),
                "fechas_afectadas": ";".join("desconocida" if pd.isna(f) else f.date().isoformat()
                                             for f in fuera["fecha"]),
            })
    return pd.DataFrame(filas)


def main() -> None:
    config.DIR_SALIDA.mkdir(exist_ok=True)
    hash_tokens = adaptadores_kit.sha256_archivo(TOKENS_PARQUET)
    ind = indice.cargar(config.DIR_DATA / "indice.pkl", config.DIR_DATA / "indice_meta.json",
                        hash_tokens)
    tfidf = ranking.cargar_tfidf(config.DIR_DATA / "tfidf.pkl", config.DIR_DATA / "tfidf_X.npz")
    pasajes = pd.read_parquet(config.PASAJES_PARQUET, columns=[
        "passage_id", "doc_id", "posicion", "fecha", "titulo", "interlocutor", "es_reportero",
        "texto"])
    cons = consultas.cargar()
    buscador = ranking.Buscador(ind, tfidf, pasajes)

    crudo = ranking.variantes_oficiales(buscador, cons)
    crudo["modelo"] = pd.Categorical(crudo["modelo"], ORDEN_MODELOS, ordered=True)
    crudo["query_id"] = pd.Categorical(crudo["query_id"], list(cons["query_id"]), ordered=True)
    crudo = crudo.sort_values(["query_id", "modelo", "rango"], kind="stable").reset_index(drop=True)
    crudo["modelo"], crudo["query_id"] = crudo["modelo"].astype(str), crudo["query_id"].astype(str)

    excepciones = validar(crudo, cons)
    print(f"Filas: {len(crudo)} (esperadas {len(cons) * 4 * ranking.K}).")
    for e in excepciones:
        print("EXCEPCIÓN:", e)

    salida = formato_ranking(crudo)
    ruta = config.DIR_SALIDA / "ranking.csv"
    salida.to_csv(ruta, index=False, encoding="utf-8", lineterminator="\n")
    shutil.copyfile(ruta, config.RAIZ / "ranking.csv")

    meta = pasajes.set_index("passage_id")[["titulo", "interlocutor", "es_reportero", "texto"]]
    detalle = formato_ranking(crudo).join(crudo["sin_senal_lexica"]).join(
        meta, on="passage_id").assign(texto=lambda d: d["texto"].str.slice(0, 400))
    detalle = detalle[COLUMNAS + ["interlocutor", "es_reportero", "titulo", "sin_senal_lexica",
                                  "texto"]]
    detalle.to_csv(config.DIR_SALIDA / "03_ranking_detalle.csv", index=False, lineterminator="\n")

    sol = solape(crudo, cons)
    sol.to_csv(config.DIR_SALIDA / "03_solape_modelos.csv", index=False, lineterminator="\n")
    exc = excluidos(crudo, cons, buscador)
    exc.to_csv(config.DIR_SALIDA / "03_excluidos_por_filtro.csv", index=False, lineterminator="\n")

    print(sol.to_string(index=False))
    idénticos = [q for q in cons["query_id"]
                 if crudo[(crudo["query_id"] == q) & (crudo["modelo"] == "tfidf_con_filtro")][
                     "passage_id"].tolist()
                 == crudo[(crudo["query_id"] == q) & (crudo["modelo"] == "bm25_con_filtro")][
                     "passage_id"].tolist()]
    print("Consultas con ranking idéntico TF-IDF y BM25 (con filtro):", idénticos or "ninguna")
    sin_senal = int(np.sum(crudo["sin_senal_lexica"]))
    print("Filas sin señal léxica:", sin_senal)


if __name__ == "__main__":
    main()

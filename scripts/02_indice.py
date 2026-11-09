"""02 · Tokens, índice invertido y TF-IDF (PRD §6.2 y §6.3). `make indice`.

Entrada: data/pasajes.parquet y data/consultas.csv. No lee juicios ni gold.
Salidas: data/tokens.parquet, data/indice.pkl, data/indice_meta.json, data/tfidf.pkl,
data/tfidf_X.npz y salida/02_postings.md, 02_vocabulario_top.csv, 02_tokens_consultas.md,
02_memoria.json. Es determinista: dos corridas producen los mismos tokens e índice.
"""
from __future__ import annotations

import hashlib
import json
import resource
import time

import numpy as np
import pandas as pd

from mtx import adaptadores_kit, config, consultas, indice, preproceso, ranking

TOKENS_PARQUET = config.DIR_DATA / "tokens.parquet"
INDICE_PKL = config.DIR_DATA / "indice.pkl"
INDICE_META = config.DIR_DATA / "indice_meta.json"
TFIDF_PKL = config.DIR_DATA / "tfidf.pkl"
TFIDF_NPZ = config.DIR_DATA / "tfidf_X.npz"
TERMINOS_POSTINGS = ["tren", "vacuna", "refinería", "huachicol"]


def rss_mb() -> float:
    """Memoria residente máxima del proceso, en MB (Linux reporta KB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def escribir_tokens_consultas(cons: pd.DataFrame) -> list[str]:
    """`02_tokens_consultas.md`: tokens originales y finales de las diez consultas."""
    lineas = ["# Tokens de las consultas", "",
              (f"Stoplist: {len(preproceso.stoplist())} palabras "
               f"(sha256 `{preproceso.hash_stoplist()[:16]}…`). Sin expansión por sinónimos."), "",
              "| Consulta | Texto | Tokens sin stem | Tokens finales (stem) |", "|---|---|---|---|"]
    avisos = []
    for r in cons.itertuples(index=False):
        sin, fin = preproceso.tokenizar_sin_stem(r.consulta), preproceso.tokenizar(r.consulta)
        if not fin:
            avisos.append(f"{r.query_id} se quedó sin tokens")
        lineas.append(f"| {r.query_id} | {r.consulta} | {' '.join(sin)} | {' '.join(fin)} |")
    if avisos:
        lineas += ["", "**Aviso:** " + "; ".join(avisos)]
    (config.DIR_SALIDA / "02_tokens_consultas.md").write_text("\n".join(lineas) + "\n",
                                                              encoding="utf-8")
    return avisos


def escribir_postings(ind: indice.Indice, pasajes: pd.DataFrame) -> None:
    """`02_postings.md`: df, idf y top-15 por tf de cuatro términos de ejemplo."""
    lineas = ["# Listas de postings de ejemplo", "",
              ("Muestra: los 15 pasajes con mayor tf por término (desempate por `doc_id` y "
               "`posicion`). La lista completa vive en `data/indice.pkl`."), ""]
    doc, pos = pasajes["doc_id"].to_numpy(), pasajes["posicion"].to_numpy()
    for crudo in TERMINOS_POSTINGS:
        raices = preproceso.tokenizar(crudo)
        if not raices:
            lineas += [f"## {crudo}", "", "El término desaparece en el preprocesamiento.", ""]
            continue
        raiz = raices[0]
        fila = ind.postings.get(raiz, {})
        lineas += [f"## {crudo} → stem `{raiz}`", "",
                   f"df = {ind.df.get(raiz, 0)} de N = {ind.N}; idf BM25 = {ind.idf_bm25(raiz):.4f}",
                   "", "| passage_id | fecha | tf | contexto (80 caracteres) |", "|---|---|---|---|"]
        orden = sorted(fila, key=lambda i: (-fila[i], doc[i], pos[i]))[:15]
        for i in orden:
            p = pasajes.iloc[i]
            fecha = "" if pd.isna(p["fecha"]) else p["fecha"].date().isoformat()
            ctx = p["texto"][int(p["inicio_cuerpo"]):][:80].replace("|", "/").replace("\n", " ")
            lineas.append(f"| {p['passage_id']} | {fecha} | {fila[i]} | {ctx} |")
        lineas.append("")
    (config.DIR_SALIDA / "02_postings.md").write_text("\n".join(lineas), encoding="utf-8")


def main() -> None:
    t0 = time.time()
    config.DIR_SALIDA.mkdir(exist_ok=True)
    pasajes = pd.read_parquet(config.PASAJES_PARQUET,
                              columns=["passage_id", "doc_id", "posicion", "fecha", "texto",
                                       "inicio_cuerpo"])
    cons = consultas.cargar()
    avisos = escribir_tokens_consultas(cons)
    print(f"Pasajes: {len(pasajes):,}. Tokenizando…")

    lista_tokens = [preproceso.tokenizar_pasaje(t, int(i))
                    for t, i in zip(pasajes["texto"], pasajes["inicio_cuerpo"])]
    pd.DataFrame({"passage_id": pasajes["passage_id"], "tokens": lista_tokens}).to_parquet(
        TOKENS_PARQUET, index=False)
    hash_tokens = adaptadores_kit.sha256_archivo(TOKENS_PARQUET)
    hash_config = hashlib.sha256(json.dumps(
        preproceso.configuracion_efectiva(), sort_keys=True).encode("utf-8")).hexdigest()
    print(f"Tokens listos ({time.time() - t0:.0f} s). Construyendo índice…")

    mem_antes = rss_mb()
    ind = indice.construir(list(pasajes["passage_id"]), lista_tokens)
    mem_indice = rss_mb()
    meta = indice.guardar(ind, INDICE_PKL, INDICE_META, hash_tokens, hash_config)

    vec, X = ranking.ajustar_tfidf(lista_tokens)
    ranking.guardar_tfidf(vec, X, TFIDF_PKL, TFIDF_NPZ)

    # Verificación cruzada con CountVectorizer sobre los mismos tokens.
    cv, M = indice.matriz_conteos(lista_tokens)
    df_cv = np.asarray((M > 0).sum(axis=0)).ravel()
    coincide = (len(cv.vocabulary_) == len(ind.postings) and all(
        ind.df[t] == df_cv[j] for t, j in cv.vocabulary_.items()))
    print(f"df del índice == df de CountVectorizer: {coincide}")
    if not coincide:
        raise SystemExit("El índice a mano no coincide con CountVectorizer")

    escribir_postings(ind, pasajes)
    top = (pd.DataFrame({"termino": list(ind.df), "df": list(ind.df.values())})
           .assign(tf_total=lambda d: [sum(ind.postings[t].values()) for t in d["termino"]])
           .sort_values(["df", "termino"], ascending=[False, True], kind="stable").head(200))
    top.to_csv(config.DIR_SALIDA / "02_vocabulario_top.csv", index=False)

    memoria = {
        "rss_maximo_mb_tras_tokens": round(mem_antes, 1),
        "rss_maximo_mb_tras_indice": round(mem_indice, 1),
        "rss_maximo_mb_final": round(rss_mb(), 1),
        "indice_pkl_mb": round(INDICE_PKL.stat().st_size / 2**20, 1),
        "tfidf_npz_mb": round(TFIDF_NPZ.stat().st_size / 2**20, 1),
        "segundos": round(time.time() - t0, 1),
        "postings_totales": int(sum(len(f) for f in ind.postings.values())),
    }
    (config.DIR_SALIDA / "02_memoria.json").write_text(json.dumps(memoria, indent=2) + "\n")
    print(json.dumps({**meta, **memoria}, indent=2))
    if avisos:
        print("AVISO:", avisos)


if __name__ == "__main__":
    main()

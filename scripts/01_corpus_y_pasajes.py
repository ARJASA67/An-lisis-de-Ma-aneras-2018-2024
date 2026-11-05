"""01 · Corpus, limpieza auditada y segmentación (PRD §6.1). `make corpus`.

Salidas: data/corpus_meta.json, data/pasajes.parquet y los archivos salida/01_*.
No lee juicios ni gold. Es determinista: dos corridas producen el mismo parquet.
"""
from __future__ import annotations

import time
from collections import Counter

import pandas as pd

from mtx import adaptadores_kit, config, corpus


def resumen_descartes(df_limpio: pd.DataFrame, descartes: pd.DataFrame) -> pd.DataFrame:
    """Desglose por interlocutor de las intervenciones descartadas por `min_tokens` + 20 ejemplos."""
    totales: Counter = Counter()
    for r in df_limpio[~df_limpio["excluido"]].itertuples(index=False):
        for quien, _ in corpus.partir_canonico(r.texto_canonico):
            totales[quien or "(sin marca)"] += 1
    cuantas = descartes.assign(interlocutor=descartes["interlocutor"].replace("", "(sin marca)"))
    filas = []
    for quien, g in cuantas.groupby("interlocutor"):
        filas.append({
            "tipo": "resumen", "interlocutor": quien,
            "es_reportero": bool(g["es_reportero"].iloc[0]),
            "intervenciones": totales[quien], "descartadas": len(g),
            "porcentaje_descartado": round(100 * len(g) / totales[quien], 2), "ejemplo": ""})
    resumen = pd.DataFrame(filas).sort_values("descartadas", ascending=False, kind="stable").head(40)
    ejemplos = cuantas.sort_values(["doc_id", "intervencion_id"]).iloc[
        :: max(1, len(cuantas) // 20)].head(20)
    ej = pd.DataFrame({
        "tipo": "ejemplo", "interlocutor": ejemplos["interlocutor"],
        "es_reportero": ejemplos["es_reportero"], "intervenciones": pd.NA,
        "descartadas": ejemplos["n_palabras"], "porcentaje_descartado": pd.NA,
        "ejemplo": ejemplos["ejemplo"]})
    return pd.concat([resumen, ej], ignore_index=True)


def main() -> None:
    t0 = time.time()
    config.DIR_DATA.mkdir(exist_ok=True)
    config.DIR_SALIDA.mkdir(exist_ok=True)

    df = corpus.cargar()
    ruta_kit = adaptadores_kit.DIR_KIT / "data" / "discursos.parquet"
    corpus.escribir_json(config.CORPUS_META, corpus.huella_corpus(df, ruta_kit))
    corpus.escribir_json(config.DIR_SALIDA / "01_estadisticas_corpus.json",
                         corpus.estadisticas_corpus(df))

    limpio, inf = corpus.limpiar_ruido(df)
    inf["auditoria"].to_csv(config.DIR_SALIDA / "01_auditoria_corpus.csv", index=False)
    inf["duplicados"].to_csv(config.DIR_SALIDA / "01_duplicados.csv", index=False)
    inf["fechas"].to_csv(config.DIR_SALIDA / "01_fechas_reparadas.csv", index=False)
    inf["etiquetas"].to_csv(config.DIR_SALIDA / "01_etiquetas_interlocutor.csv", index=False)

    pasajes, descartes = corpus.segmentar_con_descartes(limpio)
    pasajes.to_parquet(config.PASAJES_PARQUET, index=False)
    resumen_d = resumen_descartes(limpio, descartes)
    resumen_d.to_csv(config.DIR_SALIDA / "01_descartes_cortos.csv", index=False)

    rep = resumen_d[(resumen_d["tipo"] == "resumen") & resumen_d["es_reportero"]]
    n_rep, d_rep = int(rep["intervenciones"].sum()), int(rep["descartadas"].sum())
    resumen = inf["resumen"] | {
        "pasajes": len(pasajes),
        "discursos_con_pasajes": int(pasajes["doc_id"].nunique()),
        "ventanas_descartadas_por_min_tokens": len(descartes),
        "intervenciones_reportero_descartadas_pct": round(100 * d_rep / n_rep, 2) if n_rep else 0.0,
        "pasajes_de_reporteros_pct": round(100 * float(pasajes["es_reportero"].mean()), 2),
        "palabras_por_pasaje_media": round(float(pasajes["n_palabras"].mean()), 1),
        "hash_pasajes": corpus.hash_pasajes(pasajes),
        "parametros": {"tam": 200, "paso": 150, "min_tokens": 40},
    }
    corpus.escribir_json(config.DIR_SALIDA / "01_limpieza.json", resumen)

    print(f"{len(df)} discursos, {resumen['discursos_excluidos']} excluidos, "
          f"{len(pasajes)} pasajes en {time.time() - t0:.0f} s")
    print(f"Reporteros: {resumen['intervenciones_reportero_descartadas_pct']} % de sus "
          f"intervenciones quedan bajo min_tokens")
    print(f"hash de pasajes: {resumen['hash_pasajes']}")


if __name__ == "__main__":
    main()

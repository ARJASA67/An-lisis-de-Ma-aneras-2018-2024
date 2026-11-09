"""05 · Evaluación de IR (PRD §6.6, D08). `make evaluar-ir`.

Entrada: juicios_relevancia.csv (exportado por `make validar`), ranking.csv, salida/04_pool.csv,
data/consultas.csv y el índice (solo para el df de las etiquetas).
Salidas: resultados_ir.csv (raíz y salida/, cifra oficial), 05_juicios_con_ventana.csv,
05_resultados_ir_ventana.csv (complementaria), 05_relevantes_por_ventana.csv, 05_ir_por_consulta.csv,
05_ir_ganador_por_consulta.csv, 05_etiquetas_consultas.csv, 05_ejecucion_ir.json,
data/mejor_modelo.json y tres figuras en reporte/figuras/.
Se niega a correr si los juicios no validan.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from mtx import adaptadores_kit, config, consultas, evaluacion, indice, pool

JUICIOS = config.RAIZ / "juicios_relevancia.csv"
RANKING = config.RAIZ / "ranking.csv"
FIGURAS = config.RAIZ / "reporte" / "figuras"
MEJOR = config.DIR_DATA / "mejor_modelo.json"
AZUL, GRIS = "#1F4E79", "#9CA3AF"
NOMBRES = {"tfidf_con_filtro": "TF-IDF con filtro", "bm25_con_filtro": "BM25 con filtro",
           "tfidf_sin_filtro": "TF-IDF sin filtro", "bm25_sin_filtro": "BM25 sin filtro"}


def figura(fig: go.Figure, nombre: str, titulo: str, eje_y: str) -> None:
    fig.update_layout(title=titulo, yaxis_title=eje_y, template="simple_white",
                      font={"family": "Arial", "size": 14}, width=900, height=520,
                      legend={"orientation": "h", "y": -0.2}, margin={"t": 70})
    fig.write_image(FIGURAS / nombre, scale=2)


def figuras(res: pd.DataFrame) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    prom = res[res["query_id"] == evaluacion.PROMEDIO].set_index("modelo")["AP"]
    f = go.Figure(go.Bar(x=[NOMBRES[m] for m in evaluacion.VARIANTES],
                         y=[prom[m] for m in evaluacion.VARIANTES], marker_color=AZUL,
                         text=[f"{prom[m]:.3f}" for m in evaluacion.VARIANTES],
                         textposition="outside"))
    figura(f, "ir_map_por_modelo.png", "MAP por variante de ranking", "MAP (AP medio, top-10)")

    r = res[res["query_id"] != evaluacion.PROMEDIO]
    orden = sorted(r["query_id"].unique(), key=lambda q: int(q[1:]))
    f = go.Figure()
    for m, color in zip(evaluacion.MODELOS_CON_FILTRO, (AZUL, GRIS), strict=True):
        g = r[r["modelo"] == m].set_index("query_id").loc[orden]
        f.add_bar(x=orden, y=g["AP"], name=NOMBRES[m], marker_color=color)
    f.update_layout(barmode="group")
    figura(f, "ir_ap_por_consulta.png", "AP por consulta, variantes con filtro", "AP (top-10)")

    f = go.Figure()
    for variante, color in (("con_filtro", AZUL), ("sin_filtro", GRIS)):
        f.add_bar(x=["TF-IDF", "BM25"], y=[prom[f"tfidf_{variante}"], prom[f"bm25_{variante}"]],
                  name="Con filtro de fecha" if variante == "con_filtro" else "Sin filtro de fecha",
                  marker_color=color,
                  text=[f"{prom[f'tfidf_{variante}']:.3f}", f"{prom[f'bm25_{variante}']:.3f}"],
                  textposition="outside")
    f.update_layout(barmode="group")
    figura(f, "ir_con_vs_sin_filtro.png", "MAP con y sin filtro de fecha", "MAP (AP medio, top-10)")


def main() -> int:
    for ruta in (JUICIOS, RANKING, pool.POOL_CSV):
        if not ruta.exists():
            print(f"Falta {ruta.relative_to(config.RAIZ)}: corre `make validar`, `make ranking` y `make pool`.")
            return 1
    pl = pool.leer_pool()
    pasajes_h = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto_sha256"])
    errores, avisos = pool.validar_juicios(pool.JUICIOS_CSV, pl, pasajes_h)
    if errores or adaptadores_kit.sha256_archivo(JUICIOS) != adaptadores_kit.sha256_archivo(
            pool.JUICIOS_CSV):
        print("Los juicios no validan o la copia de la raíz no coincide: corre `make validar`.")
        return 1
    for a in avisos:
        print("AVISO:", a)

    # 1. Cifra oficial (kit, sin renombrar columnas).
    res = evaluacion.evaluar_oficial(JUICIOS, RANKING, config.DIR_SALIDA)
    shutil.copyfile(config.DIR_SALIDA / "resultados_ir.csv", config.RAIZ / "resultados_ir.csv")
    problemas = evaluacion.verificar_resultados(res)
    for p in problemas:
        print("PROBLEMA:", p)

    # 2. Vista con ventana (complementaria).
    juicios = pd.read_csv(JUICIOS, dtype={"passage_id": str, "relevante": int})
    j = evaluacion.juicios_con_ventana(juicios, pl)
    j.to_csv(config.DIR_SALIDA / "05_juicios_con_ventana.csv", index=False, lineterminator="\n")
    with tempfile.TemporaryDirectory() as tmp:
        base = j[["query_id", "doc_id", "passage_id", "relevante_ventana"]].rename(
            columns={"relevante_ventana": "relevante"})
        ruta = Path(tmp) / "juicios_ventana.csv"
        base.to_csv(ruta, index=False, lineterminator="\n")
        vent = evaluacion.evaluar_oficial(ruta, RANKING, Path(tmp) / "out")
    vent.to_csv(config.DIR_SALIDA / "05_resultados_ir_ventana.csv", index=False, lineterminator="\n")
    evaluacion.relevantes_por_ventana(j).to_csv(
        config.DIR_SALIDA / "05_relevantes_por_ventana.csv", index=False, lineterminator="\n")

    # 3. Tablas por consulta y ganador con etiquetas.
    cons = consultas.cargar()
    ind = indice.cargar(config.DIR_DATA / "indice.pkl")
    etiquetas = evaluacion.etiquetas_consultas(cons, ind.df, ind.N, evaluacion.cargar_sinonimos())
    etiquetas.to_csv(config.DIR_SALIDA / "05_etiquetas_consultas.csv", index=False, lineterminator="\n")
    evaluacion.tabla_ancha(res).to_csv(config.DIR_SALIDA / "05_ir_por_consulta.csv", index=False,
                                       lineterminator="\n")
    gan = evaluacion.ganador_por_consulta(res, etiquetas)
    gan.to_csv(config.DIR_SALIDA / "05_ir_ganador_por_consulta.csv", index=False, lineterminator="\n")

    # 4. Mejor modelo (D08).
    mejor = evaluacion.elegir_mejor_modelo(res)
    mejor["ranking_sha256"] = adaptadores_kit.sha256_archivo(RANKING)
    mejor["juicios_sha256"] = adaptadores_kit.sha256_archivo(JUICIOS)
    if MEJOR.exists():
        previo = json.loads(MEJOR.read_text(encoding="utf-8"))
        if previo.get("modelo") != mejor["modelo"]:
            print(f"ATENCIÓN: el ganador cambia de {previo.get('modelo')} a {mejor['modelo']}; "
                  "si ya se abrió IE exige revisión explícita (PRD §11.1).")
    MEJOR.write_text(json.dumps(mejor, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    alerta = mejor["map"] < evaluacion.UMBRAL_MAP_ALERTA
    if alerta:
        print(f"ALERTA: MAP del ganador {mejor['map']:.4f} < {evaluacion.UMBRAL_MAP_ALERTA}: "
              "revisar tokens de consulta, filtro de fechas, orden de IDs y formato de ranking.csv.")

    # 5. Figuras y registro de ejecución.
    figuras(res)
    (config.DIR_SALIDA / "05_ejecucion_ir.json").write_text(json.dumps({
        "comando": "python kit/evaluar.py ir juicios_relevancia.csv ranking.csv",
        "ejecutado": datetime.now().isoformat(timespec="seconds"),
        "juicios_sha256": mejor["juicios_sha256"], "ranking_sha256": mejor["ranking_sha256"],
        "pool_sha256": adaptadores_kit.sha256_archivo(pool.POOL_CSV),
        "evaluar_py_sha256": adaptadores_kit.sha256_archivo(adaptadores_kit.DIR_KIT / "evaluar.py"),
        "resultados_ir_sha256": adaptadores_kit.sha256_archivo(config.RAIZ / "resultados_ir.csv"),
        "problemas": problemas, "alerta_map": alerta,
        "mediana_longitud_tokens": etiquetas.attrs.get("mediana_longitud"),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("\nMAP oficial:")
    print(res[res["query_id"] == evaluacion.PROMEDIO][["modelo", "P@5", "P@10", "AP"]].to_string(
        index=False))
    print("\nMAP complementaria (con ventana):")
    print(vent[vent["query_id"] == evaluacion.PROMEDIO][["modelo", "P@5", "P@10", "AP"]].to_string(
        index=False))
    print(f"\nMejor modelo (D08): {mejor['modelo']} (MAP {mejor['map']:.4f}; "
          f"alternativa {mejor['alternativa']} {mejor['map_alternativa']:.4f}).")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

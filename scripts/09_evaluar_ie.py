"""09 · Evaluación de IE y análisis de errores (PRD §6.12, D09, D15, P04, U19). `make evaluar-ie`.

Entrada: gold_entidades.csv (raíz, exportado al cerrar el gold), entidades.csv (raíz),
anotaciones/muestra_gold.csv y anotaciones/cierre_gold.json, salida/entidades_enriquecidas.csv
(para la fuente de cada predicción), data/pasajes.parquet y config/gazetteer_extendido.csv (obras).
Salidas: resultados_ie.csv (raíz y salida/, salida literal del kit), salida/09_ie_detalle.csv,
salida/09_evaluacion_20_ids.csv, salida/09_analisis_errores.csv, salida/09_resumen_errores.csv,
salida/09_ejecucion_ie.json, la entrada `evaluar_ie` de salida/manifiesto_ejecucion.json y de
salida/tiempos_ejecucion.json, y dos figuras en reporte/figuras/.

No hay conjunto de selección: el NER se eligió por criterio técnico (data/modelo_ner.json), así que
no se genera 09_comparacion_ner.csv. El gold no elige ni ajusta nada; este script solo lo lee.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go

from mtx import adaptadores_kit, config, evaluacion

GOLD = config.RAIZ / "gold_entidades.csv"
ENTIDADES = config.RAIZ / "entidades.csv"
MUESTRA = config.DIR_ANOTACIONES / "muestra_gold.csv"
CIERRE = config.DIR_ANOTACIONES / "cierre_gold.json"
GOLD_ANOT = config.DIR_ANOTACIONES / "gold_entidades.csv"
ENRIQUECIDAS = config.DIR_SALIDA / "entidades_enriquecidas.csv"
GAZ_EXT = config.DIR_CONFIG / "gazetteer_extendido.csv"
MODELO_NER = config.DIR_DATA / "modelo_ner.json"
FIGURAS = config.RAIZ / "reporte" / "figuras"
MANIFIESTO = config.DIR_SALIDA / "manifiesto_ejecucion.json"
TIEMPOS = config.DIR_SALIDA / "tiempos_ejecucion.json"
COLORES = {"regla": "#1F4E79", "modelo": "#C2410C", "combinado": "#6B7280"}
NOMBRES = {"regla": "Reglas + gazetteer", "modelo": "NER (modelo)", "combinado": "Combinado"}
CSV = {"index": False, "lineterminator": "\n"}


def _commit() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.RAIZ, capture_output=True,
                       text=True, check=False)
    return r.stdout.strip()


def _actualizar_json(ruta, clave: str, valor: dict) -> None:
    datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    datos[clave] = valor
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
                    newline="\n")


def _figura(fig: go.Figure, nombre: str, titulo: str, **ejes) -> None:
    fig.update_layout(title=titulo, template="simple_white", font={"family": "Arial", "size": 14},
                      width=900, height=520, legend={"orientation": "h", "y": -0.18},
                      margin={"t": 70}, **ejes)
    fig.write_image(FIGURAS / nombre, scale=2)


def figuras(detalle: pd.DataFrame, resumen: pd.DataFrame) -> None:
    FIGURAS.mkdir(parents=True, exist_ok=True)
    tipos = [*evaluacion.TIPOS_IE, "TODOS"]
    f = go.Figure()
    for m in evaluacion.METODOS_IE:
        d = detalle[detalle["metodo"] == m].set_index("tipo").loc[tipos]
        y = [v if e == "ok" else None for v, e in zip(d["f1"], d["estado"], strict=True)]
        f.add_bar(x=tipos, y=y, name=NOMBRES[m], marker_color=COLORES[m],
                  text=[f"{v:.2f}" if v is not None else ("s/c" if e == "sin_cobertura" else "n/a")
                        for v, e in zip(y, d["estado"], strict=True)],
                  textposition="outside")
    f.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    _figura(f, "ie_f1_por_tipo_metodo.png", "F1 por tipo de entidad y método (gold, 20 pasajes)",
            yaxis={"title": "F1 (coincidencia exacta)", "range": [0, 1.1]},
            xaxis={"title": "s/c: el NER no predice FECHA ni MONTO"})

    base = resumen[resumen["subcategoria"].fillna("") == ""]  # sin doble conteo de subcasos
    c = base.groupby("categoria")["n"].sum().sort_values(ascending=True)
    f = go.Figure(go.Bar(x=c.values, y=c.index, orientation="h", marker_color=COLORES["regla"],
                         text=[str(v) for v in c.values], textposition="outside"))
    _figura(f, "ie_errores_por_categoria.png",
            "Errores de la extracción combinada por categoría (no excluyentes)",
            xaxis={"title": "Número de errores"}, yaxis={"title": ""}, showlegend=False)


def main() -> int:
    t0 = time.perf_counter()
    for ruta in (GOLD, ENTIDADES, MUESTRA, CIERRE, ENRIQUECIDAS, MODELO_NER):
        if not ruta.exists():
            print(f"Falta {ruta.relative_to(config.RAIZ)}: no se evalúa con una salida provisional.")
            return 1
    etiqueta = subprocess.run(["git", "tag", "--list", "reglas-congeladas"], cwd=config.RAIZ,
                              capture_output=True, text=True, check=False).stdout.strip()
    if not etiqueta:
        print("Falta la etiqueta reglas-congeladas (D15).")
        return 1
    if adaptadores_kit.sha256_archivo(GOLD) != adaptadores_kit.sha256_archivo(GOLD_ANOT):
        print("gold_entidades.csv de la raíz no coincide con anotaciones/: vuelve a exportar el gold.")
        return 1
    cierre = json.loads(CIERRE.read_text(encoding="utf-8"))
    if cierre.get("sha256_gold") != adaptadores_kit.sha256_archivo(GOLD_ANOT):
        print("AVISO: el hash del gold difiere del registrado en cierre_gold.json.")
    problemas_kit = adaptadores_kit.verificar_hashes()
    if problemas_kit:
        print("El kit no coincide con sus hashes:", problemas_kit)
        return 1

    # 1. Cifra oficial (kit, salida literal).
    res = evaluacion.evaluar_ie_oficial(GOLD, ENTIDADES, config.DIR_SALIDA)
    oficial = config.DIR_SALIDA / "resultados_ie.csv"
    # El kit escribe con el fin de línea del sistema; se normaliza a LF (eol=lf del repo) para
    # que el hash registrado coincida con un clon limpio. El contenido no cambia.
    oficial.write_bytes(oficial.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copyfile(oficial, config.RAIZ / "resultados_ie.csv")
    problemas = evaluacion.verificar_resultados_ie(res)
    alertas = evaluacion.alertas_ie(res)

    # 2. Detalle y complementaria sobre los 20 IDs del manifiesto (P04).
    gold = pd.read_csv(GOLD, dtype={"passage_id": str})
    pred = pd.read_csv(ENTIDADES, dtype={"passage_id": str, "doc_id": str})
    muestra = pd.read_csv(MUESTRA, dtype={"passage_id": str})
    ids20 = list(muestra["passage_id"])
    detalle = evaluacion.evaluar_ie(gold, pred)
    detalle.to_csv(config.DIR_SALIDA / "09_ie_detalle.csv", **CSV)
    comp = evaluacion.evaluar_ie(gold, pred, ids20)
    comp.to_csv(config.DIR_SALIDA / "09_evaluacion_20_ids.csv", **CSV)
    n_kit, n_comp = detalle.attrs["pasajes_evaluados"], comp.attrs["pasajes_evaluados"]
    vacios = sorted(set(ids20) - set(gold["passage_id"]))

    # Coherencia: el detalle propio reproduce TP y predichas del kit.
    k = res.set_index(["metodo", "tipo"])
    for f in detalle[detalle["tipo"].isin(set(res["tipo"]))].itertuples(index=False):
        fk = k.loc[(f.metodo, f.tipo)]
        if (int(fk["tp"]), int(fk["predichas"]), int(fk["gold"])) != (f.tp, f.predichas, f.soporte):
            problemas.append(f"Detalle {f.metodo} × {f.tipo} no reproduce al kit")

    # 3. Análisis de errores (predicción combinada, con la fuente de cada fila).
    enr = pd.read_csv(ENRIQUECIDAS, dtype={"passage_id": str})
    pred_f = enr[["passage_id", "tipo", "texto", "inicio", "fin", "metodo", "fuentes"]]
    pas = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto", "inicio_cuerpo"],
                          filters=[("passage_id", "in", ids20)])
    gaz = pd.read_csv(GAZ_EXT, dtype=str).fillna("")
    obras = set()
    for f in gaz[gaz["etiqueta"] == "LOC"].itertuples(index=False):
        obras |= {n.strip() for n in [f.nombre, *f.variantes.split("|"), *f.siglas.split("|")]
                  if n.strip()}
    err = evaluacion.analizar_errores(gold, pred_f, pas, obras)
    err.to_csv(config.DIR_SALIDA / "09_analisis_errores.csv", **CSV)
    resumen = evaluacion.resumen_errores(err)
    resumen.to_csv(config.DIR_SALIDA / "09_resumen_errores.csv", **CSV)

    # 4. Figuras y registro.
    figuras(detalle, resumen)
    modelo = json.loads(MODELO_NER.read_text(encoding="utf-8"))
    sha = adaptadores_kit.sha256_archivo
    registro = {
        "comando": "python kit/evaluar.py ie gold_entidades.csv entidades.csv",
        "ejecutado": datetime.now().isoformat(timespec="seconds"),
        "commit": _commit(),
        "gold_sha256": sha(GOLD), "entidades_sha256": sha(ENTIDADES),
        "evaluar_py_sha256": sha(adaptadores_kit.DIR_KIT / "evaluar.py"),
        "resultados_ie_sha256": sha(config.RAIZ / "resultados_ie.csv"),
        "gazetteer_extendido_sha256": sha(GAZ_EXT),
        "gazetteer_loc_sha256": sha(config.DIR_CONFIG / "gazetteer_loc.csv"),
        "reglas_py_sha256": sha(config.RAIZ / "src" / "mtx" / "reglas.py"),
        "modelo_ner": modelo["modelo"], "revision_ner": modelo["revision"],
        "criterio_ner": modelo["criterio"],
        "pasajes_evaluados_kit": n_kit, "pasajes_complementaria": n_comp,
        "pasajes_gold_sin_entidades": vacios, "entidades_gold": len(gold),
        "errores_clasificados": len(err), "problemas": problemas, "alertas": alertas,
    }
    (config.DIR_SALIDA / "09_ejecucion_ie.json").write_text(
        json.dumps(registro, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    _actualizar_json(MANIFIESTO, "evaluar_ie", registro)
    _actualizar_json(TIEMPOS, "evaluar_ie", {"segundos": round(time.perf_counter() - t0, 2),
                                             "ejecutado": registro["ejecutado"]})

    print("\nResultados oficiales (kit):")
    print(res.to_string(index=False))
    print(f"\nPasajes evaluados por el kit: {n_kit}; complementaria: {n_comp}; "
          f"pasajes gold sin entidades: {len(vacios)}.")
    print(f"Errores clasificados: {len(err)} filas.")
    print(resumen.groupby(["categoria", resumen["subcategoria"].fillna("")])["n"].sum().to_string())
    for a in alertas:
        print("ALERTA:", a)
    for p in problemas:
        print("PROBLEMA:", p)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

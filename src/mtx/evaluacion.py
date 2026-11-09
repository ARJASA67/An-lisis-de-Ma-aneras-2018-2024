"""Evaluación de IR (PRD §6.6, D08): cifra oficial con el kit, vista con ventana, etiquetas y ganador.

La cifra oficial sale de `kit/evaluar.py ir` sobre `juicios_relevancia.csv` y `ranking.csv`, sin
renombrar columnas. La vista con ventana es complementaria: cambia el criterio y el denominador de
AP y nunca se mezcla con la oficial. Las etiquetas por consulta las calcula el código, no se
escriben a mano. No lee ni escribe juicios: solo los consume.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd
import yaml

from . import adaptadores_kit, config, preproceso

MODELOS_CON_FILTRO = ("tfidf_con_filtro", "bm25_con_filtro")
VARIANTES = ("tfidf_con_filtro", "bm25_con_filtro", "tfidf_sin_filtro", "bm25_sin_filtro")
PROMEDIO = "PROMEDIO (MAP = AP)"
UMBRAL_DF_ALTO = 0.01
"""Un término tiene df alto si aparece en al menos 1 % de los pasajes."""
UMBRAL_MAP_ALERTA = 0.15
"""Alerta de PRD §13.2: un MAP oficial del ganador menor a esto sugiere un bug, no un resultado."""


# --------------------------------------------------------------------------- cifra oficial


def evaluar_oficial(juicios: Path, ranking: Path, destino: Path) -> pd.DataFrame:
    """Corre `kit/evaluar.py ir` (subprocess, `cwd` en `destino`) y devuelve `resultados_ir.csv`."""
    ruta = adaptadores_kit.ejecutar_evaluador("ir", juicios, ranking, destino)
    return pd.read_csv(ruta)


def verificar_resultados(res: pd.DataFrame, n_consultas: int = 10) -> list[str]:
    """Criterios de aceptación de PRD §6.6: 40 filas más 4 promedios y `no_juzgados == 0`."""
    problemas = []
    por_consulta = res[res["query_id"] != PROMEDIO]
    promedios = res[res["query_id"] == PROMEDIO]
    if len(por_consulta) != n_consultas * len(VARIANTES):
        problemas.append(f"{len(por_consulta)} filas por consulta (esperadas "
                         f"{n_consultas * len(VARIANTES)})")
    if len(promedios) != len(VARIANTES):
        problemas.append(f"{len(promedios)} filas de promedio (esperadas {len(VARIANTES)})")
    sin_juzgar = por_consulta[por_consulta["no_juzgados"] > 0]
    for f in sin_juzgar.itertuples(index=False):
        problemas.append(f"{f.query_id} {f.modelo}: {int(f.no_juzgados)} no juzgados (el pool no cubre el top-10)")
    return problemas


# --------------------------------------------------------------------------- vista con ventana


def juicios_con_ventana(juicios: pd.DataFrame, pool_df: pd.DataFrame) -> pd.DataFrame:
    """`relevante_ventana = relevante AND en_ventana`; fecha desconocida no cumple la ventana."""
    en = pool_df[["query_id", "passage_id", "en_ventana", "fecha"]].copy()
    en["en_ventana"] = en["en_ventana"].astype(str).str.lower() == "true"
    en["fecha_desconocida"] = en["fecha"].fillna("").astype(str).str.strip() == ""
    j = juicios.merge(en[["query_id", "passage_id", "en_ventana", "fecha_desconocida"]],
                      on=["query_id", "passage_id"], how="left", validate="one_to_one")
    if j["en_ventana"].isna().any():
        raise ValueError("Hay juicios fuera del pool: no se puede construir la vista con ventana")
    j["relevante_ventana"] = ((j["relevante"].astype(int) == 1) & j["en_ventana"]).astype(int)
    return j


def relevantes_por_ventana(j: pd.DataFrame) -> pd.DataFrame:
    """Por consulta: relevantes temáticos dentro, fuera de ventana y con fecha desconocida."""
    r = j[j["relevante"].astype(int) == 1]
    filas = []
    for q in dict.fromkeys(j["query_id"]):
        g = r[r["query_id"] == q]
        filas.append({"query_id": q, "relevantes_tematicos": len(g),
                      "dentro_de_ventana": int(g["en_ventana"].sum()),
                      "fuera_de_ventana": int((~g["en_ventana"] & ~g["fecha_desconocida"]).sum()),
                      "fecha_desconocida": int(g["fecha_desconocida"].sum())})
    return pd.DataFrame(filas)


# --------------------------------------------------------------------------- tablas


def tabla_ancha(res: pd.DataFrame) -> pd.DataFrame:
    """Consulta × variante en formato ancho para P@5, P@10, AP, soporte, juzgados y no juzgados."""
    r = res[res["query_id"] != PROMEDIO].copy()
    r["juzgados"] = 10 - r["no_juzgados"]
    ancho = r.pivot(index="query_id", columns="modelo",
                    values=["P@5", "P@10", "AP", "relevantes_en_pool", "juzgados", "no_juzgados"])
    ancho.columns = [f"{m}__{v}" for m, v in ancho.columns]
    ancho = ancho.reset_index()
    orden = sorted(ancho["query_id"], key=lambda q: int(q[1:]))
    return ancho.set_index("query_id").loc[orden].reset_index()


def ganador_por_consulta(res: pd.DataFrame, etiquetas: pd.DataFrame) -> pd.DataFrame:
    """Ganador por AP entre las variantes con filtro, diferencia (BM25 − TF-IDF) y etiquetas."""
    ap = res[res["query_id"] != PROMEDIO].pivot(index="query_id", columns="modelo", values="AP")
    filas = []
    for q in sorted(ap.index, key=lambda x: int(x[1:])):
        t, b = float(ap.loc[q, "tfidf_con_filtro"]), float(ap.loc[q, "bm25_con_filtro"])
        filas.append({"query_id": q, "ap_tfidf_con_filtro": t, "ap_bm25_con_filtro": b,
                      "diferencia_bm25_menos_tfidf": round(b - t, 4),
                      "ganador": "empate" if t == b else ("bm25_con_filtro" if b > t
                                                          else "tfidf_con_filtro")})
    return pd.DataFrame(filas).merge(etiquetas, on="query_id", how="left")


# --------------------------------------------------------------------------- etiquetas


def cargar_sinonimos(ruta: Path | None = None) -> dict[str, list[str]]:
    ruta = ruta or config.DIR_CONFIG / "sinonimos_consultas.yaml"
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))["grupos"]


def _plano(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower())
                   if unicodedata.category(c) != "Mn")


def tiene_sigla_o_nombre_propio(consulta: str) -> bool:
    """Sigla (2+ letras mayúsculas) o palabra con mayúscula inicial que no abre la consulta."""
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü][\w-]*", consulta)
    if any(len(p) >= 2 and p.isupper() or re.fullmatch(r"[A-ZÁÉÍÓÚÑÜ]{2,}-?\d*", p) for p in palabras):
        return True
    return any(p[0].isupper() for p in palabras[1:])


def etiquetas_consultas(cons: pd.DataFrame, df: dict[str, int], n_pasajes: int,
                        sinonimos: dict[str, list[str]]) -> pd.DataFrame:
    """Etiquetas calculadas por consulta (PRD §6.6 punto 3)."""
    filas = []
    for c in cons.itertuples(index=False):
        tokens = preproceso.tokenizar(c.consulta)
        altos = [t for t in tokens if df.get(t, 0) / n_pasajes >= UMBRAL_DF_ALTO]
        plano = _plano(c.consulta)
        grupos = [g for g, terminos in sinonimos.items() if any(_plano(t) in plano for t in terminos)]
        filas.append({"query_id": c.query_id, "longitud_tokens": len(tokens),
                      "terminos_df_alto": len(altos), "terminos_df_alto_lista": "|".join(altos),
                      "sigla_o_nombre_propio": tiene_sigla_o_nombre_propio(c.consulta),
                      "sinonimos_conocidos": "|".join(grupos)})
    e = pd.DataFrame(filas)
    mediana = float(e["longitud_tokens"].median())
    e.insert(2, "longitud", ["larga" if n > mediana else "corta" for n in e["longitud_tokens"]])
    e.attrs["mediana_longitud"] = mediana
    return e


# --------------------------------------------------------------------------- mejor modelo (D08)


def elegir_mejor_modelo(res: pd.DataFrame) -> dict:
    """Mayor MAP oficial entre las dos variantes con filtro; empate exacto a BM25 (D08)."""
    prom = res[res["query_id"] == PROMEDIO].set_index("modelo")["AP"]
    t, b = float(prom["tfidf_con_filtro"]), float(prom["bm25_con_filtro"])
    if b >= t:
        elegido, map_e, alt, map_a = "bm25_con_filtro", b, "tfidf_con_filtro", t
    else:
        elegido, map_e, alt, map_a = "tfidf_con_filtro", t, "bm25_con_filtro", b
    out = {"modelo": elegido, "map": map_e, "alternativa": alt, "map_alternativa": map_a,
           "empate_exacto": t == b}
    if abs(b - t) < 0.01:
        out["diferencia_menor_0.01"] = True
    return out

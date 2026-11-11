"""Evaluación de IR (PRD §6.6, D08) e IE (PRD §6.12): cifras oficiales con el kit y complementos.

La parte IE (al final del módulo) reproduce la semántica de `kit/evaluar.py ie` para el detalle
con FP/FN y estados, la complementaria de 20 IDs (P04) y el análisis de errores por categoría.

La cifra oficial sale de `kit/evaluar.py ir` sobre `juicios_relevancia.csv` y `ranking.csv`, sin
renombrar columnas. La vista con ventana es complementaria: cambia el criterio y el denominador de
AP y nunca se mezcla con la oficial. Las etiquetas por consulta las calcula el código, no se
escriben a mano. No lee ni escribe juicios: solo los consume.
"""
from __future__ import annotations

import re
import unicodedata
from itertools import pairwise
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


# =========================================================================== IE (PRD §6.12)

METODOS_IE = ("regla", "modelo", "combinado")
TIPOS_IE = ("PER", "ORG", "LOC", "FECHA", "MONTO")
TIPOS_SIN_MODELO = frozenset({"FECHA", "MONTO"})
"""El NER principal solo predice PER, ORG y LOC: `modelo × FECHA|MONTO` no tiene cobertura."""
UMBRAL_F1_ALERTA = 0.30
"""Alerta U19: F1 combinado TODOS menor a esto obliga a buscar un bug antes de reportar."""
SOPORTE_ALERTA_PERFECTO = 5
"""Alerta U19: F1 = 1.0 en un tipo con más de este soporte sugiere gold copiado del sistema."""
COLUMNAS_ERRORES = ["passage_id", "tipo", "texto_gold", "texto_pred", "inicio", "fin", "metodo",
                    "categoria", "fuente", "contexto"]
_RE_SIGLA = re.compile(r"[A-ZÁÉÍÓÚÑÜ]{2,7}")
VENTANA_CONTEXTO = 60


def evaluar_ie_oficial(gold: Path, entidades: Path, destino: Path) -> pd.DataFrame:
    """Corre `kit/evaluar.py ie` (subprocess, `cwd` en `destino`) y devuelve `resultados_ie.csv`."""
    ruta = adaptadores_kit.ejecutar_evaluador("ie", gold, entidades, destino)
    return pd.read_csv(ruta)


def _claves(df: pd.DataFrame) -> set[tuple[str, str, int, int]]:
    return {(str(p), t, int(i), int(f)) for p, t, i, f in
            zip(df["passage_id"], df["tipo"], df["inicio"], df["fin"], strict=True)}


def _subconjunto(pred: pd.DataFrame, metodo: str) -> pd.DataFrame:
    """Misma semántica que el kit: `regla` = regla + ambos; `modelo` = modelo + ambos."""
    return pred if metodo == "combinado" else pred[pred["metodo"].isin([metodo, "ambos"])]


def evaluar_ie(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: list[str] | None = None
               ) -> pd.DataFrame:
    """P/R/F1, TP/FP/FN y soporte por `(metodo, tipo)` sobre un conjunto de pasajes.

    Sin `pasajes` reproduce la base del kit (solo los pasajes con filas en el gold). Con la lista
    de los 20 IDs del manifiesto, una predicción en un pasaje cerrado sin entidades cuenta como FP
    (P04). Las predicciones repetidas entre consultas cuentan una vez, como en el kit. `estado`:
    `ok`, `no_aplicable` (sin soporte gold) o `sin_cobertura` (el método no predice ese tipo); en
    esos dos casos P/R/F1 quedan vacíos en lugar de un 0.0 disfrazado.
    """
    base = set(map(str, pasajes)) if pasajes is not None else set(gold["passage_id"].astype(str))
    pred = pred[pred["passage_id"].astype(str).isin(base)]
    gold = gold[gold["passage_id"].astype(str).isin(base)]
    g_all = _claves(gold)
    filas = []
    for metodo in METODOS_IE:
        p_all = _claves(_subconjunto(pred, metodo))
        for tipo in (*TIPOS_IE, "TODOS"):
            gt = g_all if tipo == "TODOS" else {x for x in g_all if x[1] == tipo}
            pt = p_all if tipo == "TODOS" else {x for x in p_all if x[1] == tipo}
            tp = len(gt & pt)
            fp, fn = len(pt) - tp, len(gt) - tp
            if metodo == "modelo" and tipo in TIPOS_SIN_MODELO:
                estado = "sin_cobertura"
            elif not gt:
                estado = "no_aplicable"
            else:
                estado = "ok"
            if estado == "ok":
                p = tp / len(pt) if pt else 0.0
                r = tp / len(gt)
                f = 2 * p * r / (p + r) if p + r else 0.0
                p, r, f = round(p, 4), round(r, 4), round(f, 4)
            else:
                p = r = f = None
            filas.append({"metodo": metodo, "tipo": tipo, "precision": p, "recall": r, "f1": f,
                          "tp": tp, "fp": fp, "fn": fn, "predichas": len(pt), "soporte": len(gt),
                          "estado": estado})
    out = pd.DataFrame(filas)
    out.attrs["pasajes_evaluados"] = len(base)
    return out


def verificar_resultados_ie(res: pd.DataFrame) -> list[str]:
    """Aceptación de `resultados_ie.csv`: las tres variantes, cada una con su fila `TODOS`."""
    return [f"{m}: falta la fila TODOS" for m in METODOS_IE
            if "TODOS" not in set(res.loc[res["metodo"] == m, "tipo"])]


def alertas_ie(res: pd.DataFrame) -> list[str]:
    """Umbrales U19 sobre la salida del kit (son alertas, no metas)."""
    alertas = []
    todos = res[(res["metodo"] == "combinado") & (res["tipo"] == "TODOS")]
    if not todos.empty and float(todos["f1"].iloc[0]) < UMBRAL_F1_ALERTA:
        alertas.append(f"F1 combinado TODOS = {float(todos['f1'].iloc[0]):.4f} < "
                       f"{UMBRAL_F1_ALERTA}: revisar offsets, mapa de etiquetas y fusión")
    perfectos = res[(res["f1"] == 1.0) & (res["gold"] > SOPORTE_ALERTA_PERFECTO)]
    for f in perfectos.itertuples(index=False):
        alertas.append(f"F1 = 1.0 en {f.metodo} × {f.tipo} con {int(f.gold)} entidades gold: "
                       "verificar que el gold no se copió del sistema")
    return alertas


# --------------------------------------------------------------------------- análisis de errores


def fuente_corta(fuentes: str) -> str:
    """`gazetteer_loc|modelo` → `gazetteer|modelo`; `regex_monto` → `regex`."""
    partes = [] if pd.isna(fuentes) else str(fuentes).split("|")
    return "|".join(dict.fromkeys(p.split("_")[0] for p in partes if p))


def _contexto(texto: str, ini: int, fin: int) -> str:
    a, b = max(0, ini - VENTANA_CONTEXTO), min(len(texto), fin + VENTANA_CONTEXTO)
    return " ".join(f"{texto[a:ini]}[[{texto[ini:fin]}]]{texto[fin:b]}".split())


def _solapa(a: dict, b: dict) -> bool:
    return a["inicio"] < b["fin"] and b["inicio"] < a["fin"]


def _clave(x: dict) -> tuple[str, int, int]:
    return x["tipo"], x["inicio"], x["fin"]


def _orden_pid(pid: str) -> tuple:
    return tuple(int(n) if n.isdigit() else n for n in pid.split("_"))


def analizar_errores(gold: pd.DataFrame, pred: pd.DataFrame, pasajes: pd.DataFrame,
                     obras: set[str] | frozenset[str] = frozenset()) -> pd.DataFrame:
    """Clasifica cada FN y FP de la predicción combinada en los pasajes del gold (PRD §6.12).

    `pred` trae `passage_id, tipo, texto, inicio, fin, metodo` y opcionalmente `fuentes`
    (de `entidades_enriquecidas.csv`); se deduplica por `(passage_id, tipo, inicio, fin)`.
    `pasajes`: `passage_id, texto, inicio_cuerpo`. `obras`: nombres de obras del gazetteer (LOC).

    Una fila por error y categoría (las categorías no son excluyentes; las subcategorías van como
    `frontera:entidad_partida`). Filas del lado gold (FN): `texto_gold` lleno y, si hay
    predicciones que solapan, `texto_pred` con ellas unidas por ` | `; `inicio`/`fin` del gold.
    Filas del lado predicción (FP que ningún FN explica): `inicio`/`fin` de la predicción y
    `texto_gold` vacío (`espuria`) o con el gold ya acertado por otra predicción (`frontera`).
    """
    obras_n = {o.casefold() for o in obras}
    textos = dict(zip(pasajes["passage_id"].astype(str), pasajes["texto"], strict=True))
    cuerpos = dict(zip(pasajes["passage_id"].astype(str), pasajes["inicio_cuerpo"], strict=True))
    if "fuentes" not in pred.columns:
        pred = pred.assign(fuentes="")
    ids = set(gold["passage_id"].astype(str))
    pred = (pred[pred["passage_id"].astype(str).isin(ids)]
            .drop_duplicates(["passage_id", "tipo", "inicio", "fin"]))
    filas: list[dict] = []

    def fila(pid, tipo, tg, tp, ini, fin, metodo, cat, fuente):
        filas.append({"passage_id": pid, "tipo": tipo, "texto_gold": tg, "texto_pred": tp,
                      "inicio": ini, "fin": fin, "metodo": metodo, "categoria": cat,
                      "fuente": fuente, "contexto": _contexto(textos[pid], ini, fin)})

    for pid in sorted(ids, key=_orden_pid):
        gs = gold[gold["passage_id"].astype(str) == pid].to_dict("records")
        ps = pred[pred["passage_id"].astype(str) == pid].to_dict("records")
        for x in gs + ps:
            x["inicio"], x["fin"] = int(x["inicio"]), int(x["fin"])
        kg, kp = {_clave(g) for g in gs}, {_clave(p) for p in ps}
        cuerpo = int(cuerpos[pid])

        for g in gs:
            if _clave(g) in kp:
                continue
            sol = [p for p in ps if _solapa(g, p)]
            mismo = [p for p in sol if p["tipo"] == g["tipo"]]
            otro = [p for p in sol if p["tipo"] != g["tipo"]]
            cats = []
            if mismo:
                cats.append("frontera")
                dentro = sorted((p for p in mismo if p["inicio"] >= g["inicio"]
                                 and p["fin"] <= g["fin"]), key=lambda p: (p["inicio"], p["fin"]))
                if any(b["inicio"] >= a["fin"] for a, b in pairwise(dentro)):
                    # dos o más piezas disjuntas dentro del gold; las anidadas no cuentan
                    cats.append("frontera:entidad_partida")
                if g["tipo"] == "MONTO" and any(p["inicio"] == g["inicio"] and p["fin"] < g["fin"]
                                                for p in mismo):
                    cats.append("frontera:monto_sin_unidad")
            mismo_span = [p for p in otro if (p["inicio"], p["fin"]) == (g["inicio"], g["fin"])]
            if mismo_span:
                cats.append("tipo")
                tipos = {g["tipo"], *(p["tipo"] for p in mismo_span)}
                if tipos == {"LOC", "ORG"} and g["texto"].casefold() in obras_n:
                    cats.append("tipo:obra_LOC_vs_ORG")
            elif otro and not mismo:
                cats.append("solape_otro_tipo")
            if _RE_SIGLA.fullmatch(g["texto"]) and not any(
                    p["inicio"] <= g["inicio"] and p["fin"] >= g["fin"] for p in ps):
                cats.append("sigla_no_reconocida")
            if not sol:
                cats.append("omision")
            if g["fin"] <= cuerpo:
                cats.append("en_marca")
            tp_txt = " | ".join(f"{p['texto']} ({p['tipo']})" for p in sol)
            metodo = "|".join(dict.fromkeys(p["metodo"] for p in sol))
            fuente = "|".join(dict.fromkeys(fuente_corta(p["fuentes"]) for p in sol))
            for c in cats:
                fila(pid, g["tipo"], g["texto"], tp_txt, g["inicio"], g["fin"], metodo, c, fuente)

        for p in ps:
            if _clave(p) in kg:
                continue
            sol = [g for g in gs if _solapa(g, p)]
            if any(_clave(g) not in kp for g in sol):
                continue  # el error ya quedó registrado del lado gold
            mismo_span = [g for g in sol if (g["inicio"], g["fin"]) == (p["inicio"], p["fin"])]
            if mismo_span:
                cats = ["tipo"]
                tipos = {p["tipo"], *(g["tipo"] for g in mismo_span)}
                if tipos == {"LOC", "ORG"} and p["texto"].casefold() in obras_n:
                    cats.append("tipo:obra_LOC_vs_ORG")
                tg = " | ".join(f"{g['texto']} ({g['tipo']})" for g in sol)
            elif sol:
                cats = ["frontera" if any(g["tipo"] == p["tipo"] for g in sol)
                        else "solape_otro_tipo"]
                tg = " | ".join(f"{g['texto']} ({g['tipo']})" for g in sol)
            else:
                cats, tg = ["espuria"], ""
            if p["fin"] <= cuerpo:
                cats.append("en_marca")
            for c in cats:
                fila(pid, p["tipo"], tg, p["texto"], p["inicio"], p["fin"], p["metodo"], c,
                     fuente_corta(p["fuentes"]))
    return pd.DataFrame(filas, columns=COLUMNAS_ERRORES)


def resumen_errores(err: pd.DataFrame) -> pd.DataFrame:
    """Conteo por categoría, subcategoría, tipo y método (y fuente, solo para `espuria`)."""
    columnas = ["categoria", "subcategoria", "tipo", "metodo", "fuente", "n"]
    if err.empty:
        return pd.DataFrame(columns=columnas)
    e = err.copy()
    partes = e["categoria"].str.split(":", n=1)
    e["categoria"] = partes.str[0]
    e["subcategoria"] = partes.str[1].astype(object).fillna("")
    e["fuente"] = e["fuente"].where(e["categoria"] == "espuria", "")
    e["metodo"] = e["metodo"].replace("", "ninguno")
    out = (e.groupby(["categoria", "subcategoria", "tipo", "metodo", "fuente"])
           .size().rename("n").reset_index())
    return out.sort_values(["categoria", "subcategoria", "n"], ascending=[True, True, False],
                           kind="mergesort").reset_index(drop=True)[columnas]

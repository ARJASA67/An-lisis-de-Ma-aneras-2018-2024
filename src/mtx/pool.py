"""Pool de relevancia y validación de juicios (PRD §6.5, D06, D07, T07, T08).

Construye la unión sin duplicados de los top-10 de las cuatro variantes por consulta, fija el orden
de presentación (barajado con semilla 42) y valida el formato y la cobertura de los juicios.

Este módulo NUNCA escribe juicios: `validar_juicios` es de solo lectura sobre
`anotaciones/juicios_relevancia.csv`; solo exporta una copia a la raíz cuando todo pasa.
"""
from __future__ import annotations

import random
import shutil
from pathlib import Path

import pandas as pd

from . import adaptadores_kit, config, ranking

VARIANTES = ["tfidf_con_filtro", "bm25_con_filtro", "tfidf_sin_filtro", "bm25_sin_filtro"]
COLUMNAS_POOL = ["query_id", "passage_id", "doc_id", "fecha", "en_ventana", "variantes",
                 "mejor_rango_tfidf", "mejor_rango_bm25", "texto", "texto_sha256"]
COLUMNAS_JUICIOS = ["query_id", "doc_id", "passage_id", "relevante"]
TAM_MIN, TAM_MAX = 15, 40
"""Rango esperado del pool por consulta (PRD §6.5). Fuera de él se avisa, no se recorta."""

POOL_CSV = config.DIR_SALIDA / "04_pool.csv"
JUICIOS_CSV = config.DIR_ANOTACIONES / "juicios_relevancia.csv"
JUICIOS_RAIZ = config.RAIZ / "juicios_relevancia.csv"


# --------------------------------------------------------------------------- construcción


def construir_pool(rank: pd.DataFrame, pasajes: pd.DataFrame, cons: pd.DataFrame) -> pd.DataFrame:
    """Unión de los top-10 de las cuatro variantes por consulta.

    `rank` es `ranking.csv` (`query_id, modelo, rango, passage_id`); `pasajes` trae `passage_id,
    doc_id, fecha, texto, texto_sha256`; `cons` trae `query_id, desde, hasta`. Un mismo pasaje en
    dos consultas genera dos filas (juicio independiente por `(query_id, passage_id)`, T08).
    """
    desconocidas = set(rank["modelo"]) - set(VARIANTES)
    if desconocidas:
        raise ValueError(f"Variantes desconocidas en el ranking: {sorted(desconocidas)}")
    sin_consulta = set(rank["query_id"]) - set(cons["query_id"])
    if sin_consulta:
        raise ValueError(f"Consultas del ranking ausentes de consultas.csv: {sorted(sin_consulta)}")
    meta = pasajes.set_index("passage_id")
    ausentes = sorted(set(rank["passage_id"]) - set(meta.index))
    if ausentes:
        raise ValueError(f"passage_id del ranking ausentes de pasajes.parquet: {ausentes[:5]}")

    filas = []
    for c in cons.itertuples(index=False):
        r = rank[rank["query_id"] == c.query_id]
        if r.empty:
            continue
        for pid in sorted(set(r["passage_id"])):
            rp = r[r["passage_id"] == pid]
            m = meta.loc[pid]
            fecha = m["fecha"]
            en_ventana = bool(ranking.mascara_fecha(
                pd.DatetimeIndex([fecha]).to_numpy(), c.desde, c.hasta)[0])
            rt = rp[rp["modelo"].str.startswith("tfidf")]["rango"]
            rb = rp[rp["modelo"].str.startswith("bm25")]["rango"]
            filas.append({
                "query_id": c.query_id, "passage_id": pid, "doc_id": int(m["doc_id"]),
                "fecha": "" if pd.isna(fecha) else pd.Timestamp(fecha).strftime("%Y-%m-%d"),
                "en_ventana": en_ventana,
                "variantes": "|".join(v for v in VARIANTES if v in set(rp["modelo"])),
                "mejor_rango_tfidf": int(rt.min()) if len(rt) else "",
                "mejor_rango_bm25": int(rb.min()) if len(rb) else "",
                "texto": m["texto"], "texto_sha256": m["texto_sha256"],
            })
    # Las consultas ya se recorrieron en el orden de consultas.csv y los pasajes ordenados.
    return pd.DataFrame(filas, columns=COLUMNAS_POOL)


def avisos_tamano(pool: pd.DataFrame, cons: pd.DataFrame) -> list[str]:
    """Consultas ausentes o con tamaño de pool fuera de 15 a 40 (se revisa el ranking, no se recorta)."""
    n = pool.groupby("query_id").size()
    avisos = []
    for q in cons["query_id"]:
        if q not in n.index:
            avisos.append(f"{q}: sin pasajes en el pool")
        elif not TAM_MIN <= n[q] <= TAM_MAX:
            avisos.append(f"{q}: pool de {n[q]} pasajes (esperado {TAM_MIN} a {TAM_MAX})")
    return avisos


def orden_presentacion(pool: pd.DataFrame, semilla: int = config.SEMILLA) -> dict[str, list[str]]:
    """Orden de presentación por consulta: IDs ordenados y barajados con `random.Random(semilla)`.

    Mismo pool y misma semilla producen siempre el mismo orden (PRD §6.5 punto 4).
    """
    orden = {}
    for q, g in pool.groupby("query_id", sort=False):
        ids = sorted(g["passage_id"])
        random.Random(semilla).shuffle(ids)
        orden[q] = ids
    return orden


# --------------------------------------------------------------------------- persistencia


def escribir_pool(pool: pd.DataFrame, ruta: Path = POOL_CSV) -> str:
    """Escribe el pool (UTF-8, `\\n`) y devuelve su SHA-256."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    pool.to_csv(ruta, index=False, encoding="utf-8", lineterminator="\n")
    return adaptadores_kit.sha256_archivo(ruta)


def leer_pool(ruta: Path = POOL_CSV) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"passage_id": str, "fecha": str, "texto": str,
                                    "texto_sha256": str}, keep_default_na=False)


def diferencias_pool(nuevo: pd.DataFrame, existente: pd.DataFrame) -> list[str]:
    """Lista legible de diferencias entre dos pools (vacía si son equivalentes)."""
    def claves(p):
        return {(q, pid): h for q, pid, h in zip(p["query_id"], p["passage_id"], p["texto_sha256"])}

    a, b = claves(nuevo), claves(existente)
    difs = [f"nuevo en el pool: {q} {pid}" for q, pid in sorted(a.keys() - b.keys())]
    difs += [f"ya no está en el pool: {q} {pid}" for q, pid in sorted(b.keys() - a.keys())]
    difs += [f"texto cambiado: {q} {pid}" for (q, pid) in sorted(a.keys() & b.keys())
             if a[(q, pid)] != b[(q, pid)]]
    for col in ("en_ventana",):
        ea = existente.set_index(["query_id", "passage_id"])[col].astype(str)
        na = nuevo.set_index(["query_id", "passage_id"])[col].astype(str)
        comunes = na.index.intersection(ea.index)
        difs += [f"{col} distinto: {q} {pid}" for q, pid in comunes if na[(q, pid)] != ea[(q, pid)]]
    return difs


def hay_juicios(ruta: Path = JUICIOS_CSV) -> bool:
    """True si el archivo de juicios existe y tiene al menos una fila de datos."""
    if not ruta.exists():
        return False
    return len(pd.read_csv(ruta, dtype=str, keep_default_na=False)) > 0


# --------------------------------------------------------------------------- validación


def validar_juicios(ruta: Path, pool: pd.DataFrame, pasajes: pd.DataFrame,
                    ) -> tuple[list[str], list[str]]:
    """Comprobaciones 1 a 6 de PRD §6.5 (solo lectura). Devuelve `(errores, avisos)`.

    Errores (impiden exportar): columnas, UTF-8 sin BOM, cobertura 100 %, valores fuera de {0, 1},
    pares fuera del pool, `doc_id` incoherente, hash del texto distinto. Aviso (no cambia nada):
    consulta sin relevantes (AP indefinido).
    """
    errores: list[str] = []
    avisos: list[str] = []
    if not ruta.exists():
        return [f"No existe {ruta}"], avisos
    crudo = ruta.read_bytes()
    if crudo.startswith(b"\xef\xbb\xbf"):
        errores.append("El archivo de juicios tiene BOM; debe ser UTF-8 sin BOM")
    try:
        j = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except (UnicodeDecodeError, pd.errors.ParserError) as e:
        return errores + [f"No se pudo leer {ruta.name}: {e}"], avisos
    if list(j.columns) != COLUMNAS_JUICIOS:
        errores.append(f"Columnas {list(j.columns)}; deben ser exactamente {COLUMNAS_JUICIOS}")
        return errores, avisos

    clave = ["query_id", "passage_id"]
    dup = j[j.duplicated(clave, keep=False)]
    for q, pid in sorted(set(map(tuple, dup[clave].to_numpy()))):
        errores.append(f"Juicio repetido: {q} {pid}")
    valores = j["relevante"].str.strip()
    pendientes = j[valores == ""]
    malos = j[~valores.isin(["0", "1", ""])]
    for f in malos.itertuples(index=False):
        errores.append(f"relevante inválido ({f.relevante!r}) en {f.query_id} {f.passage_id}")

    en_pool = set(zip(pool["query_id"], pool["passage_id"]))
    juzgados = set(zip(j["query_id"], j["passage_id"]))
    for q, pid in sorted(juzgados - en_pool):
        errores.append(f"Par fuera del pool: {q} {pid}")
    pend = set(zip(pendientes["query_id"], pendientes["passage_id"]))
    faltan = sorted((en_pool - juzgados) | (pend & en_pool))
    if faltan:
        por_q = pd.Series([q for q, _ in faltan]).value_counts().sort_index()
        errores.append("Cobertura incompleta: faltan " + ", ".join(
            f"{q}: {n}" for q, n in por_q.items()))

    doc_pool = dict(zip(zip(pool["query_id"], pool["passage_id"]), pool["doc_id"].astype(str)))
    for f in j.itertuples(index=False):
        esperado = doc_pool.get((f.query_id, f.passage_id))
        if esperado is not None and f.doc_id != esperado:
            errores.append(f"doc_id incoherente en {f.query_id} {f.passage_id}: "
                           f"{f.doc_id} (pool {esperado})")

    hashes = pasajes.set_index("passage_id")["texto_sha256"]
    for f in pool.itertuples(index=False):
        if f.passage_id not in hashes.index:
            errores.append(f"passage_id ausente del corpus: {f.passage_id}")
        elif hashes[f.passage_id] != f.texto_sha256:
            errores.append(f"texto_sha256 distinto al corpus actual: {f.passage_id}")

    if not errores:
        rel = j[valores == "1"].groupby("query_id").size()
        for q in dict.fromkeys(pool["query_id"]):
            if rel.get(q, 0) == 0:
                avisos.append(f"AP indefinido para {q}: cero relevantes (se discute en el reporte)")
    return errores, avisos


def exportar_juicios(origen: Path = JUICIOS_CSV, destino: Path = JUICIOS_RAIZ) -> None:
    """Copia idéntica a la raíz. Solo se llama después de que `validar_juicios` no dio errores."""
    shutil.copyfile(origen, destino)

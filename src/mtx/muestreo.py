"""Muestra gold de evaluación con semilla 42 y emparejamiento global (PRD §6.11, D10, U13, T09).

Universo: top-10 con filtro del mejor modelo de IR. Dos plazas por consulta, una de rango alto
(1-5) y otra de rango bajo (6-10), para no medir solo los pasajes más evidentes. Cada plaza
recibe un orden de candidatos barajado con la semilla; la asignación es un emparejamiento
bipartito plaza → pasaje (algoritmo de Kuhn con los candidatos en ese orden), de modo que un
pasaje que aparece en varias consultas nunca se duplica. Si no hay asignación completa se lanza
`MuestraInviable` con las consultas en conflicto: nunca se amplía al top-20 ni se duplican IDs.

Sustitución objetiva (U13), aplicada antes de ver predicciones: un candidato no es elegible si su
cuerpo tiene menos de 25 palabras de contenido o si más de la mitad de ellas son fórmulas de
protocolo (`config/protocolo.txt`). El sustituto es el siguiente candidato del orden sorteado de
la misma plaza. "No tiene entidades" nunca es motivo.

Esta función no lee predicciones de ningún tipo.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from mtx import config, preproceso

PROTOCOLO = config.DIR_CONFIG / "protocolo.txt"
MUESTRA_GOLD = config.DIR_ANOTACIONES / "muestra_gold.csv"
COLUMNAS_MUESTRA = ["query_id", "passage_id", "doc_id", "texto_sha256", "semilla",
                    "version_muestra"]
MIN_PALABRAS_CONTENIDO = 25
MAX_PROPORCION_PROTOCOLO = 0.5
PLAZAS = (("alto", 1, 5), ("bajo", 6, 10))


class MuestraInviable(RuntimeError):
    """No existe asignación de 20 IDs únicos; `conflictos` lista las consultas afectadas."""

    def __init__(self, conflictos: list[str]):
        self.conflictos = conflictos
        super().__init__("No hay asignación completa sin duplicar pasajes; consultas en "
                         f"conflicto: {', '.join(conflictos)}")


def cargar_protocolo(ruta: Path = PROTOCOLO) -> frozenset[str]:
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return frozenset(x.strip().lower() for x in lineas if x.strip() and not x.startswith("#"))


def hash_protocolo(ruta: Path = PROTOCOLO) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def palabras_contenido(texto: str, inicio_cuerpo: int) -> list[str]:
    """Tokens del cuerpo (sin la marca de interlocutor) en minúsculas y sin stoplist."""
    stop = preproceso.stoplist()
    return [t for t in (m.group().lower() for m in preproceso.RE_TOKEN.finditer(
        texto, inicio_cuerpo)) if t not in stop]


def motivo_sustitucion(texto: str, inicio_cuerpo: int, protocolo: frozenset[str]) -> str | None:
    """Criterio objetivo por el que el pasaje no es elegible, con su cifra; None si es elegible."""
    if not texto.strip():
        return "texto vacío o corrupto"
    palabras = palabras_contenido(texto, inicio_cuerpo)
    # Protocolo sobre palabras de contenido más las de protocolo que la stoplist quita ("gracias").
    stop = preproceso.stoplist()
    consideradas = [t for t in (m.group().lower() for m in preproceso.RE_TOKEN.finditer(
        texto, inicio_cuerpo)) if t not in stop or t in protocolo]
    prop = sum(p in protocolo for p in consideradas) / len(consideradas) if consideradas else 0
    if consideradas and prop > MAX_PROPORCION_PROTOCOLO:
        return f"{prop:.0%} de palabras de protocolo (máximo {MAX_PROPORCION_PROTOCOLO:.0%})"
    if len(palabras) < MIN_PALABRAS_CONTENIDO:
        return f"{len(palabras)} palabras de contenido (mínimo {MIN_PALABRAS_CONTENIDO})"
    return None


@dataclass
class Resultado:
    muestra: pd.DataFrame
    """Manifiesto con `COLUMNAS_MUESTRA`."""
    detalle: pd.DataFrame
    """Plaza, rango y posición en el orden sorteado de cada pasaje asignado."""
    sustituciones: pd.DataFrame
    """Candidatos no elegibles que habrían ocupado una plaza, con su motivo y su sustituto."""


def _ordenes(top: pd.DataFrame, semilla: int) -> dict[tuple[str, str], list[str]]:
    """Orden barajado de candidatos por plaza; determinista dado el ranking y la semilla."""
    rng = np.random.default_rng(semilla)
    ordenes = {}
    for q in sorted(top["query_id"].unique(), key=lambda x: int(x[1:])):
        tq = top[top["query_id"] == q].sort_values("rango")
        for nombre, lo, hi in PLAZAS:
            cand = list(tq[(tq["rango"] >= lo) & (tq["rango"] <= hi)]["passage_id"])
            if not cand:  # consulta con menos de `lo` resultados: la plaza toma cualquier rango
                cand = list(tq["passage_id"])
            ordenes[(q, nombre)] = [cand[i] for i in rng.permutation(len(cand))]
    return ordenes


def _emparejar(plazas: list[tuple[str, str]], cand: dict[tuple[str, str], list[str]]
               ) -> dict[tuple[str, str], str]:
    """Emparejamiento máximo de Kuhn; cada plaza prueba sus candidatos en su orden sorteado."""
    dueno: dict[str, tuple[str, str]] = {}

    def intentar(plaza, vistos: set[str]) -> bool:
        for pid in cand[plaza]:
            if pid in vistos:
                continue
            vistos.add(pid)
            if pid not in dueno or intentar(dueno[pid], vistos):
                dueno[pid] = plaza
                return True
        return False

    for plaza in plazas:
        intentar(plaza, set())
    return {plaza: pid for pid, plaza in dueno.items()}


def sortear_gold(top: pd.DataFrame, pasajes: pd.DataFrame, protocolo: frozenset[str],
                 semilla: int = config.SEMILLA, version: int = 1) -> Resultado:
    """Sortea la muestra gold.

    `top`: `query_id, passage_id, doc_id, rango` del top-10 con filtro del mejor modelo.
    `pasajes`: `passage_id, texto, inicio_cuerpo, texto_sha256` (al menos los de `top`).
    """
    pas = pasajes.set_index("passage_id")
    ordenes = _ordenes(top, semilla)
    no_elegibles = {}
    for pid in top["passage_id"].unique():
        m = motivo_sustitucion(pas.at[pid, "texto"], int(pas.at[pid, "inicio_cuerpo"]), protocolo)
        if m:
            no_elegibles[pid] = m
    elegibles = {k: [p for p in v if p not in no_elegibles] for k, v in ordenes.items()}
    plazas = list(ordenes)
    asignacion = _emparejar(plazas, elegibles)
    faltan = [p for p in plazas if p not in asignacion]
    if faltan:
        raise MuestraInviable(sorted({q for q, _ in faltan}, key=lambda x: int(x[1:])))

    rango = {(q, p): int(r) for q, p, r in zip(top["query_id"], top["passage_id"], top["rango"],
                                               strict=True)}
    doc = dict(zip(top["passage_id"], top["doc_id"], strict=False))
    filas, det, sust = [], [], []
    for (q, plaza) in plazas:
        pid = asignacion[(q, plaza)]
        filas.append({"query_id": q, "passage_id": pid, "doc_id": doc[pid],
                      "texto_sha256": pas.at[pid, "texto_sha256"], "semilla": semilla,
                      "version_muestra": version})
        det.append({"query_id": q, "plaza": plaza, "passage_id": pid, "rango": rango[(q, pid)],
                    "posicion_sorteo": ordenes[(q, plaza)].index(pid) + 1})
        # Candidatos no elegibles sorteados antes del asignado en esta plaza.
        for previo in ordenes[(q, plaza)][:ordenes[(q, plaza)].index(pid)]:
            if previo in no_elegibles:
                sust.append({"query_id": q, "plaza": plaza, "passage_retirado": previo,
                             "motivo": no_elegibles[previo], "sustituto": pid})
    return Resultado(pd.DataFrame(filas, columns=COLUMNAS_MUESTRA), pd.DataFrame(det),
                     pd.DataFrame(sust, columns=["query_id", "plaza", "passage_retirado",
                                                 "motivo", "sustituto"]))


def leer_muestra(ruta: Path = MUESTRA_GOLD) -> pd.DataFrame:
    return pd.read_csv(ruta, dtype={"passage_id": str, "doc_id": str, "texto_sha256": str})

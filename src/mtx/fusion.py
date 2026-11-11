"""Fusión reglas + modelo por span exacto (PRD §6.9, D12, D16, T08, T13).

Misma `(passage_id, tipo, inicio, fin)` en ambas fuentes → una fila `ambos`; si no, cada fuente
conserva su fila (`regla` o `modelo`). Solapes parciales y mismo span con tipo distinto no se
resuelven: se registran en `salida/08_solapes_parciales.csv`. No hay umbral de puntaje ni
prioridad entre fuentes, y nada aquí lee el gold.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

COLUMNAS_ENTIDADES = ["query_id", "doc_id", "passage_id", "tipo", "texto", "inicio", "fin",
                      "metodo"]
COLUMNAS_SOLAPES = ["passage_id", "clase", "tipo_regla", "inicio_regla", "fin_regla",
                    "texto_regla", "fuente_regla", "tipo_modelo", "inicio_modelo", "fin_modelo",
                    "texto_modelo", "longitud_solape"]
TIPOS = {"PER", "ORG", "LOC", "FECHA", "MONTO"}
METODOS = {"regla", "modelo", "ambos"}


@dataclass
class Fusionada:
    tipo: str
    texto: str
    inicio: int
    fin: int
    metodo: str
    fuentes: str
    en_marca: bool
    puntaje_modelo: float | None


def fusionar_pasaje(pid: str, de_reglas: list[dict], de_modelo: list[dict], inicio_cuerpo: int
                    ) -> tuple[list[Fusionada], list[dict]]:
    """Entidades únicas del pasaje con su `metodo` y los solapes no exactos entre fuentes.

    `de_reglas`: dicts `tipo, texto, inicio, fin, fuente, en_marca`.
    `de_modelo`: dicts `tipo, texto, inicio, fin, confianza`.
    """
    r = {(e["tipo"], int(e["inicio"]), int(e["fin"])): e for e in de_reglas}
    m = {(e["tipo"], int(e["inicio"]), int(e["fin"])): e for e in de_modelo}
    filas = []
    for clave in sorted(set(r) | set(m), key=lambda k: (k[1], k[2], k[0])):
        tipo, ini, fin = clave
        er, em = r.get(clave), m.get(clave)
        base = er or em
        metodo = "ambos" if er and em else ("regla" if er else "modelo")
        fuentes = "|".join(x for x in (er and er.get("fuente"), em and "modelo") if x)
        en_marca = bool(er["en_marca"]) if er else ini < inicio_cuerpo
        filas.append(Fusionada(tipo, base["texto"], ini, fin, metodo, fuentes, en_marca,
                               float(em["confianza"]) if em else None))
    solapes = []
    for (tr, ir, fr), er in sorted(r.items(), key=lambda x: (x[0][1], x[0][2])):
        for (tm, im, fm), em in sorted(m.items(), key=lambda x: (x[0][1], x[0][2])):
            if (tr, ir, fr) == (tm, im, fm) or not (ir < fm and im < fr):
                continue
            if (ir, fr) == (im, fm):
                clase = "tipo_distinto"
            else:
                clase = "solape_parcial"
            solapes.append({"passage_id": pid, "clase": clase, "tipo_regla": tr,
                            "inicio_regla": ir, "fin_regla": fr, "texto_regla": er["texto"],
                            "fuente_regla": er.get("fuente", ""), "tipo_modelo": tm,
                            "inicio_modelo": im, "fin_modelo": fm, "texto_modelo": em["texto"],
                            "longitud_solape": min(fr, fm) - max(ir, im)})
    return filas, solapes


def a_consultas(unicas: pd.DataFrame, ambito: pd.DataFrame) -> pd.DataFrame:
    """Asocia las entidades únicas por pasaje a cada consulta que recuperó el pasaje (T08).

    `ambito`: `query_id, passage_id, doc_id`. Devuelve las 8 columnas en orden, ordenado por
    `query_id` (numérico), `passage_id`, `inicio`.
    """
    df = ambito[["query_id", "passage_id", "doc_id"]].merge(unicas, on="passage_id", how="inner")
    df["_q"] = df["query_id"].str[1:].astype(int)
    df = df.sort_values(["_q", "passage_id", "inicio", "fin", "tipo"], kind="mergesort")
    return df.drop(columns="_q").reset_index(drop=True)


def validar_entidades(df: pd.DataFrame, textos: dict[str, str]) -> list[str]:
    """Contrato de `entidades.csv` (D16): columnas, dominios, clave única e invariante de offsets."""
    errores = []
    if list(df.columns) != COLUMNAS_ENTIDADES:
        return [f"Columnas {list(df.columns)}; se esperan {COLUMNAS_ENTIDADES}"]
    if not set(df["tipo"]) <= TIPOS:
        errores.append(f"Tipos fuera de dominio: {set(df['tipo']) - TIPOS}")
    if not set(df["metodo"]) <= METODOS:
        errores.append(f"Métodos fuera de dominio: {set(df['metodo']) - METODOS}")
    if df.duplicated(["query_id", "passage_id", "tipo", "inicio", "fin"]).any():
        errores.append("Clave (query_id, passage_id, tipo, inicio, fin) duplicada")
    malos = [f"{p} ({i}, {f})" for p, t, i, f in zip(df["passage_id"], df["texto"], df["inicio"],
                                                     df["fin"], strict=True)
             if textos[p][int(i):int(f)] != t]
    if malos:
        errores.append(f"Offsets rotos: {malos[:5]}")
    return errores

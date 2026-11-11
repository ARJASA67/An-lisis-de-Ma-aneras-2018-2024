"""08b · Sorteo de la muestra gold (PRD §6.11, D10). `make muestra-gold`.

Entrada: ranking.csv, data/mejor_modelo.json, data/pasajes.parquet, config/protocolo.txt. No lee
predicciones de ningún tipo. Idempotente: si `anotaciones/muestra_gold.csv` ya existe y el sorteo
da lo mismo, no escribe nada; si diera algo distinto, se detiene (la muestra está congelada).

Salidas: anotaciones/muestra_gold.csv (manifiesto), salida/08b_muestra_detalle.csv (plaza, rango y
posición en el sorteo) y salida/08b_sustituciones.csv (candidatos retirados por criterio objetivo).
El conjunto de selección (P1) no se sortea: no hay segundo NER que comparar (docs/decisiones.md).
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from mtx import config, muestreo

RANKING = config.RAIZ / "ranking.csv"
MEJOR = config.DIR_DATA / "mejor_modelo.json"


def main() -> int:
    mejor = json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]
    if not mejor.endswith("_con_filtro"):
        raise SystemExit(f"El mejor modelo debe ser una variante con filtro: {mejor}")
    rk = pd.read_csv(RANKING, dtype={"passage_id": str, "doc_id": str})
    top = rk[rk["modelo"] == mejor][["query_id", "passage_id", "doc_id", "rango"]]
    pas = pd.read_parquet(config.PASAJES_PARQUET,
                          columns=["passage_id", "texto", "inicio_cuerpo", "texto_sha256"],
                          filters=[("passage_id", "in", list(top["passage_id"].unique()))])
    try:
        res = muestreo.sortear_gold(top, pas, muestreo.cargar_protocolo())
    except muestreo.MuestraInviable as e:
        print(f"ERROR: {e}. Registra la excepción en docs/decisiones.md; no se amplía al top-20.")
        return 1

    kw = {"index": False, "lineterminator": "\n", "encoding": "utf-8"}
    if muestreo.MUESTRA_GOLD.exists():
        previa = muestreo.leer_muestra()
        nueva = res.muestra.astype(str).reset_index(drop=True)
        if not previa.astype(str).reset_index(drop=True).equals(nueva):
            print("ERROR: la muestra existente difiere del sorteo actual y está congelada. "
                  "No se sobrescribe; revisa con el alumno qué cambió.")
            return 1
        print("La muestra ya existe y coincide con el sorteo; no se escribe nada.")
    else:
        config.DIR_ANOTACIONES.mkdir(exist_ok=True)
        res.muestra.to_csv(muestreo.MUESTRA_GOLD, **kw)
        print(f"Escrita {muestreo.MUESTRA_GOLD.relative_to(config.RAIZ)}")
    res.detalle.to_csv(config.DIR_SALIDA / "08b_muestra_detalle.csv", **kw)
    res.sustituciones.to_csv(config.DIR_SALIDA / "08b_sustituciones.csv", **kw)
    print(f"{len(res.muestra)} pasajes, {res.muestra['query_id'].nunique()} consultas, "
          f"{res.muestra['passage_id'].nunique()} IDs únicos; rangos "
          f"{sorted(res.detalle['rango'])}; sustituciones: {len(res.sustituciones)}")
    if len(res.sustituciones):
        print(res.sustituciones.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

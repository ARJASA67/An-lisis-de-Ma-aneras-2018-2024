"""06 · Reglas de extracción sobre todo el corpus (PRD §6.7). `make reglas`.

Entrada: data/pasajes.parquet, config/gazetteer_extendido.csv, config/gazetteer_loc.csv,
data/mejor_modelo.json y ranking.csv. No lee juicios ni gold ni predicciones de modelo.
Salidas: salida/06_colisiones_reglas.csv, salida/06_siglas_candidatas.csv (para revisión del
alumno), salida/cantidades_auxiliares.csv (top-10 del mejor modelo por consulta; nunca entran a
entidades.csv) y salida/06_resumen_reglas.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter

import pandas as pd

from mtx import adaptadores_kit, config, reglas

COLS_AUX = ["query_id", "passage_id", "texto", "inicio", "fin", "tipo_aux", "valor_num", "unidad",
            "estado_normalizacion", "regla_id"]
RANKING = config.RAIZ / "ranking.csv"
MEJOR = config.DIR_DATA / "mejor_modelo.json"


def main() -> int:
    config.DIR_SALIDA.mkdir(exist_ok=True)
    gaz = reglas.cargar_gazetteer()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET, columns=[
        "passage_id", "texto", "inicio_cuerpo"])
    conteo: Counter[str] = Counter()
    colisiones: list[dict] = []
    for pid, texto, ic in zip(pasajes["passage_id"], pasajes["texto"], pasajes["inicio_cuerpo"],
                              strict=True):
        ents, cols = reglas.extraer_reglas_con_colisiones(texto, int(ic), gaz)
        for e in ents:
            assert texto[e.inicio:e.fin] == e.texto, f"offsets rotos en {pid}"
            conteo[f"{e.tipo}|{e.fuente}"] += 1
        colisiones += [{"passage_id": pid, **c} for c in cols]
    pd.DataFrame(colisiones).to_csv(config.DIR_SALIDA / "06_colisiones_reglas.csv", index=False,
                                    lineterminator="\n")

    siglas = reglas.minar_siglas(pasajes, gaz)
    siglas.to_csv(config.DIR_SALIDA / "06_siglas_candidatas.csv", index=False, lineterminator="\n")

    mejor = json.loads(MEJOR.read_text(encoding="utf-8"))["modelo"]
    rk = pd.read_csv(RANKING, dtype={"passage_id": str})
    top = rk[rk["modelo"] == mejor][["query_id", "passage_id"]]
    texto_de = pasajes.set_index("passage_id")["texto"]
    filas = []
    for q, pid in zip(top["query_id"], top["passage_id"], strict=True):
        filas += [{"query_id": q, "passage_id": pid, **a} for a in reglas.extraer_auxiliares(
            texto_de[pid])]
    aux = pd.DataFrame(filas, columns=COLS_AUX)
    aux["valor_num"] = aux["valor_num"].map(lambda v: format(v, "f"))
    aux.to_csv(config.DIR_SALIDA / "cantidades_auxiliares.csv", index=False, lineterminator="\n")

    resumen = {
        "pasajes": len(pasajes), "entidades_por_tipo_y_fuente": dict(sorted(conteo.items())),
        "colisiones": len(colisiones), "siglas_candidatas": len(siglas),
        "gazetteer": {"terminos_org": len(gaz.terminos("ORG")), "terminos_loc": len(gaz.terminos("LOC")),
                      "estados": len(gaz.estados)},
        "auxiliares": aux["tipo_aux"].value_counts().to_dict(), "modelo_para_auxiliares": mejor,
        "sha256_gazetteer_extendido": adaptadores_kit.sha256_archivo(reglas.GAZETTEER_EXTENDIDO),
        "sha256_gazetteer_loc": adaptadores_kit.sha256_archivo(reglas.GAZETTEER_LOC),
        "sha256_reglas_py": adaptadores_kit.sha256_archivo(config.RAIZ / "src" / "mtx" / "reglas.py"),
    }
    (config.DIR_SALIDA / "06_resumen_reglas.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

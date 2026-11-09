"""04 · Pool de relevancia (PRD §6.5, D06). `make pool`.

Entrada: ranking.csv, data/pasajes.parquet, data/consultas.csv. No escribe juicios.
Salidas: salida/04_pool.csv (si no existe), salida/04_pool_resumen.csv y data/pool_meta.json.
Si el pool ya existe lo reconstruye en memoria y compara; si cambió y hay juicios, se detiene
sin sobrescribir nada.
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from mtx import adaptadores_kit, config, consultas, pool

RANKING = config.RAIZ / "ranking.csv"
META = config.DIR_DATA / "pool_meta.json"


def main() -> int:
    cons = consultas.cargar()
    rank = pd.read_csv(RANKING, dtype={"passage_id": str}, keep_default_na=False)
    pasajes = pd.read_parquet(config.PASAJES_PARQUET, columns=[
        "passage_id", "doc_id", "fecha", "texto", "texto_sha256"])
    nuevo = pool.construir_pool(rank, pasajes, cons)

    for a in pool.avisos_tamano(nuevo, cons):
        print("AVISO:", a)

    if pool.POOL_CSV.exists():
        difs = pool.diferencias_pool(nuevo, pool.leer_pool())
        if difs:
            print(f"El pool reconstruido difiere de {pool.POOL_CSV.name} ({len(difs)} cambios):")
            for d in difs[:20]:
                print("  -", d)
            if pool.hay_juicios():
                print("Hay juicios en anotaciones/: NO se sobrescribe. Los juicios asociados "
                      "quedan inválidos hasta revisión (skill integridad-congelacion).")
                return 1
            print("Sin juicios todavía: se reescribe el pool.")
            hash_pool = pool.escribir_pool(nuevo)
        else:
            print("Pool idéntico al existente: no se escribe nada.")
            hash_pool = adaptadores_kit.sha256_archivo(pool.POOL_CSV)
    else:
        hash_pool = pool.escribir_pool(nuevo)
        print(f"Pool escrito en {pool.POOL_CSV.relative_to(config.RAIZ)}.")

    orden = pool.orden_presentacion(nuevo)
    resumen = (nuevo.groupby("query_id", sort=False).agg(
        pasajes=("passage_id", "size"), en_ventana=("en_ventana", "sum"),
        discursos=("doc_id", "nunique")).reset_index())
    resumen["fuera_de_ventana"] = resumen["pasajes"] - resumen["en_ventana"]
    resumen["en_las_4_variantes"] = [
        int((nuevo[nuevo["query_id"] == q]["variantes"].str.count(r"\|") == 3).sum())
        for q in resumen["query_id"]]
    resumen["primer_id_presentado"] = [orden[q][0] for q in resumen["query_id"]]
    resumen.to_csv(config.DIR_SALIDA / "04_pool_resumen.csv", index=False, lineterminator="\n")

    META.write_text(json.dumps({
        "pool_sha256": hash_pool, "ranking_sha256": adaptadores_kit.sha256_archivo(RANKING),
        "pasajes_sha256": adaptadores_kit.sha256_archivo(config.PASAJES_PARQUET),
        "consultas_sha256": adaptadores_kit.sha256_archivo(config.CONSULTAS_CSV),
        "semilla_orden": config.SEMILLA, "filas": len(nuevo),
        "por_consulta": {q: len(v) for q, v in orden.items()},
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(resumen.to_string(index=False))
    print(f"Total: {len(nuevo)} pares (consulta, pasaje) para juzgar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

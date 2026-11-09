"""99 · Validación de entregables. `make validar`.

Hoy valida los juicios de relevancia (PRD §6.5, §13.2 punto 4): cobertura 100 % del pool, formato,
coherencia con el corpus. Si pasa, exporta `juicios_relevancia.csv` a la raíz con el mismo contenido.
Es de solo lectura sobre `anotaciones/`. El resto de validadores (gold, resultados, manifiesto)
se suman en H6 a H9.
"""
from __future__ import annotations

import sys

import pandas as pd

from mtx import config, pool


def validar_juicios() -> bool:
    if not pool.POOL_CSV.exists():
        print("JUICIOS: falta salida/04_pool.csv (make pool).")
        return False
    pl = pool.leer_pool()
    pasajes = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto_sha256"])
    errores, avisos = pool.validar_juicios(pool.JUICIOS_CSV, pl, pasajes)
    for a in avisos:
        print("AVISO:", a)
    if errores:
        print("JUICIOS: NO válidos, no se exporta.")
        for e in errores:
            print("  -", e)
        return False
    pool.exportar_juicios()
    print(f"JUICIOS: válidos ({len(pl)} pares, 10 consultas). Exportado a juicios_relevancia.csv.")
    return True


def main() -> int:
    return 0 if validar_juicios() else 1


if __name__ == "__main__":
    sys.exit(main())

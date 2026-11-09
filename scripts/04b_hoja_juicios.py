"""04b · Hoja de cálculo para repartir juicios entre compañeros. `make hoja-juicios`.

Entrada: salida/04_pool.csv, data/consultas.csv, anotaciones/juicios_relevancia.csv (solo para saber
qué consultas faltan), config/criterios_relevancia.md. No lee juicios para otra cosa y no precarga nada.
Salida: salida/04_hoja_juicios.xlsx, una pestaña por consulta pendiente; se sube a Google Drive y se
abre como Hoja de cálculo.
"""
from __future__ import annotations

import sys

import pandas as pd

from mtx import config, consultas, hoja_juicios, pool
from mtx.app import componentes

DESTINO = config.DIR_SALIDA / "04_hoja_juicios.xlsx"


def main(argv: list[str]) -> int:
    if not componentes.criterios_listos():
        print("Falta config/criterios_relevancia.md: sin criterio aprobado no se reparte nada.")
        return 1
    pl = pool.leer_pool()
    cons = consultas.cargar()
    juicios = (pd.read_csv(pool.JUICIOS_CSV, dtype=str, keep_default_na=False)
               if pool.JUICIOS_CSV.exists() else pd.DataFrame(columns=pool.COLUMNAS_JUICIOS))
    pendientes = argv or hoja_juicios.consultas_pendientes(pl, juicios)
    if not pendientes:
        print("No quedan consultas pendientes.")
        return 0
    meta = componentes.metadatos_pasajes(list(pl["passage_id"]))
    criterios = componentes.CRITERIOS_RELEVANCIA.read_text(encoding="utf-8")
    hoja_juicios.generar(DESTINO, pl, cons, meta, criterios, pendientes)
    n = int(pl["query_id"].isin(pendientes).sum())
    print(f"Hoja escrita en {DESTINO.relative_to(config.RAIZ)}: {', '.join(pendientes)} ({n} pares).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

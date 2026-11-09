"""04c · Importa a la app los juicios que los compañeros llenaron en la hoja. Lo corre el alumno.

Uso: `uv run python scripts/04c_importar_juicios_hoja.py ruta/hoja.xlsx [--aplicar]`.
Sin `--aplicar` solo revisa (no escribe nada). Con `--aplicar` registra cada 1 o 0 con el almacén de
la app (escritura atómica, respaldo, revisión y gate de criterios) y guarda el nombre del anotador
de cada consulta en la meta. Los vacíos se ignoran: siguen pendientes. Nada se corrige ni se completa.
"""
from __future__ import annotations

import sys
from pathlib import Path

from mtx import adaptadores_kit, hoja_juicios, pool
from mtx.app import componentes


def main(argv: list[str]) -> int:
    aplicar = "--aplicar" in argv
    rutas = [a for a in argv if not a.startswith("--")]
    if len(rutas) != 1:
        print(__doc__)
        return 2
    pl = pool.leer_pool()
    hoja, anotadores = hoja_juicios.leer(Path(rutas[0]))
    errores = hoja_juicios.revisar(hoja, anotadores, pl)
    juzgados = hoja[hoja["relevante"].isin(["0", "1"])]
    print(f"Pestañas: {', '.join(anotadores)}. Filas: {len(hoja)}. Con 0/1: {len(juzgados)}. "
          f"Vacías: {len(hoja) - len(juzgados)}.")
    for q, nombre in anotadores.items():
        n = int((juzgados["query_id"] == q).sum())
        print(f"  {q}: {n} de {int((hoja['query_id'] == q).sum())} por {nombre or '(sin nombre)'}")
    if errores:
        print("NO se importa nada. Errores:")
        for e in errores[:30]:
            print("  -", e)
        return 1
    if not aplicar:
        print("Revisión sin errores. Repite con --aplicar para registrarlos.")
        return 0
    alm = componentes.AlmacenJuicios(
        componentes.cargar_pool_ciego(), hash_pool=adaptadores_kit.sha256_archivo(pool.POOL_CSV))
    previos = 0
    for f in juzgados.itertuples(index=False):
        if alm.estado(f.query_id, f.passage_id) in ("0", "1"):
            previos += 1
            continue  # nunca se pisa un juicio ya registrado
        alm.registrar(f.query_id, f.passage_id, f.relevante, anotador=anotadores[f.query_id])
    print(f"Importado. Omitidos por tener ya un juicio: {previos}. Revisión del archivo: {alm.revision}.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""Alternativa sin Streamlit para Juicios: `make app-cli` (skill `app-anotacion`).

Misma persistencia, mismo gate de criterios y mismo modo ciego que la app: solo ve consulta,
pregunta y pasaje. Acciones: 1, 0, o (omitir), a (anterior), s (salir).
"""
from __future__ import annotations

from mtx import adaptadores_kit, consultas, pool
from mtx.app import componentes


def main() -> int:
    if not pool.POOL_CSV.exists():
        print("Falta el pool: corre `make pool`.")
        return 1
    if not componentes.criterios_listos():
        print("Falta config/criterios_relevancia.md: escríbelo y apruébalo antes de juzgar.")
        return 1
    pl = componentes.cargar_pool_ciego()
    cons = consultas.cargar().set_index("query_id")
    meta = componentes.metadatos_pasajes(list(pl["passage_id"]))
    orden = pool.orden_presentacion(pl)
    alm = componentes.AlmacenJuicios(pl, hash_pool=adaptadores_kit.sha256_archivo(pool.POOL_CSV))

    for q in cons.index:
        ids = orden[q]
        idx = componentes.primer_pendiente(ids, lambda p, q=q: alm.estado(q, p))
        while idx is not None:
            pid = ids[idx]
            fila = pl[(pl["query_id"] == q) & (pl["passage_id"] == pid)].iloc[0]
            h, t = alm.progreso(q)
            print(f"\n=== {q}: {cons.loc[q, 'consulta']} ({h} de {t}) ===")
            print(f"Ayuda: {cons.loc[q, 'pregunta_extraccion']}")
            print("Criterio: relevancia temática; la fecha y el modelo no cuentan.")
            print(f"[{pid}] {meta.loc[pid, 'titulo']} · fecha {fila['fecha'] or 'desconocida'}\n")
            print(fila["texto"])
            accion = input("\n1 relevante · 0 no relevante · o omitir · a anterior · s salir > ").strip().lower()
            try:
                if accion in ("1", "0"):
                    alm.registrar(q, pid, accion)
                elif accion == "o":
                    alm.registrar(q, pid, "")
                elif accion == "a":
                    idx = max(idx - 1, 0)
                    continue
                elif accion == "s":
                    return 0
                else:
                    print("Acción no reconocida.")
                    continue
            except componentes.ConflictoRevision as e:
                print(e)
                return 1
            idx = componentes.siguiente_pendiente(ids, lambda p, q=q: alm.estado(q, p), idx)
    print("No quedan pasajes pendientes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

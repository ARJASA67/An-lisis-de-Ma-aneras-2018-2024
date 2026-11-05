"""00 · Candidatos para Q9 y Q10 (PRD §5.2). `make explorar`.

Requiere `data/pasajes.parquet` (`make corpus`). Escribe `salida/00_candidatos_q9q10.md`.
No elige consultas ni modifica `data/consultas.csv`.
"""
from __future__ import annotations

import pandas as pd

from mtx import adaptadores_kit, config, descubrimiento


def main() -> None:
    if not config.PASAJES_PARQUET.exists():
        raise SystemExit("Falta data/pasajes.parquet: corre primero `make corpus`.")
    pasajes = pd.read_parquet(config.PASAJES_PARQUET)
    norm = descubrimiento.cuerpo_normalizado(pasajes)
    cands = config.cargar_yaml("candidatos_q9q10.yaml")["candidatos"]
    resultados = [descubrimiento.analizar_candidato(pasajes, norm, c) for c in cands]
    obligatorias = pd.read_csv(adaptadores_kit.DIR_KIT / "consultas.csv")
    config.DIR_SALIDA.mkdir(exist_ok=True)
    ruta = config.DIR_SALIDA / "00_candidatos_q9q10.md"
    ruta.write_text(descubrimiento.a_markdown(resultados, obligatorias), encoding="utf-8")
    print(f"Escrito {ruta.relative_to(config.RAIZ)}")


if __name__ == "__main__":
    main()

"""00b · Escribe data/consultas.csv = kit + Q9 + Q10 desde config/consultas_q9q10.yaml. `make consultas`."""
from __future__ import annotations

from mtx import config, consultas


def main() -> None:
    cfg = config.cargar_yaml("consultas_q9q10.yaml")
    df = consultas.construir(cfg["consultas"])
    config.DIR_DATA.mkdir(exist_ok=True)
    df.to_csv(config.CONSULTAS_CSV, index=False, encoding="utf-8")
    print(f"{len(df)} consultas en {config.CONSULTAS_CSV.relative_to(config.RAIZ)}; "
          f"estado de Q9 y Q10: {cfg['estado']}")


if __name__ == "__main__":
    main()

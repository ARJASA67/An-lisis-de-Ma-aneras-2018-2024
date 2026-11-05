"""Construcción de data/consultas.csv (PRD §3.2)."""
from __future__ import annotations

import pandas as pd
import pytest

from mtx import adaptadores_kit, config, consultas

EXTRA = [
    {"query_id": "Q9", "consulta": "tema nueve", "desde": "2019-01-01", "hasta": "2020-01-01",
     "pregunta_extraccion": "Qué, quién, cuándo"},
    {"query_id": "Q10", "consulta": "tema diez", "desde": "2020-01-01", "hasta": "2021-01-01",
     "pregunta_extraccion": "Dónde"},
]


def test_q1_a_q8_quedan_literales_y_q9_q10_se_agregan_al_final():
    kit = pd.read_csv(adaptadores_kit.DIR_KIT / "consultas.csv", dtype=str, keep_default_na=False)
    todas = consultas.construir(EXTRA)
    assert list(todas.columns) == consultas.COLUMNAS
    pd.testing.assert_frame_equal(todas.iloc[:8].reset_index(drop=True), kit)
    assert todas["query_id"].tolist() == [f"Q{i}" for i in range(1, 11)]


def test_rechaza_ids_repetidos_y_ventanas_invertidas():
    with pytest.raises(ValueError, match="repetido"):
        consultas.construir([{**EXTRA[0], "query_id": "Q1"}])
    with pytest.raises(ValueError, match="invertida"):
        consultas.construir([{**EXTRA[0], "desde": "2025-01-01"}])


def test_la_configuracion_actual_es_valida():
    cfg = config.cargar_yaml("consultas_q9q10.yaml")
    assert [c["query_id"] for c in cfg["consultas"]] == ["Q9", "Q10"]
    assert len(consultas.construir(cfg["consultas"])) == 10

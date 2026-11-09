"""T04b · Criterios bloqueantes de IR sobre el corpus real (PRD §6.4). Prueba lenta: requiere
`make corpus indice ranking` ya corridos."""
from __future__ import annotations

import filecmp

import pandas as pd
import pytest

from mtx import adaptadores_kit, config

RANKING = config.RAIZ / "ranking.csv"
COLUMNAS = ["query_id", "modelo", "variante", "rango", "passage_id", "doc_id", "fecha",
            "posicion", "puntaje"]

pytestmark = [pytest.mark.lento,
              pytest.mark.skipif(not RANKING.exists(), reason="falta ranking.csv (make ranking)")]


@pytest.fixture(scope="module")
def r():
    return pd.read_csv(RANKING, dtype={"passage_id": str, "fecha": str}, keep_default_na=False)


@pytest.fixture(scope="module")
def textos():
    p = pd.read_parquet(config.PASAJES_PARQUET, columns=["passage_id", "texto"])
    return p.set_index("passage_id")["texto"]


def test_formato_y_claves(r):
    assert list(r.columns) == COLUMNAS
    assert len(r) == 400
    assert not r.duplicated(["query_id", "modelo", "rango"]).any()
    assert not r.duplicated(["query_id", "modelo", "passage_id"]).any()
    assert r.groupby(["query_id", "modelo"]).size().eq(10).all()
    assert RANKING.read_bytes()[:3] != b"\xef\xbb\xbf"
    assert filecmp.cmp(RANKING, config.DIR_SALIDA / "ranking.csv", shallow=False)
    crudo = RANKING.read_text(encoding="utf-8").splitlines()[1:]
    assert all(len(f.split(",")[-1].split(".")[1]) == 6 for f in crudo)


def test_filas_con_filtro_dentro_de_la_ventana(r):
    cons = pd.read_csv(config.CONSULTAS_CSV).set_index("query_id")
    con = r[r["variante"] == "con_filtro"]
    for fila in con.itertuples():
        assert cons.loc[fila.query_id, "desde"] <= fila.fecha <= cons.loc[fila.query_id, "hasta"]


@pytest.mark.parametrize("qid,palabras", [("Q3", ("refinería", "pemex")), ("Q1", ("tren maya",)),
                                          ("Q6", ("huachicol",))])
def test_bm25_con_filtro_recupera_el_tema(r, textos, qid, palabras):
    top = r[(r["query_id"] == qid) & (r["modelo"] == "bm25_con_filtro")]["passage_id"]
    assert any(any(p in textos[pid].lower() for p in palabras) for pid in top)


def test_tfidf_y_bm25_no_son_identicos_en_todas_las_consultas(r):
    distintos = 0
    for q, g in r[r["variante"] == "con_filtro"].groupby("query_id"):
        a = g[g["modelo"] == "tfidf_con_filtro"]["passage_id"].tolist()
        b = g[g["modelo"] == "bm25_con_filtro"]["passage_id"].tolist()
        distintos += a != b
    assert distintos > 0


def test_kit_evaluar_ir_corre_con_juicios_sinteticos(r, tmp_path):
    """Juicios sintéticos solo para esta prueba (no son juicios de relevancia reales)."""
    top = r.drop_duplicates(["query_id", "passage_id"])[["query_id", "doc_id", "passage_id"]]
    top = top.assign(relevante=(top["passage_id"].str.len() % 2).astype(int))
    top.to_csv(tmp_path / "juicios.csv", index=False)
    salida = adaptadores_kit.ejecutar_evaluador("ir", tmp_path / "juicios.csv", RANKING, tmp_path)
    assert salida.exists() and len(pd.read_csv(salida)) > 0
